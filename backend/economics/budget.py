"""BudgetGuard — pre-call cost gate reading from continuous aggregates (ADR-004).

Reads from the pre-aggregated pr_cost_hourly and agent_health_1m materialized
views. Before each LLM call, BudgetGuard checks the current spend against
the daily budget cap and per-review cap, circuit-breaking on overspend.
"""

from __future__ import annotations

from datetime import datetime, timezone

import asyncpg
import structlog

from backend.core.exceptions import BudgetExhaustedError
from backend.settings import settings

logger = structlog.get_logger(__name__)


class BudgetGuard:
    """Pre-call budget gate that reads continuous aggregates."""

    def __init__(self, pool: asyncpg.Pool | None = None) -> None:
        self._pool = pool

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                settings.tiger_database_url, min_size=1, max_size=5,
            )
        return self._pool

    async def check_daily_budget(self) -> None:
        """Check total spend today against daily budget cap.

        Raises BudgetExhaustedError if the daily limit is exceeded.
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(cost_usd), 0) AS total_cost
                FROM agent_health_1m
                WHERE bucket >= date_trunc('day', now())
                """,
            )

        current = float(row["total_cost"]) if row else 0.0

        if current >= settings.daily_budget_usd:
            raise BudgetExhaustedError(
                "daily", settings.daily_budget_usd, current,
            )

        logger.debug(
            "budget.daily_check",
            current_usd=current,
            limit_usd=settings.daily_budget_usd,
            remaining_usd=settings.daily_budget_usd - current,
        )

    async def check_review_budget(self, review_id: str) -> None:
        """Check total spend for a specific review against per-review cap.

        Raises BudgetExhaustedError if the per-review limit is exceeded.
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(total_cost_usd), 0) AS total_cost
                FROM pr_cost_hourly
                WHERE review_id = $1
                """,
                review_id,
            )

        current = float(row["total_cost"]) if row else 0.0

        if current >= settings.per_review_budget_usd:
            raise BudgetExhaustedError(
                "per_review", settings.per_review_budget_usd, current,
            )

    async def get_daily_summary(self) -> dict:
        """Get daily cost summary for the dashboard."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT agent,
                       SUM(cost_usd) AS cost_usd,
                       SUM(llm_calls) AS llm_calls,
                       SUM(tokens_in) AS tokens_in,
                       SUM(tokens_out) AS tokens_out
                FROM agent_health_1m
                WHERE bucket >= date_trunc('day', now())
                GROUP BY agent
                ORDER BY cost_usd DESC
                """,
            )

        return {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "daily_limit_usd": settings.daily_budget_usd,
            "agents": [dict(r) for r in rows],
            "total_cost_usd": sum(float(r["cost_usd"]) for r in rows),
        }
