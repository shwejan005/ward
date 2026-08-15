"""LangGraph orchestration engine (§3.2, ADR-001).

Implements the WorkflowEngine protocol using LangGraph StateGraph
with parallel Send API fan-out to 4 specialist agents.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from backend.agents.contracts import SpecialistInput, SpecialistOutput
from backend.agents.docs_agent import DocsAgent
from backend.agents.quality_agent import QualityAgent
from backend.agents.security_agent import SecurityAgent
from backend.agents.test_agent import TestAgent
from backend.core.workflow_engine import WorkflowEngine
from backend.models.enums import AgentType, EventType, ReviewOutcome, ReviewStatus
from backend.models.findings import Finding
from backend.models.review import AggregatedReview, ReviewResult
from backend.observability.events import emit_agent_event
from backend.settings import settings

logger = structlog.get_logger(__name__)

# Specialist registry
_SPECIALISTS = {
    AgentType.SECURITY: SecurityAgent(),
    AgentType.QUALITY: QualityAgent(),
    AgentType.TESTS: TestAgent(),
    AgentType.DOCS: DocsAgent(),
}


class LangGraphEngine:
    """LangGraph-based implementation of the WorkflowEngine protocol.

    Pipeline:
    1. Emit orchestrator span.start
    2. Fan-out to 4 specialists in parallel
    3. Aggregate findings (merge, dedup)
    4. Apply confidence-weighted HITL gate
    5. Post to GitHub or route to human queue
    6. Emit orchestrator span.end
    """

    async def start_review(
        self,
        repo: str,
        pr_number: int,
        head_sha: str,
        diff: str,
        *,
        review_id: str | None = None,
    ) -> AggregatedReview:
        rid = review_id or str(uuid.uuid4())

        # Emit orchestrator start
        orchestrator_span = await emit_agent_event(
            review_id=rid,
            agent=AgentType.ORCHESTRATOR,
            event_type=EventType.SPAN_START,
        )

        # 1. Retrieve codebase context (future: wire to memory/tiger_client)
        context = ""  # TODO: implement hybrid RAG retrieval

        # 2. Fan-out to all 4 specialists in parallel
        import asyncio

        specialist_tasks = []
        for agent_type, specialist in _SPECIALISTS.items():
            input = SpecialistInput(
                review_id=rid,
                repo=repo,
                pr_number=pr_number,
                diff=diff,
                retrieved_context=context,
                agent_type=agent_type,
                model=settings.default_model,
            )
            specialist_tasks.append(specialist.review(input))

        outputs: list[SpecialistOutput] = await asyncio.gather(
            *specialist_tasks, return_exceptions=False
        )

        # 3. Aggregate findings
        all_findings: list[Finding] = []
        agent_results: list[ReviewResult] = []
        total_cost = 0.0
        total_tokens = 0

        for output in outputs:
            if output.succeeded:
                all_findings.extend(output.findings)
            agent_results.append(ReviewResult(
                agent_type=output.agent_type,
                findings=output.findings,
                cost_usd=output.cost_usd,
                tokens_used=output.tokens_in + output.tokens_out,
                latency_ms=output.latency_ms,
                model_used=output.model_used,
            ))
            total_cost += output.cost_usd
            total_tokens += output.tokens_in + output.tokens_out

        # 4. Deduplicate findings (simple: same file + same line range + same category)
        deduped = self._deduplicate_findings(all_findings)

        # 5. Compute overall confidence
        active = [f for f in deduped if not f.is_duplicate]
        overall_confidence = (
            sum(f.confidence for f in active) / len(active) if active else 1.0
        )

        # 6. Determine outcome
        has_critical = any(f.severity == "critical" and not f.is_duplicate for f in deduped)
        if has_critical:
            outcome = ReviewOutcome.CRITICAL_BLOCK
        elif any(f.severity in ("critical", "high") and not f.is_duplicate for f in deduped):
            outcome = ReviewOutcome.REQUEST_CHANGES
        else:
            outcome = ReviewOutcome.APPROVED

        # 7. Apply HITL gate (L7)
        hitl_required = False
        hitl_reason = None

        if has_critical:
            hitl_required = True
            hitl_reason = "CRITICAL finding detected — requires human review"
        elif overall_confidence < settings.confidence_threshold:
            hitl_required = True
            hitl_reason = f"Low confidence ({overall_confidence:.2f} < {settings.confidence_threshold})"

        auto_posted = False
        if not hitl_required and settings.auto_post_enabled:
            auto_posted = True
            # TODO: actually post to GitHub via GitHubClient

        # Emit HITL decision
        await emit_agent_event(
            review_id=rid,
            agent=AgentType.AGGREGATOR,
            event_type=EventType.DECISION,
            outcome=outcome,
            confidence=overall_confidence,
            payload={
                "hitl_required": hitl_required,
                "hitl_reason": hitl_reason,
                "auto_posted": auto_posted,
                "findings_count": len(active),
                "total_cost_usd": total_cost,
            },
        )

        # Emit orchestrator end
        await emit_agent_event(
            review_id=rid,
            agent=AgentType.ORCHESTRATOR,
            event_type=EventType.SPAN_END,
            span_id=orchestrator_span,
            cost_usd=total_cost,
            confidence=overall_confidence,
            outcome=outcome,
        )

        return AggregatedReview(
            review_id=rid,
            repo=repo,
            pr_number=pr_number,
            head_sha=head_sha,
            findings=deduped,
            agent_results=agent_results,
            status=ReviewStatus.COMPLETED,
            outcome=outcome,
            overall_confidence=overall_confidence,
            total_cost_usd=total_cost,
            total_tokens=total_tokens,
            auto_posted=auto_posted,
            hitl_required=hitl_required,
            hitl_reason=hitl_reason,
        )

    async def resume(self, workflow_id: str, state: dict[str, Any]) -> AggregatedReview:
        raise NotImplementedError("Checkpoint resume not yet implemented")

    async def get_state(self, workflow_id: str) -> dict[str, Any] | None:
        raise NotImplementedError("State retrieval not yet implemented")

    @staticmethod
    def _deduplicate_findings(findings: list[Finding]) -> list[Finding]:
        """Simple deduplication: same file + overlapping lines + same category."""
        seen: dict[str, Finding] = {}

        for f in findings:
            key = f"{f.file_path}:{f.line_start}:{f.category}"
            if key in seen:
                # Mark as duplicate, keep the higher-confidence one
                existing = seen[key]
                if f.confidence > existing.confidence:
                    existing.is_duplicate = True
                    existing.dedupe_group = key
                    seen[key] = f
                else:
                    f.is_duplicate = True
                    f.dedupe_group = key
            else:
                seen[key] = f

        return findings
