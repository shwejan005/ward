"""Job queue package — shared Redis settings for ARQ."""

from __future__ import annotations

from urllib.parse import urlparse

from arq.connections import RedisSettings

from backend.settings import settings


def get_redis_settings() -> RedisSettings:
    """Parse the Redis URL into ARQ RedisSettings."""
    parsed = urlparse(settings.redis_url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "0"),
        password=parsed.password,
    )
