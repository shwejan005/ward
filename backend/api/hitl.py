"""API router for Human-in-the-Loop review queue and feedback."""

from __future__ import annotations

from typing import Any
import structlog
from fastapi import APIRouter, HTTPException, Query, status

from backend.api.schemas import FindingFeedbackRequest, HITLDecisionRequest
from backend.hitl.queue import HITLQueue
from backend.models.enums import FeedbackType, HITLStatus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/hitl", tags=["hitl"])

# Fallback in-memory HITL store
_MEMORY_HITL_QUEUE: list[dict[str, Any]] = []
_MEMORY_FEEDBACK: list[dict[str, Any]] = []


@router.get("/queue")
async def get_hitl_queue(limit: int = Query(50, ge=1, le=100)) -> list[dict[str, Any]]:
    """List pending reviews awaiting human approval."""
    try:
        queue = HITLQueue()
        pending = await queue.get_pending(limit=limit)
        if pending:
            return pending
    except Exception as e:
        logger.debug("hitl.db_unavailable_using_memory", error=str(e))

    return [item for item in _MEMORY_HITL_QUEUE if item.get("status") == HITLStatus.PENDING][:limit]


@router.post("/{hitl_id}/decide")
async def decide_hitl_review(hitl_id: str, payload: HITLDecisionRequest) -> dict[str, str]:
    """Approve, reject, or modify an agent review from the human queue."""
    decision = payload.decision.lower()
    if decision not in ("approve", "reject", "modify"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be 'approve', 'reject', or 'modify'",
        )

    try:
        queue = HITLQueue()
        await queue.decide(hitl_id, decision, notes=payload.notes)
    except Exception as e:
        logger.debug("hitl.db_unavailable_updating_memory", error=str(e))
        for item in _MEMORY_HITL_QUEUE:
            if item.get("id") == hitl_id:
                item["status"] = HITLStatus.APPROVED if decision == "approve" else HITLStatus.REJECTED
                item["decision"] = decision
                item["decision_notes"] = payload.notes
                break

    logger.info("api.hitl_decided", hitl_id=hitl_id, decision=decision)
    return {"status": "success", "hitl_id": hitl_id, "decision": decision}


@router.post("/feedback")
async def submit_finding_feedback(payload: FindingFeedbackRequest) -> dict[str, str]:
    """Submit developer feedback or dispute against a specific agent finding."""
    feedback_entry = {
        "finding_id": payload.finding_id,
        "feedback_type": payload.feedback_type,
        "comment": payload.comment,
        "submitted_by": payload.submitted_by,
    }
    _MEMORY_FEEDBACK.append(feedback_entry)
    logger.info("api.feedback_received", finding_id=payload.finding_id, feedback=payload.feedback_type)
    return {"status": "recorded", "finding_id": payload.finding_id}
