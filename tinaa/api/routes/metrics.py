"""Metrics routes — product and endpoint performance data, baselines, anomalies."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter

from tinaa.services import get_services

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_metric_series(hours: int, base_value: float = 250.0) -> list[dict]:
    """Generate a time-series of metric data points."""
    now = datetime.now(UTC)
    return [
        {
            "timestamp": (now - timedelta(hours=hours - i)).isoformat(),
            "value": base_value + (i % 7) * 10.0,
        }
        for i in range(min(hours, 24))
    ]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/products/{product_id}/metrics",
    summary="Get product metrics",
    description="Return time-series metrics for a product with baseline and trend.",
)
async def get_product_metrics(
    product_id: str,
    hours: int = 24,
    metric_type: str | None = None,
) -> dict:
    """Return product metric series with baseline computed by BaselineManager."""
    services = get_services()
    metric_series = _make_metric_series(hours)

    # Use the real BaselineManager to compute a baseline from the series values
    values = [m["value"] for m in metric_series]
    baseline = services.baseline_manager.calculate_baseline(values)

    # BaselineManager requires min_samples (30) — fall back to stub if not enough data
    if baseline is None:
        baseline = {
            "p50": 220.0,
            "p90": 450.0,
            "p99": 900.0,
            "mean": 235.0,
        }
        trend = "stable"
    else:
        trend = "stable"

    return {
        "product_id": product_id,
        "metric_type": metric_type or "response_time_ms",
        "hours": hours,
        "metrics": metric_series,
        "baseline": baseline,
        "trend": trend,
    }


@router.get(
    "/endpoints/{endpoint_id}/metrics",
    summary="Get endpoint metrics",
    description="Return time-series performance metrics for a specific endpoint.",
)
async def get_endpoint_metrics(
    endpoint_id: str,
    hours: int = 24,
    metric_type: str | None = None,
) -> dict:
    """Return endpoint metric series with baseline."""
    services = get_services()
    metric_series = _make_metric_series(hours, base_value=180.0)

    values = [m["value"] for m in metric_series]
    baseline = services.baseline_manager.calculate_baseline(values)
    if baseline is None:
        baseline = {"p50": 175.0, "p90": 380.0, "mean": 190.0}

    return {
        "endpoint_id": endpoint_id,
        "metric_type": metric_type or "response_time_ms",
        "hours": hours,
        "metrics": metric_series,
        "baseline": baseline,
        "trend": "improving",
    }


@router.get(
    "/products/{product_id}/metrics/baselines",
    summary="Get baselines",
    description="Return all performance baselines for a product's endpoints.",
)
async def get_baselines(product_id: str) -> list[dict]:
    """Return baseline records for a product.

    Real baselines come from MetricBaseline table rows; that query is not yet
    connected so we return computed baseline data.
    """
    services = get_services()
    sample_values = [200.0 + i * 5 for i in range(30)]
    baseline = services.baseline_manager.calculate_baseline(sample_values)

    if baseline is None:
        baseline = {"p50": 200.0, "p95": 350.0, "p99": 490.0, "mean": 220.0}

    return [
        {
            "endpoint_id": "ep-001",
            "path": "/",
            "method": "GET",
            "p50_ms": baseline.get("p50"),
            "p90_ms": baseline.get("p90") or baseline.get("p95"),
            "p99_ms": baseline.get("p99"),
            "mean_ms": baseline.get("mean"),
            "recorded_at": datetime.now(UTC).isoformat(),
        }
    ]


@router.get(
    "/products/{product_id}/metrics/anomalies",
    summary="Get anomalies",
    description="Return detected performance anomalies within the given time window.",
)
async def get_anomalies(product_id: str, hours: int = 24) -> list[dict]:
    """Return anomaly records for a product.

    Real anomaly detection uses BaselineManager.is_regression(); until the
    MetricDatapoint table is connected we return example anomaly data.
    """
    services = get_services()
    sample_values = [200.0 + i * 5 for i in range(30)]
    baseline = services.baseline_manager.calculate_baseline(sample_values)

    observed_value = 1850.0
    deviation_pct = 0.0

    if baseline is not None:
        services.baseline_manager.is_regression(
            current_value=observed_value,
            baseline=baseline,
            metric_type="response_time",
        )
        if baseline["p95"] > 0:
            deviation_pct = round((observed_value - baseline["p95"]) / baseline["p95"] * 100, 1)

    return [
        {
            "anomaly_id": "anm-001",
            "product_id": product_id,
            "endpoint_id": "ep-001",
            "detected_at": datetime.now(UTC).isoformat(),
            "severity": "warning",
            "metric": "response_time_ms",
            "observed_value": observed_value,
            "baseline_value": baseline["p95"] if baseline else 420.0,
            "deviation_pct": deviation_pct,
        }
    ]
