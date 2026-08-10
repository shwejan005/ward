"""ARQ worker process.

Run with: python -m backend.job_queue.arq_worker
"""

from __future__ import annotations

from arq.connections import RedisSettings

from backend.job_queue.tasks import review_pull_request
from backend.settings import settings


def _redis_settings() -> RedisSettings:
    from urllib.parse import urlparse

    parsed = urlparse(settings.redis_url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "0"),
        password=parsed.password,
    )


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [review_pull_request]
    redis_settings = _redis_settings()
    max_jobs = 10
    job_timeout = 300  # 5 minutes per review
    health_check_interval = 30
