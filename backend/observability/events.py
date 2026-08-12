"""Events spine — emit_agent_event() → agent_events hypertable (L6, §3.6).

Every agent action becomes one append-only row. This single function is the
write side of the events spine. It feeds the trace viewer, audit trail, and
cost ledger from one table.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg
import structlog

from backend.models.enums import EventType
from backend.settings import settings

logger = structlog.get_logger(__name__)

# Module-level connection pool (initialized lazily)
_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool:
    """Get or create the asyncpg connection pool for event writes."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.tiger_database_url,
            min_size=2,
            max_size=10,
        )
    return _pool


async def emit_agent_event(
    review_id: str,
    agent: str,
    event_type: EventType | str,
    *,
    span_id: str | None = None,
    parent_span: str | None = None,
    model: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    cost_usd: float | None = None,
    latency_ms: int | None = None,
    outcome: str | None = None,
    confidence: float | None = None,
    payload: dict[str, Any] | None = None,
) -> str:
    """Write a single event row to the agent_events hypertable.

    Returns the span_id (generated if not provided).
    """
    sid = span_id or str(uuid.uuid4())

    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agent_events (
                    ts, review_id, agent, span_id, parent_span, event_type,
                    model, tokens_in, tokens_out, cost_usd, latency_ms,
                    outcome, confidence, payload
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
                )
                """,
                datetime.now(timezone.utc),
                uuid.UUID(review_id),
                agent,
                uuid.UUID(sid),
                uuid.UUID(parent_span) if parent_span else None,
                str(event_type),
                model,
                tokens_in,
                tokens_out,
                cost_usd,
                latency_ms,
                outcome,
                confidence,
                payload,
            )
    except Exception:
        # Events are best-effort — never crash the pipeline for observability
        logger.warning(
            "events.write_failed",
            review_id=review_id,
            agent=agent,
            event_type=str(event_type),
            exc_info=True,
        )

    return sid
