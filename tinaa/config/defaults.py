"""Default and convenience configuration factories for TINAA MSP."""

from __future__ import annotations

import copy

from tinaa.config.schema import (
    AlertsConfig,
    EnvironmentConfig,
    MonitoringConfig,
    QualityGateConfig,
    TestingConfig,
    TINAAConfig,
)


def get_default_config() -> TINAAConfig:
    """Return a sensible default TINAAConfig with no environments.

    Suitable as a base for merging with user-supplied configurations.

    Returns:
        TINAAConfig with all defaults populated.
    """
    return TINAAConfig(
        product_name="",
        team="",
        description="",
        environments=[],
        quality_gates={
            "default": QualityGateConfig(
                min_score=80.0,
                no_critical_failures=True,
                max_performance_regression_percent=20.0,
                max_new_accessibility_violations=0,
            )
        },
        testing=TestingConfig(
            schedule=None,
            on_deploy=True,
            on_pr=True,
            browsers=["chromium"],
            viewports=[
                {"name": "desktop", "width": 1440, "height": 900},
                {"name": "mobile", "width": 375, "height": 812},
            ],
            parallel=False,
            retries=0,
            timeout_ms=30000,
        ),
        alerts=AlertsConfig(channels=[], rules=[]),
        tags=[],
        ignore_paths=[],
    )


def get_minimal_config(name: str, production_url: str) -> TINAAConfig:
    """Return a minimal config for quick onboarding.

    Creates a config with only the product name and a single production
    environment. All other settings use sensible defaults.

    Args:
        name: Product name (e.g. ``"acme-webapp"``).
        production_url: The production environment URL (must be HTTP/S).

    Returns:
        TINAAConfig ready for immediate use.
    """
    base = get_default_config()
    base.product_name = name
    base.environments = [
        EnvironmentConfig(
            name="production",
            url=production_url,
            env_type="production",
            monitoring=MonitoringConfig(interval="5m", interval_seconds=300, endpoints=[]),
        )
    ]
    return base


def merge_configs(base: TINAAConfig, override: TINAAConfig) -> TINAAConfig:
    """Merge two TINAAConfig objects; *override* takes precedence.

    Rules:
    - Scalar string fields: override wins when non-empty.
    - List fields: override replaces base when non-empty.
    - Dict fields (quality_gates): merged key-by-key, override wins on conflict.
    - Nested dataclasses (testing, alerts): replaced when override is non-default.

    The originals are never mutated.

    Args:
        base: Base configuration (lower precedence).
        override: Overriding configuration (higher precedence).

    Returns:
        New TINAAConfig that is the merge of *base* and *override*.
    """
    merged = copy.deepcopy(base)
    _apply_scalar_overrides(merged, override)
    _apply_list_overrides(merged, override)
    _apply_quality_gate_merge(merged, base, override)
    _apply_nested_overrides(merged, override)
    return merged


def _apply_scalar_overrides(merged: TINAAConfig, override: TINAAConfig) -> None:
    """Override scalar string fields when the override value is non-empty."""
    if override.product_name:
        merged.product_name = override.product_name
    if override.team:
        merged.team = override.team
    if override.description:
        merged.description = override.description


def _apply_list_overrides(merged: TINAAConfig, override: TINAAConfig) -> None:
    """Override list fields when the override list is non-empty."""
    if override.environments:
        merged.environments = copy.deepcopy(override.environments)
    if override.tags:
        merged.tags = list(override.tags)
    if override.ignore_paths:
        merged.ignore_paths = list(override.ignore_paths)


def _apply_quality_gate_merge(
    merged: TINAAConfig,
    base: TINAAConfig,
    override: TINAAConfig,
) -> None:
    """Key-level merge of quality_gates; override wins on conflict."""
    merged_gates = dict(copy.deepcopy(base.quality_gates))
    for gate_name, gate in override.quality_gates.items():
        merged_gates[gate_name] = copy.deepcopy(gate)
    merged.quality_gates = merged_gates


def _apply_nested_overrides(merged: TINAAConfig, override: TINAAConfig) -> None:
    """Replace nested dataclasses when the override is non-default."""
    if override.testing != TestingConfig():
        merged.testing = copy.deepcopy(override.testing)
    if override.alerts != AlertsConfig():
        merged.alerts = copy.deepcopy(override.alerts)
