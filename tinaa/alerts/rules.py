"""
TINAA Alert Rules — Definitions for alert conditions, severities, and channels.

Provides the core data types for the alert system:
- AlertConditionType: what kind of quality issue was detected
- AlertSeverity: how urgent the alert is
- AlertChannel: where to deliver the alert
- AlertRule: when and how to alert
- Alert: a triggered alert instance
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AlertConditionType(str, Enum):
    """Types of conditions that can trigger an alert."""

    QUALITY_SCORE_DROP = "quality_score_drop"
    QUALITY_SCORE_BELOW = "quality_score_below"
    TEST_FAILURE = "test_failure"
    TEST_SUITE_FAILURE = "test_suite_failure"
    PERFORMANCE_REGRESSION = "performance_regression"
    ENDPOINT_DOWN = "endpoint_down"
    ENDPOINT_DEGRADED = "endpoint_degraded"
    SECURITY_ISSUE = "security_issue"
    ACCESSIBILITY_REGRESSION = "accessibility_regression"
    AVAILABILITY_DROP = "availability_drop"
    ERROR_RATE_SPIKE = "error_rate_spike"


class AlertSeverity(str, Enum):
    """Severity levels for alerts."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertChannel(str, Enum):
    """Delivery channels for alert notifications."""

    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    GITHUB_ISSUE = "github_issue"
    PAGERDUTY = "pagerduty"


@dataclass
class AlertRule:
    """Defines when and how to alert.

    Threshold examples by condition_type:
    - quality_score_drop:     {"drop_amount": 10}
    - quality_score_below:    {"min_score": 70}
    - test_failure:           {"max_failures": 0}
    - performance_regression: {"regression_percent": 20}
    - endpoint_down:          {"consecutive_failures": 3}
    - endpoint_degraded:      {"max_response_time_ms": 2000}
    - availability_drop:      {"min_availability": 99.0}
    - error_rate_spike:       {"max_error_rate": 5.0}
    """

    name: str
    condition_type: AlertConditionType
    severity: AlertSeverity = AlertSeverity.WARNING
    channels: list[AlertChannel] = field(default_factory=lambda: [AlertChannel.SLACK])
    threshold: dict[str, Any] = field(default_factory=dict)
    cooldown_minutes: int = 30
    is_active: bool = True
    product_id: str | None = None  # None means global (applies to all products)


@dataclass
class Alert:
    """A triggered alert instance."""

    rule_name: str
    severity: AlertSeverity
    condition_type: AlertConditionType
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    product_id: str | None = None
    product_name: str | None = None
    environment: str | None = None
    triggered_at: str = ""  # ISO timestamp
    acknowledged: bool = False
    resolved: bool = False
