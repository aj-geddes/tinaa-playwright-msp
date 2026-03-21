"""Quality gates for TINAA deployment decisions.

A quality gate evaluates a computed quality score plus supplementary
signals (test results, performance regression, new violations) to decide
whether a deployment should proceed.
"""

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Score delta below which divergence is considered significant
REVIEW_SCORE_MARGIN = 5.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class QualityGateConfig:
    """Configuration for a quality gate."""

    min_score: float = 80.0
    no_critical_failures: bool = True
    max_performance_regression_percent: float = 20.0
    max_new_accessibility_violations: int = 0
    max_security_issues: int = 0
    required_test_pass_rate: float = 100.0


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------


class QualityGate:
    """Evaluates whether a deployment should be allowed to proceed."""

    def __init__(self, config: QualityGateConfig | None = None) -> None:
        self.config = config or QualityGateConfig()

    def evaluate(
        self,
        quality_score: dict,
        test_results: dict | None = None,
        performance_comparison: dict | None = None,
        new_accessibility_violations: int = 0,
        new_security_issues: int = 0,
    ) -> dict:
        """Evaluate whether a deployment passes the quality gate.

        Returns a dict with: passed, score, checks, blocking_reasons, recommendation.
        """
        checks: list[dict[str, Any]] = []
        blocking_reasons: list[str] = []
        score = quality_score.get("score", 0.0)

        self._check_minimum_score(score, checks, blocking_reasons)
        if performance_comparison is not None:
            self._check_performance_regression(performance_comparison, checks, blocking_reasons)
        self._check_accessibility_violations(new_accessibility_violations, checks, blocking_reasons)
        self._check_security_issues(new_security_issues, checks, blocking_reasons)
        if test_results is not None:
            self._check_test_pass_rate(test_results, checks, blocking_reasons)

        overall_passed = len(blocking_reasons) == 0
        return {
            "passed": overall_passed,
            "score": score,
            "checks": checks,
            "blocking_reasons": blocking_reasons,
            "recommendation": self._recommend(overall_passed, score, self.config.min_score),
        }

    def _check_minimum_score(self, score: float, checks: list, blocking_reasons: list) -> None:
        """Append the minimum-score check result."""
        passed = score >= self.config.min_score
        checks.append(
            {
                "name": "minimum_quality_score",
                "passed": passed,
                "value": score,
                "threshold": self.config.min_score,
                "message": (
                    f"Quality score {score:.1f} meets minimum {self.config.min_score}"
                    if passed
                    else f"Quality score {score:.1f} is below minimum {self.config.min_score}"
                ),
            }
        )
        if not passed:
            blocking_reasons.append(
                f"Quality score {score:.1f} is below required minimum of {self.config.min_score}"
            )

    def _check_performance_regression(
        self, comparison: dict, checks: list, blocking_reasons: list
    ) -> None:
        """Append the performance-regression check result."""
        regression_pct = comparison.get("regression_percent", 0.0)
        max_allowed = self.config.max_performance_regression_percent
        passed = regression_pct <= max_allowed
        checks.append(
            {
                "name": "performance_regression",
                "passed": passed,
                "value": regression_pct,
                "threshold": max_allowed,
                "message": (
                    f"Performance regression {regression_pct:.1f}% within acceptable limit"
                    if passed
                    else f"Performance regression {regression_pct:.1f}% exceeds limit of {max_allowed}%"
                ),
            }
        )
        if not passed:
            blocking_reasons.append(
                f"Performance regression {regression_pct:.1f}% exceeds allowed {max_allowed}%"
            )

    def _check_accessibility_violations(
        self, count: int, checks: list, blocking_reasons: list
    ) -> None:
        """Append the new-accessibility-violations check result."""
        max_allowed = self.config.max_new_accessibility_violations
        passed = count <= max_allowed
        checks.append(
            {
                "name": "new_accessibility_violations",
                "passed": passed,
                "value": count,
                "threshold": max_allowed,
                "message": (
                    "No new accessibility violations introduced"
                    if passed
                    else f"{count} new accessibility violation(s) introduced (max allowed: {max_allowed})"
                ),
            }
        )
        if not passed:
            blocking_reasons.append(
                f"{count} new accessibility violation(s) exceed the allowed maximum"
            )

    def _check_security_issues(self, count: int, checks: list, blocking_reasons: list) -> None:
        """Append the new-security-issues check result."""
        max_allowed = self.config.max_security_issues
        passed = count <= max_allowed
        checks.append(
            {
                "name": "new_security_issues",
                "passed": passed,
                "value": count,
                "threshold": max_allowed,
                "message": (
                    "No new security issues introduced"
                    if passed
                    else f"{count} new security issue(s) introduced (max allowed: {max_allowed})"
                ),
            }
        )
        if not passed:
            blocking_reasons.append(f"{count} new security issue(s) exceed the allowed maximum")

    def _check_test_pass_rate(
        self, test_results: dict, checks: list, blocking_reasons: list
    ) -> None:
        """Append the test-pass-rate check result."""
        total = test_results.get("total", 0)
        passed_count = test_results.get("passed", 0)
        pass_rate = (passed_count / total * 100.0) if total > 0 else 0.0
        required = self.config.required_test_pass_rate
        passed = pass_rate >= required
        checks.append(
            {
                "name": "test_pass_rate",
                "passed": passed,
                "value": pass_rate,
                "threshold": required,
                "message": (
                    f"Test pass rate {pass_rate:.1f}% meets requirement"
                    if passed
                    else f"Test pass rate {pass_rate:.1f}% below required {required}%"
                ),
            }
        )
        if not passed:
            blocking_reasons.append(
                f"Test pass rate {pass_rate:.1f}% is below required {required}%"
            )

    def evaluate_for_deployment_protection(
        self,
        quality_score: dict,
        test_results: dict | None = None,
    ) -> dict:
        """Evaluate for GitHub Deployment Protection Rule response.

        Returns: {"state": "approved" | "rejected", "comment": str}
        """
        result = self.evaluate(quality_score, test_results=test_results)
        if result["passed"]:
            state = "approved"
            score = result["score"]
            comment = (
                f"Quality gate passed. Score: {score:.1f}/100. "
                f"All {len(result['checks'])} check(s) passed. Deployment approved."
            )
        else:
            state = "rejected"
            reasons = "; ".join(result["blocking_reasons"])
            comment = (
                f"Quality gate failed. Score: {result['score']:.1f}/100. "
                f"Blocking reasons: {reasons}. Fix issues before deploying."
            )

        return {"state": state, "comment": comment}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _recommend(passed: bool, score: float, min_score: float) -> str:
        """Return approve / reject / review based on gate outcome and score proximity."""
        if not passed:
            return "reject"
        # Passed but score is close to the minimum threshold — flag for review
        if score < min_score + REVIEW_SCORE_MARGIN:
            return "review"
        return "approve"
