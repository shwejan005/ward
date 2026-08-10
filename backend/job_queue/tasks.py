"""ARQ job queue tasks.

Defines the review task that the ARQ worker consumes, and the enqueue
helper called by the webhook ingress.
"""

from __future__ import annotations

import structlog
from arq import create_pool
from arq.connections import RedisSettings

from backend.settings import settings

logger = structlog.get_logger(__name__)


def _redis_settings() -> RedisSettings:
    """Parse the Redis URL into ARQ RedisSettings."""
    # arq uses its own RedisSettings, not a URL string
    from urllib.parse import urlparse

    parsed = urlparse(settings.redis_url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "0"),
        password=parsed.password,
    )


async def enqueue_review(
    repo: str,
    pr_number: int,
    head_sha: str,
    delivery_id: str,
) -> None:
    """Enqueue a PR review job to the ARQ queue.

    Called by the webhook ingress after validation + idempotency check.
    """
    pool = await create_pool(_redis_settings())
    try:
        job = await pool.enqueue_job(
            "review_pull_request",
            repo=repo,
            pr_number=pr_number,
            head_sha=head_sha,
            delivery_id=delivery_id,
        )
        logger.info(
            "job.enqueued",
            job_id=job.job_id if job else "unknown",
            repo=repo,
            pr_number=pr_number,
        )
    finally:
        await pool.close()


async def review_pull_request(
    ctx: dict,
    *,
    repo: str,
    pr_number: int,
    head_sha: str,
    delivery_id: str,
) -> dict:
    """The main review task consumed by the ARQ worker.

    Orchestrates the full review pipeline:
    1. Fetch the diff from GitHub
    2. Run the LangGraph orchestrator (fan-out to 4 specialists)
    3. Aggregate, apply HITL gate
    4. Post to GitHub or route to human queue
    """
    logger.info(
        "review.started",
        repo=repo,
        pr_number=pr_number,
        head_sha=head_sha,
    )

    try:
        # Import here to avoid circular deps at module load time
        from backend.integrations.github_client import GitHubClient
        from backend.orchestrator.langgraph_engine import LangGraphEngine

        # 1. Fetch the diff
        github = GitHubClient()
        diff = await github.get_pull_request_diff(repo, pr_number)

        # 2. Run the orchestrator
        engine = LangGraphEngine()
        review = await engine.start_review(
            repo=repo,
            pr_number=pr_number,
            head_sha=head_sha,
            diff=diff,
        )

        logger.info(
            "review.completed",
            repo=repo,
            pr_number=pr_number,
            outcome=review.outcome,
            findings_count=len(review.active_findings),
            cost_usd=review.total_cost_usd,
        )

        return {
            "review_id": review.review_id,
            "outcome": review.outcome,
            "findings_count": len(review.active_findings),
            "auto_posted": review.auto_posted,
        }

    except Exception as e:
        logger.error(
            "review.failed",
            repo=repo,
            pr_number=pr_number,
            error=str(e),
            exc_info=True,
        )
        raise
