"""HMAC-SHA256 webhook signature validator (L2, L8 §3.1).

Verifies the X-Hub-Signature-256 header against the payload body using
the configured GITHUB_WEBHOOK_SECRET. Rejects forgeries before any work.
"""

from __future__ import annotations

import hashlib
import hmac

from backend.core.exceptions import WebhookValidationError
from backend.settings import settings


def verify_github_signature(payload_body: bytes, signature_header: str) -> None:
    """Verify the GitHub webhook HMAC-SHA256 signature.

    Args:
        payload_body: Raw request body bytes.
        signature_header: Value of the X-Hub-Signature-256 header.

    Raises:
        WebhookValidationError: If the signature is missing or invalid.
    """
    if not signature_header:
        raise WebhookValidationError("Missing X-Hub-Signature-256 header")

    if not signature_header.startswith("sha256="):
        raise WebhookValidationError("Invalid signature format: must start with 'sha256='")

    expected_signature = "sha256=" + hmac.new(
        key=settings.github_webhook_secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        raise WebhookValidationError("Signature verification failed")
