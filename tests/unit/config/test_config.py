"""Unit tests for tinaa.config — the TINAA MSP configuration system."""

import os
import textwrap
import pytest

from tinaa.config.schema import (
    AlertChannelConfig,
    AlertsConfig,
    EndpointConfig,
    EnvironmentConfig,
    MonitoringConfig,
    QualityGateConfig,
    TestingConfig,
    TINAAConfig,
)
from tinaa.config.parser import ConfigParser
from tinaa.config.defaults import get_default_config, get_minimal_config, merge_configs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FULL_YAML = textwrap.dedent("""\
    product:
      name: acme-webapp
      team: platform-engineering
      description: "Main web application"
      tags: [web, critical]

    environments:
      production:
        url: https://app.acme.com
        monitoring:
          interval: 5m
          endpoints:
            - path: /
              performance_budget: 3000
              lcp: 2500
            - path: /api/health
              type: health
              expected_status: 200
              max_response_time: 500ms
      staging:
        url: https://staging.acme.com
        monitoring:
          interval: 15m

    quality_gates:
      deploy_to_production:
        min_score: 80
        no_critical_failures: true
        max_performance_regression: 20%
      deploy_to_staging:
        min_score: 60

    testing:
      schedule: "*/30 * * * *"
      on_deploy: true
      on_pr: true
      browsers: [chromium]
      viewports:
        - name: desktop
          width: 1440
          height: 900
        - name: mobile
          width: 375
          height: 812
      retries: 1
      timeout: 30s

    alerts:
      channels:
        - type: slack
          channel: "#acme-alerts"
        - type: pagerduty
          routing_key: "${PAGERDUTY_KEY}"
          severity_threshold: critical
      rules:
        - type: quality_score_drop
          threshold: 10
          severity: warning
        - type: endpoint_down
          consecutive_failures: 3
          severity: critical

    ignore_paths:
      - "node_modules/**"
      - "**/*.test.*"
      - "docs/**"
""")

MINIMAL_YAML = textwrap.dedent("""\
    product:
      name: simple-app

    environments:
      production:
        url: https://example.com
""")


@pytest.fixture
def parser() -> ConfigParser:
    return ConfigParser()


# ---------------------------------------------------------------------------
# Schema dataclass tests
# ---------------------------------------------------------------------------

class TestSchemaDefaults:
    """Verify default values on all schema dataclasses."""

    def test_endpoint_config_defaults(self) -> None:
        ep = EndpointConfig(path="/health")
        assert ep.method == "GET"
        assert ep.endpoint_type == "page"
        assert ep.expected_status == 200
        assert ep.performance_budget_ms is None
        assert ep.lcp_budget_ms is None
        assert ep.cls_budget is None
        assert ep.max_response_time_ms is None

    def test_monitoring_config_defaults(self) -> None:
        mc = MonitoringConfig()
        assert mc.interval == "5m"
        assert mc.interval_seconds == 300
        assert mc.endpoints == []

    def test_quality_gate_defaults(self) -> None:
        qg = QualityGateConfig()
        assert qg.min_score == 80.0
        assert qg.no_critical_failures is True
        assert qg.max_performance_regression_percent == 20.0
        assert qg.max_new_accessibility_violations == 0

    def test_testing_config_defaults(self) -> None:
        tc = TestingConfig()
        assert tc.on_deploy is True
        assert tc.on_pr is True
        assert tc.browsers == ["chromium"]
        assert tc.retries == 0
        assert tc.timeout_ms == 30000
        assert tc.parallel is False
        assert len(tc.viewports) == 2

    def test_tinaa_config_defaults(self) -> None:
        cfg = TINAAConfig()
        assert cfg.product_name == ""
        assert cfg.environments == []
        assert cfg.quality_gates == {}
        assert cfg.tags == []
        assert cfg.ignore_paths == []


# ---------------------------------------------------------------------------
# Interval parsing
# ---------------------------------------------------------------------------

class TestParseInterval:
    """parse_interval converts human-readable intervals to seconds."""

    def test_seconds(self, parser: ConfigParser) -> None:
        assert parser.parse_interval("30s") == 30

    def test_minutes(self, parser: ConfigParser) -> None:
        assert parser.parse_interval("5m") == 300

    def test_hours(self, parser: ConfigParser) -> None:
        assert parser.parse_interval("1h") == 3600

    def test_days(self, parser: ConfigParser) -> None:
        assert parser.parse_interval("1d") == 86400

    def test_multi_digit_minutes(self, parser: ConfigParser) -> None:
        assert parser.parse_interval("15m") == 900

    def test_multi_digit_seconds(self, parser: ConfigParser) -> None:
        assert parser.parse_interval("90s") == 90

    def test_invalid_unit_raises(self, parser: ConfigParser) -> None:
        with pytest.raises(ValueError, match="Cannot parse interval"):
            parser.parse_interval("5x")

    def test_empty_string_raises(self, parser: ConfigParser) -> None:
        with pytest.raises(ValueError):
            parser.parse_interval("")


# ---------------------------------------------------------------------------
# Duration parsing
# ---------------------------------------------------------------------------

class TestParseDuration:
    """parse_duration converts human-readable durations to milliseconds."""

    def test_milliseconds(self, parser: ConfigParser) -> None:
        assert parser.parse_duration("500ms") == 500

    def test_seconds_to_ms(self, parser: ConfigParser) -> None:
        assert parser.parse_duration("3s") == 3000

    def test_thirty_seconds(self, parser: ConfigParser) -> None:
        assert parser.parse_duration("30s") == 30000

    def test_one_minute(self, parser: ConfigParser) -> None:
        assert parser.parse_duration("1m") == 60000

    def test_bare_integer_treated_as_ms(self, parser: ConfigParser) -> None:
        """A plain integer (from YAML) is treated as milliseconds."""
        assert parser.parse_duration(3000) == 3000

    def test_invalid_raises(self, parser: ConfigParser) -> None:
        with pytest.raises(ValueError, match="Cannot parse duration"):
            parser.parse_duration("5x")


# ---------------------------------------------------------------------------
# Percentage parsing
# ---------------------------------------------------------------------------

class TestParsePercentage:
    """parse_percentage normalises percentage strings to float values."""

    def test_percent_string(self, parser: ConfigParser) -> None:
        assert parser.parse_percentage("20%") == 20.0

    def test_plain_float_string(self, parser: ConfigParser) -> None:
        assert parser.parse_percentage("0.5") == 0.5

    def test_plain_integer_string(self, parser: ConfigParser) -> None:
        assert parser.parse_percentage("15") == 15.0

    def test_zero_percent(self, parser: ConfigParser) -> None:
        assert parser.parse_percentage("0%") == 0.0

    def test_bare_number(self, parser: ConfigParser) -> None:
        """Numeric value (e.g. from YAML int) passes through."""
        assert parser.parse_percentage(20) == 20.0


# ---------------------------------------------------------------------------
# Environment variable resolution
# ---------------------------------------------------------------------------

class TestResolveEnvVars:
    """resolve_env_vars handles ${VAR} and ${VAR:-default} patterns."""

    def test_simple_var(self, parser: ConfigParser, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_KEY", "secret123")
        assert parser.resolve_env_vars("${MY_KEY}") == "secret123"

    def test_var_with_default_present(self, parser: ConfigParser, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAGERDUTY_KEY", "pd-abc")
        assert parser.resolve_env_vars("${PAGERDUTY_KEY:-fallback}") == "pd-abc"

    def test_var_with_default_absent(self, parser: ConfigParser, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MISSING_VAR", raising=False)
        assert parser.resolve_env_vars("${MISSING_VAR:-my-default}") == "my-default"

    def test_missing_var_no_default_returns_empty(self, parser: ConfigParser, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ABSENT_VAR", raising=False)
        assert parser.resolve_env_vars("${ABSENT_VAR}") == ""

    def test_no_interpolation_needed(self, parser: ConfigParser) -> None:
        assert parser.resolve_env_vars("plain-string") == "plain-string"

    def test_inline_substitution(self, parser: ConfigParser, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOST", "api.acme.com")
        assert parser.resolve_env_vars("https://${HOST}/v1") == "https://api.acme.com/v1"


# ---------------------------------------------------------------------------
# Parsing — full YAML
# ---------------------------------------------------------------------------

class TestParseFullConfig:
    """parse() correctly hydrates all sections of the full YAML example."""

    @pytest.fixture(autouse=True)
    def _set_pd_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PAGERDUTY_KEY", "test-pd-key")

    @pytest.fixture
    def config(self, parser: ConfigParser) -> TINAAConfig:
        return parser.parse(FULL_YAML)

    def test_product_name(self, config: TINAAConfig) -> None:
        assert config.product_name == "acme-webapp"

    def test_team(self, config: TINAAConfig) -> None:
        assert config.team == "platform-engineering"

    def test_description(self, config: TINAAConfig) -> None:
        assert config.description == "Main web application"

    def test_tags(self, config: TINAAConfig) -> None:
        assert config.tags == ["web", "critical"]

    def test_two_environments(self, config: TINAAConfig) -> None:
        assert len(config.environments) == 2

    def test_production_env_name_and_url(self, config: TINAAConfig) -> None:
        prod = next(e for e in config.environments if e.name == "production")
        assert prod.url == "https://app.acme.com"
        assert prod.env_type == "production"

    def test_production_monitoring_interval(self, config: TINAAConfig) -> None:
        prod = next(e for e in config.environments if e.name == "production")
        assert prod.monitoring.interval == "5m"
        assert prod.monitoring.interval_seconds == 300

    def test_production_endpoints_count(self, config: TINAAConfig) -> None:
        prod = next(e for e in config.environments if e.name == "production")
        assert len(prod.monitoring.endpoints) == 2

    def test_root_endpoint_budgets(self, config: TINAAConfig) -> None:
        prod = next(e for e in config.environments if e.name == "production")
        root_ep = next(ep for ep in prod.monitoring.endpoints if ep.path == "/")
        assert root_ep.performance_budget_ms == 3000
        assert root_ep.lcp_budget_ms == 2500.0

    def test_health_endpoint_type_and_status(self, config: TINAAConfig) -> None:
        prod = next(e for e in config.environments if e.name == "production")
        health_ep = next(ep for ep in prod.monitoring.endpoints if ep.path == "/api/health")
        assert health_ep.endpoint_type == "health"
        assert health_ep.expected_status == 200
        assert health_ep.max_response_time_ms == 500

    def test_staging_env(self, config: TINAAConfig) -> None:
        staging = next(e for e in config.environments if e.name == "staging")
        assert staging.url == "https://staging.acme.com"
        assert staging.monitoring.interval_seconds == 900  # 15m

    def test_quality_gates_count(self, config: TINAAConfig) -> None:
        assert len(config.quality_gates) == 2

    def test_production_quality_gate(self, config: TINAAConfig) -> None:
        gate = config.quality_gates["deploy_to_production"]
        assert gate.min_score == 80.0
        assert gate.no_critical_failures is True
        assert gate.max_performance_regression_percent == 20.0

    def test_staging_quality_gate(self, config: TINAAConfig) -> None:
        gate = config.quality_gates["deploy_to_staging"]
        assert gate.min_score == 60.0

    def test_testing_schedule(self, config: TINAAConfig) -> None:
        assert config.testing.schedule == "*/30 * * * *"

    def test_testing_browsers(self, config: TINAAConfig) -> None:
        assert config.testing.browsers == ["chromium"]

    def test_testing_retries(self, config: TINAAConfig) -> None:
        assert config.testing.retries == 1

    def test_testing_timeout_ms(self, config: TINAAConfig) -> None:
        assert config.testing.timeout_ms == 30000  # 30s -> 30000ms

    def test_testing_viewports(self, config: TINAAConfig) -> None:
        assert len(config.testing.viewports) == 2
        assert config.testing.viewports[0]["name"] == "desktop"
        assert config.testing.viewports[1]["name"] == "mobile"

    def test_alert_channels_count(self, config: TINAAConfig) -> None:
        assert len(config.alerts.channels) == 2

    def test_slack_channel(self, config: TINAAConfig) -> None:
        slack = next(c for c in config.alerts.channels if c.type == "slack")
        assert slack.config.get("channel") == "#acme-alerts"

    def test_pagerduty_env_var_resolved(self, config: TINAAConfig) -> None:
        pd = next(c for c in config.alerts.channels if c.type == "pagerduty")
        assert pd.config.get("routing_key") == "test-pd-key"

    def test_alert_rules_count(self, config: TINAAConfig) -> None:
        assert len(config.alerts.rules) == 2

    def test_ignore_paths(self, config: TINAAConfig) -> None:
        assert config.ignore_paths == ["node_modules/**", "**/*.test.*", "docs/**"]


# ---------------------------------------------------------------------------
# Parsing — minimal YAML
# ---------------------------------------------------------------------------

class TestParseMinimalConfig:
    """parse() handles a minimal YAML with only product name and one env."""

    @pytest.fixture
    def config(self, parser: ConfigParser) -> TINAAConfig:
        return parser.parse(MINIMAL_YAML)

    def test_product_name(self, config: TINAAConfig) -> None:
        assert config.product_name == "simple-app"

    def test_single_environment(self, config: TINAAConfig) -> None:
        assert len(config.environments) == 1

    def test_production_url(self, config: TINAAConfig) -> None:
        assert config.environments[0].url == "https://example.com"

    def test_defaults_applied_to_testing(self, config: TINAAConfig) -> None:
        assert config.testing.browsers == ["chromium"]
        assert config.testing.on_deploy is True

    def test_no_quality_gates(self, config: TINAAConfig) -> None:
        assert config.quality_gates == {}

    def test_no_alerts(self, config: TINAAConfig) -> None:
        assert config.alerts.channels == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestParseEdgeCases:
    """Edge cases: empty content, missing sections, unknown fields ignored."""

    def test_empty_yaml_returns_default_config(self, parser: ConfigParser) -> None:
        cfg = parser.parse("")
        assert isinstance(cfg, TINAAConfig)
        assert cfg.product_name == ""
        assert cfg.environments == []

    def test_none_content_raises(self, parser: ConfigParser) -> None:
        with pytest.raises((ValueError, TypeError)):
            parser.parse(None)  # type: ignore[arg-type]

    def test_unknown_top_level_keys_ignored(self, parser: ConfigParser) -> None:
        yaml_content = textwrap.dedent("""\
            product:
              name: test-app
            environments:
              production:
                url: https://test.com
            unknown_section:
              foo: bar
        """)
        cfg = parser.parse(yaml_content)
        assert cfg.product_name == "test-app"

    def test_missing_product_section(self, parser: ConfigParser) -> None:
        yaml_content = textwrap.dedent("""\
            environments:
              production:
                url: https://test.com
        """)
        cfg = parser.parse(yaml_content)
        assert cfg.product_name == ""
        assert len(cfg.environments) == 1

    def test_environment_without_monitoring(self, parser: ConfigParser) -> None:
        yaml_content = textwrap.dedent("""\
            environments:
              production:
                url: https://test.com
        """)
        cfg = parser.parse(yaml_content)
        env = cfg.environments[0]
        assert env.monitoring.interval == "5m"
        assert env.monitoring.endpoints == []

    def test_invalid_yaml_raises_value_error(self, parser: ConfigParser) -> None:
        with pytest.raises(ValueError, match="Invalid YAML"):
            parser.parse("key: [unclosed bracket")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    """validate() returns a list of error strings for each misconfiguration."""

    def test_valid_config_no_errors(self, parser: ConfigParser) -> None:
        cfg = parser.parse(MINIMAL_YAML)
        errors = parser.validate(cfg)
        assert errors == []

    def test_no_environments_error(self, parser: ConfigParser) -> None:
        cfg = TINAAConfig()
        errors = parser.validate(cfg)
        assert any("environment" in e.lower() for e in errors)

    def test_invalid_url_error(self, parser: ConfigParser) -> None:
        cfg = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="not-a-url")]
        )
        errors = parser.validate(cfg)
        assert any("url" in e.lower() for e in errors)

    def test_valid_url_no_error(self, parser: ConfigParser) -> None:
        cfg = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="https://example.com")]
        )
        errors = parser.validate(cfg)
        assert not any("url" in e.lower() for e in errors)

    def test_quality_gate_score_out_of_range(self, parser: ConfigParser) -> None:
        cfg = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="https://example.com")],
            quality_gates={"gate": QualityGateConfig(min_score=150.0)},
        )
        errors = parser.validate(cfg)
        assert any("score" in e.lower() or "quality" in e.lower() for e in errors)

    def test_invalid_browser_name(self, parser: ConfigParser) -> None:
        cfg = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="https://example.com")],
            testing=TestingConfig(browsers=["chrome"]),  # "chrome" not valid
        )
        errors = parser.validate(cfg)
        assert any("browser" in e.lower() for e in errors)

    def test_valid_browsers_no_error(self, parser: ConfigParser) -> None:
        cfg = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="https://example.com")],
            testing=TestingConfig(browsers=["chromium", "firefox", "webkit"]),
        )
        errors = parser.validate(cfg)
        assert not any("browser" in e.lower() for e in errors)

    def test_invalid_cron_expression(self, parser: ConfigParser) -> None:
        cfg = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="https://example.com")],
            testing=TestingConfig(schedule="not-a-cron"),
        )
        errors = parser.validate(cfg)
        assert any("cron" in e.lower() or "schedule" in e.lower() for e in errors)

    def test_valid_cron_no_error(self, parser: ConfigParser) -> None:
        cfg = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="https://example.com")],
            testing=TestingConfig(schedule="*/30 * * * *"),
        )
        errors = parser.validate(cfg)
        assert not any("cron" in e.lower() or "schedule" in e.lower() for e in errors)

    def test_unrecognised_alert_channel_type(self, parser: ConfigParser) -> None:
        cfg = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="https://example.com")],
            alerts=AlertsConfig(
                channels=[AlertChannelConfig(type="telegram")]
            ),
        )
        errors = parser.validate(cfg)
        assert any("channel" in e.lower() or "alert" in e.lower() for e in errors)

    def test_zero_viewport_dimension(self, parser: ConfigParser) -> None:
        cfg = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="https://example.com")],
            testing=TestingConfig(
                viewports=[{"name": "bad", "width": 0, "height": 800}]
            ),
        )
        errors = parser.validate(cfg)
        assert any("viewport" in e.lower() for e in errors)

    def test_multiple_errors_collected(self, parser: ConfigParser) -> None:
        """All errors are collected; validate does not short-circuit."""
        cfg = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="bad-url")],
            testing=TestingConfig(browsers=["ie11"]),
        )
        errors = parser.validate(cfg)
        assert len(errors) >= 2


# ---------------------------------------------------------------------------
# parse_file
# ---------------------------------------------------------------------------

class TestParseFile:
    """parse_file reads from disk and delegates to parse()."""

    def test_parse_file_success(self, parser: ConfigParser, tmp_path) -> None:
        config_file = tmp_path / ".tinaa.yml"
        config_file.write_text(MINIMAL_YAML)
        cfg = parser.parse_file(str(config_file))
        assert cfg.product_name == "simple-app"

    def test_parse_file_not_found(self, parser: ConfigParser) -> None:
        with pytest.raises((FileNotFoundError, OSError)):
            parser.parse_file("/nonexistent/path/.tinaa.yml")


# ---------------------------------------------------------------------------
# Default config
# ---------------------------------------------------------------------------

class TestGetDefaultConfig:
    """get_default_config() returns a fully populated TINAAConfig."""

    def test_returns_tinaa_config(self) -> None:
        cfg = get_default_config()
        assert isinstance(cfg, TINAAConfig)

    def test_has_sensible_testing_defaults(self) -> None:
        cfg = get_default_config()
        assert "chromium" in cfg.testing.browsers
        assert cfg.testing.timeout_ms > 0
        assert cfg.testing.retries >= 0

    def test_monitoring_interval_positive(self) -> None:
        cfg = get_default_config()
        # Default config may have no environments; that's fine — check TestingConfig
        assert cfg.testing.timeout_ms == 30000


# ---------------------------------------------------------------------------
# Minimal config
# ---------------------------------------------------------------------------

class TestGetMinimalConfig:
    """get_minimal_config() returns a TINAAConfig with one production env."""

    def test_product_name_set(self) -> None:
        cfg = get_minimal_config("my-app", "https://myapp.com")
        assert cfg.product_name == "my-app"

    def test_production_environment_present(self) -> None:
        cfg = get_minimal_config("my-app", "https://myapp.com")
        assert len(cfg.environments) == 1
        assert cfg.environments[0].url == "https://myapp.com"
        assert cfg.environments[0].env_type == "production"

    def test_passes_validation(self) -> None:
        parser = ConfigParser()
        cfg = get_minimal_config("my-app", "https://myapp.com")
        errors = parser.validate(cfg)
        assert errors == []


# ---------------------------------------------------------------------------
# Config merging
# ---------------------------------------------------------------------------

class TestMergeConfigs:
    """merge_configs() merges two TINAAConfig objects, override wins."""

    def test_override_product_name(self) -> None:
        base = TINAAConfig(product_name="base-app")
        override = TINAAConfig(product_name="override-app")
        merged = merge_configs(base, override)
        assert merged.product_name == "override-app"

    def test_base_value_preserved_when_override_empty(self) -> None:
        base = TINAAConfig(product_name="base-app", team="eng")
        override = TINAAConfig(product_name="override-app")
        merged = merge_configs(base, override)
        assert merged.team == "eng"

    def test_override_environments_replace_base(self) -> None:
        base = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="https://base.com")]
        )
        override = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="https://override.com")]
        )
        merged = merge_configs(base, override)
        assert len(merged.environments) == 1
        assert merged.environments[0].url == "https://override.com"

    def test_base_environments_kept_when_override_empty(self) -> None:
        base = TINAAConfig(
            environments=[EnvironmentConfig(name="prod", url="https://base.com")]
        )
        override = TINAAConfig()
        merged = merge_configs(base, override)
        assert len(merged.environments) == 1
        assert merged.environments[0].url == "https://base.com"

    def test_override_quality_gates_merge(self) -> None:
        base = TINAAConfig(
            quality_gates={"gate_a": QualityGateConfig(min_score=70.0)}
        )
        override = TINAAConfig(
            quality_gates={"gate_a": QualityGateConfig(min_score=90.0), "gate_b": QualityGateConfig(min_score=50.0)}
        )
        merged = merge_configs(base, override)
        assert merged.quality_gates["gate_a"].min_score == 90.0
        assert "gate_b" in merged.quality_gates

    def test_merge_does_not_mutate_originals(self) -> None:
        base = TINAAConfig(product_name="base")
        override = TINAAConfig(product_name="override")
        merge_configs(base, override)
        assert base.product_name == "base"
        assert override.product_name == "override"

    def test_override_tags_replace_base(self) -> None:
        base = TINAAConfig(tags=["a", "b"])
        override = TINAAConfig(tags=["c"])
        merged = merge_configs(base, override)
        assert merged.tags == ["c"]

    def test_base_tags_kept_when_override_empty(self) -> None:
        base = TINAAConfig(tags=["a", "b"])
        override = TINAAConfig()
        merged = merge_configs(base, override)
        assert merged.tags == ["a", "b"]
