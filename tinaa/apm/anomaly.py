"""
Anomaly detection for TINAA APM.

Provides statistical anomaly detection for metric time series using Z-score
analysis, trend comparison, and availability drop detection.
"""

from __future__ import annotations

import logging
import statistics

logger = logging.getLogger(__name__)

# Shift percent boundary above/below which a trend is flagged as directional
_STABLE_SHIFT_PCT = 5.0


class AnomalyDetector:
    """Detects anomalies in metric time series.

    Args:
        z_score_threshold: Z-score magnitude above which a point is anomalous.
        min_history: Minimum historical samples required before detection runs.
    """

    def __init__(
        self,
        z_score_threshold: float = 3.0,
        min_history: int = 10,
    ) -> None:
        self._z_threshold = z_score_threshold
        self._min_history = min_history

    def detect_point_anomaly(
        self,
        value: float,
        history: list[float],
    ) -> dict:
        """Detect if a single value is anomalous relative to historical data.

        Uses Z-score: ``z = (value - mean) / stddev``.
        When stddev is zero (all identical values), any different value is
        treated as anomalous; identical values are normal.

        Returns:
            dict with keys: is_anomaly, z_score, value, mean, stddev, direction
        """
        if len(history) < self._min_history:
            return {
                "is_anomaly": False,
                "z_score": 0.0,
                "value": value,
                "mean": 0.0,
                "stddev": 0.0,
                "direction": "normal",
            }

        mean = statistics.mean(history)
        stddev = statistics.pstdev(history)

        if stddev == 0.0:
            # All history values are identical: no variance means no basis for
            # declaring a statistical anomaly via Z-score. Return not anomalous.
            return {
                "is_anomaly": False,
                "z_score": 0.0,
                "value": value,
                "mean": mean,
                "stddev": stddev,
                "direction": "normal",
            }

        z_score = (value - mean) / stddev
        is_anomaly = abs(z_score) > self._z_threshold
        direction = _direction(value, mean, is_anomaly)

        return {
            "is_anomaly": is_anomaly,
            "z_score": z_score,
            "value": value,
            "mean": mean,
            "stddev": stddev,
            "direction": direction,
        }

    def detect_trend_anomaly(
        self,
        recent_values: list[float],
        historical_values: list[float],
    ) -> dict:
        """Detect whether the mean of recent values is anomalous vs history.

        Computes the Z-score of ``mean(recent_values)`` within the distribution
        of ``historical_values``.

        Returns:
            dict with keys: is_anomaly, recent_mean, historical_mean,
            shift_percent, direction
        """
        if len(historical_values) < self._min_history or not recent_values:
            return {
                "is_anomaly": False,
                "recent_mean": statistics.mean(recent_values) if recent_values else 0.0,
                "historical_mean": statistics.mean(historical_values) if historical_values else 0.0,
                "shift_percent": 0.0,
                "direction": "stable",
            }

        recent_mean = statistics.mean(recent_values)
        historical_mean = statistics.mean(historical_values)
        historical_stddev = statistics.pstdev(historical_values)

        if historical_stddev == 0.0:
            # No variance in historical data: cannot apply Z-score.
            # Not anomalous by default.
            is_anomaly = False
        else:
            z = (recent_mean - historical_mean) / historical_stddev
            is_anomaly = abs(z) > self._z_threshold

        shift_percent = _safe_shift_pct(recent_mean, historical_mean)
        direction = _trend_direction(shift_percent, is_anomaly)

        return {
            "is_anomaly": is_anomaly,
            "recent_mean": recent_mean,
            "historical_mean": historical_mean,
            "shift_percent": shift_percent,
            "direction": direction,
        }

    def detect_availability_drop(
        self,
        success_count: int,
        total_count: int,
        expected_rate: float = 0.99,
    ) -> dict:
        """Detect if availability has dropped below the expected rate.

        Returns:
            dict with keys: is_anomaly, current_rate, expected_rate,
            deficit_percent
        """
        if total_count == 0:
            return {
                "is_anomaly": False,
                "current_rate": 0.0,
                "expected_rate": expected_rate,
                "deficit_percent": 0.0,
            }

        current_rate = success_count / total_count
        is_anomaly = current_rate < expected_rate

        if expected_rate != 0.0:
            deficit_percent = (expected_rate - current_rate) / expected_rate * 100.0
        else:
            deficit_percent = 0.0

        return {
            "is_anomaly": is_anomaly,
            "current_rate": current_rate,
            "expected_rate": expected_rate,
            "deficit_percent": max(0.0, deficit_percent),
        }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _direction(value: float, mean: float, is_anomaly: bool) -> str:
    if not is_anomaly:
        return "normal"
    return "high" if value > mean else "low"


def _safe_shift_pct(recent_mean: float, historical_mean: float) -> float:
    if historical_mean == 0.0:
        return 0.0
    return (recent_mean - historical_mean) / abs(historical_mean) * 100.0


def _trend_direction(shift_percent: float, is_anomaly: bool) -> str:
    if not is_anomaly:
        return "stable"
    if shift_percent > _STABLE_SHIFT_PCT:
        return "increasing"
    if shift_percent < -_STABLE_SHIFT_PCT:
        return "decreasing"
    return "stable"
