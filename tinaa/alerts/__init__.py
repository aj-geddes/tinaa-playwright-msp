"""
TINAA Alerts — Proactive quality issue notification system.

Fuses test failures, APM anomalies, endpoint downtime, security issues,
and quality score drops into actionable alerts delivered through multiple
channels (Slack, email, webhooks, GitHub Issues, PagerDuty).
"""

from tinaa.alerts.channels import (
    EmailChannel,
    GitHubIssueChannel,
    PagerDutyChannel,
    SlackChannel,
    WebhookChannel,
)
from tinaa.alerts.engine import AlertEngine
from tinaa.alerts.rules import (
    Alert,
    AlertChannel,
    AlertConditionType,
    AlertRule,
    AlertSeverity,
)

__all__ = [
    "Alert",
    "AlertChannel",
    "AlertConditionType",
    "AlertEngine",
    "AlertRule",
    "AlertSeverity",
    "EmailChannel",
    "GitHubIssueChannel",
    "PagerDutyChannel",
    "SlackChannel",
    "WebhookChannel",
]
