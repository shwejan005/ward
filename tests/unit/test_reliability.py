"""Unit tests for reliability mechanisms."""

from __future__ import annotations

import asyncio

import pytest

from backend.core.exceptions import CircuitOpenError
from backend.reliability.circuit_breaker import CircuitBreaker, CircuitState
from backend.reliability.timeout import with_timeout
from backend.core.exceptions import TimeoutExceededError


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_starts_closed(self):
        cb = CircuitBreaker("test-service", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self):
        cb = CircuitBreaker("test-service", failure_threshold=2)

        async def failing():
            raise ValueError("boom")

        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(failing)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_rejects_when_open(self):
        cb = CircuitBreaker("test-service", failure_threshold=1)

        async def failing():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            await cb.call(failing)

        with pytest.raises(CircuitOpenError):
            await cb.call(failing)

    @pytest.mark.asyncio
    async def test_success_resets(self):
        cb = CircuitBreaker("test-service", failure_threshold=3)

        async def failing():
            raise ValueError("boom")

        async def succeeding():
            return "ok"

        # One failure
        with pytest.raises(ValueError):
            await cb.call(failing)

        # Success resets
        result = await cb.call(succeeding)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED


class TestTimeout:
    @pytest.mark.asyncio
    async def test_succeeds_within_timeout(self):
        @with_timeout(1000, "test_op")
        async def fast():
            return 42

        assert await fast() == 42

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self):
        @with_timeout(50, "slow_op")
        async def slow():
            await asyncio.sleep(1.0)
            return 42

        with pytest.raises(TimeoutExceededError, match="slow_op"):
            await slow()
