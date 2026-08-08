"""Async timeout wrapper with dead-letter logging (L8)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import structlog

from backend.core.exceptions import TimeoutExceededError

logger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def with_timeout(timeout_ms: int, operation_name: str = "") -> Callable[[F], F]:
    """Decorator that wraps an async function with an asyncio timeout.

    If the timeout is exceeded, raises TimeoutExceededError and logs
    the event to the dead-letter trail.
    """

    def decorator(func: F) -> F:
        name = operation_name or func.__name__

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_ms / 1000,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "timeout.exceeded",
                    operation=name,
                    timeout_ms=timeout_ms,
                )
                raise TimeoutExceededError(name, timeout_ms)

        return wrapper  # type: ignore[return-value]

    return decorator
