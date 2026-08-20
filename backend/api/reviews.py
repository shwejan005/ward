"""API router for PR review triggers and queries."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import structlog
from fastapi import APIRouter, HTTPException, Query, status

from backend.api.schemas import (
    FindingResponse,
    ReviewDetailResponse,
    ReviewSummaryResponse,
    TriggerReviewRequest,
)
from backend.models.enums import ReviewStatus, Severity
from backend.models.review import AggregatedReview
from backend.orchestrator.langgraph_engine import LangGraphEngine

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

# In-memory store for fast retrieval / demo resilience if database is disconnected
_REVIEWS_STORE: dict[str, AggregatedReview] = {}


@router.post("/trigger", response_model=ReviewDetailResponse, status_code=status.HTTP_201_CREATED)
async def trigger_review(payload: TriggerReviewRequest) -> ReviewDetailResponse:
    """Manually trigger an asynchronous or synchronous PR review analysis."""
    review_id = str(uuid.uuid4())
    logger.info(
        "api.review_triggered",
        repo=payload.repo,
        pr=payload.pr_number,
        review_id=review_id,
    )

    engine = LangGraphEngine()
    review = await engine.start_review(
        repo=payload.repo,
        pr_number=payload.pr_number,
        head_sha=payload.head_sha,
        diff=payload.diff,
        review_id=review_id,
    )

    _REVIEWS_STORE[review.review_id] = review

    return _to_detail_response(review)


@router.get("", response_model=list[ReviewSummaryResponse])
async def list_reviews(
    repo: str | None = Query(None, description="Filter by repository"),
    limit: int = Query(20, ge=1, le=100),
) -> list[ReviewSummaryResponse]:
    """List recent PR reviews."""
    reviews = list(_REVIEWS_STORE.values())
    if repo:
        reviews = [r for r in reviews if r.repo.lower() == repo.lower()]
    
    # Sort newest first
    reviews.sort(key=lambda r: r.created_at, reverse=True)
    return [_to_summary_response(r) for r in reviews[:limit]]


@router.get("/{review_id}", response_model=ReviewDetailResponse)
async def get_review(review_id: str) -> ReviewDetailResponse:
    """Retrieve full details for a specific review."""
    review = _REVIEWS_STORE.get(review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review '{review_id}' not found.",
        )
    return _to_detail_response(review)


def _to_summary_response(r: AggregatedReview) -> ReviewSummaryResponse:
    active = r.active_findings
    criticals = sum(1 for f in active if f.severity == Severity.CRITICAL)
    return ReviewSummaryResponse(
        review_id=r.review_id,
        repo=r.repo,
        pr_number=r.pr_number,
        head_sha=r.head_sha,
        status=r.status,
        outcome=r.outcome,
        overall_confidence=round(r.overall_confidence, 3),
        total_findings=len(active),
        critical_findings=criticals,
        total_cost_usd=round(r.total_cost_usd, 5),
        total_tokens=r.total_tokens,
        auto_posted=r.auto_posted,
        hitl_required=r.hitl_required,
        hitl_reason=r.hitl_reason,
        created_at=r.created_at,
        completed_at=r.completed_at,
    )


def _to_detail_response(r: AggregatedReview) -> ReviewDetailResponse:
    summary = _to_summary_response(r)
    findings_resp = [
        FindingResponse(
            id=f.id,
            agent_type=f.agent_type,
            severity=f.severity,
            category=f.category,
            file_path=f.file_path,
            line_start=f.line_start,
            line_end=f.line_end,
            title=f.title,
            description=f.description,
            rationale=f.rationale,
            suggestion=f.suggestion,
            confidence=round(f.confidence, 3),
            is_duplicate=f.is_duplicate,
            dedupe_group=f.dedupe_group,
            created_at=f.created_at,
        )
        for f in r.findings
    ]

    agent_breakdown = {
        res.agent_type: {
            "findings_count": len(res.findings),
            "cost_usd": res.cost_usd,
            "tokens_used": res.tokens_used,
            "latency_ms": res.latency_ms,
            "model": res.model_used,
        }
        for res in r.agent_results
    }

    return ReviewDetailResponse(
        **summary.model_dump(),
        findings=findings_resp,
        agent_breakdown=agent_breakdown,
    )
