"""GitHub webhook handler — signature verification and event routing."""

import hashlib
import hmac
import logging
import os

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()
logger = logging.getLogger(__name__)

# Configurable via environment variable; patched in tests.
GITHUB_WEBHOOK_SECRET: str = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

_MISSING_SIG_STATUS = 400
_INVALID_SIG_STATUS = 401


def _verify_github_signature(secret: str, payload: bytes, signature_header: str | None) -> bool:
    """Return True if the HMAC-SHA256 signature matches the payload.

    Args:
        secret: Shared webhook secret.
        payload: Raw request body bytes.
        signature_header: Value of the X-Hub-Signature-256 header.
    """
    if not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


# ---------------------------------------------------------------------------
# Event handlers (stubs — extend per integration need)
# ---------------------------------------------------------------------------


async def _handle_deployment_status(payload: dict) -> dict:
    logger.info("GitHub deployment_status: %s", payload.get("state"))
    return {"action": "track_deployment", "state": payload.get("state")}


async def _handle_pull_request(payload: dict) -> dict:
    logger.info("GitHub pull_request: #%s %s", payload.get("number"), payload.get("action"))
    return {"action": "analyze_pr", "number": payload.get("number")}


async def _handle_push(payload: dict) -> dict:
    logger.info("GitHub push: ref=%s", payload.get("ref"))
    return {"action": "detect_changes", "ref": payload.get("ref")}


async def _handle_installation(payload: dict) -> dict:
    logger.info("GitHub installation: %s", payload.get("action"))
    return {"action": "handle_installation", "install_action": payload.get("action")}


_EVENT_HANDLERS = {
    "deployment_status": _handle_deployment_status,
    "pull_request": _handle_pull_request,
    "push": _handle_push,
    "installation": _handle_installation,
}


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post(
    "/webhooks/github",
    summary="GitHub webhook",
    description=(
        "Receives GitHub webhook events. Verifies HMAC-SHA256 signature, "
        "then routes to the appropriate handler."
    ),
)
async def github_webhook(request: Request) -> dict:
    """Handle incoming GitHub webhook events.

    Steps:
    1. Reject with 503 if GITHUB_WEBHOOK_SECRET is not configured.
    2. Read raw body and verify X-Hub-Signature-256 header against the secret.
    3. Parse JSON payload.
    4. Route to the handler for the X-GitHub-Event type.
    5. Return 200 with event summary.
    """
    if not GITHUB_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="GitHub webhook integration not configured. Set GITHUB_WEBHOOK_SECRET environment variable.",
        )

    body = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256")
    event_type = request.headers.get("X-GitHub-Event", "unknown")

    # Reject requests with missing signature.
    if not sig_header:
        raise HTTPException(
            status_code=_MISSING_SIG_STATUS, detail="Missing X-Hub-Signature-256 header"
        )

    # Reject requests that fail signature verification.
    if not _verify_github_signature(GITHUB_WEBHOOK_SECRET, body, sig_header):
        raise HTTPException(status_code=_INVALID_SIG_STATUS, detail="Invalid webhook signature")

    try:
        import json

        payload: dict = json.loads(body)
    except Exception as err:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from err

    handler = _EVENT_HANDLERS.get(event_type)
    if handler:
        handler_result = await handler(payload)
    else:
        logger.info("Unhandled GitHub event: %s", event_type)
        handler_result = {"action": "ignored"}

    return {
        "status": "received",
        "event": event_type,
        **handler_result,
    }
