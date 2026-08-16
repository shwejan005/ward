"""Evaluation metrics & judge comparing agent findings against golden ground truth."""

from __future__ import annotations

from typing import Any
from backend.models.findings import Finding


class EvaluationResult:
    def __init__(
        self,
        precision: float,
        recall: float,
        f1_score: float,
        matched_findings: list[dict[str, Any]],
        unmatched_expected: list[dict[str, Any]],
        spurious_findings: list[Finding],
    ) -> None:
        self.precision = precision
        self.recall = recall
        self.f1_score = f1_score
        self.matched_findings = matched_findings
        self.unmatched_expected = unmatched_expected
        self.spurious_findings = spurious_findings


class ReviewJudge:
    """Computes Precision, Recall, and F1 by matching findings with ground truth expectations."""

    def evaluate(
        self,
        actual_findings: list[Finding],
        expected_findings: list[dict[str, Any]],
    ) -> EvaluationResult:
        matched: list[dict[str, Any]] = []
        unmatched_exp = list(expected_findings)
        spurious = []

        for actual in actual_findings:
            if actual.is_duplicate:
                continue

            match_found = False
            for exp in list(unmatched_exp):
                agent_match = actual.agent_type == exp["agent_type"]
                category_match = actual.category == exp["category"]
                
                # Check keyword match in description/title/rationale
                text = f"{actual.title} {actual.description} {actual.rationale or ''}".lower()
                keyword_match = any(kw.lower() in text for kw in exp.get("keywords", []))

                if agent_match and (category_match or keyword_match):
                    matched.append({"actual": actual, "expected": exp})
                    unmatched_exp.remove(exp)
                    match_found = True
                    break

            if not match_found:
                spurious.append(actual)

        tp = len(matched)
        fp = len(spurious)
        fn = len(unmatched_exp)

        precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if not expected_findings else 0.0)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        return EvaluationResult(
            precision=round(precision, 3),
            recall=round(recall, 3),
            f1_score=round(f1, 3),
            matched_findings=matched,
            unmatched_expected=unmatched_exp,
            spurious_findings=spurious,
        )
