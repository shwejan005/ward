"""Rate limiting and payload size protection middleware for API ingress."""

from __future__ import annotations

import time
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding window rate limiter per client IP."""

    def __init__(self, app, max_requests_per_minute: int = 120, max_payload_bytes: int = 5 * 1024 * 1024) -> None:
        super().__init__(app)
        self.max_requests = max_requests_per_minute
        self.max_payload_bytes = max_payload_bytes
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check payload size from Content-Length header if present
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_payload_bytes:
            logger.warning("security.payload_too_large", size=content_length)
            return Response(status_code=413, content="Payload Too Large (max 5MB)")

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60.0

        # Clean timestamps older than 1 minute
        self._requests[client_ip] = [t for t in self._requests[client_ip] if t > window_start]

        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning("security.rate_limit_exceeded", client_ip=client_ip)
            return Response(
                status_code=429,
                content="Too Many Requests. Please slow down.",
                headers={"Retry-After": "60"},
            )

        self._requests[client_ip].append(now)
        response = await call_next(request)
        return response
