"""
TINAA Alert Engine — Evaluates quality conditions and triggers alerts.

The engine evaluates registered rules against incoming quality metrics
(test results, endpoint health, performance data, security scans) and
dispatches matching alerts through registered channel handlers.

Cooldown windows prevent alert fatigue by suppressing duplicate
notifications within a configurable time period.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from tinaa.alerts.rules import (
    Alert,
    AlertChannel,
    AlertConditionType,
    AlertRule,
    AlertSeverity,
)

logger = logging.getLogger(__name__)

# Default threshold values used when a rule has no explicit threshold key
_DEFAULT_MAX_FAILURES = 0
_DEFAULT_CONSECUTIVE_FAILURES = 3
_DEFAULT_REGRESSION_PERCENT = 30.0
_DEFAULT_MIN_AVAILABILITY = 99.0
_DEFAULT_MAX_ERROR_RATE = 5.0
_DEFAULT_MAX_RESPONSE_TIME_MS = 2000.0

# Pre-built default rule set — instantiated once at import time
_DEFAULT_RULE_SPECS: list[AlertRule] = [
    AlertRule(
        name="default-quality-score-drop",
        condition_type=AlertConditionType.QUALITY_SCORE_DROP,
        severity=AlertSeverity.WARNING,
        threshold={"drop_amount": 10},
        cooldown_minutes=60,
    ),
    AlertRule(
        name="default-quality-score-critical",
        condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
        severity=AlertSeverity.CRITICAL,
        threshold={"min_score": 50},
        cooldown_minutes=30,
    ),
    AlertRule(
        name="default-test-failure",
        condition_type=AlertConditionType.TEST_FAILURE,
        severity=AlertSeverity.WARNING,
        threshold={"max_failures": 0},
        cooldown_minutes=30,
    ),
    AlertRule(
        name="default-endpoint-down",
        condition_type=AlertConditionType.ENDPOINT_DOWN,
        severity=AlertSeverity.CRITICAL,
        threshold={"consecutive_failures": 3},
        cooldown_minutes=15,
    ),
    AlertRule(
        name="default-performance-regression",
        condition_type=AlertConditionType.PERFORMANCE_REGRESSION,
        severity=AlertSeverity.WARNING,
        threshold={"regression_percent": 30},
        cooldown_minutes=60,
    ),
    AlertRule(
        name="default-availability-drop",
        condition_type=AlertConditionType.AVAILABILITY_DROP,
        severity=AlertSeverity.CRITICAL,
        threshold={"min_availability": 99.0},
        cooldown_minutes=30,
    ),
    AlertRule(
        name="default-error-rate-spike",
        condition_type=AlertConditionType.ERROR_RATE_SPIKE,
        severity=AlertSeverity.WARNING,
        threshold={"max_error_rate": 5.0},
        cooldown_minutes=30,
    ),
]


class AlertEngine:
    """Evaluates conditions and triggers alerts.

    Usage::

        engine = AlertEngine()
        for rule in engine.get_default_rules():
            engine.register_rule(rule)

        engine.register_channel(
            AlertChannel.SLACK,
            lambda alert, cfg: slack_channel.send(alert, cfg),
        )

        alerts = await engine.evaluate_quality_score(
            product_id="my-app",
            product_name="My App",
            current_score=58.0,
            previous_score=75.0,
        )
    """

    def __init__(self) -> None:
        self._rules: list[AlertRule] = []
        self._recent_alerts: list[Alert] = []
        self._channel_registry: dict[AlertChannel, Callable] = {}

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def register_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self._rules.append(rule)

    def remove_rule(self, rule_name: str) -> None:
        """Remove an alert rule by name. No-op if the rule does not exist."""
        self._rules = [r for r in self._rules if r.name != rule_name]

    def register_channel(self, channel: AlertChannel, handler: Callable) -> None:
        """Register a channel handler function.

        Handler signature::

            async def handler(alert: Alert, config: dict) -> bool
        """
        self._channel_registry[channel] = handler

    # ------------------------------------------------------------------
    # Evaluation methods
    # ------------------------------------------------------------------

    async def evaluate_quality_score(
        self,
        product_id: str,
        product_name: str,
        current_score: float,
        previous_score: float | None = None,
    ) -> list[Alert]:
        """Evaluate quality score against alert rules.

        Checks: quality_score_drop, quality_score_below.
        Returns the list of triggered Alert instances.
        """
        triggered: list[Alert] = []
        applicable_types = {
            AlertConditionType.QUALITY_SCORE_DROP,
            AlertConditionType.QUALITY_SCORE_BELOW,
        }

        for rule in self._applicable_rules(product_id, applicable_types):
            alert: Alert | None = None

            if rule.condition_type == AlertConditionType.QUALITY_SCORE_DROP:
                alert = self._check_quality_score_drop(
                    rule, product_id, product_name, current_score, previous_score
                )
            elif rule.condition_type == AlertConditionType.QUALITY_SCORE_BELOW:
                alert = self._check_quality_score_below(
                    rule, product_id, product_name, current_score
                )

            if alert is not None:
                sent = await self._trigger_alert(alert, rule.channels)
                if sent:
                    triggered.append(alert)

        return triggered

    async def evaluate_test_results(
        self,
        product_id: str,
        product_name: str,
        test_run: dict[str, Any],
    ) -> list[Alert]:
        """Evaluate test run results against alert rules.

        Checks: test_failure, test_suite_failure.
        test_run expected keys: total, passed, failed, suite (optional).
        """
        triggered: list[Alert] = []
        applicable_types = {
            AlertConditionType.TEST_FAILURE,
            AlertConditionType.TEST_SUITE_FAILURE,
        }

        for rule in self._applicable_rules(product_id, applicable_types):
            alert: Alert | None = None

            if rule.condition_type == AlertConditionType.TEST_FAILURE:
                alert = self._check_test_failure(rule, product_id, product_name, test_run)
            elif rule.condition_type == AlertConditionType.TEST_SUITE_FAILURE:
                alert = self._check_test_suite_failure(rule, product_id, product_name, test_run)

            if alert is not None:
                sent = await self._trigger_alert(alert, rule.channels)
                if sent:
                    triggered.append(alert)

        return triggered

    async def evaluate_endpoint_health(
        self,
        product_id: str,
        product_name: str,
        endpoint_path: str,
        probe_result: dict[str, Any],
    ) -> list[Alert]:
        """Evaluate endpoint health against alert rules.

        Checks: endpoint_down, endpoint_degraded, availability_drop, error_rate_spike.
        probe_result expected keys: status, consecutive_failures (optional),
        response_time_ms (optional), availability_percent (optional), error_rate (optional).
        """
        triggered: list[Alert] = []
        applicable_types = {
            AlertConditionType.ENDPOINT_DOWN,
            AlertConditionType.ENDPOINT_DEGRADED,
            AlertConditionType.AVAILABILITY_DROP,
            AlertConditionType.ERROR_RATE_SPIKE,
        }

        for rule in self._applicable_rules(product_id, applicable_types):
            alert: Alert | None = None

            if rule.condition_type == AlertConditionType.ENDPOINT_DOWN:
                alert = self._check_endpoint_down(
                    rule, product_id, product_name, endpoint_path, probe_result
                )
            elif rule.condition_type == AlertConditionType.ENDPOINT_DEGRADED:
                alert = self._check_endpoint_degraded(
                    rule, product_id, product_name, endpoint_path, probe_result
                )
            elif rule.condition_type == AlertConditionType.AVAILABILITY_DROP:
                alert = self._check_availability_drop(
                    rule, product_id, product_name, endpoint_path, probe_result
                )
            elif rule.condition_type == AlertConditionType.ERROR_RATE_SPIKE:
                alert = self._check_error_rate_spike(
                    rule, product_id, product_name, endpoint_path, probe_result
                )

            if alert is not None:
                sent = await self._trigger_alert(alert, rule.channels)
                if sent:
                    triggered.append(alert)

        return triggered

    async def evaluate_performance(
        self,
        product_id: str,
        product_name: str,
        endpoint_path: str,
        current_value: float,
        baseline_p95: float,
        metric_type: str,
    ) -> list[Alert]:
        """Evaluate performance against alert rules.

        Checks: performance_regression.
        Regression is computed as ((current - baseline) / baseline) * 100.
        """
        triggered: list[Alert] = []
        applicable_types = {AlertConditionType.PERFORMANCE_REGRESSION}

        for rule in self._applicable_rules(product_id, applicable_types):
            alert = self._check_performance_regression(
                rule,
                product_id,
                product_name,
                endpoint_path,
                current_value,
                baseline_p95,
                metric_type,
            )
            if alert is not None:
                sent = await self._trigger_alert(alert, rule.channels)
                if sent:
                    triggered.append(alert)

        return triggered

    async def evaluate_security(
        self,
        product_id: str,
        product_name: str,
        security_results: dict[str, Any],
    ) -> list[Alert]:
        """Evaluate security scan results.

        Checks: security_issue.
        security_results expected key: issues — list of issue dicts.
        """
        triggered: list[Alert] = []
        applicable_types = {AlertConditionType.SECURITY_ISSUE}

        for rule in self._applicable_rules(product_id, applicable_types):
            alert = self._check_security_issue(rule, product_id, product_name, security_results)
            if alert is not None:
                sent = await self._trigger_alert(alert, rule.channels)
                if sent:
                    triggered.append(alert)

        return triggered

    # ------------------------------------------------------------------
    # Trigger and cooldown
    # ------------------------------------------------------------------

    async def _trigger_alert(self, alert: Alert, channels: list[AlertChannel]) -> bool:
        """Trigger an alert through configured channels.

        Respects cooldown periods — returns False if the rule is in cooldown.
        Handles channel delivery failures gracefully (logs and continues).
        Returns True if the alert was dispatched (not in cooldown).
        """
        cooldown = self._lookup_cooldown(alert.rule_name)
        if self._is_in_cooldown(alert.rule_name, cooldown):
            logger.debug("Alert '%s' suppressed by cooldown (%d min)", alert.rule_name, cooldown)
            return False

        alert.triggered_at = datetime.now(UTC).isoformat()
        self._recent_alerts.append(alert)

        for channel in channels:
            handler = self._channel_registry.get(channel)
            if handler is None:
                logger.debug("No handler registered for channel '%s'", channel.value)
                continue
            try:
                await handler(alert, {})
            except Exception as exc:
                logger.error(
                    "Channel '%s' failed for alert '%s': %s",
                    channel.value,
                    alert.rule_name,
                    exc,
                )

        return True

    def _is_in_cooldown(self, rule_name: str, cooldown_minutes: int) -> bool:
        """Check if a rule is in its cooldown period.

        Returns True if a non-resolved alert for this rule was triggered
        within the cooldown window.
        """
        if cooldown_minutes <= 0:
            return False

        cutoff = datetime.now(UTC) - timedelta(minutes=cooldown_minutes)

        for alert in reversed(self._recent_alerts):
            if alert.rule_name != rule_name:
                continue
            if not alert.triggered_at:
                continue
            try:
                triggered = datetime.fromisoformat(alert.triggered_at)
                # Ensure timezone-aware comparison
                if triggered.tzinfo is None:
                    triggered = triggered.replace(tzinfo=UTC)
                if triggered >= cutoff:
                    return True
            except ValueError:
                continue

        return False

    def _lookup_cooldown(self, rule_name: str) -> int:
        """Return cooldown_minutes for a named rule, or 30 as fallback."""
        for rule in self._rules:
            if rule.name == rule_name:
                return rule.cooldown_minutes
        return 30

    # ------------------------------------------------------------------
    # Alert management
    # ------------------------------------------------------------------

    def get_active_alerts(self, product_id: str | None = None) -> list[Alert]:
        """Get recent unresolved alerts, optionally filtered by product."""
        alerts = [a for a in self._recent_alerts if not a.resolved]
        if product_id is not None:
            alerts = [a for a in alerts if a.product_id == product_id]
        return alerts

    def acknowledge_alert(self, alert_index: int, acknowledged_by: str) -> bool:
        """Acknowledge an alert by its index in _recent_alerts.

        Returns True if the alert was found and acknowledged.
        """
        if alert_index < 0 or alert_index >= len(self._recent_alerts):
            return False
        self._recent_alerts[alert_index].acknowledged = True
        logger.info("Alert %d acknowledged by %s", alert_index, acknowledged_by)
        return True

    def resolve_alert(self, alert_index: int) -> bool:
        """Mark an alert as resolved by its index in _recent_alerts.

        Returns True if the alert was found and resolved.
        """
        if alert_index < 0 or alert_index >= len(self._recent_alerts):
            return False
        self._recent_alerts[alert_index].resolved = True
        return True

    def get_default_rules(self) -> list[AlertRule]:
        """Return sensible default alert rules for a new product.

        Defaults:
        - Quality score drops by 10+ points → warning
        - Quality score below 50 → critical
        - Any test failure → warning
        - Endpoint down 3+ consecutive checks → critical
        - Performance regression > 30% → warning
        - Availability below 99% → critical
        - Error rate above 5% → warning
        """
        return [rule for rule in _DEFAULT_RULE_SPECS]

    # ------------------------------------------------------------------
    # Private condition checkers
    # ------------------------------------------------------------------

    def _applicable_rules(
        self,
        product_id: str,
        condition_types: set[AlertConditionType],
    ) -> list[AlertRule]:
        """Return active rules matching the given condition types and product scope."""
        return [
            r
            for r in self._rules
            if r.is_active
            and r.condition_type in condition_types
            and (r.product_id is None or r.product_id == product_id)
        ]

    def _check_quality_score_drop(
        self,
        rule: AlertRule,
        product_id: str,
        product_name: str,
        current_score: float,
        previous_score: float | None,
    ) -> Alert | None:
        if previous_score is None:
            return None
        drop_amount: float = rule.threshold.get("drop_amount", 10.0)
        actual_drop = previous_score - current_score
        if actual_drop < drop_amount:
            return None
        return Alert(
            rule_name=rule.name,
            severity=rule.severity,
            condition_type=AlertConditionType.QUALITY_SCORE_DROP,
            message=(
                f"Quality score dropped by {actual_drop:.1f} points "
                f"({previous_score:.1f} → {current_score:.1f}) for {product_name}"
            ),
            details={
                "previous_score": previous_score,
                "current_score": current_score,
                "drop_amount": actual_drop,
                "threshold": drop_amount,
            },
            product_id=product_id,
            product_name=product_name,
        )

    def _check_quality_score_below(
        self,
        rule: AlertRule,
        product_id: str,
        product_name: str,
        current_score: float,
    ) -> Alert | None:
        min_score: float = rule.threshold.get("min_score", 70.0)
        if current_score >= min_score:
            return None
        return Alert(
            rule_name=rule.name,
            severity=rule.severity,
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            message=(
                f"Quality score {current_score:.1f} is below minimum threshold "
                f"{min_score:.1f} for {product_name}"
            ),
            details={
                "current_score": current_score,
                "min_score": min_score,
            },
            product_id=product_id,
            product_name=product_name,
        )

    def _check_test_failure(
        self,
        rule: AlertRule,
        product_id: str,
        product_name: str,
        test_run: dict[str, Any],
    ) -> Alert | None:
        failed: int = test_run.get("failed", 0)
        max_failures: int = rule.threshold.get("max_failures", _DEFAULT_MAX_FAILURES)
        if failed <= max_failures:
            return None
        total: int = test_run.get("total", 0)
        suite: str = test_run.get("suite", "unknown")
        return Alert(
            rule_name=rule.name,
            severity=rule.severity,
            condition_type=AlertConditionType.TEST_FAILURE,
            message=(
                f"{failed} test(s) failed in suite '{suite}' ({failed}/{total}) for {product_name}"
            ),
            details={
                "failures": failed,
                "failed": failed,
                "total": total,
                "passed": test_run.get("passed", 0),
                "suite": suite,
            },
            product_id=product_id,
            product_name=product_name,
        )

    def _check_test_suite_failure(
        self,
        rule: AlertRule,
        product_id: str,
        product_name: str,
        test_run: dict[str, Any],
    ) -> Alert | None:
        total: int = test_run.get("total", 0)
        passed: int = test_run.get("passed", 0)
        failed: int = test_run.get("failed", 0)
        suite: str = test_run.get("suite", "unknown")

        # Suite failure: all tests failed or explicit 100% failure rate
        if total == 0 or passed > 0:
            return None

        return Alert(
            rule_name=rule.name,
            severity=rule.severity,
            condition_type=AlertConditionType.TEST_SUITE_FAILURE,
            message=(f"Entire test suite '{suite}' failed ({failed}/{total}) for {product_name}"),
            details={
                "failures": failed,
                "failed": failed,
                "total": total,
                "suite": suite,
            },
            product_id=product_id,
            product_name=product_name,
        )

    def _check_endpoint_down(
        self,
        rule: AlertRule,
        product_id: str,
        product_name: str,
        endpoint_path: str,
        probe_result: dict[str, Any],
    ) -> Alert | None:
        consecutive: int = probe_result.get("consecutive_failures", 0)
        threshold: int = rule.threshold.get("consecutive_failures", _DEFAULT_CONSECUTIVE_FAILURES)
        if consecutive < threshold:
            return None
        return Alert(
            rule_name=rule.name,
            severity=rule.severity,
            condition_type=AlertConditionType.ENDPOINT_DOWN,
            message=(
                f"Endpoint {endpoint_path} is down "
                f"({consecutive} consecutive failures) for {product_name}"
            ),
            details={
                "endpoint": endpoint_path,
                "consecutive_failures": consecutive,
                "threshold": threshold,
            },
            product_id=product_id,
            product_name=product_name,
        )

    def _check_endpoint_degraded(
        self,
        rule: AlertRule,
        product_id: str,
        product_name: str,
        endpoint_path: str,
        probe_result: dict[str, Any],
    ) -> Alert | None:
        response_time: float | None = probe_result.get("response_time_ms")
        if response_time is None:
            return None
        max_rt: float = rule.threshold.get("max_response_time_ms", _DEFAULT_MAX_RESPONSE_TIME_MS)
        if response_time <= max_rt:
            return None
        return Alert(
            rule_name=rule.name,
            severity=rule.severity,
            condition_type=AlertConditionType.ENDPOINT_DEGRADED,
            message=(
                f"Endpoint {endpoint_path} is degraded — response time "
                f"{response_time:.0f}ms exceeds {max_rt:.0f}ms threshold "
                f"for {product_name}"
            ),
            details={
                "endpoint": endpoint_path,
                "response_time_ms": response_time,
                "max_response_time_ms": max_rt,
            },
            product_id=product_id,
            product_name=product_name,
        )

    def _check_availability_drop(
        self,
        rule: AlertRule,
        product_id: str,
        product_name: str,
        endpoint_path: str,
        probe_result: dict[str, Any],
    ) -> Alert | None:
        availability: float | None = probe_result.get("availability_percent")
        if availability is None:
            return None
        min_availability: float = rule.threshold.get("min_availability", _DEFAULT_MIN_AVAILABILITY)
        if availability >= min_availability:
            return None
        return Alert(
            rule_name=rule.name,
            severity=rule.severity,
            condition_type=AlertConditionType.AVAILABILITY_DROP,
            message=(
                f"Endpoint {endpoint_path} availability {availability:.2f}% is below "
                f"minimum {min_availability:.2f}% for {product_name}"
            ),
            details={
                "endpoint": endpoint_path,
                "availability_percent": availability,
                "min_availability": min_availability,
            },
            product_id=product_id,
            product_name=product_name,
        )

    def _check_error_rate_spike(
        self,
        rule: AlertRule,
        product_id: str,
        product_name: str,
        endpoint_path: str,
        probe_result: dict[str, Any],
    ) -> Alert | None:
        error_rate: float | None = probe_result.get("error_rate")
        if error_rate is None:
            return None
        max_error_rate: float = rule.threshold.get("max_error_rate", _DEFAULT_MAX_ERROR_RATE)
        if error_rate <= max_error_rate:
            return None
        return Alert(
            rule_name=rule.name,
            severity=rule.severity,
            condition_type=AlertConditionType.ERROR_RATE_SPIKE,
            message=(
                f"Error rate {error_rate:.1f}% exceeds maximum {max_error_rate:.1f}% "
                f"on {endpoint_path} for {product_name}"
            ),
            details={
                "endpoint": endpoint_path,
                "error_rate": error_rate,
                "max_error_rate": max_error_rate,
            },
            product_id=product_id,
            product_name=product_name,
        )

    def _check_performance_regression(
        self,
        rule: AlertRule,
        product_id: str,
        product_name: str,
        endpoint_path: str,
        current_value: float,
        baseline_p95: float,
        metric_type: str,
    ) -> Alert | None:
        if baseline_p95 <= 0:
            return None
        regression_pct = ((current_value - baseline_p95) / baseline_p95) * 100.0
        if regression_pct <= 0:
            return None  # improvement, not a regression
        threshold_pct: float = rule.threshold.get("regression_percent", _DEFAULT_REGRESSION_PERCENT)
        if regression_pct < threshold_pct:
            return None
        return Alert(
            rule_name=rule.name,
            severity=rule.severity,
            condition_type=AlertConditionType.PERFORMANCE_REGRESSION,
            message=(
                f"Performance regression detected on {endpoint_path}: "
                f"{metric_type} increased by {regression_pct:.1f}% "
                f"({baseline_p95:.1f} → {current_value:.1f}) for {product_name}"
            ),
            details={
                "endpoint": endpoint_path,
                "metric_type": metric_type,
                "current_value": current_value,
                "baseline_p95": baseline_p95,
                "regression_percent": round(regression_pct, 2),
                "threshold_percent": threshold_pct,
            },
            product_id=product_id,
            product_name=product_name,
        )

    def _check_security_issue(
        self,
        rule: AlertRule,
        product_id: str,
        product_name: str,
        security_results: dict[str, Any],
    ) -> Alert | None:
        issues: list[dict[str, Any]] = security_results.get("issues", [])
        if not issues:
            return None
        issue_count = len(issues)
        severities = [i.get("severity", "unknown") for i in issues]
        return Alert(
            rule_name=rule.name,
            severity=rule.severity,
            condition_type=AlertConditionType.SECURITY_ISSUE,
            message=(
                f"{issue_count} security issue(s) detected for {product_name}: "
                + ", ".join(i.get("title", "unknown") for i in issues[:3])
                + ("..." if issue_count > 3 else "")
            ),
            details={
                "issue_count": issue_count,
                "severities": severities,
                "issues": issues,
            },
            product_id=product_id,
            product_name=product_name,
        )
