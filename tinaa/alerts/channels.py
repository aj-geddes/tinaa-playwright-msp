"""
TINAA Alert Channels — Async delivery handlers for alert notifications.

Each channel implements an async send(alert, config) -> bool interface.
Failures are logged and return False rather than raising, ensuring engine
robustness when individual channels are unavailable.
"""

import logging
from typing import Any

import httpx

from tinaa.alerts.rules import Alert, AlertSeverity
from tinaa.alerts.teams_channel import TeamsChannel

logger = logging.getLogger(__name__)

# Re-export so callers can use either tinaa.alerts.channels or tinaa.alerts.teams_channel
__all__ = [
    "EmailChannel",
    "GitHubIssueChannel",
    "PagerDutyChannel",
    "SlackChannel",
    "TeamsChannel",
    "WebhookChannel",
]

# ---------------------------------------------------------------------------
# Slack color constants
# ---------------------------------------------------------------------------

SLACK_COLOR_CRITICAL = "#FF0000"
SLACK_COLOR_WARNING = "#E67E22"
SLACK_COLOR_INFO = "#2196F3"

_SEVERITY_TO_SLACK_COLOR: dict[AlertSeverity, str] = {
    AlertSeverity.CRITICAL: SLACK_COLOR_CRITICAL,
    AlertSeverity.WARNING: SLACK_COLOR_WARNING,
    AlertSeverity.INFO: SLACK_COLOR_INFO,
}

# PagerDuty Events API v2 endpoint
PAGERDUTY_EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"


class SlackChannel:
    """Delivers alerts to Slack via incoming webhook.

    Formats alerts as rich Slack messages with color-coded attachments,
    structured fields, and a link to the TINAA dashboard.
    """

    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    async def send(self, alert: Alert, config: dict[str, Any] | None = None) -> bool:
        """Send alert to Slack.

        Returns True if the message was delivered successfully.
        """
        payload = self._format_message(alert)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self._webhook_url, json=payload)
                response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.error("SlackChannel delivery failed: %s", exc)
            return False
        except Exception as exc:
            logger.error("SlackChannel unexpected error: %s", exc)
            return False

    def _format_message(self, alert: Alert) -> dict[str, Any]:
        """Format alert as a Slack webhook payload.

        Uses legacy attachments format for broad compatibility.
        Color-coded: red=critical, orange=warning, blue=info.
        """
        color = _SEVERITY_TO_SLACK_COLOR.get(alert.severity, SLACK_COLOR_INFO)
        severity_label = alert.severity.value.upper()
        product_label = alert.product_name or alert.product_id or "Unknown"
        title = f"[{severity_label}] TINAA Alert — {product_label}"
        fields = self._build_slack_fields(alert, product_label)
        attachment: dict[str, Any] = {
            "color": color,
            "title": title,
            "text": alert.message,
            "fields": fields,
            "footer": "TINAA MSP",
            "actions": [
                {
                    "type": "button",
                    "text": "View in TINAA Dashboard",
                    "url": "https://tinaa.app/alerts",
                }
            ],
        }
        return {"attachments": [attachment]}

    def _build_slack_fields(self, alert: Alert, product_label: str) -> list[dict[str, Any]]:
        """Build Slack attachment fields from alert data."""
        fields: list[dict[str, Any]] = [
            {
                "title": "Condition",
                "value": alert.condition_type.value.replace("_", " ").title(),
                "short": True,
            },
            {"title": "Product", "value": product_label, "short": True},
        ]
        if alert.environment:
            fields.append({"title": "Environment", "value": alert.environment, "short": True})
        if alert.triggered_at:
            fields.append({"title": "Triggered At", "value": alert.triggered_at, "short": True})
        for key, value in alert.details.items():
            fields.append(
                {"title": key.replace("_", " ").title(), "value": str(value), "short": True}
            )
        return fields


class EmailChannel:
    """Delivers alerts via email (SMTP).

    Requires 'to' addresses in the config dict to send.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._from_addr = from_addr

    async def send(self, alert: Alert, config: dict[str, Any] | None = None) -> bool:
        """Send alert via email.

        config must include:
            to: list[str]  — recipient addresses
        Optionally:
            subject_prefix: str  — e.g. "[TINAA]"

        Returns True if sent successfully, False otherwise.
        """
        cfg = config or {}
        recipients: list[str] = cfg.get("to", [])
        if not recipients:
            logger.warning("EmailChannel: no 'to' addresses configured")
            return False

        subject_prefix = cfg.get("subject_prefix", "[TINAA]")
        subject = (
            f"{subject_prefix} [{alert.severity.value.upper()}] "
            f"{alert.condition_type.value.replace('_', ' ').title()} "
            f"— {alert.product_name or alert.product_id or 'Unknown'}"
        )
        body = self._build_body(alert)

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self._from_addr
            msg["To"] = ", ".join(recipients)
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()
                server.login(self._username, self._password)
                server.sendmail(self._from_addr, recipients, msg.as_string())
            return True
        except Exception as exc:
            logger.error("EmailChannel delivery failed: %s", exc)
            return False

    def _build_body(self, alert: Alert) -> str:
        """Build plain-text email body."""
        lines = [
            f"TINAA Alert — {alert.severity.value.upper()}",
            "",
            f"Product:    {alert.product_name or alert.product_id or 'Unknown'}",
            f"Condition:  {alert.condition_type.value.replace('_', ' ').title()}",
            f"Triggered:  {alert.triggered_at}",
            "",
            alert.message,
        ]
        if alert.details:
            lines.append("")
            lines.append("Details:")
            for key, value in alert.details.items():
                lines.append(f"  {key}: {value}")
        lines.extend(["", "---", "TINAA Managed Service Platform"])
        return "\n".join(lines)


class WebhookChannel:
    """Delivers alerts via HTTP POST webhook.

    The alert is serialised as JSON and POSTed to the configured URL.
    """

    async def send(self, alert: Alert, config: dict[str, Any] | None = None) -> bool:
        """POST alert as JSON to configured webhook URL.

        config must include:
            url: str  — webhook endpoint
        Optionally:
            headers: dict[str, str]  — additional HTTP headers

        Returns True if the server responded with 2xx status.
        """
        cfg = config or {}
        url: str | None = cfg.get("url")
        if not url:
            logger.warning("WebhookChannel: no 'url' configured")
            return False

        headers: dict[str, str] = cfg.get("headers", {})
        payload = self._serialize_alert(alert)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.error("WebhookChannel delivery failed: %s", exc)
            return False
        except Exception as exc:
            logger.error("WebhookChannel unexpected error: %s", exc)
            return False

    def _serialize_alert(self, alert: Alert) -> dict[str, Any]:
        """Serialize alert to a JSON-safe dictionary."""
        return {
            "rule_name": alert.rule_name,
            "severity": alert.severity.value,
            "condition_type": alert.condition_type.value,
            "message": alert.message,
            "details": alert.details,
            "product_id": alert.product_id,
            "product_name": alert.product_name,
            "environment": alert.environment,
            "triggered_at": alert.triggered_at,
            "acknowledged": alert.acknowledged,
            "resolved": alert.resolved,
        }


class PagerDutyChannel:
    """Delivers alerts to PagerDuty via Events API v2."""

    def __init__(self, routing_key: str) -> None:
        self._routing_key = routing_key

    async def send(self, alert: Alert, config: dict[str, Any] | None = None) -> bool:
        """Send alert to PagerDuty Events API v2.

        Maps TINAA severity to PagerDuty severity and builds a v2 event payload.
        Returns True if the event was accepted (HTTP 202).
        """
        payload = self._build_payload(alert)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(PAGERDUTY_EVENTS_URL, json=payload)
                response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.error("PagerDutyChannel delivery failed: %s", exc)
            return False
        except Exception as exc:
            logger.error("PagerDutyChannel unexpected error: %s", exc)
            return False

    def _build_payload(self, alert: Alert) -> dict[str, Any]:
        """Build PagerDuty Events API v2 payload."""
        product_label = alert.product_name or alert.product_id or "Unknown"
        dedup_key = f"tinaa-{alert.rule_name}-{alert.product_id or 'global'}"

        return {
            "routing_key": self._routing_key,
            "event_action": "trigger",
            "dedup_key": dedup_key,
            "payload": {
                "summary": f"[TINAA] {alert.message}",
                "source": product_label,
                "severity": self._map_severity(alert.severity),
                "component": alert.condition_type.value,
                "group": alert.product_id or "global",
                "class": alert.condition_type.value,
                "custom_details": {
                    **alert.details,
                    "environment": alert.environment,
                    "product_name": alert.product_name,
                    "triggered_at": alert.triggered_at,
                },
            },
        }

    def _map_severity(self, severity: AlertSeverity) -> str:
        """Map TINAA severity to PagerDuty severity string."""
        mapping: dict[AlertSeverity, str] = {
            AlertSeverity.CRITICAL: "critical",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.INFO: "info",
        }
        return mapping.get(severity, "warning")


class GitHubIssueChannel:
    """Creates GitHub Issues for alerts."""

    def __init__(self, github_client: Any) -> None:
        self._client = github_client

    async def send(self, alert: Alert, config: dict[str, Any] | None = None) -> bool:
        """Create a GitHub Issue for the alert.

        config must include:
            owner: str  — GitHub organisation or user
            repo:  str  — repository name
        Optionally:
            labels: list[str]  — issue labels (default: ["tinaa-alert"])

        Returns True if the issue was created successfully.
        """
        cfg = config or {}
        owner: str | None = cfg.get("owner")
        repo: str | None = cfg.get("repo")
        if not owner or not repo:
            logger.warning("GitHubIssueChannel: 'owner' and 'repo' are required in config")
            return False

        labels: list[str] = cfg.get("labels", ["tinaa-alert"])
        title = (
            f"[TINAA {alert.severity.value.upper()}] "
            f"{alert.condition_type.value.replace('_', ' ').title()} "
            f"— {alert.product_name or alert.product_id or 'Unknown'}"
        )
        body = self._build_issue_body(alert)

        try:
            await self._client.create_issue(
                owner=owner,
                repo=repo,
                title=title,
                body=body,
                labels=labels,
            )
            return True
        except Exception as exc:
            logger.error("GitHubIssueChannel delivery failed: %s", exc)
            return False

    def _build_issue_body(self, alert: Alert) -> str:
        """Build GitHub Issue markdown body."""
        lines = [
            f"## TINAA Alert — {alert.severity.value.upper()}",
            "",
            f"**Product:** {alert.product_name or alert.product_id or 'Unknown'}",
            f"**Condition:** {alert.condition_type.value.replace('_', ' ').title()}",
            f"**Triggered:** {alert.triggered_at}",
            "",
            "### Summary",
            alert.message,
        ]
        if alert.details:
            lines.append("")
            lines.append("### Details")
            lines.append("| Key | Value |")
            lines.append("|-----|-------|")
            for key, value in alert.details.items():
                lines.append(f"| {key} | {value} |")
        lines.extend(["", "---", "_Generated by TINAA Managed Service Platform_"])
        return "\n".join(lines)
