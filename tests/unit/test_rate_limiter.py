"""Unit tests for RateLimitMiddleware."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.security.rate_limiter import RateLimitMiddleware

test_app = FastAPI()
test_app.add_middleware(RateLimitMiddleware, max_requests_per_minute=3, max_payload_bytes=100)


@test_app.get("/ping")
def ping():
    return {"message": "pong"}


@test_app.post("/upload")
def upload(body: dict):
    return {"status": "received"}


def test_rate_limiter_allows_under_limit():
    client = TestClient(test_app)
    resp = client.get("/ping")
    assert resp.status_code == 200


def test_rate_limiter_blocks_over_limit():
    client = TestClient(test_app)
    # Fire requests up to the limit
    client.get("/ping")
    client.get("/ping")
    client.get("/ping")
    # 4th should get 429
    resp = client.get("/ping")
    assert resp.status_code == 429
    assert "Too Many Requests" in resp.text
