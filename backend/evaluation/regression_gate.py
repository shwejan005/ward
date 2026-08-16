"""CI regression gate ensuring review quality and recall thresholds."""

from __future__ import annotations

import structlog
from backend.evaluation.golden_dataset import GOLDEN_PRS
from backend.evaluation.judge import ReviewJudge
from backend.models.findings import Finding

logger = structlog.get_logger(__name__)


class RegressionGate:
    """Verifies that agent finding quality meets minimum recall and precision thresholds."""

    def __init__(self, min_recall: float = 0.70, min_precision: float = 0.60) -> None:
        self.min_recall = min_recall
        self.min_precision = min_precision
        self.judge = ReviewJudge()

    def run_check(self, sample_results: dict[str, list[Finding]]) -> bool:
        """Run gate across all golden PR evaluations.

        sample_results: mapping of golden PR id -> list of produced Findings.
        """
        all_passed = True

        for golden in GOLDEN_PRS:
            pr_id = golden["id"]
            findings = sample_results.get(pr_id, [])
            eval_res = self.judge.evaluate(findings, golden["expected_findings"])

            passed = (
                eval_res.recall >= self.min_recall
                and eval_res.precision >= self.min_precision
            )
            if not passed:
                logger.error(
                    "regression_gate.failed",
                    pr_id=pr_id,
                    recall=eval_res.recall,
                    precision=eval_res.precision,
                    min_recall=self.min_recall,
                    min_precision=self.min_precision,
                )
                all_passed = False
            else:
                logger.info(
                    "regression_gate.passed",
                    pr_id=pr_id,
                    f1=eval_res.f1_score,
                )

        return all_passed
