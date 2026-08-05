"""Abstract workflow engine protocol (ADR-001 / ADR-002).

The orchestrator module implements this with LangGraph. If we ever swap to
Temporal or another engine, only the implementing module changes — core and
every consumer stay untouched.
"""

from __future__ import annotations

from typing import Any, Protocol

from backend.models.review import AggregatedReview


class WorkflowEngine(Protocol):
    """Abstract interface for the review orchestration engine."""

    async def start_review(
        self,
        repo: str,
        pr_number: int,
        head_sha: str,
        diff: str,
        *,
        review_id: str | None = None,
    ) -> AggregatedReview:
        """Run the full review pipeline: retrieve context → fan-out specialists
        → aggregate → apply HITL gate.

        Returns the aggregated review result (which may be auto-posted or
        routed to the HITL queue depending on confidence).
        """
        ...

    async def resume(self, workflow_id: str, state: dict[str, Any]) -> AggregatedReview:
        """Resume a checkpointed workflow from saved state."""
        ...

    async def get_state(self, workflow_id: str) -> dict[str, Any] | None:
        """Retrieve the current state of a running or completed workflow."""
        ...
