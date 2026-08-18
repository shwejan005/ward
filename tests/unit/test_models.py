"""Unit tests for domain models."""

from __future__ import annotations

from backend.models.enums import AgentType, Severity, FindingCategory, ReviewOutcome
from backend.models.findings import Finding
from backend.models.review import AggregatedReview, ReviewResult


class TestFindingModel:
    def test_create_finding(self):
        finding = Finding(
            agent_type=AgentType.SECURITY,
            severity=Severity.HIGH,
            category=FindingCategory.INJECTION,
            file_path="src/api/handler.py",
            line_start=42,
            title="SQL Injection in user query",
            description="User input is directly interpolated into SQL query.",
            rationale="The f-string concatenation bypasses parameterized queries.",
            suggestion="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
            confidence=0.92,
        )
        assert finding.severity == Severity.HIGH
        assert finding.confidence == 0.92
        assert finding.is_duplicate is False
        assert finding.id  # UUID is auto-generated

    def test_finding_defaults(self):
        finding = Finding(
            agent_type=AgentType.QUALITY,
            severity=Severity.MEDIUM,
            category=FindingCategory.CODE_SMELL,
            title="Complex function",
            description="Function exceeds 50 lines.",
        )
        assert finding.confidence == 0.5
        assert finding.file_path is None
        assert finding.is_duplicate is False


class TestAggregatedReview:
    def test_has_critical_findings(self):
        review = AggregatedReview(
            repo="org/repo",
            pr_number=123,
            head_sha="abc123",
            findings=[
                Finding(
                    agent_type=AgentType.SECURITY,
                    severity=Severity.CRITICAL,
                    category=FindingCategory.INJECTION,
                    title="Critical vuln",
                    description="Very bad",
                    confidence=0.95,
                ),
            ],
        )
        assert review.has_critical_findings is True

    def test_active_findings_excludes_duplicates(self):
        dup = Finding(
            agent_type=AgentType.QUALITY,
            severity=Severity.LOW,
            category=FindingCategory.CODE_SMELL,
            title="Dup",
            description="Duplicate",
            is_duplicate=True,
        )
        active = Finding(
            agent_type=AgentType.QUALITY,
            severity=Severity.MEDIUM,
            category=FindingCategory.LOGIC_ERROR,
            title="Real",
            description="Real finding",
        )
        review = AggregatedReview(
            repo="org/repo",
            pr_number=1,
            head_sha="sha",
            findings=[dup, active],
        )
        assert len(review.active_findings) == 1
        assert review.active_findings[0].title == "Real"

    def test_findings_by_agent(self):
        review = AggregatedReview(
            repo="org/repo",
            pr_number=1,
            head_sha="sha",
            findings=[
                Finding(agent_type=AgentType.SECURITY, severity=Severity.HIGH, category=FindingCategory.XSS, title="XSS", description="d", confidence=0.8),
                Finding(agent_type=AgentType.QUALITY, severity=Severity.MEDIUM, category=FindingCategory.CODE_SMELL, title="Smell", description="d", confidence=0.6),
                Finding(agent_type=AgentType.SECURITY, severity=Severity.LOW, category=FindingCategory.SECRETS_EXPOSURE, title="Secret", description="d", confidence=0.4),
            ],
        )
        by_agent = review.findings_by_agent
        assert len(by_agent[AgentType.SECURITY]) == 2
        assert len(by_agent[AgentType.QUALITY]) == 1


class TestEnums:
    def test_agent_type_values(self):
        assert AgentType.SECURITY == "security"
        assert AgentType.ORCHESTRATOR == "orchestrator"

    def test_severity_ordering(self):
        severities = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
        assert len(severities) == 5

    def test_review_outcome_values(self):
        assert ReviewOutcome.APPROVED == "approved"
        assert ReviewOutcome.CRITICAL_BLOCK == "critical_block"
