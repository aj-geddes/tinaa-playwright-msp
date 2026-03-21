"""Parser for .tinaa.yml configuration files."""

from __future__ import annotations

import os
import re

import yaml

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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_BROWSERS: frozenset[str] = frozenset({"chromium", "firefox", "webkit"})
VALID_ALERT_TYPES: frozenset[str] = frozenset({"slack", "email", "webhook", "pagerduty"})
VALID_ENV_TYPES: frozenset[str] = frozenset({"production", "staging", "development", "preview"})

_INTERVAL_UNITS: dict[str, int] = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_INTERVAL_PATTERN: re.Pattern[str] = re.compile(r"^(\d+)([smhd])$")

_DURATION_MS_PATTERN: re.Pattern[str] = re.compile(r"^(\d+)ms$")
_DURATION_S_PATTERN: re.Pattern[str] = re.compile(r"^(\d+)s$")
_DURATION_M_PATTERN: re.Pattern[str] = re.compile(r"^(\d+)m$")

_MS_PER_SECOND: int = 1000
_MS_PER_MINUTE: int = 60 * _MS_PER_SECOND

_ENV_VAR_PATTERN: re.Pattern[str] = re.compile(r"\$\{([^}]+)\}")
_URL_PATTERN: re.Pattern[str] = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)

# A basic cron expression: 5 or 6 space-separated fields, each matching
# the standard cron character set (digits, * / - ,).
_CRON_PATTERN: re.Pattern[str] = re.compile(r"^(\S+\s+){4}\S+(\s+\S+)?$")
_CRON_FIELD_PATTERN: re.Pattern[str] = re.compile(r"^[\d*/,\-]+$")


class ConfigParser:
    """Parses .tinaa.yml configuration files into TINAAConfig objects."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, content: str) -> TINAAConfig:
        """Parse YAML string content into a TINAAConfig.

        Args:
            content: Raw YAML text from a .tinaa.yml file.

        Returns:
            Hydrated TINAAConfig dataclass.

        Raises:
            TypeError: If ``content`` is not a string.
            ValueError: If the YAML is syntactically invalid.
        """
        if content is None:
            raise TypeError("content must be a string, not None")

        try:
            data: dict | None = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML: {exc}") from exc

        if data is None:
            return TINAAConfig()

        if not isinstance(data, dict):
            raise ValueError("Invalid YAML: top-level value must be a mapping")

        return self._build_config(data)

    def parse_file(self, file_path: str) -> TINAAConfig:
        """Parse a .tinaa.yml file from disk.

        Args:
            file_path: Absolute or relative path to the YAML file.

        Returns:
            Hydrated TINAAConfig dataclass.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the YAML is syntactically invalid.
        """
        with open(file_path, encoding="utf-8") as fh:
            return self.parse(fh.read())

    def parse_interval(self, value: str) -> int:
        """Parse an interval string into seconds.

        Supports: ``"30s"``, ``"5m"``, ``"1h"``, ``"1d"``.

        Args:
            value: Human-readable interval string.

        Returns:
            Number of seconds as an integer.

        Raises:
            ValueError: If the string cannot be parsed.
        """
        if not value:
            raise ValueError("Cannot parse interval: empty string")

        match = _INTERVAL_PATTERN.match(str(value).strip())
        if not match:
            raise ValueError(f"Cannot parse interval: {value!r}")

        amount = int(match.group(1))
        unit = match.group(2)
        return amount * _INTERVAL_UNITS[unit]

    def parse_duration(self, value: str | int) -> int:
        """Parse a duration string into milliseconds.

        Supports: ``"500ms"``, ``"3s"``, ``"30s"``, ``"1m"``.
        A bare integer is treated as milliseconds.

        Args:
            value: Human-readable duration string or integer milliseconds.

        Returns:
            Number of milliseconds as an integer.

        Raises:
            ValueError: If the string cannot be parsed.
        """
        if isinstance(value, (int, float)):
            return int(value)

        text = str(value).strip()

        ms_match = _DURATION_MS_PATTERN.match(text)
        if ms_match:
            return int(ms_match.group(1))

        s_match = _DURATION_S_PATTERN.match(text)
        if s_match:
            return int(s_match.group(1)) * _MS_PER_SECOND

        m_match = _DURATION_M_PATTERN.match(text)
        if m_match:
            return int(m_match.group(1)) * _MS_PER_MINUTE

        raise ValueError(f"Cannot parse duration: {value!r}")

    def parse_percentage(self, value: str | int | float) -> float:
        """Parse a percentage value to a plain float.

        ``"20%"`` → ``20.0``,  ``"0.5"`` → ``0.5``,  ``20`` → ``20.0``.

        Args:
            value: Percentage string (with or without ``%``) or numeric value.

        Returns:
            Float representation.
        """
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        if text.endswith("%"):
            return float(text[:-1])
        return float(text)

    def resolve_env_vars(self, value: str) -> str:
        """Resolve ``${VAR}`` and ``${VAR:-default}`` patterns.

        Unknown variables with no default expand to an empty string.

        Args:
            value: String potentially containing env-var placeholders.

        Returns:
            String with all placeholders replaced.
        """

        def _replace(match: re.Match[str]) -> str:
            spec = match.group(1)
            if ":-" in spec:
                var_name, default = spec.split(":-", 1)
                return os.environ.get(var_name.strip(), default)
            return os.environ.get(spec.strip(), "")

        return _ENV_VAR_PATTERN.sub(_replace, value)

    def validate(self, config: TINAAConfig) -> list[str]:
        """Validate a parsed config.

        Args:
            config: The TINAAConfig to validate.

        Returns:
            List of human-readable error messages.  Empty list means valid.
        """
        errors: list[str] = []
        errors.extend(self._validate_environments(config))
        errors.extend(self._validate_quality_gates(config))
        errors.extend(self._validate_testing(config))
        errors.extend(self._validate_alerts(config))
        return errors

    # ------------------------------------------------------------------
    # Private parsing helpers
    # ------------------------------------------------------------------

    def _build_config(self, data: dict) -> TINAAConfig:
        """Assemble a TINAAConfig from a parsed YAML dict."""
        product = data.get("product") or {}
        tags = product.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]

        environments = self._parse_environments(data.get("environments") or {})
        quality_gates = self._parse_quality_gates(data.get("quality_gates") or {})
        testing = self._parse_testing(data.get("testing") or {})
        alerts = self._parse_alerts(data.get("alerts") or {})
        ignore_paths = data.get("ignore_paths") or []

        return TINAAConfig(
            product_name=str(product.get("name") or ""),
            team=str(product.get("team") or ""),
            description=str(product.get("description") or ""),
            environments=environments,
            quality_gates=quality_gates,
            testing=testing,
            alerts=alerts,
            tags=list(tags),
            ignore_paths=list(ignore_paths),
        )

    def _parse_environments(self, data: dict) -> list[EnvironmentConfig]:
        """Parse the ``environments`` mapping."""
        return [self._parse_environment(name, cfg) for name, cfg in data.items()]

    def _parse_environment(self, name: str, data: dict) -> EnvironmentConfig:
        """Parse a single environment block."""
        url = str(data.get("url") or "")
        env_type = _infer_env_type(name, str(data.get("type") or ""))
        monitoring = self._parse_monitoring(data.get("monitoring") or {})
        return EnvironmentConfig(
            name=name,
            url=url,
            env_type=env_type,
            monitoring=monitoring,
        )

    def _parse_monitoring(self, data: dict) -> MonitoringConfig:
        """Parse a monitoring block."""
        interval_raw = data.get("interval") or "5m"
        interval_str = str(interval_raw)
        interval_seconds = self.parse_interval(interval_str)

        endpoints_raw = data.get("endpoints") or []
        endpoints = [self._parse_endpoint(ep) for ep in endpoints_raw]

        return MonitoringConfig(
            interval=interval_str,
            interval_seconds=interval_seconds,
            endpoints=endpoints,
        )

    def _parse_endpoint(self, data: dict) -> EndpointConfig:
        """Parse an endpoint configuration block."""
        path = str(data.get("path") or "")
        method = str(data.get("method") or "GET").upper()
        endpoint_type = str(data.get("type") or "page")

        perf_raw = data.get("performance_budget")
        performance_budget_ms = self.parse_duration(perf_raw) if perf_raw is not None else None

        lcp_raw = data.get("lcp")
        lcp_budget_ms = float(self.parse_duration(lcp_raw)) if lcp_raw is not None else None

        cls_raw = data.get("cls")
        cls_budget = float(cls_raw) if cls_raw is not None else None

        expected_status = int(data.get("expected_status") or 200)

        max_rt_raw = data.get("max_response_time")
        max_response_time_ms = self.parse_duration(max_rt_raw) if max_rt_raw is not None else None

        return EndpointConfig(
            path=path,
            method=method,
            endpoint_type=endpoint_type,
            performance_budget_ms=performance_budget_ms,
            lcp_budget_ms=lcp_budget_ms,
            cls_budget=cls_budget,
            expected_status=expected_status,
            max_response_time_ms=max_response_time_ms,
        )

    def _parse_quality_gates(self, data: dict) -> dict[str, QualityGateConfig]:
        """Parse the ``quality_gates`` mapping."""
        return {name: self._parse_quality_gate(gate) for name, gate in data.items()}

    def _parse_quality_gate(self, data: dict) -> QualityGateConfig:
        """Parse a single quality gate block."""
        min_score = float(data.get("min_score") or 80.0)

        no_critical = data.get("no_critical_failures")
        no_critical_failures = bool(no_critical) if no_critical is not None else True

        max_regression_raw = data.get("max_performance_regression")
        if max_regression_raw is not None:
            max_regression = self.parse_percentage(max_regression_raw)
        else:
            max_regression = 20.0

        max_a11y = int(data.get("max_new_accessibility_violations") or 0)

        return QualityGateConfig(
            min_score=min_score,
            no_critical_failures=no_critical_failures,
            max_performance_regression_percent=max_regression,
            max_new_accessibility_violations=max_a11y,
        )

    def _parse_testing(self, data: dict) -> TestingConfig:
        """Parse the ``testing`` block."""
        schedule = data.get("schedule") or None
        on_deploy = bool(data.get("on_deploy", True))
        on_pr = bool(data.get("on_pr", True))

        browsers_raw = data.get("browsers") or ["chromium"]
        browsers = list(browsers_raw) if isinstance(browsers_raw, list) else [browsers_raw]

        viewports_raw = data.get("viewports")
        if viewports_raw:
            viewports = [dict(vp) for vp in viewports_raw]
        else:
            viewports = [
                {"name": "desktop", "width": 1440, "height": 900},
                {"name": "mobile", "width": 375, "height": 812},
            ]

        parallel = bool(data.get("parallel", False))
        retries = int(data.get("retries") or 0)

        timeout_raw = data.get("timeout")
        timeout_ms = self.parse_duration(timeout_raw) if timeout_raw is not None else 30000

        return TestingConfig(
            schedule=schedule,
            on_deploy=on_deploy,
            on_pr=on_pr,
            browsers=browsers,
            viewports=viewports,
            parallel=parallel,
            retries=retries,
            timeout_ms=timeout_ms,
        )

    def _parse_alerts(self, data: dict) -> AlertsConfig:
        """Parse the ``alerts`` block."""
        channels_raw = data.get("channels") or []
        channels = [self._parse_alert_channel(ch) for ch in channels_raw]

        rules_raw = data.get("rules") or []
        rules = [dict(r) for r in rules_raw]

        return AlertsConfig(channels=channels, rules=rules)

    def _parse_alert_channel(self, data: dict) -> AlertChannelConfig:
        """Parse a single alert channel block.

        All keys except ``type`` are placed in the ``config`` dict.
        String values undergo environment variable resolution.
        """
        channel_type = str(data.get("type") or "")
        config: dict = {}
        for key, value in data.items():
            if key == "type":
                continue
            if isinstance(value, str):
                value = self.resolve_env_vars(value)
            config[key] = value
        return AlertChannelConfig(type=channel_type, config=config)

    # ------------------------------------------------------------------
    # Private validation helpers
    # ------------------------------------------------------------------

    def _validate_environments(self, config: TINAAConfig) -> list[str]:
        errors: list[str] = []
        if not config.environments:
            errors.append("At least one environment must be defined")
            return errors
        for env in config.environments:
            if not _URL_PATTERN.match(env.url):
                errors.append(
                    f"Environment '{env.name}': URL '{env.url}' is not a valid HTTP(S) URL"
                )
        return errors

    def _validate_quality_gates(self, config: TINAAConfig) -> list[str]:
        errors: list[str] = []
        for gate_name, gate in config.quality_gates.items():
            if not (0.0 <= gate.min_score <= 100.0):
                errors.append(
                    f"Quality gate '{gate_name}': min_score {gate.min_score} must be between 0 and 100"
                )
        return errors

    def _validate_testing(self, config: TINAAConfig) -> list[str]:
        errors: list[str] = []

        if config.testing.schedule is not None and not _is_valid_cron(config.testing.schedule):
            errors.append(
                f"Testing schedule '{config.testing.schedule}' is not a valid cron expression"
            )

        for browser in config.testing.browsers:
            if browser not in VALID_BROWSERS:
                errors.append(
                    f"Browser '{browser}' is not valid; choose from {sorted(VALID_BROWSERS)}"
                )

        for vp in config.testing.viewports:
            width = vp.get("width", 0)
            height = vp.get("height", 0)
            name = vp.get("name", "<unnamed>")
            if not isinstance(width, int) or width <= 0:
                errors.append(f"Viewport '{name}': width must be a positive integer")
            if not isinstance(height, int) or height <= 0:
                errors.append(f"Viewport '{name}': height must be a positive integer")

        return errors

    def _validate_alerts(self, config: TINAAConfig) -> list[str]:
        errors: list[str] = []
        for channel in config.alerts.channels:
            if channel.type not in VALID_ALERT_TYPES:
                errors.append(
                    f"Alert channel type '{channel.type}' is not recognised; "
                    f"choose from {sorted(VALID_ALERT_TYPES)}"
                )
        return errors


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _infer_env_type(name: str, explicit: str) -> str:
    """Determine env_type from an explicit value or environment name."""
    if explicit and explicit in VALID_ENV_TYPES:
        return explicit
    lower = name.lower()
    if lower in VALID_ENV_TYPES:
        return lower
    if "prod" in lower:
        return "production"
    if "stag" in lower:
        return "staging"
    if "dev" in lower:
        return "development"
    if "preview" in lower or "pr" in lower:
        return "preview"
    return "staging"


def _is_valid_cron(expr: str) -> bool:
    """Return True if *expr* looks like a valid 5- or 6-field cron expression."""
    fields = expr.strip().split()
    if len(fields) not in (5, 6):
        return False
    return all(_CRON_FIELD_PATTERN.match(f) for f in fields)
