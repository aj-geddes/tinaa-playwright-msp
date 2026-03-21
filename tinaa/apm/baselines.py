"""
Baseline management for TINAA APM.

Computes statistical baselines from historical metric samples and evaluates
regressions against those baselines using per-metric-type heuristics.
"""

from __future__ import annotations

import logging
import statistics

logger = logging.getLogger(__name__)

# Percentage thresholds for severity classification
_SEVERITY_MINOR_PCT = 10.0
_SEVERITY_MAJOR_PCT = 50.0
_SEVERITY_CRITICAL_PCT = 100.0

# Trend classification: change must exceed this % to leave "stable"
_TREND_THRESHOLD_PCT = 10.0

# Metric types where lower values are better (performance timings + error metrics)
_LOWER_IS_BETTER = frozenset(
    [
        "response_time",
        "lcp",
        "fcp",
        "ttfb",
        "inp",
        "cls",
        "error_rate",
        "dns_time",
        "tls_time",
    ]
)


class BaselineManager:
    """Manages performance baselines for endpoints.

    Args:
        min_samples: Minimum number of samples required to compute a baseline.
        window_hours: Historical window in hours (used externally when querying
            storage; stored here for reference).
    """

    def __init__(self, min_samples: int = 30, window_hours: int = 168) -> None:
        self._min_samples = min_samples
        self._window_hours = window_hours

    def calculate_baseline(self, values: list[float]) -> dict | None:
        """Compute a statistical baseline from a list of metric values.

        Returns ``None`` when fewer than ``min_samples`` values are provided.

        Returns:
            dict with keys: p50, p95, p99, mean, stddev, min, max, sample_count
        """
        if len(values) < self._min_samples:
            return None

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        mean = statistics.mean(sorted_vals)
        stddev = statistics.pstdev(sorted_vals)

        return {
            "p50": _percentile(sorted_vals, 50),
            "p95": _percentile(sorted_vals, 95),
            "p99": _percentile(sorted_vals, 99),
            "mean": mean,
            "stddev": stddev,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "sample_count": n,
        }

    def is_regression(
        self,
        current_value: float,
        baseline: dict,
        metric_type: str,
        sensitivity: float = 1.5,
    ) -> dict:
        """Evaluate whether ``current_value`` is a regression versus ``baseline``.

        Strategy per metric_type:
        - Lower-is-better metrics: regression when current > p95 * sensitivity
        - availability: regression when current < p50 / sensitivity

        Severity is determined by how far current exceeds the threshold:
        - none: no regression
        - minor: delta_percent in [0, 50)
        - major: delta_percent in [50, 100)
        - critical: delta_percent >= 100

        Returns:
            dict with keys: is_regression, severity, current, baseline_p95,
            delta_percent, message
        """
        p95 = baseline["p95"]
        p50 = baseline["p50"]
        delta_percent = _safe_pct_delta(current_value, p95)

        if metric_type == "availability":
            # Availability regression: any drop below median is a concern.
            # Use p50 as the expected rate; a drop beyond sensitivity margin triggers.
            # Threshold: current < p50 / sensitivity (e.g. 99.5/1.5=66.3 would be too lenient)
            # Instead treat ANY drop below p50 as at least a minor regression.
            is_reg = current_value < p50
            delta_pct_avail = _safe_pct_delta(current_value, p50)
            severity = _availability_severity(current_value, p50) if is_reg else "none"
            return {
                "is_regression": is_reg,
                "severity": severity,
                "current": current_value,
                "baseline_p95": p95,
                "delta_percent": abs(delta_pct_avail),
                "message": _build_message(metric_type, current_value, p95, is_reg),
            }

        threshold = p95 * sensitivity
        is_reg = current_value > threshold
        severity = _performance_severity(delta_percent) if is_reg else "none"

        return {
            "is_regression": is_reg,
            "severity": severity,
            "current": current_value,
            "baseline_p95": p95,
            "delta_percent": delta_percent,
            "message": _build_message(metric_type, current_value, p95, is_reg),
        }

    def compare_baselines(self, old_baseline: dict, new_baseline: dict) -> dict:
        """Compare two baselines to identify performance trends.

        Returns:
            dict with keys: p50_delta_percent, p95_delta_percent, trend, message
        """
        p50_delta = _safe_pct_delta(new_baseline["p50"], old_baseline["p50"])
        p95_delta = _safe_pct_delta(new_baseline["p95"], old_baseline["p95"])

        trend = _classify_trend(p50_delta, p95_delta)
        message = _trend_message(trend, p50_delta, p95_delta)

        return {
            "p50_delta_percent": p50_delta,
            "p95_delta_percent": p95_delta,
            "trend": trend,
            "message": message,
        }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Return the p-th percentile from a pre-sorted list using linear interpolation."""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (n - 1)
    lower = int(rank)
    upper = lower + 1
    if upper >= n:
        return sorted_values[-1]
    fraction = rank - lower
    return sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])


def _safe_pct_delta(current: float, reference: float) -> float:
    """Percent change from reference to current; 0 when reference is zero."""
    if reference == 0:
        return 0.0
    return (current - reference) / abs(reference) * 100.0


def _performance_severity(delta_percent: float) -> str:
    if delta_percent >= _SEVERITY_CRITICAL_PCT:
        return "critical"
    if delta_percent >= _SEVERITY_MAJOR_PCT:
        return "major"
    if delta_percent >= _SEVERITY_MINOR_PCT:
        return "minor"
    return "none"


def _availability_severity(current: float, p50: float) -> str:
    drop = p50 - current
    drop_pct = (drop / p50 * 100) if p50 != 0 else 0
    if drop_pct >= 5:
        return "critical"
    if drop_pct >= 2:
        return "major"
    return "minor"


def _build_message(metric_type: str, current: float, p95: float, is_reg: bool) -> str:
    if not is_reg:
        return f"{metric_type}: value {current:.2f} is within baseline (p95={p95:.2f})"
    return f"{metric_type}: value {current:.2f} exceeds baseline p95={p95:.2f}"


def _classify_trend(p50_delta: float, p95_delta: float) -> str:
    avg_delta = (p50_delta + p95_delta) / 2
    if avg_delta <= -_TREND_THRESHOLD_PCT:
        return "improving"
    if avg_delta >= _TREND_THRESHOLD_PCT:
        return "degrading"
    return "stable"


def _trend_message(trend: str, p50_delta: float, p95_delta: float) -> str:
    return f"Baseline trend: {trend} (p50 {p50_delta:+.1f}%, p95 {p95_delta:+.1f}%)"
