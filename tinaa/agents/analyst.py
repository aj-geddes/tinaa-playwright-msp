"""
AnalystAgent — analyses test results and APM data to produce insights.
"""

from __future__ import annotations

from typing import Any

from tinaa.agents.base import AgentTask, BaseAgent

# Quality score parameters
_QUALITY_WEIGHT_PASS_RATE = 0.6
_QUALITY_WEIGHT_PERFORMANCE = 0.4
_PERFORMANCE_REGRESSION_THRESHOLD = 0.20  # 20% slower counts as a regression


class AnalystAgent(BaseAgent):
    """Produces structured quality insights from test runs and metrics."""

    def __init__(self) -> None:
        super().__init__("analyst")

    # ------------------------------------------------------------------
    # BaseAgent._run dispatch
    # ------------------------------------------------------------------

    async def _run(self, task: AgentTask) -> Any:
        action = task.action

        if action == "analyze_test_run":
            return await self.analyze_test_run(
                task.params.get("test_run", {}),
                task.params.get("baselines"),
            )

        if action == "correlate_deployment":
            return await self.correlate_deployment(
                task.params.get("deployment", {}),
                task.params.get("test_results", []),
                task.params.get("metrics_before", {}),
                task.params.get("metrics_after", {}),
            )

        if action == "generate_quality_report":
            return await self._generate_quality_report(task.params)

        if action == "identify_regressions":
            return await self.identify_regressions(
                task.params.get("current_results", {}),
                task.params.get("historical_results", []),
            )

        raise ValueError(f"AnalystAgent has no handler for action '{action}'")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_test_run(self, test_run: dict, baselines: dict | None = None) -> dict:
        """Analyse a test run's results.

        Returns a structured analysis including pass rate, failures,
        performance regressions, quality impact, and recommendations.
        """
        steps = test_run.get("steps", [])
        assertions = test_run.get("assertions", [])
        status = test_run.get("status", "unknown")

        failures = self._extract_failures(steps, assertions)
        pass_rate = self._compute_pass_rate(steps, assertions)
        performance_regressions = self._detect_perf_regressions(steps, baselines)
        quality_impact = self._compute_quality_impact(pass_rate, performance_regressions)
        recommendations = self._build_recommendations(failures, performance_regressions, status)
        summary = self._build_summary(pass_rate, failures, status)

        return {
            "summary": summary,
            "pass_rate": pass_rate,
            "failures": failures,
            "performance_regressions": performance_regressions,
            "quality_impact": quality_impact,
            "recommendations": recommendations,
        }

    async def correlate_deployment(
        self,
        deployment: dict,
        test_results: list[dict],
        metrics_before: dict,
        metrics_after: dict,
    ) -> dict:
        """Correlate a deployment event with its quality impact."""
        deployment_id = deployment.get("id", deployment.get("commit_sha", "unknown"))

        all_failures = []
        total_pass_rate = 0.0
        for result in test_results:
            analysis = await self.analyze_test_run(result)
            all_failures.extend(analysis["failures"])
            total_pass_rate += analysis["pass_rate"]

        avg_pass_rate = total_pass_rate / len(test_results) if test_results else 1.0
        quality_score_delta = (avg_pass_rate - 1.0) * 100

        root_causes = self._identify_root_causes(all_failures, metrics_before, metrics_after)
        affected_endpoints = list({f.get("step", "unknown") for f in all_failures})
        recommendations = self._build_deployment_recommendations(root_causes, quality_score_delta)

        return {
            "deployment_id": deployment_id,
            "quality_score_delta": round(quality_score_delta, 2),
            "root_causes": root_causes,
            "affected_endpoints": affected_endpoints,
            "recommendations": recommendations,
        }

    async def identify_regressions(
        self, current_results: dict, historical_results: list[dict]
    ) -> list[dict]:
        """Identify regressions by comparing current vs historical results."""
        regressions: list[dict] = []

        if not historical_results:
            return regressions

        current_analysis = await self.analyze_test_run(current_results)
        current_pass_rate = current_analysis["pass_rate"]

        historical_pass_rates = []
        for hist in historical_results:
            hist_analysis = await self.analyze_test_run(hist)
            historical_pass_rates.append(hist_analysis["pass_rate"])

        if not historical_pass_rates:
            return regressions

        avg_historical = sum(historical_pass_rates) / len(historical_pass_rates)

        if current_pass_rate < avg_historical - 0.05:
            severity = self._regression_severity(current_pass_rate, avg_historical)
            regressions.append(
                {
                    "type": "functional",
                    "description": (
                        f"Pass rate dropped from {avg_historical:.0%} to {current_pass_rate:.0%}"
                    ),
                    "first_seen": "current",
                    "severity": severity,
                    "evidence": {
                        "current_pass_rate": current_pass_rate,
                        "historical_avg": avg_historical,
                    },
                }
            )

        for regression in current_analysis["performance_regressions"]:
            regressions.append(
                {
                    "type": "performance",
                    "description": f"Performance regression on {regression.get('endpoint', 'unknown')}: {regression.get('metric', '')} {regression.get('delta', '')}",
                    "first_seen": "current",
                    "severity": "major",
                    "evidence": regression,
                }
            )

        return regressions

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_failures(self, steps: list[dict], assertions: list[dict]) -> list[dict]:
        """Extract failure records from steps and assertions."""
        failures: list[dict] = []

        for step in steps:
            if step.get("status") in ("failed", "error"):
                failures.append(
                    {
                        "step": step.get("name", "unknown"),
                        "reason": step.get("error") or "Step failed",
                        "severity": self._step_severity(step),
                    }
                )

        for assertion in assertions:
            if not assertion.get("passed", True):
                failures.append(
                    {
                        "step": assertion.get("name", "assertion"),
                        "reason": "Assertion failed",
                        "severity": "major",
                    }
                )

        return failures

    def _compute_pass_rate(self, steps: list[dict], assertions: list[dict]) -> float:
        """Compute the fraction of steps + assertions that passed."""
        total = len(steps) + len(assertions)
        if total == 0:
            return 1.0

        passed = sum(1 for s in steps if s.get("status") == "passed") + sum(
            1 for a in assertions if a.get("passed", True)
        )
        return round(passed / total, 4)

    def _detect_perf_regressions(self, steps: list[dict], baselines: dict | None) -> list[dict]:
        """Compare step durations against baselines to find regressions."""
        if not baselines:
            return []

        regressions: list[dict] = []
        for step in steps:
            name = step.get("name", "")
            duration = step.get("duration_ms", 0)
            baseline = baselines.get(name, {}).get("duration_ms")
            if baseline and duration > baseline * (1 + _PERFORMANCE_REGRESSION_THRESHOLD):
                delta_pct = int((duration - baseline) / baseline * 100)
                regressions.append(
                    {
                        "endpoint": name,
                        "metric": "duration_ms",
                        "delta": f"+{delta_pct}%",
                        "current": duration,
                        "baseline": baseline,
                    }
                )

        return regressions

    def _compute_quality_impact(
        self, pass_rate: float, performance_regressions: list[dict]
    ) -> dict:
        """Compute a quality score delta and list affected components."""
        score_delta = (pass_rate - 1.0) * 100
        if performance_regressions:
            score_delta -= len(performance_regressions) * 2.0

        affected = [r.get("endpoint", "unknown") for r in performance_regressions]
        return {
            "score_delta": round(score_delta, 2),
            "affected_components": affected,
        }

    def _build_recommendations(
        self,
        failures: list[dict],
        performance_regressions: list[dict],
        status: str,
    ) -> list[str]:
        """Build human-readable recommendations from analysis."""
        recommendations: list[str] = []

        critical_failures = [f for f in failures if f.get("severity") == "critical"]
        if critical_failures:
            recommendations.append(f"Investigate critical failure: {critical_failures[0]['step']}")

        if performance_regressions:
            endpoints = ", ".join(r["endpoint"] for r in performance_regressions[:3])
            recommendations.append(f"Review performance regressions on: {endpoints}")

        if status == "error":
            recommendations.append("Fix test infrastructure errors before analysing results")

        if not failures and not performance_regressions:
            recommendations.append("All checks passed — no action required")

        return recommendations

    def _build_summary(self, pass_rate: float, failures: list[dict], status: str) -> str:
        """Build a human-readable summary string."""
        if status == "error":
            return "Test run encountered infrastructure errors and could not complete"
        if pass_rate == 1.0 and not failures:
            return "All steps and assertions passed successfully"
        failed_count = len(failures)
        pct = int(pass_rate * 100)
        return (
            f"{pct}% of checks passed; "
            f"{failed_count} failure{'s' if failed_count != 1 else ''} detected"
        )

    def _identify_root_causes(
        self,
        failures: list[dict],
        metrics_before: dict,
        metrics_after: dict,
    ) -> list[dict]:
        """Attempt to identify root causes from failure evidence and metric deltas."""
        causes: list[dict] = []

        if failures:
            cause_names = list({f.get("step", "unknown") for f in failures[:3]})
            for name in cause_names:
                causes.append(
                    {
                        "change": name,
                        "impact": "Introduced test failures",
                        "confidence": 0.7,
                    }
                )

        for key in set(metrics_before) & set(metrics_after):
            before_val = metrics_before[key]
            after_val = metrics_after[key]
            if (
                isinstance(before_val, (int, float))
                and isinstance(after_val, (int, float))
                and before_val > 0
            ):
                change_ratio = (after_val - before_val) / before_val
                if abs(change_ratio) >= _PERFORMANCE_REGRESSION_THRESHOLD:
                    direction = "increased" if change_ratio > 0 else "decreased"
                    causes.append(
                        {
                            "change": f"{key} {direction} by {abs(int(change_ratio * 100))}%",
                            "impact": "Performance metric shift",
                            "confidence": 0.5,
                        }
                    )

        return causes

    def _build_deployment_recommendations(
        self, root_causes: list[dict], quality_score_delta: float
    ) -> list[str]:
        """Recommendations specific to a deployment correlation."""
        recommendations: list[str] = []

        if quality_score_delta < -10:
            recommendations.append("Consider rolling back this deployment")
        elif quality_score_delta < -5:
            recommendations.append("Monitor closely — quality score declined after deployment")
        else:
            recommendations.append("Deployment appears stable")

        for cause in root_causes[:2]:
            recommendations.append(f"Investigate: {cause['change']}")

        return recommendations

    @staticmethod
    def _step_severity(step: dict) -> str:
        """Classify a failing step's severity."""
        name = step.get("name", "").lower()
        if any(kw in name for kw in ("auth", "login", "payment", "assert")):
            return "critical"
        if step.get("status") == "error":
            return "major"
        return "minor"

    @staticmethod
    def _regression_severity(current: float, historical: float) -> str:
        """Classify regression severity by pass rate drop magnitude."""
        drop = historical - current
        if drop >= 0.3:
            return "critical"
        if drop >= 0.1:
            return "major"
        return "minor"

    async def _generate_quality_report(self, params: dict) -> dict:
        """Stub quality report generation (placeholder for full implementation)."""
        test_run = params.get("test_run", {})
        return await self.analyze_test_run(test_run)
