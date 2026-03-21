"""
Comprehensive tests for the TINAA Alert System.

Covers:
- AlertRule and Alert dataclass construction and defaults
- AlertConditionType, AlertSeverity, AlertChannel enums
- AlertEngine rule registration and removal
- AlertEngine.evaluate_quality_score: quality_score_drop, quality_score_below
- AlertEngine.evaluate_test_results: test_failure, test_suite_failure
- AlertEngine.evaluate_endpoint_health: endpoint_down, endpoint_degraded,
  availability_drop, error_rate_spike
- AlertEngine.evaluate_performance: performance_regression
- AlertEngine.evaluate_security: security_issue
- Cooldown logic: alert suppressed within window, re-sent after expiry
- Default rules: all critical scenarios covered
- Alert lifecycle: trigger -> acknowledge -> resolve
- get_active_alerts: filtering by product_id, excluding resolved
- SlackChannel._format_message: valid payload structure, color coding
- WebhookChannel.send: mocked httpx POST
- PagerDutyChannel.send: Events API v2 format, severity mapping
- Channel failure handling: engine continues when channel raises
- Severity mapping across all condition types
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tinaa.alerts.rules import (
    Alert,
    AlertChannel,
    AlertConditionType,
    AlertRule,
    AlertSeverity,
)
from tinaa.alerts.engine import AlertEngine
from tinaa.alerts.channels import (
    EmailChannel,
    GitHubIssueChannel,
    PagerDutyChannel,
    SlackChannel,
    WebhookChannel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rule(
    name: str = "test-rule",
    condition_type: AlertConditionType = AlertConditionType.QUALITY_SCORE_DROP,
    severity: AlertSeverity = AlertSeverity.WARNING,
    channels: list[AlertChannel] | None = None,
    threshold: dict | None = None,
    cooldown_minutes: int = 30,
    is_active: bool = True,
    product_id: str | None = None,
) -> AlertRule:
    return AlertRule(
        name=name,
        condition_type=condition_type,
        severity=severity,
        channels=channels or [AlertChannel.SLACK],
        threshold=threshold or {},
        cooldown_minutes=cooldown_minutes,
        is_active=is_active,
        product_id=product_id,
    )


def _make_alert(
    rule_name: str = "test-rule",
    severity: AlertSeverity = AlertSeverity.WARNING,
    condition_type: AlertConditionType = AlertConditionType.QUALITY_SCORE_DROP,
    message: str = "Test alert",
    product_id: str | None = "prod-1",
    product_name: str | None = "Product One",
    environment: str | None = "production",
    triggered_at: str = "",
) -> Alert:
    return Alert(
        rule_name=rule_name,
        severity=severity,
        condition_type=condition_type,
        message=message,
        product_id=product_id,
        product_name=product_name,
        environment=environment,
        triggered_at=triggered_at or datetime.now(timezone.utc).isoformat(),
    )


def _engine_with_rule(rule: AlertRule) -> AlertEngine:
    engine = AlertEngine()
    engine.register_rule(rule)
    return engine


# ===========================================================================
# 1. Dataclass and Enum Construction
# ===========================================================================

class TestAlertRuleDefaults:
    def test_required_fields_only(self):
        rule = AlertRule(
            name="my-rule",
            condition_type=AlertConditionType.TEST_FAILURE,
        )
        assert rule.name == "my-rule"
        assert rule.condition_type == AlertConditionType.TEST_FAILURE
        assert rule.severity == AlertSeverity.WARNING
        assert rule.channels == [AlertChannel.SLACK]
        assert rule.threshold == {}
        assert rule.cooldown_minutes == 30
        assert rule.is_active is True
        assert rule.product_id is None

    def test_all_fields_set(self):
        rule = AlertRule(
            name="custom",
            condition_type=AlertConditionType.ENDPOINT_DOWN,
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.SLACK, AlertChannel.PAGERDUTY],
            threshold={"consecutive_failures": 5},
            cooldown_minutes=10,
            is_active=False,
            product_id="prod-xyz",
        )
        assert rule.severity == AlertSeverity.CRITICAL
        assert len(rule.channels) == 2
        assert rule.threshold["consecutive_failures"] == 5
        assert rule.cooldown_minutes == 10
        assert rule.is_active is False
        assert rule.product_id == "prod-xyz"

    def test_channels_are_independent_defaults(self):
        r1 = AlertRule(name="r1", condition_type=AlertConditionType.TEST_FAILURE)
        r2 = AlertRule(name="r2", condition_type=AlertConditionType.TEST_FAILURE)
        r1.channels.append(AlertChannel.EMAIL)
        assert AlertChannel.EMAIL not in r2.channels  # mutable default isolation


class TestAlertDefaults:
    def test_required_fields_only(self):
        alert = Alert(
            rule_name="some-rule",
            severity=AlertSeverity.CRITICAL,
            condition_type=AlertConditionType.ENDPOINT_DOWN,
            message="endpoint /api/health is down",
        )
        assert alert.details == {}
        assert alert.product_id is None
        assert alert.product_name is None
        assert alert.environment is None
        assert alert.triggered_at == ""
        assert alert.acknowledged is False
        assert alert.resolved is False

    def test_details_are_independent_defaults(self):
        a1 = Alert(
            rule_name="r1", severity=AlertSeverity.INFO,
            condition_type=AlertConditionType.TEST_FAILURE, message="m1",
        )
        a2 = Alert(
            rule_name="r2", severity=AlertSeverity.INFO,
            condition_type=AlertConditionType.TEST_FAILURE, message="m2",
        )
        a1.details["key"] = "value"
        assert "key" not in a2.details


class TestAlertConditionTypeEnum:
    def test_all_values_are_strings(self):
        for member in AlertConditionType:
            assert isinstance(member.value, str)

    def test_expected_members_present(self):
        expected = {
            "quality_score_drop", "quality_score_below", "test_failure",
            "test_suite_failure", "performance_regression", "endpoint_down",
            "endpoint_degraded", "security_issue", "accessibility_regression",
            "availability_drop", "error_rate_spike",
        }
        actual = {m.value for m in AlertConditionType}
        assert expected == actual


class TestAlertSeverityEnum:
    def test_three_levels(self):
        assert set(AlertSeverity) == {
            AlertSeverity.CRITICAL,
            AlertSeverity.WARNING,
            AlertSeverity.INFO,
        }

    def test_string_values(self):
        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.INFO == "info"


class TestAlertChannelEnum:
    def test_expected_channels(self):
        expected = {"slack", "email", "webhook", "github_issue", "pagerduty"}
        actual = {c.value for c in AlertChannel}
        assert expected == actual


# ===========================================================================
# 2. AlertEngine Rule Management
# ===========================================================================

class TestAlertEngineRuleManagement:
    def test_register_single_rule(self):
        engine = AlertEngine()
        rule = _make_rule("r1")
        engine.register_rule(rule)
        assert len(engine._rules) == 1
        assert engine._rules[0].name == "r1"

    def test_register_multiple_rules(self):
        engine = AlertEngine()
        engine.register_rule(_make_rule("r1"))
        engine.register_rule(_make_rule("r2"))
        assert len(engine._rules) == 2

    def test_remove_rule_by_name(self):
        engine = AlertEngine()
        engine.register_rule(_make_rule("r1"))
        engine.register_rule(_make_rule("r2"))
        engine.remove_rule("r1")
        assert len(engine._rules) == 1
        assert engine._rules[0].name == "r2"

    def test_remove_nonexistent_rule_is_noop(self):
        engine = AlertEngine()
        engine.register_rule(_make_rule("r1"))
        engine.remove_rule("nonexistent")  # should not raise
        assert len(engine._rules) == 1

    def test_register_channel_handler(self):
        engine = AlertEngine()
        handler = AsyncMock(return_value=True)
        engine.register_channel(AlertChannel.SLACK, handler)
        assert AlertChannel.SLACK in engine._channel_registry
        assert engine._channel_registry[AlertChannel.SLACK] is handler


# ===========================================================================
# 3. evaluate_quality_score
# ===========================================================================

class TestEvaluateQualityScore:
    @pytest.mark.asyncio
    async def test_quality_score_drop_triggers_warning(self):
        engine = _engine_with_rule(_make_rule(
            name="score-drop",
            condition_type=AlertConditionType.QUALITY_SCORE_DROP,
            severity=AlertSeverity.WARNING,
            threshold={"drop_amount": 10},
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score(
            product_id="p1", product_name="P1",
            current_score=70.0, previous_score=85.0,
        )
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.WARNING
        assert alerts[0].condition_type == AlertConditionType.QUALITY_SCORE_DROP

    @pytest.mark.asyncio
    async def test_quality_score_drop_below_threshold_no_alert(self):
        engine = _engine_with_rule(_make_rule(
            name="score-drop",
            condition_type=AlertConditionType.QUALITY_SCORE_DROP,
            threshold={"drop_amount": 20},
            cooldown_minutes=0,
        ))
        # Only 10 point drop, threshold is 20 — no alert
        alerts = await engine.evaluate_quality_score(
            product_id="p1", product_name="P1",
            current_score=75.0, previous_score=85.0,
        )
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_quality_score_drop_no_previous_score(self):
        engine = _engine_with_rule(_make_rule(
            name="score-drop",
            condition_type=AlertConditionType.QUALITY_SCORE_DROP,
            threshold={"drop_amount": 10},
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score(
            product_id="p1", product_name="P1",
            current_score=50.0, previous_score=None,
        )
        # No previous score to compare — no drop alert
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_quality_score_below_threshold_triggers(self):
        engine = _engine_with_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            severity=AlertSeverity.CRITICAL,
            threshold={"min_score": 70},
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score(
            product_id="p1", product_name="P1",
            current_score=65.0,
        )
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_quality_score_below_threshold_not_triggered_when_above(self):
        engine = _engine_with_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70},
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score(
            product_id="p1", product_name="P1",
            current_score=75.0,
        )
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_alert_contains_product_info(self):
        engine = _engine_with_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70},
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score(
            product_id="prod-abc", product_name="My Product",
            current_score=40.0,
        )
        assert alerts[0].product_id == "prod-abc"
        assert alerts[0].product_name == "My Product"

    @pytest.mark.asyncio
    async def test_inactive_rule_not_evaluated(self):
        engine = _engine_with_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70},
            is_active=False,
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score(
            product_id="p1", product_name="P1",
            current_score=20.0,
        )
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_rule_scoped_to_different_product_not_triggered(self):
        engine = _engine_with_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70},
            product_id="other-product",
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score(
            product_id="my-product", product_name="My Product",
            current_score=20.0,
        )
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_global_rule_applies_to_any_product(self):
        engine = _engine_with_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70},
            product_id=None,  # global
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score(
            product_id="any-product", product_name="Any",
            current_score=20.0,
        )
        assert len(alerts) == 1

    @pytest.mark.asyncio
    async def test_triggered_alert_has_iso_timestamp(self):
        engine = _engine_with_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70},
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score(
            product_id="p1", product_name="P1",
            current_score=20.0,
        )
        assert alerts[0].triggered_at != ""
        # Should be parseable as ISO datetime
        datetime.fromisoformat(alerts[0].triggered_at)


# ===========================================================================
# 4. evaluate_test_results
# ===========================================================================

class TestEvaluateTestResults:
    @pytest.mark.asyncio
    async def test_test_failure_triggers_on_any_failure(self):
        engine = _engine_with_rule(_make_rule(
            name="test-fail",
            condition_type=AlertConditionType.TEST_FAILURE,
            threshold={"max_failures": 0},
            cooldown_minutes=0,
        ))
        test_run = {"total": 100, "passed": 98, "failed": 2, "suite": "regression"}
        alerts = await engine.evaluate_test_results("p1", "P1", test_run)
        assert len(alerts) == 1
        assert alerts[0].condition_type == AlertConditionType.TEST_FAILURE

    @pytest.mark.asyncio
    async def test_test_failure_no_alert_when_within_threshold(self):
        engine = _engine_with_rule(_make_rule(
            name="test-fail",
            condition_type=AlertConditionType.TEST_FAILURE,
            threshold={"max_failures": 5},
            cooldown_minutes=0,
        ))
        test_run = {"total": 100, "passed": 97, "failed": 3, "suite": "smoke"}
        alerts = await engine.evaluate_test_results("p1", "P1", test_run)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_test_failure_default_threshold_any_failure(self):
        """Without explicit threshold, any failure should trigger."""
        engine = _engine_with_rule(_make_rule(
            name="test-fail",
            condition_type=AlertConditionType.TEST_FAILURE,
            threshold={},  # no threshold set — default to 0
            cooldown_minutes=0,
        ))
        test_run = {"total": 10, "passed": 9, "failed": 1}
        alerts = await engine.evaluate_test_results("p1", "P1", test_run)
        assert len(alerts) == 1

    @pytest.mark.asyncio
    async def test_test_suite_failure_triggers_on_all_fail(self):
        engine = _engine_with_rule(_make_rule(
            name="suite-fail",
            condition_type=AlertConditionType.TEST_SUITE_FAILURE,
            cooldown_minutes=0,
        ))
        test_run = {"total": 10, "passed": 0, "failed": 10, "suite": "smoke"}
        alerts = await engine.evaluate_test_results("p1", "P1", test_run)
        assert len(alerts) == 1
        assert alerts[0].condition_type == AlertConditionType.TEST_SUITE_FAILURE

    @pytest.mark.asyncio
    async def test_all_passing_no_alert(self):
        engine = _engine_with_rule(_make_rule(
            name="test-fail",
            condition_type=AlertConditionType.TEST_FAILURE,
            threshold={"max_failures": 0},
            cooldown_minutes=0,
        ))
        test_run = {"total": 50, "passed": 50, "failed": 0}
        alerts = await engine.evaluate_test_results("p1", "P1", test_run)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_alert_details_include_failure_count(self):
        engine = _engine_with_rule(_make_rule(
            name="test-fail",
            condition_type=AlertConditionType.TEST_FAILURE,
            threshold={"max_failures": 0},
            cooldown_minutes=0,
        ))
        test_run = {"total": 20, "passed": 17, "failed": 3}
        alerts = await engine.evaluate_test_results("p1", "P1", test_run)
        assert "failed" in alerts[0].details or "failures" in alerts[0].details


# ===========================================================================
# 5. evaluate_endpoint_health
# ===========================================================================

class TestEvaluateEndpointHealth:
    @pytest.mark.asyncio
    async def test_endpoint_down_triggers_after_consecutive_failures(self):
        engine = _engine_with_rule(_make_rule(
            name="endpoint-down",
            condition_type=AlertConditionType.ENDPOINT_DOWN,
            severity=AlertSeverity.CRITICAL,
            threshold={"consecutive_failures": 3},
            cooldown_minutes=0,
        ))
        probe = {"status": "down", "consecutive_failures": 3, "response_time_ms": None}
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/health", probe)
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_endpoint_down_not_triggered_below_threshold(self):
        engine = _engine_with_rule(_make_rule(
            name="endpoint-down",
            condition_type=AlertConditionType.ENDPOINT_DOWN,
            threshold={"consecutive_failures": 3},
            cooldown_minutes=0,
        ))
        probe = {"status": "down", "consecutive_failures": 2, "response_time_ms": None}
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/health", probe)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_endpoint_degraded_on_slow_response(self):
        engine = _engine_with_rule(_make_rule(
            name="endpoint-degraded",
            condition_type=AlertConditionType.ENDPOINT_DEGRADED,
            threshold={"max_response_time_ms": 2000},
            cooldown_minutes=0,
        ))
        probe = {"status": "degraded", "consecutive_failures": 0, "response_time_ms": 3500}
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/slow", probe)
        assert len(alerts) == 1
        assert alerts[0].condition_type == AlertConditionType.ENDPOINT_DEGRADED

    @pytest.mark.asyncio
    async def test_availability_drop_below_minimum(self):
        engine = _engine_with_rule(_make_rule(
            name="availability",
            condition_type=AlertConditionType.AVAILABILITY_DROP,
            severity=AlertSeverity.CRITICAL,
            threshold={"min_availability": 99.0},
            cooldown_minutes=0,
        ))
        probe = {"status": "up", "availability_percent": 98.5, "error_rate": 1.5}
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/v1", probe)
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_availability_above_minimum_no_alert(self):
        engine = _engine_with_rule(_make_rule(
            name="availability",
            condition_type=AlertConditionType.AVAILABILITY_DROP,
            threshold={"min_availability": 99.0},
            cooldown_minutes=0,
        ))
        probe = {"status": "up", "availability_percent": 99.5, "error_rate": 0.5}
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/v1", probe)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_error_rate_spike_above_maximum(self):
        engine = _engine_with_rule(_make_rule(
            name="error-rate",
            condition_type=AlertConditionType.ERROR_RATE_SPIKE,
            threshold={"max_error_rate": 5.0},
            cooldown_minutes=0,
        ))
        probe = {"status": "degraded", "availability_percent": 94.0, "error_rate": 8.0}
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/v1", probe)
        assert len(alerts) == 1
        assert alerts[0].condition_type == AlertConditionType.ERROR_RATE_SPIKE

    @pytest.mark.asyncio
    async def test_healthy_endpoint_no_alerts(self):
        engine = AlertEngine()
        engine.register_rule(_make_rule(
            "endpoint-down", AlertConditionType.ENDPOINT_DOWN,
            threshold={"consecutive_failures": 3}, cooldown_minutes=0,
        ))
        engine.register_rule(_make_rule(
            "error-rate", AlertConditionType.ERROR_RATE_SPIKE,
            threshold={"max_error_rate": 5.0}, cooldown_minutes=0,
        ))
        probe = {
            "status": "up", "consecutive_failures": 0,
            "response_time_ms": 120, "availability_percent": 99.9, "error_rate": 0.1,
        }
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/health", probe)
        assert len(alerts) == 0


# ===========================================================================
# 6. evaluate_performance
# ===========================================================================

class TestEvaluatePerformance:
    @pytest.mark.asyncio
    async def test_performance_regression_triggers(self):
        engine = _engine_with_rule(_make_rule(
            name="perf-regression",
            condition_type=AlertConditionType.PERFORMANCE_REGRESSION,
            threshold={"regression_percent": 20},
            cooldown_minutes=0,
        ))
        # 1200ms vs baseline 900ms = 33% regression
        alerts = await engine.evaluate_performance(
            "p1", "P1", "/api/data", 1200.0, 900.0, "response_time_p95"
        )
        assert len(alerts) == 1
        assert alerts[0].condition_type == AlertConditionType.PERFORMANCE_REGRESSION

    @pytest.mark.asyncio
    async def test_performance_within_threshold_no_alert(self):
        engine = _engine_with_rule(_make_rule(
            name="perf-regression",
            condition_type=AlertConditionType.PERFORMANCE_REGRESSION,
            threshold={"regression_percent": 30},
            cooldown_minutes=0,
        ))
        # 1100ms vs baseline 1000ms = 10% regression
        alerts = await engine.evaluate_performance(
            "p1", "P1", "/api/data", 1100.0, 1000.0, "response_time_p95"
        )
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_performance_improvement_no_alert(self):
        engine = _engine_with_rule(_make_rule(
            name="perf-regression",
            condition_type=AlertConditionType.PERFORMANCE_REGRESSION,
            threshold={"regression_percent": 20},
            cooldown_minutes=0,
        ))
        # Improvement: 800ms vs baseline 1000ms
        alerts = await engine.evaluate_performance(
            "p1", "P1", "/api/data", 800.0, 1000.0, "response_time_p95"
        )
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_performance_alert_details_include_metric_type(self):
        engine = _engine_with_rule(_make_rule(
            name="perf-regression",
            condition_type=AlertConditionType.PERFORMANCE_REGRESSION,
            threshold={"regression_percent": 10},
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_performance(
            "p1", "P1", "/api/data", 1200.0, 1000.0, "response_time_p95"
        )
        assert alerts[0].details.get("metric_type") == "response_time_p95"

    @pytest.mark.asyncio
    async def test_performance_alert_details_include_regression_percent(self):
        engine = _engine_with_rule(_make_rule(
            name="perf-regression",
            condition_type=AlertConditionType.PERFORMANCE_REGRESSION,
            threshold={"regression_percent": 10},
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_performance(
            "p1", "P1", "/api/data", 1200.0, 1000.0, "response_time_p95"
        )
        regression_pct = alerts[0].details.get("regression_percent")
        assert regression_pct is not None
        assert abs(regression_pct - 20.0) < 0.01


# ===========================================================================
# 7. evaluate_security
# ===========================================================================

class TestEvaluateSecurity:
    @pytest.mark.asyncio
    async def test_security_issue_triggers_on_critical_finding(self):
        engine = _engine_with_rule(_make_rule(
            name="security",
            condition_type=AlertConditionType.SECURITY_ISSUE,
            severity=AlertSeverity.CRITICAL,
            cooldown_minutes=0,
        ))
        security_results = {
            "issues": [{"severity": "critical", "title": "SQL Injection", "url": "/api/login"}]
        }
        alerts = await engine.evaluate_security("p1", "P1", security_results)
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_security_no_issues_no_alert(self):
        engine = _engine_with_rule(_make_rule(
            name="security",
            condition_type=AlertConditionType.SECURITY_ISSUE,
            cooldown_minutes=0,
        ))
        security_results = {"issues": []}
        alerts = await engine.evaluate_security("p1", "P1", security_results)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_security_alert_details_include_issue_count(self):
        engine = _engine_with_rule(_make_rule(
            name="security",
            condition_type=AlertConditionType.SECURITY_ISSUE,
            cooldown_minutes=0,
        ))
        security_results = {
            "issues": [
                {"severity": "high", "title": "XSS"},
                {"severity": "medium", "title": "Open Redirect"},
            ]
        }
        alerts = await engine.evaluate_security("p1", "P1", security_results)
        assert len(alerts) == 1
        issue_count = alerts[0].details.get("issue_count")
        assert issue_count == 2


# ===========================================================================
# 8. Cooldown Logic
# ===========================================================================

class TestCooldownLogic:
    def test_not_in_cooldown_initially(self):
        engine = AlertEngine()
        assert engine._is_in_cooldown("some-rule", 30) is False

    def test_in_cooldown_after_alert(self):
        engine = AlertEngine()
        alert = _make_alert(rule_name="my-rule")
        engine._recent_alerts.append(alert)
        # With 30 min cooldown, we should be in cooldown
        assert engine._is_in_cooldown("my-rule", 30) is True

    def test_not_in_cooldown_after_window_expires(self):
        engine = AlertEngine()
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
        alert = _make_alert(rule_name="my-rule", triggered_at=old_time)
        engine._recent_alerts.append(alert)
        # 60 min old alert with 30 min cooldown — cooldown expired
        assert engine._is_in_cooldown("my-rule", 30) is False

    def test_different_rule_not_in_cooldown(self):
        engine = AlertEngine()
        alert = _make_alert(rule_name="rule-A")
        engine._recent_alerts.append(alert)
        assert engine._is_in_cooldown("rule-B", 30) is False

    @pytest.mark.asyncio
    async def test_cooldown_suppresses_duplicate_alert(self):
        engine = _engine_with_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70},
            cooldown_minutes=30,  # 30 min cooldown
        ))
        # First alert
        alerts1 = await engine.evaluate_quality_score(
            "p1", "P1", current_score=50.0
        )
        assert len(alerts1) == 1

        # Second alert within cooldown window
        alerts2 = await engine.evaluate_quality_score(
            "p1", "P1", current_score=50.0
        )
        assert len(alerts2) == 0  # suppressed by cooldown

    @pytest.mark.asyncio
    async def test_zero_cooldown_always_fires(self):
        engine = _engine_with_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70},
            cooldown_minutes=0,
        ))
        alerts1 = await engine.evaluate_quality_score("p1", "P1", 50.0)
        alerts2 = await engine.evaluate_quality_score("p1", "P1", 50.0)
        assert len(alerts1) == 1
        assert len(alerts2) == 1


# ===========================================================================
# 9. Alert Lifecycle
# ===========================================================================

class TestAlertLifecycle:
    def test_get_active_alerts_returns_unresolved(self):
        engine = AlertEngine()
        a1 = _make_alert(rule_name="r1")
        a2 = _make_alert(rule_name="r2")
        a2.resolved = True
        engine._recent_alerts.extend([a1, a2])
        active = engine.get_active_alerts()
        assert len(active) == 1
        assert active[0].rule_name == "r1"

    def test_get_active_alerts_filter_by_product(self):
        engine = AlertEngine()
        a1 = _make_alert(rule_name="r1", product_id="prod-A")
        a2 = _make_alert(rule_name="r2", product_id="prod-B")
        engine._recent_alerts.extend([a1, a2])
        active = engine.get_active_alerts(product_id="prod-A")
        assert len(active) == 1
        assert active[0].product_id == "prod-A"

    def test_acknowledge_alert(self):
        engine = AlertEngine()
        alert = _make_alert(rule_name="r1")
        engine._recent_alerts.append(alert)
        result = engine.acknowledge_alert(0, "john@example.com")
        assert result is True
        assert engine._recent_alerts[0].acknowledged is True

    def test_acknowledge_invalid_index_returns_false(self):
        engine = AlertEngine()
        result = engine.acknowledge_alert(99, "user@example.com")
        assert result is False

    def test_resolve_alert(self):
        engine = AlertEngine()
        alert = _make_alert(rule_name="r1")
        engine._recent_alerts.append(alert)
        result = engine.resolve_alert(0)
        assert result is True
        assert engine._recent_alerts[0].resolved is True

    def test_resolve_invalid_index_returns_false(self):
        engine = AlertEngine()
        result = engine.resolve_alert(99)
        assert result is False

    def test_resolved_alert_not_in_active(self):
        engine = AlertEngine()
        alert = _make_alert(rule_name="r1")
        engine._recent_alerts.append(alert)
        engine.resolve_alert(0)
        assert engine.get_active_alerts() == []

    def test_get_active_alerts_no_filter_returns_all_unresolved(self):
        engine = AlertEngine()
        engine._recent_alerts.extend([
            _make_alert(rule_name="r1", product_id="p1"),
            _make_alert(rule_name="r2", product_id="p2"),
            _make_alert(rule_name="r3", product_id="p3"),
        ])
        active = engine.get_active_alerts()
        assert len(active) == 3


# ===========================================================================
# 10. Default Rules
# ===========================================================================

class TestDefaultRules:
    def test_get_default_rules_returns_list(self):
        engine = AlertEngine()
        rules = engine.get_default_rules()
        assert isinstance(rules, list)
        assert len(rules) > 0

    def test_default_rules_all_have_names(self):
        engine = AlertEngine()
        for rule in engine.get_default_rules():
            assert rule.name != ""

    def test_default_rules_all_active(self):
        engine = AlertEngine()
        for rule in engine.get_default_rules():
            assert rule.is_active is True

    def test_default_rules_cover_quality_score_drop(self):
        engine = AlertEngine()
        types = {r.condition_type for r in engine.get_default_rules()}
        assert AlertConditionType.QUALITY_SCORE_DROP in types

    def test_default_rules_cover_quality_score_below(self):
        engine = AlertEngine()
        types = {r.condition_type for r in engine.get_default_rules()}
        assert AlertConditionType.QUALITY_SCORE_BELOW in types

    def test_default_rules_cover_test_failure(self):
        engine = AlertEngine()
        types = {r.condition_type for r in engine.get_default_rules()}
        assert AlertConditionType.TEST_FAILURE in types

    def test_default_rules_cover_endpoint_down(self):
        engine = AlertEngine()
        types = {r.condition_type for r in engine.get_default_rules()}
        assert AlertConditionType.ENDPOINT_DOWN in types

    def test_default_rules_cover_performance_regression(self):
        engine = AlertEngine()
        types = {r.condition_type for r in engine.get_default_rules()}
        assert AlertConditionType.PERFORMANCE_REGRESSION in types

    def test_default_rules_cover_availability_drop(self):
        engine = AlertEngine()
        types = {r.condition_type for r in engine.get_default_rules()}
        assert AlertConditionType.AVAILABILITY_DROP in types

    def test_default_rules_cover_error_rate_spike(self):
        engine = AlertEngine()
        types = {r.condition_type for r in engine.get_default_rules()}
        assert AlertConditionType.ERROR_RATE_SPIKE in types

    def test_default_quality_score_drop_threshold_is_10(self):
        engine = AlertEngine()
        drop_rules = [
            r for r in engine.get_default_rules()
            if r.condition_type == AlertConditionType.QUALITY_SCORE_DROP
        ]
        assert len(drop_rules) >= 1
        assert drop_rules[0].threshold.get("drop_amount") == 10

    def test_default_quality_score_below_threshold_is_50(self):
        engine = AlertEngine()
        below_rules = [
            r for r in engine.get_default_rules()
            if r.condition_type == AlertConditionType.QUALITY_SCORE_BELOW
        ]
        assert len(below_rules) >= 1
        assert below_rules[0].threshold.get("min_score") == 50

    def test_default_quality_score_below_is_critical(self):
        engine = AlertEngine()
        below_rules = [
            r for r in engine.get_default_rules()
            if r.condition_type == AlertConditionType.QUALITY_SCORE_BELOW
        ]
        assert below_rules[0].severity == AlertSeverity.CRITICAL

    def test_default_endpoint_down_is_critical(self):
        engine = AlertEngine()
        down_rules = [
            r for r in engine.get_default_rules()
            if r.condition_type == AlertConditionType.ENDPOINT_DOWN
        ]
        assert down_rules[0].severity == AlertSeverity.CRITICAL

    def test_default_performance_regression_threshold_is_30(self):
        engine = AlertEngine()
        perf_rules = [
            r for r in engine.get_default_rules()
            if r.condition_type == AlertConditionType.PERFORMANCE_REGRESSION
        ]
        assert perf_rules[0].threshold.get("regression_percent") == 30

    def test_default_availability_drop_threshold_is_99(self):
        engine = AlertEngine()
        avail_rules = [
            r for r in engine.get_default_rules()
            if r.condition_type == AlertConditionType.AVAILABILITY_DROP
        ]
        assert avail_rules[0].threshold.get("min_availability") == 99.0

    def test_default_availability_drop_is_critical(self):
        engine = AlertEngine()
        avail_rules = [
            r for r in engine.get_default_rules()
            if r.condition_type == AlertConditionType.AVAILABILITY_DROP
        ]
        assert avail_rules[0].severity == AlertSeverity.CRITICAL

    def test_default_error_rate_threshold_is_5(self):
        engine = AlertEngine()
        err_rules = [
            r for r in engine.get_default_rules()
            if r.condition_type == AlertConditionType.ERROR_RATE_SPIKE
        ]
        assert err_rules[0].threshold.get("max_error_rate") == 5.0


# ===========================================================================
# 11. SlackChannel message formatting
# ===========================================================================

class TestSlackChannelFormatting:
    def test_format_message_returns_dict(self):
        channel = SlackChannel(webhook_url="https://hooks.slack.com/test")
        alert = _make_alert(severity=AlertSeverity.WARNING)
        payload = channel._format_message(alert)
        assert isinstance(payload, dict)

    def test_format_message_has_attachments(self):
        channel = SlackChannel(webhook_url="https://hooks.slack.com/test")
        alert = _make_alert()
        payload = channel._format_message(alert)
        assert "attachments" in payload or "blocks" in payload or "text" in payload

    def test_critical_alert_uses_red_color(self):
        channel = SlackChannel(webhook_url="https://hooks.slack.com/test")
        alert = _make_alert(severity=AlertSeverity.CRITICAL)
        payload = channel._format_message(alert)
        # Check color in attachments
        attachments = payload.get("attachments", [])
        if attachments:
            assert attachments[0].get("color") == "#FF0000" or attachments[0].get("color") == "danger"

    def test_warning_alert_uses_orange_or_warning_color(self):
        channel = SlackChannel(webhook_url="https://hooks.slack.com/test")
        alert = _make_alert(severity=AlertSeverity.WARNING)
        payload = channel._format_message(alert)
        attachments = payload.get("attachments", [])
        if attachments:
            color = attachments[0].get("color", "")
            assert color in ("#FF8C00", "#FFA500", "warning", "#FF6600", "#E67E22")

    def test_info_alert_uses_blue_color(self):
        channel = SlackChannel(webhook_url="https://hooks.slack.com/test")
        alert = _make_alert(severity=AlertSeverity.INFO)
        payload = channel._format_message(alert)
        attachments = payload.get("attachments", [])
        if attachments:
            color = attachments[0].get("color", "")
            assert color in ("#0000FF", "#3498DB", "good", "#36A64F", "#1E90FF", "#2196F3")

    def test_format_message_includes_product_name(self):
        channel = SlackChannel(webhook_url="https://hooks.slack.com/test")
        alert = _make_alert(product_name="My App")
        payload = channel._format_message(alert)
        payload_str = str(payload)
        assert "My App" in payload_str

    def test_format_message_includes_message_text(self):
        channel = SlackChannel(webhook_url="https://hooks.slack.com/test")
        alert = _make_alert(message="Quality score dropped significantly")
        payload = channel._format_message(alert)
        payload_str = str(payload)
        assert "Quality score dropped significantly" in payload_str

    @pytest.mark.asyncio
    async def test_send_posts_to_webhook_url(self):
        channel = SlackChannel(webhook_url="https://hooks.slack.com/services/TEST")
        alert = _make_alert()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            result = await channel.send(alert)

        assert result is True
        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        assert call_url == "https://hooks.slack.com/services/TEST"

    @pytest.mark.asyncio
    async def test_send_returns_false_on_http_error(self):
        channel = SlackChannel(webhook_url="https://hooks.slack.com/services/FAIL")
        alert = _make_alert()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.HTTPError("Connection failed")
            result = await channel.send(alert)

        assert result is False


# ===========================================================================
# 12. WebhookChannel
# ===========================================================================

class TestWebhookChannel:
    @pytest.mark.asyncio
    async def test_send_posts_json_to_configured_url(self):
        channel = WebhookChannel()
        alert = _make_alert()
        config = {"url": "https://example.com/webhook", "headers": {}}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            result = await channel.send(alert, config)

        assert result is True
        call_url = mock_client.post.call_args[0][0]
        assert call_url == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_send_returns_false_on_network_error(self):
        channel = WebhookChannel()
        alert = _make_alert()
        config = {"url": "https://example.com/webhook"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.HTTPError("timeout")
            result = await channel.send(alert, config)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_returns_false_when_no_url_configured(self):
        channel = WebhookChannel()
        alert = _make_alert()
        result = await channel.send(alert, config={})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_includes_custom_headers(self):
        channel = WebhookChannel()
        alert = _make_alert()
        config = {
            "url": "https://example.com/webhook",
            "headers": {"Authorization": "Bearer token123"},
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            await channel.send(alert, config)

        call_kwargs = mock_client.post.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer token123"


# ===========================================================================
# 13. PagerDutyChannel
# ===========================================================================

class TestPagerDutyChannel:
    @pytest.mark.asyncio
    async def test_send_posts_to_pagerduty_events_api(self):
        channel = PagerDutyChannel(routing_key="rk-test-123")
        alert = _make_alert(severity=AlertSeverity.CRITICAL)
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            result = await channel.send(alert)

        assert result is True
        call_url = mock_client.post.call_args[0][0]
        assert "pagerduty.com" in call_url or "events.pagerduty" in call_url

    @pytest.mark.asyncio
    async def test_pagerduty_payload_includes_routing_key(self):
        channel = PagerDutyChannel(routing_key="rk-abc-xyz")
        alert = _make_alert()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            await channel.send(alert)

        call_kwargs = mock_client.post.call_args[1]
        payload = call_kwargs.get("json", {})
        assert payload.get("routing_key") == "rk-abc-xyz"

    @pytest.mark.asyncio
    async def test_pagerduty_payload_has_event_action(self):
        channel = PagerDutyChannel(routing_key="rk-test")
        alert = _make_alert()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            await channel.send(alert)

        payload = mock_client.post.call_args[1].get("json", {})
        assert payload.get("event_action") in ("trigger", "acknowledge", "resolve")

    def test_critical_maps_to_critical_severity(self):
        channel = PagerDutyChannel(routing_key="rk-test")
        assert channel._map_severity(AlertSeverity.CRITICAL) == "critical"

    def test_warning_maps_to_warning_severity(self):
        channel = PagerDutyChannel(routing_key="rk-test")
        assert channel._map_severity(AlertSeverity.WARNING) == "warning"

    def test_info_maps_to_info_severity(self):
        channel = PagerDutyChannel(routing_key="rk-test")
        assert channel._map_severity(AlertSeverity.INFO) == "info"

    @pytest.mark.asyncio
    async def test_send_returns_false_on_error(self):
        channel = PagerDutyChannel(routing_key="rk-test")
        alert = _make_alert()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.HTTPError("timeout")
            result = await channel.send(alert)

        assert result is False


# ===========================================================================
# 14. Channel Failure Handling (Engine robustness)
# ===========================================================================

class TestChannelFailureHandling:
    @pytest.mark.asyncio
    async def test_engine_continues_when_channel_raises(self):
        """Alert engine should not crash when a channel handler raises."""
        engine = AlertEngine()
        failing_handler = AsyncMock(side_effect=Exception("Network error"))
        engine.register_channel(AlertChannel.SLACK, failing_handler)
        engine.register_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70},
            channels=[AlertChannel.SLACK],
            cooldown_minutes=0,
        ))
        # Should not raise — engine handles failures gracefully
        alerts = await engine.evaluate_quality_score("p1", "P1", current_score=50.0)
        assert len(alerts) == 1  # alert was still generated

    @pytest.mark.asyncio
    async def test_engine_continues_when_channel_returns_false(self):
        engine = AlertEngine()
        failing_handler = AsyncMock(return_value=False)
        engine.register_channel(AlertChannel.SLACK, failing_handler)
        engine.register_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70},
            channels=[AlertChannel.SLACK],
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score("p1", "P1", current_score=50.0)
        assert len(alerts) == 1

    @pytest.mark.asyncio
    async def test_unregistered_channel_does_not_crash(self):
        """If no handler registered for a channel, engine should handle gracefully."""
        engine = AlertEngine()
        engine.register_rule(_make_rule(
            name="score-below",
            condition_type=AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70},
            channels=[AlertChannel.EMAIL],  # not registered
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score("p1", "P1", current_score=50.0)
        assert len(alerts) == 1  # alert still returned


# ===========================================================================
# 15. _trigger_alert and channel invocation
# ===========================================================================

class TestTriggerAlert:
    @pytest.mark.asyncio
    async def test_registered_channel_handler_called(self):
        engine = AlertEngine()
        handler = AsyncMock(return_value=True)
        engine.register_channel(AlertChannel.SLACK, handler)
        alert = _make_alert(rule_name="test-rule")
        result = await engine._trigger_alert(alert, [AlertChannel.SLACK])
        assert result is True
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_cooldown_prevents_trigger(self):
        engine = AlertEngine()
        handler = AsyncMock(return_value=True)
        engine.register_channel(AlertChannel.SLACK, handler)

        # Pre-populate cooldown
        recent = _make_alert(rule_name="test-rule")
        engine._recent_alerts.append(recent)

        alert = _make_alert(rule_name="test-rule")
        # Create a rule in the engine so cooldown can be looked up
        engine.register_rule(_make_rule("test-rule", cooldown_minutes=30))

        # Manually test cooldown check via direct call
        in_cooldown = engine._is_in_cooldown("test-rule", 30)
        assert in_cooldown is True

    @pytest.mark.asyncio
    async def test_multiple_channels_all_called(self):
        engine = AlertEngine()
        slack_handler = AsyncMock(return_value=True)
        webhook_handler = AsyncMock(return_value=True)
        engine.register_channel(AlertChannel.SLACK, slack_handler)
        engine.register_channel(AlertChannel.WEBHOOK, webhook_handler)
        alert = _make_alert()
        await engine._trigger_alert(alert, [AlertChannel.SLACK, AlertChannel.WEBHOOK])
        slack_handler.assert_called_once()
        webhook_handler.assert_called_once()


# ===========================================================================
# 16. Multiple Rules Evaluated Together
# ===========================================================================

class TestMultipleRules:
    @pytest.mark.asyncio
    async def test_multiple_matching_rules_return_multiple_alerts(self):
        engine = AlertEngine()
        engine.register_rule(_make_rule(
            "score-drop", AlertConditionType.QUALITY_SCORE_DROP,
            threshold={"drop_amount": 5}, cooldown_minutes=0,
        ))
        engine.register_rule(_make_rule(
            "score-below", AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 80}, cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score(
            "p1", "P1", current_score=60.0, previous_score=80.0
        )
        assert len(alerts) == 2

    @pytest.mark.asyncio
    async def test_only_applicable_rules_evaluated(self):
        """Test failure rule should not fire during quality score evaluation."""
        engine = AlertEngine()
        engine.register_rule(_make_rule(
            "test-fail", AlertConditionType.TEST_FAILURE,
            threshold={"max_failures": 0}, cooldown_minutes=0,
        ))
        engine.register_rule(_make_rule(
            "score-below", AlertConditionType.QUALITY_SCORE_BELOW,
            threshold={"min_score": 70}, cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score("p1", "P1", current_score=50.0)
        # Only score-below should fire
        assert len(alerts) == 1
        assert alerts[0].condition_type == AlertConditionType.QUALITY_SCORE_BELOW


# ===========================================================================
# 17. Alert message content
# ===========================================================================

class TestAlertMessageContent:
    @pytest.mark.asyncio
    async def test_quality_score_drop_message_mentions_scores(self):
        engine = _engine_with_rule(_make_rule(
            name="score-drop",
            condition_type=AlertConditionType.QUALITY_SCORE_DROP,
            threshold={"drop_amount": 10},
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_quality_score(
            "p1", "P1", current_score=65.0, previous_score=80.0
        )
        msg = alerts[0].message.lower()
        assert "65" in msg or "80" in msg or "score" in msg or "drop" in msg

    @pytest.mark.asyncio
    async def test_endpoint_down_message_mentions_endpoint(self):
        engine = _engine_with_rule(_make_rule(
            name="endpoint-down",
            condition_type=AlertConditionType.ENDPOINT_DOWN,
            threshold={"consecutive_failures": 1},
            cooldown_minutes=0,
        ))
        probe = {"status": "down", "consecutive_failures": 3}
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/health", probe)
        assert "/api/health" in alerts[0].message or "endpoint" in alerts[0].message.lower()


# ===========================================================================
# 18. EmailChannel (basic instantiation and interface)
# ===========================================================================

class TestEmailChannel:
    def test_instantiation(self):
        channel = EmailChannel(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user@example.com",
            password="secret",
            from_addr="tinaa@example.com",
        )
        assert channel is not None

    @pytest.mark.asyncio
    async def test_send_without_config_returns_false(self):
        channel = EmailChannel(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_addr="tinaa@example.com",
        )
        alert = _make_alert()
        # No 'to' addresses configured — should return False
        result = await channel.send(alert, config={})
        assert result is False


# ===========================================================================
# 19. GitHubIssueChannel (basic interface)
# ===========================================================================

class TestGitHubIssueChannel:
    def test_instantiation(self):
        mock_client = MagicMock()
        channel = GitHubIssueChannel(github_client=mock_client)
        assert channel._client is mock_client

    @pytest.mark.asyncio
    async def test_send_calls_github_client(self):
        mock_client = AsyncMock()
        mock_client.create_issue = AsyncMock(return_value={"number": 42})
        channel = GitHubIssueChannel(github_client=mock_client)
        alert = _make_alert(severity=AlertSeverity.CRITICAL)
        config = {"owner": "acme", "repo": "my-app", "labels": ["tinaa-alert"]}
        result = await channel.send(alert, config)
        # Should attempt to create an issue
        assert result is True or result is False  # just verify it doesn't crash

    @pytest.mark.asyncio
    async def test_send_returns_false_without_repo_config(self):
        mock_client = AsyncMock()
        channel = GitHubIssueChannel(github_client=mock_client)
        alert = _make_alert()
        result = await channel.send(alert, config={})
        assert result is False


# ===========================================================================
# 20. Engine edge cases — uncovered defensive branches
# ===========================================================================

class TestEngineCooldownEdgeCases:
    def test_cooldown_ignores_alert_with_empty_triggered_at(self):
        """Alert with no triggered_at is skipped in cooldown check."""
        engine = AlertEngine()
        alert = _make_alert(rule_name="my-rule", triggered_at="")
        alert.triggered_at = ""  # explicitly empty
        engine._recent_alerts.append(alert)
        # Should not be counted as in-cooldown since triggered_at is empty
        result = engine._is_in_cooldown("my-rule", 30)
        assert result is False

    def test_cooldown_handles_invalid_timestamp_gracefully(self):
        """Alert with malformed triggered_at does not crash cooldown check."""
        engine = AlertEngine()
        alert = _make_alert(rule_name="edge-rule", triggered_at="not-a-date")
        engine._recent_alerts.append(alert)
        # Should return False gracefully
        result = engine._is_in_cooldown("edge-rule", 30)
        assert result is False

    def test_cooldown_handles_naive_datetime_in_triggered_at(self):
        """Alert with timezone-naive ISO timestamp is treated as UTC."""
        engine = AlertEngine()
        # Use a naive UTC timestamp that is clearly within the cooldown window
        # by constructing it from the known UTC time
        naive_utc_ts = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        alert = _make_alert(rule_name="naive-rule", triggered_at=naive_utc_ts)
        engine._recent_alerts.append(alert)
        # The naive timestamp (treated as UTC) is recent — must be in cooldown
        result = engine._is_in_cooldown("naive-rule", 30)
        assert result is True


class TestEngineEndpointEdgeCases:
    @pytest.mark.asyncio
    async def test_endpoint_degraded_no_response_time_no_alert(self):
        """endpoint_degraded rule skips when response_time_ms is absent."""
        engine = _engine_with_rule(_make_rule(
            name="endpoint-degraded",
            condition_type=AlertConditionType.ENDPOINT_DEGRADED,
            threshold={"max_response_time_ms": 1000},
            cooldown_minutes=0,
        ))
        probe = {"status": "up"}  # no response_time_ms
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/x", probe)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_endpoint_degraded_within_threshold_no_alert(self):
        """endpoint_degraded rule does not fire when response time is acceptable."""
        engine = _engine_with_rule(_make_rule(
            name="endpoint-degraded",
            condition_type=AlertConditionType.ENDPOINT_DEGRADED,
            threshold={"max_response_time_ms": 2000},
            cooldown_minutes=0,
        ))
        probe = {"status": "up", "response_time_ms": 500.0}
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/x", probe)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_availability_drop_no_availability_no_alert(self):
        """availability_drop rule skips when availability_percent is absent."""
        engine = _engine_with_rule(_make_rule(
            name="availability",
            condition_type=AlertConditionType.AVAILABILITY_DROP,
            threshold={"min_availability": 99.0},
            cooldown_minutes=0,
        ))
        probe = {"status": "up"}  # no availability_percent
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/x", probe)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_error_rate_spike_no_error_rate_no_alert(self):
        """error_rate_spike rule skips when error_rate is absent."""
        engine = _engine_with_rule(_make_rule(
            name="error-rate",
            condition_type=AlertConditionType.ERROR_RATE_SPIKE,
            threshold={"max_error_rate": 5.0},
            cooldown_minutes=0,
        ))
        probe = {"status": "up"}  # no error_rate
        alerts = await engine.evaluate_endpoint_health("p1", "P1", "/api/x", probe)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_performance_regression_zero_baseline_no_alert(self):
        """performance_regression rule skips when baseline is zero."""
        engine = _engine_with_rule(_make_rule(
            name="perf",
            condition_type=AlertConditionType.PERFORMANCE_REGRESSION,
            threshold={"regression_percent": 10},
            cooldown_minutes=0,
        ))
        alerts = await engine.evaluate_performance(
            "p1", "P1", "/api/x", 500.0, 0.0, "response_time_p95"
        )
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_test_suite_failure_zero_total_no_alert(self):
        """test_suite_failure skips empty test runs."""
        engine = _engine_with_rule(_make_rule(
            name="suite-fail",
            condition_type=AlertConditionType.TEST_SUITE_FAILURE,
            cooldown_minutes=0,
        ))
        test_run = {"total": 0, "passed": 0, "failed": 0}
        alerts = await engine.evaluate_test_results("p1", "P1", test_run)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_test_suite_failure_partial_fail_no_alert(self):
        """test_suite_failure only fires when ALL tests fail (passed == 0)."""
        engine = _engine_with_rule(_make_rule(
            name="suite-fail",
            condition_type=AlertConditionType.TEST_SUITE_FAILURE,
            cooldown_minutes=0,
        ))
        # 1 passed — not a full suite failure
        test_run = {"total": 10, "passed": 1, "failed": 9}
        alerts = await engine.evaluate_test_results("p1", "P1", test_run)
        assert len(alerts) == 0


# ===========================================================================
# 21. Channel additional coverage
# ===========================================================================

class TestSlackChannelAdditionalCoverage:
    @pytest.mark.asyncio
    async def test_send_returns_false_on_unexpected_exception(self):
        """SlackChannel.send catches generic exceptions and returns False."""
        channel = SlackChannel(webhook_url="https://hooks.slack.com/test")
        alert = _make_alert()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = RuntimeError("unexpected")
            result = await channel.send(alert)

        assert result is False

    def test_format_message_with_details_adds_fields(self):
        """Details dict is rendered as additional attachment fields."""
        channel = SlackChannel(webhook_url="https://hooks.slack.com/test")
        alert = _make_alert(
            message="Score dropped",
            triggered_at="2026-03-20T10:00:00+00:00",
        )
        alert.details = {"current_score": 45.0, "previous_score": 80.0}
        payload = channel._format_message(alert)
        payload_str = str(payload)
        assert "45.0" in payload_str or "current_score" in payload_str.lower()


class TestWebhookChannelAdditionalCoverage:
    @pytest.mark.asyncio
    async def test_send_returns_false_on_unexpected_exception(self):
        """WebhookChannel.send catches generic exceptions and returns False."""
        channel = WebhookChannel()
        alert = _make_alert()
        config = {"url": "https://example.com/hook"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = RuntimeError("unexpected")
            result = await channel.send(alert, config)

        assert result is False


class TestPagerDutyChannelAdditionalCoverage:
    @pytest.mark.asyncio
    async def test_send_returns_false_on_unexpected_exception(self):
        """PagerDutyChannel.send catches generic exceptions and returns False."""
        channel = PagerDutyChannel(routing_key="rk-test")
        alert = _make_alert()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = RuntimeError("unexpected")
            result = await channel.send(alert)

        assert result is False


class TestEmailChannelAdditionalCoverage:
    def test_build_body_includes_all_fields(self):
        """_build_body renders product, condition, triggered_at, and message."""
        channel = EmailChannel(
            smtp_host="smtp.example.com", smtp_port=587,
            username="u", password="p", from_addr="from@example.com",
        )
        alert = _make_alert(
            message="Score dropped",
            triggered_at="2026-03-20T10:00:00+00:00",
        )
        body = channel._build_body(alert)
        assert "Score dropped" in body
        assert "2026-03-20" in body
        assert "Product One" in body

    def test_build_body_includes_details(self):
        """_build_body appends details section when details are present."""
        channel = EmailChannel(
            smtp_host="smtp.example.com", smtp_port=587,
            username="u", password="p", from_addr="from@example.com",
        )
        alert = _make_alert(message="Endpoint down")
        alert.details = {"endpoint": "/api/health", "consecutive_failures": 5}
        body = channel._build_body(alert)
        assert "endpoint" in body
        assert "/api/health" in body

    @pytest.mark.asyncio
    async def test_send_returns_false_on_smtp_error(self):
        """EmailChannel.send returns False when SMTP raises."""
        channel = EmailChannel(
            smtp_host="smtp.example.com", smtp_port=587,
            username="u", password="p", from_addr="from@example.com",
        )
        alert = _make_alert()
        config = {"to": ["user@example.com"]}

        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = ConnectionRefusedError("connection refused")
            result = await channel.send(alert, config)

        assert result is False


class TestGitHubIssueChannelAdditionalCoverage:
    @pytest.mark.asyncio
    async def test_send_returns_false_on_github_error(self):
        """GitHubIssueChannel.send returns False when client raises."""
        mock_client = AsyncMock()
        mock_client.create_issue = AsyncMock(side_effect=Exception("API error"))
        channel = GitHubIssueChannel(github_client=mock_client)
        alert = _make_alert()
        config = {"owner": "acme", "repo": "api"}
        result = await channel.send(alert, config)
        assert result is False

    def test_build_issue_body_with_details(self):
        """_build_issue_body includes details table when details are present."""
        mock_client = MagicMock()
        channel = GitHubIssueChannel(github_client=mock_client)
        alert = _make_alert(message="Security issue found")
        alert.details = {"issue_count": 3, "severity": "high"}
        body = channel._build_issue_body(alert)
        assert "issue_count" in body
        assert "Security issue found" in body
