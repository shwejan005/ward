"""Unit tests for webhook validation and parsing."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from backend.core.exceptions import WebhookValidationError
from backend.webhook_receiver.parser import parse_webhook_payload
from backend.webhook_receiver.validator import verify_github_signature


class TestWebhookValidator:
    def _sign(self, payload: bytes, secret: str = "test-secret") -> str:
        return "sha256=" + hmac.new(
            secret.encode(), payload, hashlib.sha256,
        ).hexdigest()

    def test_valid_signature(self, monkeypatch):
        monkeypatch.setattr(
            "backend.webhook_receiver.validator.settings.github_webhook_secret",
            "test-secret",
        )
        payload = b'{"action": "opened"}'
        sig = self._sign(payload, "test-secret")
        # Should not raise
        verify_github_signature(payload, sig)

    def test_invalid_signature(self, monkeypatch):
        monkeypatch.setattr(
            "backend.webhook_receiver.validator.settings.github_webhook_secret",
            "test-secret",
        )
        payload = b'{"action": "opened"}'
        with pytest.raises(WebhookValidationError, match="verification failed"):
            verify_github_signature(payload, "sha256=invalid")

    def test_missing_signature(self, monkeypatch):
        monkeypatch.setattr(
            "backend.webhook_receiver.validator.settings.github_webhook_secret",
            "test-secret",
        )
        with pytest.raises(WebhookValidationError, match="Missing"):
            verify_github_signature(b"body", "")

    def test_wrong_format(self, monkeypatch):
        monkeypatch.setattr(
            "backend.webhook_receiver.validator.settings.github_webhook_secret",
            "test-secret",
        )
        with pytest.raises(WebhookValidationError, match="Invalid signature format"):
            verify_github_signature(b"body", "md5=abc")


class TestWebhookParser:
    def _make_payload(self, action: str = "opened") -> dict:
        return {
            "action": action,
            "number": 42,
            "pull_request": {
                "number": 42,
                "title": "Add feature X",
                "state": "open",
                "user": {"login": "dev1", "id": 1},
                "head": {"sha": "abc123", "ref": "feature-x"},
                "base": {"sha": "def456", "ref": "main"},
            },
            "repository": {"full_name": "org/repo"},
            "sender": {"login": "dev1", "id": 1},
        }

    def test_parse_opened_event(self):
        data = self._make_payload("opened")
        body = json.dumps(data).encode()
        event = parse_webhook_payload(body, "delivery-123")

        assert event.action == "opened"
        assert event.pr_number == 42
        assert event.head_sha == "abc123"
        assert event.repo_full_name == "org/repo"
        assert event.delivery_id == "delivery-123"
        assert event.is_reviewable is True

    def test_closed_is_not_reviewable(self):
        data = self._make_payload("closed")
        body = json.dumps(data).encode()
        event = parse_webhook_payload(body, "delivery-456")
        assert event.is_reviewable is False

    def test_synchronize_is_reviewable(self):
        data = self._make_payload("synchronize")
        body = json.dumps(data).encode()
        event = parse_webhook_payload(body, "delivery-789")
        assert event.is_reviewable is True
