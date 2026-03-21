"""Configuration data structures for TINAA MSP.

All types are plain dataclasses — no database dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EndpointConfig:
    """Configuration for a single monitored endpoint."""

    path: str
    method: str = "GET"
    endpoint_type: str = "page"  # page, api, health
    performance_budget_ms: int | None = None
    lcp_budget_ms: float | None = None
    cls_budget: float | None = None
    expected_status: int = 200
    max_response_time_ms: int | None = None


@dataclass
class MonitoringConfig:
    """Monitoring frequency and endpoint list for one environment."""

    interval: str = "5m"  # human-readable: "30s", "5m", "1h"
    interval_seconds: int = 300  # computed from interval
    endpoints: list[EndpointConfig] = field(default_factory=list)


@dataclass
class EnvironmentConfig:
    """Configuration for a single deployment environment."""

    name: str
    url: str
    env_type: str = "staging"  # production, staging, development, preview
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)


@dataclass
class QualityGateConfig:
    """Pass/fail thresholds for a quality gate."""

    min_score: float = 80.0
    no_critical_failures: bool = True
    max_performance_regression_percent: float = 20.0
    max_new_accessibility_violations: int = 0


@dataclass
class TestingConfig:
    """Testing schedule and execution configuration."""

    schedule: str | None = None  # cron expression
    on_deploy: bool = True
    on_pr: bool = True
    browsers: list[str] = field(default_factory=lambda: ["chromium"])
    viewports: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"name": "desktop", "width": 1440, "height": 900},
            {"name": "mobile", "width": 375, "height": 812},
        ]
    )
    parallel: bool = False
    retries: int = 0
    timeout_ms: int = 30000


@dataclass
class AlertChannelConfig:
    """Configuration for a single alert delivery channel.

    Supported types and their config keys:

    - slack: ``webhook_url`` or ``channel``
    - email: ``to`` (list), ``from``
    - webhook: ``url``, ``headers`` (dict)
    - pagerduty: ``routing_key``, ``severity_threshold``
    """

    type: str  # slack, email, webhook, pagerduty
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertsConfig:
    """Collection of alert channels and routing rules."""

    channels: list[AlertChannelConfig] = field(default_factory=list)
    rules: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TINAAConfig:
    """Complete TINAA configuration for a product."""

    product_name: str = ""
    team: str = ""
    description: str = ""
    environments: list[EnvironmentConfig] = field(default_factory=list)
    quality_gates: dict[str, QualityGateConfig] = field(default_factory=dict)
    testing: TestingConfig = field(default_factory=TestingConfig)
    alerts: AlertsConfig = field(default_factory=AlertsConfig)
    tags: list[str] = field(default_factory=list)
    ignore_paths: list[str] = field(default_factory=list)
