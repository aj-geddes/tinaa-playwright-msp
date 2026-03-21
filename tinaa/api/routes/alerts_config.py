"""API routes for configuring alert channels and rules."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/alerts")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory stores (replace with DB persistence in production)
# ---------------------------------------------------------------------------

_channels: dict[str, dict[str, Any]] = {}
_rules: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Channel configuration models
# ---------------------------------------------------------------------------


class SlackChannelConfig(BaseModel):
    webhook_url: str
    channel_name: str = ""


class TeamsChannelConfig(BaseModel):
    webhook_url: str
    channel_name: str = ""


class PagerDutyChannelConfig(BaseModel):
    routing_key: str
    service_name: str = ""
    severity_threshold: str = "warning"


class EmailChannelConfig(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    username: str
    password: str
    from_address: str
    to_addresses: list[str]


class WebhookChannelConfig(BaseModel):
    url: str
    headers: dict[str, str] = {}
    method: str = "POST"


class ChannelConfig(BaseModel):
    channel_type: str  # slack, teams, pagerduty, email, webhook
    name: str
    enabled: bool = True
    config: dict[str, Any]


class TestNotification(BaseModel):
    channel_type: str
    config: dict[str, Any]


# ---------------------------------------------------------------------------
# Channel routes
# ---------------------------------------------------------------------------


@router.get("/channels")
async def list_configured_channels() -> list[dict[str, Any]]:
    """List all configured alert channels.

    Returns each channel with id, type, name, enabled flag, and last_sent timestamp.
    """
    return list(_channels.values())


@router.post("/channels")
async def add_channel(request: ChannelConfig) -> dict[str, Any]:
    """Add a new alert channel.

    Returns the created channel record with a generated id and status=configured.
    """
    channel_id = str(uuid.uuid4())
    record: dict[str, Any] = {
        "id": channel_id,
        "type": request.channel_type,
        "name": request.name,
        "enabled": request.enabled,
        "config": request.config,
        "last_sent": None,
        "status": "configured",
    }
    _channels[channel_id] = record
    return {
        "id": channel_id,
        "type": request.channel_type,
        "name": request.name,
        "status": "configured",
    }


@router.delete("/channels/{channel_id}")
async def remove_channel(channel_id: str) -> dict[str, Any]:
    """Remove an alert channel by id.

    Raises 404 if the channel does not exist.
    """
    if channel_id not in _channels:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")
    del _channels[channel_id]
    return {"deleted": channel_id}


@router.patch("/channels/{channel_id}")
async def update_channel(channel_id: str, request: dict[str, Any]) -> dict[str, Any]:
    """Update one or more fields on an alert channel.

    Raises 404 if the channel does not exist.
    """
    if channel_id not in _channels:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")
    _channels[channel_id].update(request)
    return _channels[channel_id]


@router.post("/channels/test")
async def test_channel(request: TestNotification) -> dict[str, Any]:
    """Send a test notification through a channel configuration.

    Creates a minimal test alert and attempts delivery through the specified
    channel type and config. Returns success/failure with a human-readable message.
    """
    from datetime import UTC, datetime

    from tinaa.alerts.rules import Alert, AlertConditionType, AlertSeverity

    test_alert = Alert(
        rule_name="tinaa-test",
        severity=AlertSeverity.INFO,
        condition_type=AlertConditionType.TEST_FAILURE,
        message="This is a test notification from TINAA MSP. If you see this, your alert channel is configured correctly.",
        product_name="TINAA",
        environment="test",
        triggered_at=datetime.now(UTC).isoformat(),
    )

    try:
        channel_type = request.channel_type
        cfg = request.config

        if channel_type == "slack":
            from tinaa.alerts.channels import SlackChannel

            webhook_url = cfg.get("webhook_url", "")
            if not webhook_url:
                return {"success": False, "message": "webhook_url is required for Slack"}
            channel = SlackChannel(webhook_url)
            success = await channel.send(test_alert)

        elif channel_type == "teams":
            from tinaa.alerts.teams_channel import TeamsChannel

            webhook_url = cfg.get("webhook_url", "")
            if not webhook_url:
                return {"success": False, "message": "webhook_url is required for Teams"}
            channel = TeamsChannel(webhook_url)
            success = await channel.send(test_alert)

        elif channel_type == "pagerduty":
            from tinaa.alerts.channels import PagerDutyChannel

            routing_key = cfg.get("routing_key", "")
            if not routing_key:
                return {"success": False, "message": "routing_key is required for PagerDuty"}
            channel = PagerDutyChannel(routing_key)
            success = await channel.send(test_alert)

        elif channel_type == "webhook":
            from tinaa.alerts.channels import WebhookChannel

            if not cfg.get("url"):
                return {"success": False, "message": "url is required for Webhook"}
            channel = WebhookChannel()
            success = await channel.send(test_alert, config=cfg)

        else:
            return {"success": False, "message": f"Unsupported channel type: {channel_type}"}

        if success:
            return {"success": True, "message": "Test notification sent successfully."}
        return {
            "success": False,
            "message": "Delivery failed. Check channel configuration and credentials.",
        }

    except Exception as exc:
        logger.error("Test notification error for %s: %s", request.channel_type, exc)
        return {"success": False, "message": f"Error: {exc}"}


# ---------------------------------------------------------------------------
# Rule routes
# ---------------------------------------------------------------------------


@router.get("/rules")
async def list_alert_rules() -> list[dict[str, Any]]:
    """List all configured alert rules."""
    return list(_rules.values())


@router.post("/rules")
async def add_alert_rule(request: dict[str, Any]) -> dict[str, Any]:
    """Add a new alert rule.

    Accepts any dict payload, assigns an id, and persists in the in-memory store.
    Returns the rule record including the generated id.
    """
    rule_id = str(uuid.uuid4())
    record: dict[str, Any] = {"id": rule_id, **request}
    _rules[rule_id] = record
    return record


@router.delete("/rules/{rule_id}")
async def remove_alert_rule(rule_id: str) -> dict[str, Any]:
    """Remove an alert rule by id.

    Raises 404 if the rule does not exist.
    """
    if rule_id not in _rules:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    del _rules[rule_id]
    return {"deleted": rule_id}


# ---------------------------------------------------------------------------
# Setup guides
# ---------------------------------------------------------------------------


@router.get("/setup-guides")
async def get_channel_setup_guides() -> dict[str, Any]:
    """Return step-by-step setup instructions and field definitions for each channel type.

    Used by the frontend to dynamically render the channel configuration form.
    """
    return {
        "slack": {
            "title": "Slack",
            "icon": "slack",
            "description": "Send alerts to a Slack channel via incoming webhook.",
            "steps": [
                {
                    "step": 1,
                    "title": "Create a Slack App",
                    "description": "Go to api.slack.com/apps → Create New App → From scratch.",
                },
                {
                    "step": 2,
                    "title": "Enable Incoming Webhooks",
                    "description": "In your app settings, go to Incoming Webhooks → Activate.",
                },
                {
                    "step": 3,
                    "title": "Add webhook to channel",
                    "description": "Click 'Add New Webhook to Workspace' and select your alerts channel.",
                },
                {
                    "step": 4,
                    "title": "Copy webhook URL",
                    "description": "Copy the webhook URL and paste it below.",
                },
            ],
            "fields": [
                {
                    "name": "webhook_url",
                    "label": "Webhook URL",
                    "type": "url",
                    "placeholder": "https://hooks.slack.com/services/...",
                    "required": True,
                },
                {
                    "name": "channel_name",
                    "label": "Channel Name (display only)",
                    "type": "text",
                    "placeholder": "#alerts",
                    "required": False,
                },
            ],
        },
        "teams": {
            "title": "Microsoft Teams",
            "icon": "teams",
            "description": "Send alerts to a Teams channel via incoming webhook connector.",
            "steps": [
                {
                    "step": 1,
                    "title": "Open Teams channel",
                    "description": "Go to the Teams channel where you want alerts.",
                },
                {
                    "step": 2,
                    "title": "Add connector",
                    "description": "Click ··· → Connectors → Incoming Webhook → Configure.",
                },
                {
                    "step": 3,
                    "title": "Name and create",
                    "description": "Name it 'TINAA Alerts' and click Create.",
                },
                {
                    "step": 4,
                    "title": "Copy webhook URL",
                    "description": "Copy the webhook URL and paste it below.",
                },
            ],
            "fields": [
                {
                    "name": "webhook_url",
                    "label": "Webhook URL",
                    "type": "url",
                    "placeholder": "https://outlook.office.com/webhook/...",
                    "required": True,
                },
                {
                    "name": "channel_name",
                    "label": "Channel Name (display only)",
                    "type": "text",
                    "placeholder": "General",
                    "required": False,
                },
            ],
        },
        "pagerduty": {
            "title": "PagerDuty",
            "icon": "pagerduty",
            "description": "Trigger PagerDuty incidents for critical alerts.",
            "steps": [
                {
                    "step": 1,
                    "title": "Create a service",
                    "description": "In PagerDuty, go to Services → New Service → Name it 'TINAA Quality Alerts'.",
                },
                {
                    "step": 2,
                    "title": "Add integration",
                    "description": "Under Integrations, add 'Events API v2'.",
                },
                {
                    "step": 3,
                    "title": "Copy routing key",
                    "description": "Copy the Integration Key (routing key) and paste it below.",
                },
            ],
            "fields": [
                {
                    "name": "routing_key",
                    "label": "Routing Key",
                    "type": "password",
                    "placeholder": "Your PagerDuty routing key",
                    "required": True,
                },
                {
                    "name": "service_name",
                    "label": "Service Name (display only)",
                    "type": "text",
                    "placeholder": "TINAA Quality Alerts",
                    "required": False,
                },
                {
                    "name": "severity_threshold",
                    "label": "Minimum Severity",
                    "type": "select",
                    "options": ["critical", "warning", "info"],
                    "required": True,
                },
            ],
        },
        "email": {
            "title": "Email (SMTP)",
            "icon": "email",
            "description": "Send alert emails via SMTP.",
            "steps": [
                {
                    "step": 1,
                    "title": "Get SMTP credentials",
                    "description": "You'll need your mail server hostname, port, username, and password.",
                },
                {
                    "step": 2,
                    "title": "Configure below",
                    "description": "Enter your SMTP settings and recipient addresses.",
                },
            ],
            "fields": [
                {
                    "name": "smtp_host",
                    "label": "SMTP Host",
                    "type": "text",
                    "placeholder": "smtp.gmail.com",
                    "required": True,
                },
                {
                    "name": "smtp_port",
                    "label": "SMTP Port",
                    "type": "number",
                    "placeholder": "587",
                    "required": True,
                },
                {
                    "name": "username",
                    "label": "Username",
                    "type": "text",
                    "placeholder": "alerts@example.com",
                    "required": True,
                },
                {
                    "name": "password",
                    "label": "Password",
                    "type": "password",
                    "placeholder": "App password",
                    "required": True,
                },
                {
                    "name": "from_address",
                    "label": "From Address",
                    "type": "email",
                    "placeholder": "tinaa@example.com",
                    "required": True,
                },
                {
                    "name": "to_addresses",
                    "label": "To Addresses (comma-separated)",
                    "type": "text",
                    "placeholder": "team@example.com, oncall@example.com",
                    "required": True,
                },
            ],
        },
        "webhook": {
            "title": "Custom Webhook",
            "icon": "webhook",
            "description": "Send alerts as JSON to any HTTP endpoint.",
            "steps": [
                {
                    "step": 1,
                    "title": "Set up endpoint",
                    "description": "Create an HTTP endpoint that accepts POST requests with JSON body.",
                },
                {
                    "step": 2,
                    "title": "Enter URL",
                    "description": "Enter your webhook URL below.",
                },
            ],
            "fields": [
                {
                    "name": "url",
                    "label": "Webhook URL",
                    "type": "url",
                    "placeholder": "https://your-service.com/webhook",
                    "required": True,
                },
                {
                    "name": "method",
                    "label": "HTTP Method",
                    "type": "select",
                    "options": ["POST", "PUT"],
                    "required": True,
                },
            ],
        },
    }
