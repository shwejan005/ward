"""Retry decorator with exponential backoff and jitter (L8)."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import structlog

from backend.core.exceptions import RetryableError

logger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry_async(
    max_retries: int = 3,
    base_delay_ms: int = 500,
    max_delay_ms: int = 30_000,
    retryable_exceptions: tuple[type[Exception], ...] = (RetryableError,),
) -> Callable[[F], F]:
    """Decorator that retries async functions with exponential backoff + jitter.

    Only retries on exceptions in retryable_exceptions. Non-retriable
    exceptions propagate immediately.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            "retry.exhausted",
                            func=func.__name__,
                            attempts=max_retries + 1,
                            error=str(e),
                        )
                        raise

                    # Exponential backoff with full jitter
                    delay_ms = min(base_delay_ms * (2 ** attempt), max_delay_ms)
                    jittered_delay = random.uniform(0, delay_ms)  # noqa: S311

                    logger.warning(
                        "retry.attempt",
                        func=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay_ms=round(jittered_delay),
                        error=str(e),
                    )
                    await asyncio.sleep(jittered_delay / 1000)

            # Should never reach here, but satisfy type checker
            if last_exception:
                raise last_exception

        return wrapper  # type: ignore[return-value]

    return decorator
