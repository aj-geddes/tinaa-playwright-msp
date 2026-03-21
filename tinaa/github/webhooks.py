"""
GitHub webhook handler and payload extraction utilities.

Verifies webhook signatures and routes events to registered handlers.
Provides helper functions for extracting typed data from webhook payloads.
"""

import hashlib
import hmac
import logging
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

SIGNATURE_PREFIX = "sha256="


class WebhookHandler:
    """Handles incoming GitHub webhooks.

    Verifies HMAC-SHA256 signatures and routes events to registered
    async handler callbacks.
    """

    def __init__(self, webhook_secret: str) -> None:
        """Initialise with the webhook secret used for signature verification.

        Args:
            webhook_secret: The secret configured in the GitHub App settings.
        """
        self._secret = webhook_secret
        self._handlers: dict[str, list[Callable[..., Coroutine[Any, Any, Any]]]] = {}

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify a webhook payload against its HMAC-SHA256 signature.

        Args:
            payload: Raw request body bytes.
            signature: Value of the X-Hub-Signature-256 header
                       (format: ``sha256=<hex_digest>``).

        Returns:
            True if the signature is valid, False otherwise.
        """
        if not signature.startswith(SIGNATURE_PREFIX):
            return False
        provided_digest = signature[len(SIGNATURE_PREFIX) :]
        expected_digest = hmac.new(self._secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(provided_digest, expected_digest)

    def on(
        self,
        event: str,
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        """Register an async handler for a webhook event.

        Args:
            event: GitHub event name (e.g. ``pull_request``, ``push``).
            handler: Async callable that receives the parsed payload dict.
        """
        self._handlers.setdefault(event, []).append(handler)

    async def handle(
        self,
        event: str,
        action: str | None,
        payload: dict[str, Any],
    ) -> list[Any]:
        """Route a webhook event to all registered handlers.

        Args:
            event: Value of the X-GitHub-Event header.
            action: Value of ``payload.get("action")``, if present.
            payload: Parsed webhook JSON payload.

        Returns:
            List of return values from each handler.
        """
        handlers = self._handlers.get(event, [])
        results: list[Any] = []
        for handler in handlers:
            try:
                result = await handler(payload)
                results.append(result)
            except Exception:
                logger.exception(
                    "Handler %s raised an exception for event %s/%s",
                    handler.__name__,
                    event,
                    action,
                )
        return results


# ---------------------------------------------------------------------------
# Payload extraction helpers
# ---------------------------------------------------------------------------


def extract_deployment_info(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract typed deployment data from a ``deployment_status`` webhook.

    Args:
        payload: Parsed ``deployment_status`` webhook payload.

    Returns:
        Dictionary with standardised deployment fields.
    """
    deployment_status = payload["deployment_status"]
    deployment = payload["deployment"]
    repository = payload["repository"]
    installation = payload["installation"]

    return {
        "deployment_id": deployment["id"],
        "environment": deployment_status["environment"],
        "state": deployment_status["state"],
        "target_url": deployment_status.get("target_url"),
        "commit_sha": deployment["sha"],
        "ref": deployment["ref"],
        "creator": deployment["creator"]["login"],
        "repository_full_name": repository["full_name"],
        "installation_id": installation["id"],
    }


def extract_pull_request_info(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract typed PR data from a ``pull_request`` webhook.

    Args:
        payload: Parsed ``pull_request`` webhook payload.

    Returns:
        Dictionary with standardised pull request fields.
    """
    pr = payload["pull_request"]
    repository = payload["repository"]
    installation = payload["installation"]
    pr_number = payload["number"]

    # Expand the pulls_url template to a concrete URL for this PR
    pulls_url = repository.get("pulls_url", "")
    changed_files_url = pulls_url.replace("{/number}", f"/{pr_number}/files")

    return {
        "pr_number": pr_number,
        "action": payload["action"],
        "title": pr["title"],
        "head_sha": pr["head"]["sha"],
        "head_ref": pr["head"]["ref"],
        "base_ref": pr["base"]["ref"],
        "repository_full_name": repository["full_name"],
        "changed_files_url": changed_files_url,
        "installation_id": installation["id"],
    }


def extract_push_info(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract typed push data from a ``push`` webhook.

    Args:
        payload: Parsed ``push`` webhook payload.

    Returns:
        Dictionary with standardised push fields.
    """
    repository = payload["repository"]
    installation = payload["installation"]

    commits = [
        {
            "id": c["id"],
            "message": c["message"],
            "modified": c.get("modified", []),
            "added": c.get("added", []),
            "removed": c.get("removed", []),
        }
        for c in payload.get("commits", [])
    ]

    return {
        "ref": payload["ref"],
        "commit_sha": payload["after"],
        "commits": commits,
        "repository_full_name": repository["full_name"],
        "installation_id": installation["id"],
    }
