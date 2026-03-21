"""
High-level TINAA GitHub App orchestrator.

Wires together the client, webhook handler, checks manager, and deployment
tracker into a single entry point for GitHub App lifecycle management.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from tinaa.github.checks import ChecksManager
from tinaa.github.client import GitHubClient
from tinaa.github.deployments import DeploymentTracker
from tinaa.github.webhooks import WebhookHandler

logger = logging.getLogger(__name__)


class TINAAGitHubApp:
    """High-level GitHub App manager for TINAA."""

    def __init__(self, app_id: str, private_key: str, webhook_secret: str) -> None:
        """Initialise the app with GitHub App credentials.

        Args:
            app_id: GitHub App ID.
            private_key: PEM private key content.
            webhook_secret: Webhook secret configured in the App settings.
        """
        self.client = GitHubClient(app_id, private_key)
        self.webhooks = WebhookHandler(webhook_secret)
        self.checks = ChecksManager(self.client)
        self.deployments = DeploymentTracker(self.client)
        self._setup_default_handlers()

    def _setup_default_handlers(self) -> None:
        """Register default handlers for common GitHub webhook events."""
        self.webhooks.on("deployment_status", self._on_deployment_status)
        self.webhooks.on("pull_request", self._on_pull_request)
        self.webhooks.on("push", self._on_push)
        self.webhooks.on("installation", self._on_installation)

    async def handle_webhook(
        self,
        event: str,
        payload: bytes,
        signature: str,
    ) -> dict[str, Any]:
        """Entry point for processing an incoming GitHub webhook.

        1. Verifies the HMAC-SHA256 signature.
        2. Parses the JSON payload.
        3. Routes the event to registered handlers.
        4. Returns a status dict.

        Args:
            event: Value of the ``X-GitHub-Event`` header.
            payload: Raw request body bytes.
            signature: Value of the ``X-Hub-Signature-256`` header.

        Returns:
            Dict with ``status`` (``"ok"`` or ``"error"``) and optional
            ``message`` and ``results`` keys.
        """
        if not self.webhooks.verify_signature(payload, signature):
            logger.warning("Webhook signature verification failed for event '%s'", event)
            return {
                "status": "error",
                "message": "Invalid signature — webhook rejected",
            }

        try:
            parsed_payload: dict[str, Any] = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            logger.error("Failed to parse webhook payload: %s", exc)
            return {"status": "error", "message": f"Payload parse error: {exc}"}

        action: str | None = parsed_payload.get("action")
        results = await self.webhooks.handle(event, action, parsed_payload)

        return {"status": "ok", "event": event, "action": action, "results": results}

    async def onboard_repository(
        self,
        installation_id: int,
        owner: str,
        repo: str,
    ) -> dict[str, Any]:
        """Discover environments and configuration for a newly connected repo.

        Attempts to:
        1. Read ``.tinaa.yml`` from the default branch.
        2. List GitHub environments.
        3. Resolve the latest deployment URL for each environment.

        Args:
            installation_id: GitHub App installation ID.
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Dict with ``tinaa_config`` (str or None), ``environments``
            (list), and ``deployment_urls`` (dict).
        """
        # 1. Try to read .tinaa.yml
        tinaa_config: str | None = None
        try:
            tinaa_config = await self.client.get_file_content(
                installation_id, owner, repo, ".tinaa.yml"
            )
        except Exception:
            logger.debug(
                "No .tinaa.yml found in %s/%s — proceeding with auto-discovery",
                owner,
                repo,
            )

        # 2. List environments
        environments = await self.deployments.list_environments(installation_id, owner, repo)

        # 3. Resolve deployment URLs per environment
        deployment_urls: dict[str, str | None] = {}
        for env in environments:
            env_name: str = env["name"]
            url = await self.deployments.get_latest_deployment_url(
                installation_id, owner, repo, environment=env_name
            )
            deployment_urls[env_name] = url

        return {
            "tinaa_config": tinaa_config,
            "environments": environments,
            "deployment_urls": deployment_urls,
        }

    # ------------------------------------------------------------------
    # Default event handlers
    # ------------------------------------------------------------------

    async def _on_deployment_status(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Handle deployment_status events."""
        result = await self.deployments.handle_deployment_status(payload)
        if result:
            logger.info(
                "Deployment to %s completed: %s",
                result["environment"],
                result["url"],
            )
        return result

    async def _on_pull_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle pull_request events."""
        action = payload.get("action", "")
        pr_number = payload.get("number")
        logger.info("Pull request #%s action: %s", pr_number, action)
        return {"handled": True, "pr_number": pr_number, "action": action}

    async def _on_push(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle push events."""
        ref = payload.get("ref", "")
        sha = payload.get("after", "")
        logger.info("Push to %s, SHA %s", ref, sha)
        return {"handled": True, "ref": ref, "sha": sha}

    async def _on_installation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle installation events (install / uninstall)."""
        action = payload.get("action", "")
        installation_id = payload.get("installation", {}).get("id")
        logger.info("App installation event: %s (id=%s)", action, installation_id)
        return {"handled": True, "action": action, "installation_id": installation_id}
