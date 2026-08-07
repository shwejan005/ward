"""Redis-backed idempotency guard (L8).

Uses X-GitHub-Delivery UUIDs as idempotency keys in Redis with a 24-hour
TTL. Prevents duplicate webhook deliveries from triggering duplicate reviews.
"""

from __future__ import annotations

import redis.asyncio as redis

from backend.core.exceptions import IdempotencyConflictError
from backend.settings import settings

# 24 hours — long enough that GitHub won't retry a delivery after this
_TTL_SECONDS = 86400
_KEY_PREFIX = "ward:idempotency:"


class IdempotencyGuard:
    """Check-and-mark idempotency using Redis SET NX."""

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self._redis = redis_client

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def check_and_mark(self, key: str) -> None:
        """Mark a delivery key as seen. Raises if already seen.

        Args:
            key: The idempotency key (typically X-GitHub-Delivery UUID).

        Raises:
            IdempotencyConflictError: If this key was already processed.
        """
        r = await self._get_redis()
        full_key = f"{_KEY_PREFIX}{key}"

        # SET NX returns True only if the key did not exist
        was_set = await r.set(full_key, "1", nx=True, ex=_TTL_SECONDS)

        if not was_set:
            raise IdempotencyConflictError(key)

    async def is_seen(self, key: str) -> bool:
        """Check if a delivery key has been processed without marking it."""
        r = await self._get_redis()
        return bool(await r.exists(f"{_KEY_PREFIX}{key}"))
