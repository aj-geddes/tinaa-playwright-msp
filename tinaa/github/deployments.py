"""
GitHub Deployment awareness and protection rule handling.

Tracks deployments, discovers deployment URLs from environment statuses,
and approves or rejects deployment protection rule requests.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tinaa.github.client import GitHubClient

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
PRODUCTION_ENVIRONMENT_NAMES = frozenset({"production", "prod"})


class DeploymentTracker:
    """Tracks deployments and discovers deployment URLs."""

    def __init__(self, client: GitHubClient) -> None:
        """Initialise with a GitHub API client.

        Args:
            client: Authenticated GitHubClient instance.
        """
        self._client = client

    async def get_latest_deployment_url(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        environment: str = "production",
    ) -> str | None:
        """Get the URL of the latest successful deployment for an environment.

        Algorithm:
        1. Fetch the most recent deployment for the given environment.
        2. Fetch its statuses and find the first ``success`` status.
        3. Return its ``environment_url``, or ``None`` if not found.

        Args:
            installation_id: GitHub App installation ID.
            owner: Repository owner.
            repo: Repository name.
            environment: Target environment name (default ``production``).

        Returns:
            The deployment URL string, or ``None``.
        """
        deployments_url = (
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/deployments"
            f"?environment={environment}&per_page=1"
        )
        deployments = await self._client._request("GET", deployments_url, installation_id)
        if not deployments:
            return None

        deployment = deployments[0]
        statuses_url = deployment["statuses_url"]
        statuses = await self._client._request("GET", statuses_url, installation_id)

        for status in statuses:
            if status.get("state") == "success":
                env_url = status.get("environment_url")
                if env_url:
                    return env_url

        return None

    async def list_environments(
        self,
        installation_id: int,
        owner: str,
        repo: str,
    ) -> list[dict[str, Any]]:
        """List all environments configured for a repository.

        Args:
            installation_id: GitHub App installation ID.
            owner: Repository owner.
            repo: Repository name.

        Returns:
            List of environment dicts with ``name``, ``url``, and
            ``protection_rules`` keys.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/environments"
        data = await self._client._request("GET", url, installation_id)
        environments: list[dict[str, Any]] = data.get("environments", [])
        return [
            {
                "name": env["name"],
                "url": env.get("html_url"),
                "protection_rules": env.get("protection_rules", []),
            }
            for env in environments
        ]

    async def handle_deployment_status(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Process a ``deployment_status`` webhook payload.

        Returns a structured dict only when the deployment succeeded and
        a target URL is present.

        Args:
            payload: Parsed webhook payload for the ``deployment_status``
                     event.

        Returns:
            Dict with deployment details, or ``None`` when the state is not
            ``success`` or no target URL exists.
        """
        deployment_status = payload["deployment_status"]
        deployment = payload["deployment"]

        state: str = deployment_status["state"]
        target_url: str | None = deployment_status.get("target_url")

        if state != "success" or not target_url:
            return None

        environment: str = deployment_status["environment"]
        is_production = environment.lower() in PRODUCTION_ENVIRONMENT_NAMES

        return {
            "environment": environment,
            "url": target_url,
            "commit_sha": deployment["sha"],
            "deployment_id": deployment["id"],
            "is_production": is_production,
        }

    async def respond_to_protection_rule(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        run_id: int,
        approved: bool,
        comment: str = "",
    ) -> None:
        """Approve or reject a deployment protection rule request.

        Args:
            installation_id: GitHub App installation ID.
            owner: Repository owner.
            repo: Repository name.
            run_id: Actions workflow run ID that triggered the gate.
            approved: ``True`` to approve, ``False`` to reject.
            comment: Optional explanatory comment.
        """
        url = (
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
            f"/actions/runs/{run_id}/deployment_protection_rule"
        )
        state = "approved" if approved else "rejected"
        await self._client._request(
            "POST",
            url,
            installation_id,
            json={"state": state, "comment": comment},
        )
