"""
GitHub Check Runs API manager.

Creates and updates check runs on pull requests to report test results
inline with rich markdown summaries and file annotations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tinaa.github.client import GitHubClient

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"

# Mapping from issue severity strings to GitHub annotation levels
SEVERITY_TO_ANNOTATION_LEVEL: dict[str, str] = {
    "notice": "notice",
    "info": "notice",
    "warning": "warning",
    "warn": "warning",
    "error": "failure",
    "failure": "failure",
    "critical": "failure",
}


class ChecksManager:
    """Manages GitHub Check Runs for reporting test results."""

    def __init__(self, client: GitHubClient) -> None:
        """Initialise with a GitHub API client.

        Args:
            client: Authenticated GitHubClient instance.
        """
        self._client = client

    async def create_check_run(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        name: str,
        head_sha: str,
        status: str = "queued",
        details_url: str | None = None,
    ) -> dict[str, int]:
        """Create a new check run on a commit.

        Args:
            installation_id: GitHub App installation ID.
            owner: Repository owner.
            repo: Repository name.
            name: Display name of the check run.
            head_sha: Commit SHA to attach the check run to.
            status: Initial status — ``queued``, ``in_progress``, or
                    ``completed``.
            details_url: Optional URL linking to the full report.

        Returns:
            Dictionary containing ``check_run_id``.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/check-runs"
        body: dict[str, Any] = {
            "name": name,
            "head_sha": head_sha,
            "status": status,
        }
        if details_url is not None:
            body["details_url"] = details_url

        response = await self._client._request("POST", url, installation_id, json=body)
        return {"check_run_id": response["id"]}

    async def update_check_run(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        check_run_id: int,
        status: str | None = None,
        conclusion: str | None = None,
        title: str | None = None,
        summary: str | None = None,
        text: str | None = None,
        annotations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Update an existing check run with results.

        Args:
            installation_id: GitHub App installation ID.
            owner: Repository owner.
            repo: Repository name.
            check_run_id: ID of the check run to update.
            status: New status (``queued``, ``in_progress``, ``completed``).
            conclusion: Required when status is ``completed``.  One of:
                ``success``, ``failure``, ``neutral``, ``cancelled``,
                ``timed_out``, ``action_required``.
            title: Short summary title shown in the check run output.
            summary: Markdown summary (supports GFM).
            text: Additional details in Markdown.
            annotations: List of file-line annotations.  Each annotation is::

                {
                    "path": "src/pages/login.tsx",
                    "start_line": 47,
                    "end_line": 47,
                    "annotation_level": "warning",  # notice | warning | failure
                    "message": "Button missing aria-label",
                    "title": "Accessibility Issue"
                }

        Returns:
            Updated check run object from the API.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/check-runs/{check_run_id}"
        body: dict[str, Any] = {}

        if status is not None:
            body["status"] = status
        if conclusion is not None:
            body["conclusion"] = conclusion

        # Build output section only when there is something to report
        output: dict[str, Any] = {}
        if title is not None:
            output["title"] = title
        if summary is not None:
            output["summary"] = summary
        if text is not None:
            output["text"] = text
        if annotations is not None:
            output["annotations"] = annotations
        if output:
            body["output"] = output

        return await self._client._request("PATCH", url, installation_id, json=body)

    async def report_test_results(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        head_sha: str,
        test_run_summary: dict[str, Any],
    ) -> int:
        """Create and populate a check run from a test run summary.

        Creates the check run, then immediately updates it as ``completed``
        with a rich Markdown summary and per-issue annotations.

        Args:
            installation_id: GitHub App installation ID.
            owner: Repository owner.
            repo: Repository name.
            head_sha: Commit SHA to attach the check run to.
            test_run_summary: Dictionary with the keys:

                - ``name`` (str)
                - ``passed`` (int)
                - ``failed`` (int)
                - ``skipped`` (int)
                - ``duration_ms`` (int)
                - ``quality_score`` (float)
                - ``quality_score_delta`` (float)
                - ``performance_summary`` (str)
                - ``issues`` (list of dicts with ``file``, ``line``,
                  ``message``, ``severity``)

        Returns:
            The ``check_run_id`` integer.
        """
        name: str = test_run_summary.get("name", "TINAA Quality Check")
        passed: int = test_run_summary.get("passed", 0)
        failed: int = test_run_summary.get("failed", 0)
        skipped: int = test_run_summary.get("skipped", 0)
        duration_ms: int = test_run_summary.get("duration_ms", 0)
        quality_score: float = test_run_summary.get("quality_score", 0.0)
        quality_score_delta: float = test_run_summary.get("quality_score_delta", 0.0)
        performance_summary: str = test_run_summary.get("performance_summary", "")
        issues: list[dict[str, Any]] = test_run_summary.get("issues", [])

        result = await self.create_check_run(
            installation_id=installation_id,
            owner=owner,
            repo=repo,
            name=name,
            head_sha=head_sha,
            status="in_progress",
        )
        check_run_id: int = result["check_run_id"]

        conclusion = "success" if failed == 0 else "failure"

        delta_sign = "+" if quality_score_delta >= 0 else ""
        summary = _build_markdown_summary(
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_ms=duration_ms,
            quality_score=quality_score,
            delta_sign=delta_sign,
            quality_score_delta=quality_score_delta,
            performance_summary=performance_summary,
        )

        annotations = _build_annotations(issues)

        await self.update_check_run(
            installation_id=installation_id,
            owner=owner,
            repo=repo,
            check_run_id=check_run_id,
            status="completed",
            conclusion=conclusion,
            title=f"{name}: {passed} passed, {failed} failed",
            summary=summary,
            annotations=annotations if annotations else None,
        )

        return check_run_id


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_markdown_summary(
    *,
    passed: int,
    failed: int,
    skipped: int,
    duration_ms: int,
    quality_score: float,
    delta_sign: str,
    quality_score_delta: float,
    performance_summary: str,
) -> str:
    """Compose a GFM Markdown summary for a check run."""
    duration_s = duration_ms / 1000
    return (
        f"## TINAA Quality Report\n\n"
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Quality Score | **{quality_score:.1f}** ({delta_sign}{quality_score_delta:.1f}) |\n"
        f"| Tests Passed | {passed} |\n"
        f"| Tests Failed | {failed} |\n"
        f"| Tests Skipped | {skipped} |\n"
        f"| Duration | {duration_s:.1f}s |\n"
        f"| Performance | {performance_summary} |\n"
    )


def _build_annotations(
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert issue dicts into GitHub annotation objects."""
    annotations: list[dict[str, Any]] = []
    for issue in issues:
        severity = issue.get("severity", "warning")
        level = SEVERITY_TO_ANNOTATION_LEVEL.get(severity, "warning")
        line = issue.get("line", 1)
        annotations.append(
            {
                "path": issue["file"],
                "start_line": line,
                "end_line": line,
                "annotation_level": level,
                "message": issue["message"],
                "title": f"TINAA: {severity.capitalize()}",
            }
        )
    return annotations
