"""ARQ worker process.

Run with: python -m backend.job_queue.arq_worker
"""

from __future__ import annotations

from backend.job_queue import get_redis_settings
from backend.job_queue.tasks import review_pull_request


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [review_pull_request]
    redis_settings = get_redis_settings()
    max_jobs = 10
    job_timeout = 300  # 5 minutes per review
    health_check_interval = 30
