"""HITL approval queue and escalation logic (L7, §3.4).

When the HITL gate triggers (low confidence or CRITICAL findings),
the review is inserted into the hitl_reviews table and a human
is notified to approve, reject, or modify the automated review.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
import structlog

from backend.models.enums import HITLStatus
from backend.settings import settings

logger = structlog.get_logger(__name__)


class HITLQueue:
    """HITL approval queue backed by the hitl_reviews table."""

    def __init__(self, pool: asyncpg.Pool | None = None) -> None:
        self._pool = pool

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                settings.tiger_database_url, min_size=1, max_size=5,
            )
        return self._pool

    async def enqueue(
        self,
        review_id: str,
        reason: str,
        *,
        assigned_to: str | None = None,
        ttl_hours: int = 48,
    ) -> str:
        """Add a review to the HITL approval queue.

        Returns the hitl_review ID.
        """
        hitl_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO hitl_reviews (id, review_id, reason, status, assigned_to, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                uuid.UUID(hitl_id),
                uuid.UUID(review_id),
                reason,
                HITLStatus.PENDING,
                assigned_to,
                expires_at,
            )

        logger.info(
            "hitl.enqueued",
            hitl_id=hitl_id,
            review_id=review_id,
            reason=reason,
            assigned_to=assigned_to,
        )
        return hitl_id

    async def decide(
        self,
        hitl_id: str,
        decision: str,
        *,
        notes: str | None = None,
    ) -> None:
        """Record a human decision on a HITL review.

        Args:
            hitl_id: The HITL review ID.
            decision: "approve", "reject", or "modify".
            notes: Optional decision notes from the reviewer.
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE hitl_reviews
                SET status = $2, decision = $3, decision_notes = $4, decided_at = $5
                WHERE id = $1
                """,
                uuid.UUID(hitl_id),
                HITLStatus.APPROVED if decision == "approve" else HITLStatus.REJECTED,
                decision,
                notes,
                datetime.now(timezone.utc),
            )

        logger.info("hitl.decided", hitl_id=hitl_id, decision=decision)

    async def get_pending(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch pending HITL reviews for the dashboard."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT h.id, h.review_id, h.reason, h.status,
                       h.assigned_to, h.created_at, h.expires_at,
                       r.repo, r.pr_number, r.pr_title, r.head_sha
                FROM hitl_reviews h
                JOIN pr_review_records r ON r.id = h.review_id
                WHERE h.status = 'pending'
                  AND (h.expires_at IS NULL OR h.expires_at > now())
                ORDER BY h.created_at ASC
                LIMIT $1
                """,
                limit,
            )
        return [dict(r) for r in rows]

    async def expire_stale(self) -> int:
        """Mark expired HITL reviews as expired. Returns count of expired."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE hitl_reviews
                SET status = 'expired'
                WHERE status = 'pending' AND expires_at < now()
                """,
            )
        count = int(result.split()[-1])  # e.g. "UPDATE 3"
        if count > 0:
            logger.info("hitl.expired_stale", count=count)
        return count
