"""Base specialist agent — shared prompt assembly, LLM call, output parsing.

All four specialist agents (security, quality, tests, docs) inherit from
BaseSpecialist and override only the prompt template and agent_type.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

import structlog

from backend.agents.contracts import SpecialistInput, SpecialistOutput
from backend.models.enums import AgentType, EventType
from backend.models.findings import Finding
from backend.observability.events import emit_agent_event
from backend.settings import settings

logger = structlog.get_logger(__name__)


class BaseSpecialist(ABC):
    """Abstract base for all specialist review agents."""

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """The specialist concern this agent handles."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The system prompt for this specialist."""
        ...

    async def review(self, input: SpecialistInput) -> SpecialistOutput:
        """Run the specialist review and return structured findings.

        This method handles:
        1. Emit span.start event
        2. Assemble the prompt with diff + context
        3. Call the LLM for structured output
        4. Parse findings from the response
        5. Emit llm.call and span.end events
        """
        span_id = await emit_agent_event(
            review_id=input.review_id,
            agent=self.agent_type,
            event_type=EventType.SPAN_START,
        )

        start_time = time.monotonic()

        try:
            # Build the user message
            user_message = self._build_user_message(input)

            # Call LLM (lazy import to avoid circular deps)
            from backend.tools.llm_client import call_llm_structured

            response = await call_llm_structured(
                system_prompt=self.system_prompt,
                user_message=user_message,
                model=input.model,
                response_schema=self._findings_schema(),
            )

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            # Parse findings from structured response
            findings = self._parse_findings(response.get("findings", []))

            # Emit LLM call event
            await emit_agent_event(
                review_id=input.review_id,
                agent=self.agent_type,
                event_type=EventType.LLM_CALL,
                span_id=span_id,
                model=response.get("model", input.model),
                tokens_in=response.get("tokens_in", 0),
                tokens_out=response.get("tokens_out", 0),
                cost_usd=response.get("cost_usd", 0.0),
                latency_ms=elapsed_ms,
            )

            output = SpecialistOutput(
                agent_type=self.agent_type,
                findings=findings,
                cost_usd=response.get("cost_usd", 0.0),
                tokens_in=response.get("tokens_in", 0),
                tokens_out=response.get("tokens_out", 0),
                latency_ms=elapsed_ms,
                model_used=response.get("model", input.model),
            )

        except Exception as e:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(
                "specialist.failed",
                agent=self.agent_type,
                review_id=input.review_id,
                error=str(e),
            )
            output = SpecialistOutput(
                agent_type=self.agent_type,
                latency_ms=elapsed_ms,
                error=str(e),
            )

        # Emit span end
        await emit_agent_event(
            review_id=input.review_id,
            agent=self.agent_type,
            event_type=EventType.SPAN_END,
            span_id=span_id,
            latency_ms=output.latency_ms,
            confidence=self._avg_confidence(output.findings),
        )

        return output

    def _build_user_message(self, input: SpecialistInput) -> str:
        """Assemble the user prompt with diff and retrieved context."""
        parts = [f"## Repository: {input.repo}\n## PR #{input.pr_number}\n"]

        if input.retrieved_context:
            parts.append(f"## Retrieved Codebase Context\n{input.retrieved_context}\n")

        parts.append(f"## Diff to Review\n```diff\n{input.diff}\n```")

        return "\n".join(parts)

    def _findings_schema(self) -> dict:
        """JSON schema for structured LLM output."""
        return {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "severity": {"type": "string", "enum": ["critical", "high", "medium", "low", "info"]},
                            "category": {"type": "string"},
                            "file_path": {"type": "string"},
                            "line_start": {"type": "integer"},
                            "line_end": {"type": "integer"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "rationale": {"type": "string"},
                            "suggestion": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                        "required": ["severity", "category", "title", "description", "confidence"],
                    },
                },
            },
            "required": ["findings"],
        }

    def _parse_findings(self, raw_findings: list[dict]) -> list[Finding]:
        """Parse raw LLM output into typed Finding objects."""
        findings = []
        for raw in raw_findings:
            try:
                finding = Finding(
                    agent_type=self.agent_type,
                    severity=raw.get("severity", "medium"),
                    category=raw.get("category", "other"),
                    file_path=raw.get("file_path"),
                    line_start=raw.get("line_start"),
                    line_end=raw.get("line_end"),
                    title=raw["title"],
                    description=raw["description"],
                    rationale=raw.get("rationale"),
                    suggestion=raw.get("suggestion"),
                    confidence=raw.get("confidence", 0.5),
                )
                findings.append(finding)
            except Exception as e:
                logger.warning(
                    "specialist.finding_parse_error",
                    agent=self.agent_type,
                    error=str(e),
                    raw=raw,
                )
        return findings

    @staticmethod
    def _avg_confidence(findings: list[Finding]) -> float | None:
        if not findings:
            return None
        return sum(f.confidence for f in findings) / len(findings)
