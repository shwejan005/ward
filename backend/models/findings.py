"""The Finding model — the unit that flows through the entire system (L2).

Every specialist agent produces a list of Findings. Each Finding carries
agent_type, severity, category, file/line, confidence, and rationale — the
shape that was defined at L2 Map the Mess and flows through the aggregator,
the HITL gate, and into the database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from backend.models.enums import AgentType, FindingCategory, Severity


class Finding(BaseModel):
    """A single review finding raised by a specialist agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Which specialist raised this
    agent_type: AgentType

    # Severity and categorization
    severity: Severity
    category: FindingCategory

    # Location in the codebase
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None

    # The finding itself
    title: str
    description: str
    rationale: str | None = None
    suggestion: str | None = None

    # Confidence drives the HITL gate (L7)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)

    # Deduplication (set by aggregator)
    is_duplicate: bool = False
    dedupe_group: str | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"frozen": False}
