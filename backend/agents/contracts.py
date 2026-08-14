"""Specialist agent contracts — typed input/output for the fan-out (L1, §3.4).

Every specialist receives the same SpecialistInput and returns a SpecialistOutput.
The aggregator processes the outputs into a merged AggregatedReview.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.models.enums import AgentType
from backend.models.findings import Finding


class SpecialistInput(BaseModel):
    """Input provided to each specialist agent by the orchestrator."""

    review_id: str
    repo: str
    pr_number: int
    diff: str
    retrieved_context: str = ""  # Relevant codebase context from RAG
    agent_type: AgentType
    model: str = "gpt-4o"


class SpecialistOutput(BaseModel):
    """Output returned by each specialist agent."""

    agent_type: AgentType
    findings: list[Finding] = Field(default_factory=list)
    cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    model_used: str = ""
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None
