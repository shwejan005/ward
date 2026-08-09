"""Webhook ingress router (§3.1).

The three-step ingress contract:
1. Verify HMAC-SHA256 signature → reject forgeries
2. Check idempotency key → drop duplicate deliveries
3. Enqueue job to Redis/ARQ → return 200 immediately

GitHub expects a fast acknowledgment. Heavy work happens in the ARQ worker.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, Request, Response

from backend.core.exceptions import IdempotencyConflictError, WebhookValidationError
from backend.reliability.idempotency import IdempotencyGuard
from backend.webhook_receiver.parser import parse_webhook_payload
from backend.webhook_receiver.validator import verify_github_signature

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["webhook"])


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str = Header(""),
    x_github_delivery: str = Header(""),
    x_github_event: str = Header(""),
) -> Response:
    """GitHub webhook endpoint.

    Validates, deduplicates, and enqueues — never processes inline.
    """
    body = await request.body()

    # Step 1: Verify signature
    try:
        verify_github_signature(body, x_hub_signature_256)
    except WebhookValidationError as e:
        logger.warning("webhook.signature_invalid", error=str(e))
        return Response(status_code=401, content="Signature verification failed")

    # Only process pull_request events
    if x_github_event != "pull_request":
        logger.debug("webhook.ignored_event", event_type=x_github_event)
        return Response(status_code=200, content="Event type ignored")

    # Step 2: Parse and check reviewability
    event = parse_webhook_payload(body, delivery_id=x_github_delivery)

    if not event.is_reviewable:
        logger.debug("webhook.non_reviewable_action", action=event.action)
        return Response(status_code=200, content="Action not reviewable")

    # Step 3: Idempotency check
    idempotency = IdempotencyGuard()
    try:
        await idempotency.check_and_mark(x_github_delivery)
    except IdempotencyConflictError:
        logger.info("webhook.duplicate_delivery", delivery_id=x_github_delivery)
        return Response(status_code=200, content="Duplicate delivery acknowledged")

    # Step 4: Enqueue to ARQ (lazy import to avoid circular deps at module load)
    from backend.job_queue.tasks import enqueue_review

    await enqueue_review(
        repo=event.repo_full_name,
        pr_number=event.pr_number,
        head_sha=event.head_sha,
        delivery_id=x_github_delivery,
    )

    logger.info(
        "webhook.enqueued",
        repo=event.repo_full_name,
        pr_number=event.pr_number,
        head_sha=event.head_sha,
        delivery_id=x_github_delivery,
    )
    return Response(status_code=200, content="Review enqueued")
