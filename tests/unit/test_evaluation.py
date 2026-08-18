"""Unit tests for the evaluation suite and judge."""

from __future__ import annotations

from backend.evaluation.golden_dataset import GOLDEN_PRS
from backend.evaluation.judge import ReviewJudge
from backend.evaluation.regression_gate import RegressionGate
from backend.models.enums import AgentType, FindingCategory, Severity
from backend.models.findings import Finding


def test_golden_dataset_structure():
    assert len(GOLDEN_PRS) >= 2
    for pr in GOLDEN_PRS:
        assert "diff" in pr
        assert "expected_findings" in pr


def test_review_judge_precision_recall():
    judge = ReviewJudge()
    expected = [
        {
            "agent_type": AgentType.SECURITY,
            "category": FindingCategory.INJECTION,
            "keywords": ["sql", "injection"],
        }
    ]

    actual = [
        Finding(
            agent_type=AgentType.SECURITY,
            severity=Severity.CRITICAL,
            category=FindingCategory.INJECTION,
            title="SQL injection vulnerability",
            description="User input concatenated into query string",
            confidence=0.9,
        )
    ]

    result = judge.evaluate(actual, expected)
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1_score == 1.0
    assert len(result.matched_findings) == 1


def test_regression_gate():
    gate = RegressionGate(min_recall=0.5, min_precision=0.5)
    sample_results = {
        "golden-pr-001": [
            Finding(
                agent_type=AgentType.SECURITY,
                severity=Severity.CRITICAL,
                category=FindingCategory.INJECTION,
                title="SQL Injection found",
                description="Query with format string interpolation",
                confidence=0.95,
            )
        ],
        "golden-pr-002": [
            Finding(
                agent_type=AgentType.QUALITY,
                severity=Severity.HIGH,
                category=FindingCategory.NULL_SAFETY,
                title="Potential Null Pointer Exception",
                description="customer.tier dereferenced without None check",
                confidence=0.88,
            )
        ],
    }

    assert gate.run_check(sample_results) is True
