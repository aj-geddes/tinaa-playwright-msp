"""Microsoft Teams alert channel via incoming webhook."""

import logging
from typing import Any

import httpx

from tinaa.alerts.rules import Alert, AlertSeverity

logger = logging.getLogger(__name__)

# Hex color constants for Teams Adaptive Card severity headers
TEAMS_COLOR_CRITICAL = "#EF4444"
TEAMS_COLOR_WARNING = "#F59E0B"
TEAMS_COLOR_INFO = "#3B82F6"

_SEVERITY_TO_TEAMS_COLOR: dict[AlertSeverity, str] = {
    AlertSeverity.CRITICAL: TEAMS_COLOR_CRITICAL,
    AlertSeverity.WARNING: TEAMS_COLOR_WARNING,
    AlertSeverity.INFO: TEAMS_COLOR_INFO,
}

_SEVERITY_TO_ICON: dict[AlertSeverity, str] = {
    AlertSeverity.CRITICAL: "🔴",
    AlertSeverity.WARNING: "🟠",
    AlertSeverity.INFO: "🔵",
}


class TeamsChannel:
    """Delivers alerts to Microsoft Teams via incoming webhook connector.

    Uses the Teams Adaptive Card format (webhook card envelope) for rich,
    color-coded notifications with structured facts and a dashboard action link.
    """

    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    async def send(self, alert: Alert, config: dict[str, Any] | None = None) -> bool:
        """Send alert to Teams using Adaptive Card format.

        Posts a Teams webhook card envelope containing an Adaptive Card with:
        - Color-coded header (red=critical, orange=warning, blue=info)
        - Title: severity icon + product name + alert type
        - Facts: condition, current value, threshold, environment, timestamp
        - Action button: "View in TINAA Dashboard"

        Returns True if sent successfully, False otherwise.
        """
        payload = self._build_adaptive_card(alert)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self._webhook_url, json=payload)
                response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.error("TeamsChannel delivery failed: %s", exc)
            return False
        except Exception as exc:
            logger.error("TeamsChannel unexpected error: %s", exc)
            return False

    def _build_adaptive_card(self, alert: Alert) -> dict[str, Any]:
        """Build Teams webhook card envelope containing an Adaptive Card payload.

        The outer envelope uses the Teams incoming webhook message format:
        {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": { <AdaptiveCard> }
            }]
        }
        """
        color = self._severity_color(alert.severity)
        icon = _SEVERITY_TO_ICON.get(alert.severity, "🔵")
        severity_label = alert.severity.value.upper()
        product_label = alert.product_name or alert.product_id or "Unknown"
        condition_label = alert.condition_type.value.replace("_", " ").title()
        title_text = f"{icon} [{severity_label}] {product_label} — {condition_label}"

        facts = self._build_facts(alert)

        card_body: list[dict[str, Any]] = [
            {
                "type": "Container",
                "style": "emphasis",
                "bleed": True,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": title_text,
                        "weight": "Bolder",
                        "size": "Medium",
                        "color": "Light",
                        "wrap": True,
                    }
                ],
                "backgroundColor": color,
            },
            {
                "type": "TextBlock",
                "text": alert.message,
                "wrap": True,
                "spacing": "Medium",
            },
            {
                "type": "FactSet",
                "facts": facts,
            },
        ]

        card_actions: list[dict[str, Any]] = [
            {
                "type": "Action.OpenUrl",
                "title": "View in TINAA Dashboard",
                "url": "https://tinaa.app/alerts",
            }
        ]

        adaptive_card: dict[str, Any] = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": card_body,
            "actions": card_actions,
        }

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": adaptive_card,
                }
            ],
        }

    def _build_facts(self, alert: Alert) -> list[dict[str, str]]:
        """Build the FactSet facts list from alert data."""
        facts: list[dict[str, str]] = [
            {
                "title": "Condition",
                "value": alert.condition_type.value.replace("_", " ").title(),
            },
            {
                "title": "Product",
                "value": alert.product_name or alert.product_id or "Unknown",
            },
        ]
        if alert.environment:
            facts.append({"title": "Environment", "value": alert.environment})
        if alert.triggered_at:
            facts.append({"title": "Triggered At", "value": alert.triggered_at})
        for key, value in alert.details.items():
            facts.append({"title": key.replace("_", " ").title(), "value": str(value)})
        return facts

    def _severity_color(self, severity: AlertSeverity) -> str:
        """Map severity to hex color for the card accent header.

        critical → #EF4444 (red)
        warning  → #F59E0B (amber)
        info     → #3B82F6 (blue)
        """
        return _SEVERITY_TO_TEAMS_COLOR.get(severity, TEAMS_COLOR_INFO)
