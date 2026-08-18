"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from backend.api.economics import router as economics_router
from backend.api.hitl import router as hitl_router
from backend.api.reviews import router as reviews_router
from backend.webhook_receiver.router import router as webhook_router

from backend.security.rate_limiter import RateLimitMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    logger.info("ward.starting", version="0.1.0")
    yield
    logger.info("ward.shutdown")


app = FastAPI(
    title="WARD — Autonomous PR Review Agent",
    description="Multi-agent PR review with grounded specialist reasoners",
    version="0.1.0",
    lifespan=lifespan,
)

# Attach Rate Limiting and Payload Protection Middleware
app.add_middleware(RateLimitMiddleware, max_requests_per_minute=300)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(webhook_router)
app.include_router(reviews_router)
app.include_router(hitl_router)
app.include_router(economics_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "ward", "version": "0.1.0"}
