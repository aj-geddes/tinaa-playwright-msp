"""Quality trend analysis for TINAA MSP.

Analyses sequences of quality score history entries to detect trends,
find regressions, and compare environments.
"""

import statistics
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIVERGENCE_THRESHOLD = 5.0  # score-point gap that counts as "diverging"
STABLE_SLOPE_THRESHOLD = 0.5  # points per day — below this is "stable"

_COMPONENT_KEYS = (
    "test_health",
    "performance_health",
    "security_posture",
    "accessibility",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_timestamp(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp string into a timezone-aware datetime."""
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _days_between(older: datetime, newer: datetime) -> float:
    """Return the number of days between two datetimes (newer - older)."""
    return (newer - older).total_seconds() / 86400.0


def _linear_regression(xs: list[float], ys: list[float]) -> float:
    """Return the slope (dy/dx) of the best-fit line through the points."""
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    denominator = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if abs(denominator) < 1e-10:
        return 0.0
    return numerator / denominator


def _score_at_days_ago(
    sorted_entries: list[dict],
    now: datetime,
    target_days: float,
    tolerance_days: float = 2.0,
) -> float | None:
    """Find the score closest to *target_days* ago within *tolerance_days*."""
    best: float | None = None
    best_delta = float("inf")
    for entry in sorted_entries:
        ts = _parse_timestamp(entry["timestamp"])
        days_ago = _days_between(ts, now)
        delta = abs(days_ago - target_days)
        if delta <= tolerance_days and delta < best_delta:
            best = entry["score"]
            best_delta = delta
    return best


def _component_score(entry: dict, component: str) -> float | None:
    """Extract a component score from a history entry."""
    components = entry.get("components", {})
    comp = components.get(component)
    if comp is None:
        return None
    if isinstance(comp, dict):
        return comp.get("score")
    return float(comp)


# ---------------------------------------------------------------------------
# Trend Analyzer
# ---------------------------------------------------------------------------


class QualityTrendAnalyzer:
    """Analyses quality score trends over time."""

    def analyze_trend(self, scores: list[dict], window_days: int = 7) -> dict:
        """Analyse quality score trend from a list of history entries.

        Each entry: {"score": float, "timestamp": str (ISO-8601), "components": dict}

        Returns a comprehensive trend analysis dict.
        """
        if not scores:
            return self._empty_trend()

        sorted_scores = sorted(scores, key=lambda e: _parse_timestamp(e["timestamp"]))
        now = _parse_timestamp(sorted_scores[-1]["timestamp"])
        current_score = float(sorted_scores[-1]["score"])

        slope, direction = self._compute_slope_and_direction(sorted_scores, now)

        score_7d_ago = _score_at_days_ago(sorted_scores, now, 7.0)
        score_30d_ago = _score_at_days_ago(sorted_scores, now, 30.0, tolerance_days=3.0)
        delta_7d = (current_score - score_7d_ago) if score_7d_ago is not None else None
        delta_30d = (current_score - score_30d_ago) if score_30d_ago is not None else None

        return {
            "current_score": current_score,
            "trend_direction": direction,
            "trend_slope": slope,
            "score_7d_ago": score_7d_ago,
            "score_30d_ago": score_30d_ago,
            "delta_7d": delta_7d,
            "delta_30d": delta_30d,
            "component_trends": self._compute_component_trends(sorted_scores, now),
            "volatility": self._compute_volatility(sorted_scores, now, window_days),
            "forecast_7d": float(max(0.0, min(100.0, current_score + slope * 7.0))),
        }

    @staticmethod
    def _compute_slope_and_direction(sorted_scores: list[dict], now: datetime) -> tuple[float, str]:
        """Return (slope in points/day, direction string) from sorted score history."""
        # Negate days_ago so that x increases toward now -> positive slope = improving
        xs = [-_days_between(_parse_timestamp(e["timestamp"]), now) for e in sorted_scores]
        ys = [float(e["score"]) for e in sorted_scores]
        slope = _linear_regression(xs, ys)
        if slope > STABLE_SLOPE_THRESHOLD:
            direction = "improving"
        elif slope < -STABLE_SLOPE_THRESHOLD:
            direction = "degrading"
        else:
            direction = "stable"
        return slope, direction

    @staticmethod
    def _compute_volatility(sorted_scores: list[dict], now: datetime, window_days: int) -> float:
        """Return the standard deviation of scores within *window_days*."""
        recent = [
            entry["score"]
            for entry in sorted_scores
            if _days_between(_parse_timestamp(entry["timestamp"]), now) <= window_days
        ]
        return statistics.stdev(recent) if len(recent) >= 2 else 0.0

    def find_score_drops(self, scores: list[dict], threshold: float = 5.0) -> list[dict]:
        """Find significant score drops exceeding *threshold* points.

        Returns a list of drop events sorted chronologically.
        """
        if len(scores) < 2:
            return []

        sorted_scores = sorted(scores, key=lambda e: _parse_timestamp(e["timestamp"]))
        drops: list[dict] = []

        for i in range(1, len(sorted_scores)):
            prev = float(sorted_scores[i - 1]["score"])
            curr = float(sorted_scores[i]["score"])
            delta = curr - prev  # negative means a drop
            if delta <= -threshold:
                drops.append(
                    {
                        "from_score": prev,
                        "to_score": curr,
                        "delta": delta,
                        "timestamp": sorted_scores[i]["timestamp"],
                        "probable_cause": None,  # requires external context to determine
                    }
                )

        return drops

    def compare_environments(
        self,
        prod_scores: list[dict],
        staging_scores: list[dict],
    ) -> dict:
        """Compare quality scores between production and staging.

        Returns a comparison dict with divergence detection.
        """
        prod_current = self._latest_score(prod_scores)
        staging_current = self._latest_score(staging_scores)

        if prod_current is None or staging_current is None:
            return {
                "prod_current": prod_current,
                "staging_current": staging_current,
                "delta": None,
                "diverging": False,
                "message": "Insufficient data for comparison.",
            }

        delta = prod_current - staging_current
        diverging = abs(delta) >= DIVERGENCE_THRESHOLD

        if abs(delta) < DIVERGENCE_THRESHOLD:
            message = (
                f"Environments are aligned. "
                f"Production: {prod_current:.1f}, Staging: {staging_current:.1f}."
            )
        elif staging_current < prod_current:
            message = (
                f"Staging quality ({staging_current:.1f}) is {abs(delta):.1f} points "
                f"below production ({prod_current:.1f}). Review before promoting."
            )
        else:
            message = (
                f"Staging quality ({staging_current:.1f}) is {abs(delta):.1f} points "
                f"above production ({prod_current:.1f}). Production may need attention."
            )

        return {
            "prod_current": prod_current,
            "staging_current": staging_current,
            "delta": delta,
            "diverging": diverging,
            "message": message,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _latest_score(scores: list[dict]) -> float | None:
        """Return the most recent score from a history list."""
        if not scores:
            return None
        latest = max(scores, key=lambda e: _parse_timestamp(e["timestamp"]))
        return float(latest["score"])

    @staticmethod
    def _empty_trend() -> dict:
        """Return the structure for an empty trend result."""
        return {
            "current_score": None,
            "trend_direction": "stable",
            "trend_slope": 0.0,
            "score_7d_ago": None,
            "score_30d_ago": None,
            "delta_7d": None,
            "delta_30d": None,
            "component_trends": {k: {"direction": "stable", "delta": 0.0} for k in _COMPONENT_KEYS},
            "volatility": 0.0,
            "forecast_7d": None,
        }

    def _compute_component_trends(self, sorted_scores: list[dict], now: datetime) -> dict:
        """Compute per-component trend direction and delta vs. oldest entry."""
        result: dict = {}
        for comp in _COMPONENT_KEYS:
            current_val = _component_score(sorted_scores[-1], comp)
            oldest_val = _component_score(sorted_scores[0], comp)

            if current_val is None or oldest_val is None:
                result[comp] = {"direction": "stable", "delta": 0.0}
                continue

            delta = current_val - oldest_val
            days_span = _days_between(_parse_timestamp(sorted_scores[0]["timestamp"]), now)
            slope = (delta / days_span) if days_span > 0 else 0.0

            if slope > STABLE_SLOPE_THRESHOLD:
                direction = "improving"
            elif slope < -STABLE_SLOPE_THRESHOLD:
                direction = "degrading"
            else:
                direction = "stable"

            result[comp] = {"direction": direction, "delta": delta}

        return result
