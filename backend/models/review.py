"""Review result models — the output of the aggregation step."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from backend.models.enums import AgentType, ReviewOutcome, ReviewStatus, Severity
from backend.models.findings import Finding


class ReviewResult(BaseModel):
    """Output from a single specialist agent."""

    agent_type: AgentType
    findings: list[Finding] = Field(default_factory=list)
    cost_usd: float = 0.0
    tokens_used: int = 0
    latency_ms: int = 0
    model_used: str | None = None


class AggregatedReview(BaseModel):
    """The merged, deduplicated review from all specialists.

    This is the final output of the orchestrator before the HITL gate
    decides whether to auto-post or route to a human.
    """

    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repo: str
    pr_number: int
    head_sha: str

    # Aggregated findings (deduplicated)
    findings: list[Finding] = Field(default_factory=list)

    # Per-agent results for transparency
    agent_results: list[ReviewResult] = Field(default_factory=list)

    # Overall assessment
    status: ReviewStatus = ReviewStatus.PENDING
    outcome: ReviewOutcome | None = None
    overall_confidence: float = 0.0

    # Cost accounting
    total_cost_usd: float = 0.0
    total_tokens: int = 0

    # HITL gate decision
    auto_posted: bool = False
    hitl_required: bool = False
    hitl_reason: str | None = None

    # GitHub state
    github_review_id: int | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def has_critical_findings(self) -> bool:
        """Check if any non-duplicate finding is CRITICAL severity."""
        return any(
            f.severity == Severity.CRITICAL and not f.is_duplicate
            for f in self.findings
        )

    @property
    def active_findings(self) -> list[Finding]:
        """Return findings that are not marked as duplicates."""
        return [f for f in self.findings if not f.is_duplicate]

    @property
    def findings_by_agent(self) -> dict[AgentType, list[Finding]]:
        """Group active findings by agent_type."""
        result: dict[AgentType, list[Finding]] = {}
        for f in self.active_findings:
            result.setdefault(f.agent_type, []).append(f)
        return result
