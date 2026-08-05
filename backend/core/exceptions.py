"""Shared exception hierarchy for WARD.

All custom exceptions inherit from WardError so callers can catch
the entire family with a single except clause when needed.
"""

from __future__ import annotations


class WardError(Exception):
    """Base exception for all WARD errors."""


# ── Retriable infrastructure errors ──────────────────────────────────────────

class RetryableError(WardError):
    """An error that is safe to retry (transient network, rate-limit, etc.)."""


class CircuitOpenError(RetryableError):
    """The circuit breaker for a downstream service is open."""

    def __init__(self, service: str) -> None:
        self.service = service
        super().__init__(f"Circuit breaker open for service: {service}")


class TimeoutExceededError(RetryableError):
    """An async operation exceeded its deadline."""

    def __init__(self, operation: str, timeout_ms: int) -> None:
        self.operation = operation
        self.timeout_ms = timeout_ms
        super().__init__(f"{operation} exceeded timeout of {timeout_ms}ms")


# ── Non-retriable domain errors ──────────────────────────────────────────────

class BudgetExhaustedError(WardError):
    """The daily or per-review token/cost budget has been exceeded."""

    def __init__(self, budget_type: str, limit: float, current: float) -> None:
        self.budget_type = budget_type
        self.limit = limit
        self.current = current
        super().__init__(
            f"{budget_type} budget exhausted: ${current:.4f} / ${limit:.4f}"
        )


class IdempotencyConflictError(WardError):
    """A duplicate delivery was detected via the idempotency key."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Duplicate delivery detected: {key}")


class WebhookValidationError(WardError):
    """The webhook payload failed HMAC signature verification."""


class ReviewNotFoundError(WardError):
    """The requested review does not exist."""

    def __init__(self, review_id: str) -> None:
        self.review_id = review_id
        super().__init__(f"Review not found: {review_id}")


class OrchestrationError(WardError):
    """A failure within the LangGraph orchestration pipeline."""


class SpecialistError(WardError):
    """A specialist agent failed to produce valid findings."""

    def __init__(self, agent_type: str, reason: str) -> None:
        self.agent_type = agent_type
        super().__init__(f"Specialist '{agent_type}' failed: {reason}")


class RetrievalError(WardError):
    """The RAG retrieval layer failed to fetch context."""


class GitHubAPIError(WardError):
    """A GitHub REST API call failed after retries."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"GitHub API error {status_code}: {message}")
