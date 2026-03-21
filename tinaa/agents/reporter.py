"""
ReporterAgent — formats and delivers quality reports through various channels.
"""

from __future__ import annotations

from typing import Any

from tinaa.agents.base import AgentTask, BaseAgent

# Pass rate threshold above which a check run is "success"
_SUCCESS_THRESHOLD = 0.95


class ReporterAgent(BaseAgent):
    """Formats analysis results into Markdown, GitHub Check Runs, and alerts."""

    def __init__(self) -> None:
        super().__init__("reporter")

    # ------------------------------------------------------------------
    # BaseAgent._run dispatch
    # ------------------------------------------------------------------

    async def _run(self, task: AgentTask) -> Any:
        action = task.action

        if action == "report_to_github":
            return await self.format_check_run_output(task.params.get("analysis", {}))

        if action == "report_to_slack":
            return await self._format_slack_message(task.params)

        if action == "format_quality_report":
            return await self.format_quality_report(
                task.params.get("product_name", ""),
                task.params.get("quality_data", {}),
                task.params.get("test_summary", {}),
                task.params.get("metrics_summary", {}),
            )

        if action == "create_pr_comment":
            return await self.format_pr_comment(
                task.params.get("analysis", {}),
                task.params.get("quality_score", {}),
            )

        raise ValueError(f"ReporterAgent has no handler for action '{action}'")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def format_check_run_output(self, analysis: dict) -> dict:
        """Format analysis results for a GitHub Check Run.

        Returns a dict with title, summary, text, annotations, and conclusion.
        """
        pass_rate = analysis.get("pass_rate", 1.0)
        failures = analysis.get("failures", [])
        summary_text = analysis.get("summary", "No summary available")
        recommendations = analysis.get("recommendations", [])

        conclusion = self._compute_conclusion(pass_rate, failures)
        title = self._check_run_title(conclusion, pass_rate)
        summary = self._render_check_summary(summary_text, pass_rate, failures)
        text = self._render_check_detail(analysis, recommendations)
        annotations = self._build_annotations(failures)

        return {
            "title": title,
            "summary": summary,
            "text": text,
            "annotations": annotations,
            "conclusion": conclusion,
        }

    async def format_pr_comment(self, analysis: dict, quality_score: dict) -> str:
        """Format a PR comment in Markdown with test results and quality impact."""
        pass_rate = analysis.get("pass_rate", 1.0)
        failures = analysis.get("failures", [])
        summary_text = analysis.get("summary", "")
        recommendations = analysis.get("recommendations", [])
        score = quality_score.get("score", 0.0)
        trend = quality_score.get("trend", "stable")
        grade = quality_score.get("grade", "?")

        icon = "green_circle" if pass_rate >= _SUCCESS_THRESHOLD else "red_circle"
        status_label = "Passed" if pass_rate >= _SUCCESS_THRESHOLD else "Failed"

        lines: list[str] = [
            f"## TINAA Quality Report :{icon}: {status_label}",
            "",
            f"**Summary:** {summary_text}",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Pass Rate | {pass_rate:.0%} |",
            f"| Quality Score | {score:.1f} ({grade}) |",
            f"| Trend | {trend.title()} |",
            "",
        ]

        if failures:
            lines += [
                "### Failures",
                "",
            ]
            for failure in failures[:10]:
                lines.append(
                    f"- **{failure.get('step', 'unknown')}**: {failure.get('reason', 'failed')}"
                )
            lines.append("")

        if recommendations:
            lines += ["### Recommendations", ""]
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)

    async def format_quality_report(
        self,
        product_name: str,
        quality_data: dict,
        test_summary: dict,
        metrics_summary: dict,
    ) -> dict:
        """Format a comprehensive quality report for a product."""
        score = float(quality_data.get("score", 0.0))
        trend = quality_data.get("trend", "stable")
        total = test_summary.get("total", 0)
        passed = test_summary.get("passed", 0)
        failed = test_summary.get("failed", 0)
        pass_rate = test_summary.get("pass_rate", 1.0)
        avg_response = metrics_summary.get("avg_response_ms")
        error_rate = metrics_summary.get("error_rate")

        text = self._render_full_report(
            product_name,
            score,
            trend,
            total,
            passed,
            failed,
            pass_rate,
            avg_response,
            error_rate,
            metrics_summary,
        )
        summary = self._render_report_summary(product_name, score, trend, pass_rate)
        top_issues = self._extract_top_issues(quality_data, test_summary)

        return {
            "text": text,
            "summary": summary,
            "score": score,
            "trend": trend,
            "top_issues": top_issues,
        }

    async def format_alert_message(self, alert: dict) -> dict:
        """Format an alert for delivery via Slack, email, or webhook."""
        severity = alert.get("severity", "warning")
        alert_type = alert.get("type", "alert")
        endpoint = alert.get("endpoint", "unknown")
        metric = alert.get("metric", "")
        value = alert.get("value")
        threshold = alert.get("threshold")

        subject = f"[{severity.upper()}] TINAA Alert: {alert_type} on {endpoint}"

        body_lines: list[str] = [
            f"**Alert Type:** {alert_type}",
            f"**Severity:** {severity}",
            f"**Endpoint:** {endpoint}",
        ]
        if metric:
            body_lines.append(f"**Metric:** {metric}")
        if value is not None:
            body_lines.append(f"**Current Value:** {value}")
        if threshold is not None:
            body_lines.append(f"**Threshold:** {threshold}")

        actions = self._suggest_alert_actions(severity, alert_type, endpoint)

        return {
            "subject": subject,
            "body": "\n".join(body_lines),
            "severity": severity,
            "actions": actions,
        }

    # ------------------------------------------------------------------
    # Private rendering helpers
    # ------------------------------------------------------------------

    def _compute_conclusion(self, pass_rate: float, failures: list[dict]) -> str:
        """Determine the GitHub check run conclusion."""
        if pass_rate >= _SUCCESS_THRESHOLD and not failures:
            return "success"
        if failures:
            return "failure"
        return "neutral"

    def _check_run_title(self, conclusion: str, pass_rate: float) -> str:
        """Short title for the check run."""
        pct = int(pass_rate * 100)
        if conclusion == "success":
            return f"TINAA — All checks passed ({pct}%)"
        if conclusion == "failure":
            return f"TINAA — Checks failed ({pct}% pass rate)"
        return f"TINAA — Checks completed ({pct}%)"

    def _render_check_summary(
        self, summary_text: str, pass_rate: float, failures: list[dict]
    ) -> str:
        """Markdown summary for the check run."""
        icon = ":white_check_mark:" if pass_rate >= _SUCCESS_THRESHOLD else ":x:"
        lines = [
            f"## {icon} TINAA Quality Check",
            "",
            summary_text,
            "",
            f"**Pass Rate:** {pass_rate:.0%}",
        ]
        if failures:
            lines += [
                "",
                f"**{len(failures)} failure(s) detected.**",
            ]
        return "\n".join(lines)

    def _render_check_detail(self, analysis: dict, recommendations: list[str]) -> str:
        """Detailed Markdown text for the check run body."""
        failures = analysis.get("failures", [])
        perf_regressions = analysis.get("performance_regressions", [])
        lines = ["## Detailed Results", ""]

        if failures:
            lines += ["### Failures", ""]
            for f in failures:
                severity = f.get("severity", "minor")
                lines.append(
                    f"- **[{severity}]** `{f.get('step', 'unknown')}`: {f.get('reason', 'failed')}"
                )
            lines.append("")

        if perf_regressions:
            lines += ["### Performance Regressions", ""]
            for reg in perf_regressions:
                lines.append(
                    f"- `{reg.get('endpoint', 'unknown')}`: {reg.get('metric', '')} {reg.get('delta', '')}"
                )
            lines.append("")

        if recommendations:
            lines += ["### Recommendations", ""]
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)

    def _build_annotations(self, failures: list[dict]) -> list[dict]:
        """Build GitHub annotation objects from failures (path is unknown — use root)."""
        annotations: list[dict] = []
        for failure in failures:
            severity = failure.get("severity", "minor")
            level = "failure" if severity in ("critical", "major") else "warning"
            annotations.append(
                {
                    "path": ".",
                    "start_line": 1,
                    "end_line": 1,
                    "annotation_level": level,
                    "message": f"{failure.get('step', 'unknown')}: {failure.get('reason', 'failed')}",
                }
            )
        return annotations

    def _render_full_report(
        self,
        product_name: str,
        score: float,
        trend: str,
        total: int,
        passed: int,
        failed: int,
        pass_rate: float,
        avg_response: Any,
        error_rate: Any,
        metrics_summary: dict,
    ) -> str:
        """Render the full Markdown quality report."""
        grade = self._score_to_grade(score)
        trend_icon = {"improving": "↑", "declining": "↓", "stable": "→"}.get(trend, "→")

        lines: list[str] = [
            f"# Quality Report: {product_name}",
            "",
            f"**Overall Score:** {score:.1f}/100 (Grade: {grade}) {trend_icon} {trend.title()}",
            "",
            "## Test Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Tests | {total} |",
            f"| Passed | {passed} |",
            f"| Failed | {failed} |",
            f"| Pass Rate | {pass_rate:.0%} |",
            "",
        ]

        if avg_response is not None or error_rate is not None:
            lines += [
                "## Performance Metrics",
                "",
                "| Metric | Value |",
                "|--------|-------|",
            ]
            if avg_response is not None:
                lines.append(f"| Avg Response | {avg_response} ms |")
            if error_rate is not None:
                lines.append(f"| Error Rate | {error_rate:.1%} |")
            lines.append("")

        return "\n".join(lines)

    def _render_report_summary(
        self, product_name: str, score: float, trend: str, pass_rate: float
    ) -> str:
        """One-paragraph plain-English summary."""
        grade = self._score_to_grade(score)
        return (
            f"{product_name} has a quality score of {score:.1f}/100 (grade {grade}), "
            f"with a {pass_rate:.0%} test pass rate. "
            f"The quality trend is {trend}."
        )

    def _extract_top_issues(self, quality_data: dict, test_summary: dict) -> list[dict]:
        """Extract the top issues from quality and test data."""
        issues: list[dict] = []
        failed = test_summary.get("failed", 0)
        if failed > 0:
            issues.append(
                {
                    "type": "test_failures",
                    "count": failed,
                    "severity": "critical" if failed >= 5 else "major",
                }
            )
        return issues

    @staticmethod
    def _score_to_grade(score: float) -> str:
        """Convert a numeric quality score to a letter grade."""
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"

    @staticmethod
    def _suggest_alert_actions(severity: str, alert_type: str, endpoint: str) -> list[str]:
        """Return a list of suggested remediation actions for an alert."""
        actions: list[str] = [f"Investigate {endpoint}"]
        if severity == "critical":
            actions.append("Consider rolling back the latest deployment")
            actions.append("Page on-call engineer")
        elif severity in ("high", "warning"):
            actions.append("Review recent changes to the affected component")
        if alert_type == "anomaly":
            actions.append(f"Run targeted tests for {endpoint}")
        return actions

    async def _format_slack_message(self, params: dict) -> dict:
        """Format a Slack notification (stub)."""
        analysis = params.get("analysis", {})
        pass_rate = analysis.get("pass_rate", 1.0)
        icon = ":white_check_mark:" if pass_rate >= _SUCCESS_THRESHOLD else ":x:"
        return {
            "text": f"{icon} TINAA quality check: {pass_rate:.0%} pass rate",
            "blocks": [],
        }
