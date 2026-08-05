"""Domain enumerations for WARD.

Every enum here maps directly to a TEXT column in the database schema.
Using StrEnum so values serialize as plain strings in JSON / SQL.
"""

from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Backport of StrEnum for Python < 3.11."""
        pass


class AgentType(StrEnum):
    """The four specialist concerns from L1, plus system-level agents."""

    SECURITY = "security"
    QUALITY = "quality"
    TESTS = "tests"
    DOCS = "docs"
    AGGREGATOR = "aggregator"
    ORCHESTRATOR = "orchestrator"


class Severity(StrEnum):
    """Finding severity levels, CRITICAL → INFO."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(StrEnum):
    """Finding categories used by specialist agents."""

    # Security
    INJECTION = "injection"
    AUTH_BYPASS = "auth_bypass"
    SECRETS_EXPOSURE = "secrets_exposure"
    UNSAFE_DESERIALIZATION = "unsafe_deserialization"
    XSS = "xss"
    SSRF = "ssrf"

    # Quality
    LOGIC_ERROR = "logic_error"
    NULL_SAFETY = "null_safety"
    RACE_CONDITION = "race_condition"
    CODE_SMELL = "code_smell"
    COMPLEXITY = "complexity"
    ERROR_HANDLING = "error_handling"

    # Tests
    MISSING_TEST = "missing_test"
    UNTESTED_EDGE = "untested_edge"
    BRITTLE_ASSERTION = "brittle_assertion"
    COVERAGE_GAP = "coverage_gap"

    # Docs
    MISSING_DOCSTRING = "missing_docstring"
    OUTDATED_COMMENT = "outdated_comment"
    UNDOCUMENTED_API = "undocumented_api"
    MISLEADING_DOCS = "misleading_docs"

    # General
    OTHER = "other"


class ReviewStatus(StrEnum):
    """Review lifecycle status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewOutcome(StrEnum):
    """Final review decision."""

    APPROVED = "approved"
    REQUEST_CHANGES = "request_changes"
    CRITICAL_BLOCK = "critical_block"
    ESCALATED = "escalated"


class EventType(StrEnum):
    """Event types for the agent_events hypertable."""

    SPAN_START = "span.start"
    SPAN_END = "span.end"
    LLM_CALL = "llm.call"
    TOOL_CALL = "tool.call"
    DECISION = "decision"
    ESCALATION = "escalation"
    ERROR = "error"


class HITLStatus(StrEnum):
    """HITL review queue status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class FeedbackType(StrEnum):
    """Developer feedback on a finding."""

    AGREE = "agree"
    DISAGREE = "disagree"
    DISPUTE = "dispute"
    FALSE_POSITIVE = "false_positive"
