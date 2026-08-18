"""Unit tests for the REST API routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ward"


def test_list_reviews_empty_or_populated():
    response = client.get("/api/reviews")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_hitl_queue_endpoint():
    response = client.get("/api/hitl/queue")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_economics_summary_endpoint():
    response = client.get("/api/economics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_cost_usd" in data
    assert "agents" in data
    assert len(data["agents"]) > 0


def test_traces_endpoint():
    response = client.get("/api/economics/traces")
    assert response.status_code == 200
    traces = response.json()
    assert isinstance(traces, list)
    assert len(traces) > 0
