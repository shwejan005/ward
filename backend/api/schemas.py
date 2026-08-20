"""API request and response schemas for WARD."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from backend.models.enums import (
    AgentType,
    FeedbackType,
    FindingCategory,
    ReviewOutcome,
    ReviewStatus,
    Severity,
)


class TriggerReviewRequest(BaseModel):
    """Payload to trigger a PR review manually."""

    repo: str = Field(..., json_schema_extra={"example": "facebook/react"})
    pr_number: int = Field(..., json_schema_extra={"example": 101})
    head_sha: str = Field(default="head-sha-latest")
    diff: str = Field(..., description="The unified diff to analyze")


class FindingResponse(BaseModel):
    """API response for a single finding."""

    id: str
    agent_type: AgentType
    severity: Severity
    category: FindingCategory
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    title: str
    description: str
    rationale: str | None = None
    suggestion: str | None = None
    confidence: float
    is_duplicate: bool = False
    dedupe_group: str | None = None
    created_at: datetime


class ReviewSummaryResponse(BaseModel):
    """Summary representation of a review."""

    review_id: str
    repo: str
    pr_number: int
    head_sha: str
    status: ReviewStatus
    outcome: ReviewOutcome | None = None
    overall_confidence: float
    total_findings: int
    critical_findings: int
    total_cost_usd: float
    total_tokens: int
    auto_posted: bool
    hitl_required: bool
    hitl_reason: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ReviewDetailResponse(ReviewSummaryResponse):
    """Detailed review response with active findings and agent breakdowns."""

    findings: list[FindingResponse]
    agent_breakdown: dict[str, Any] = Field(default_factory=dict)


class HITLDecisionRequest(BaseModel):
    """Human decision on a flagged review."""

    decision: str = Field(..., description="'approve', 'reject', or 'modify'")
    notes: str | None = None
    modified_findings: list[dict[str, Any]] | None = None


class FindingFeedbackRequest(BaseModel):
    """Developer feedback on a specific finding."""

    finding_id: str
    feedback_type: FeedbackType
    comment: str | None = None
    submitted_by: str = Field(default="developer")


class EconomicsSummaryResponse(BaseModel):
    """Daily cost & token economics breakdown."""

    date: str
    daily_limit_usd: float
    total_cost_usd: float
    agents: list[dict[str, Any]]
