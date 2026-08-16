"""Prompt injection detection guard.

Scans diff content before sending to LLM for common prompt injection patterns.
Logs but does not block — the diff is still reviewed, but with a warning.
"""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)

# Patterns that suggest prompt injection attempts in PR diffs
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"```\s*system\b", re.IGNORECASE),
    re.compile(r"IMPORTANT:\s*do\s+not\s+review", re.IGNORECASE),
    re.compile(r"override\s+the\s+review", re.IGNORECASE),
]


def scan_for_injection(diff: str, *, review_id: str = "") -> list[dict[str, str]]:
    """Scan a diff for potential prompt injection patterns.

    Returns a list of detected patterns with location info.
    Does NOT block — returns warnings for the observability layer.
    """
    detections = []

    for i, line in enumerate(diff.split("\n"), 1):
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(line):
                detection = {
                    "line_number": str(i),
                    "pattern": pattern.pattern,
                    "content": line[:200],
                }
                detections.append(detection)
                logger.warning(
                    "injection.detected",
                    review_id=review_id,
                    line=i,
                    pattern=pattern.pattern,
                )

    return detections


def mask_secrets_in_diff(diff: str) -> str:
    """Redact potential secrets from a diff before sending to the LLM.

    Replaces patterns that look like API keys, tokens, passwords, etc.
    with [REDACTED] to prevent leaking through the LLM's output.
    """
    # Common secret patterns
    secret_patterns = [
        (re.compile(r'(sk-[a-zA-Z0-9]{20,})'), '[REDACTED_API_KEY]'),
        (re.compile(r'(ghp_[a-zA-Z0-9]{36,})'), '[REDACTED_GH_TOKEN]'),
        (re.compile(r'(AKIA[0-9A-Z]{16})'), '[REDACTED_AWS_KEY]'),
        (re.compile(r'(password\s*[=:]\s*["\'][^"\']{8,}["\'])'), '[REDACTED_PASSWORD]'),
        (re.compile(r'(bearer\s+[a-zA-Z0-9._-]{20,})', re.IGNORECASE), '[REDACTED_BEARER]'),
    ]

    masked = diff
    for pattern, replacement in secret_patterns:
        masked = pattern.sub(replacement, masked)

    return masked
