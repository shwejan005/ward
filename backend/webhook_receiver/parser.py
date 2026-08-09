"""Webhook payload parser.

Transforms raw GitHub JSON into typed WebhookEvent models, filtering
for reviewable actions only.
"""

from __future__ import annotations

import json

from backend.models.webhook import WebhookEvent


def parse_webhook_payload(body: bytes, delivery_id: str) -> WebhookEvent:
    """Parse raw webhook body into a typed WebhookEvent.

    Args:
        body: Raw JSON payload bytes.
        delivery_id: X-GitHub-Delivery UUID from the request header.

    Returns:
        A validated WebhookEvent instance with the delivery_id injected.
    """
    data = json.loads(body)
    event = WebhookEvent.model_validate(data)
    event.delivery_id = delivery_id
    return event
