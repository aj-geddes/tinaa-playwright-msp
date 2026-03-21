"""
Tests for TINAA APM layer.

Covers:
- MetricCollector buffering and flushing
- BaselineManager calculation and regression detection
- AnomalyDetector point, trend, and availability detection
- WebVitalsCollector threshold evaluation
- EndpointMonitor HTTP probe with mocked httpx
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tinaa.apm.collector import MetricCollector, MetricSample, MetricType
from tinaa.apm.baselines import BaselineManager
from tinaa.apm.anomaly import AnomalyDetector
from tinaa.apm.web_vitals import WebVitalsCollector
from tinaa.apm.monitor import EndpointMonitor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_sample(
    metric_type: MetricType = MetricType.RESPONSE_TIME,
    value: float = 200.0,
    endpoint_id: str = "endpoint-uuid-1",
) -> MetricSample:
    return MetricSample(
        endpoint_id=endpoint_id,
        metric_type=metric_type,
        value=value,
        timestamp=datetime.now(tz=timezone.utc),
    )


# ===========================================================================
# MetricCollector tests
# ===========================================================================


class TestMetricCollectorBuffering:
    """MetricCollector buffers samples in memory."""

    @pytest.mark.asyncio
    async def test_record_single_sample_increments_buffer(self):
        collector = MetricCollector()
        sample = make_sample()
        await collector.record(sample)
        assert collector.get_buffer_size() == 1

    @pytest.mark.asyncio
    async def test_record_batch_adds_all_samples(self):
        collector = MetricCollector()
        samples = [make_sample(value=float(i)) for i in range(5)]
        await collector.record_batch(samples)
        assert collector.get_buffer_size() == 5

    @pytest.mark.asyncio
    async def test_buffer_is_empty_on_creation(self):
        collector = MetricCollector()
        assert collector.get_buffer_size() == 0

    @pytest.mark.asyncio
    async def test_flush_clears_buffer(self):
        collector = MetricCollector()
        for _ in range(3):
            await collector.record(make_sample())
        await collector.flush()
        assert collector.get_buffer_size() == 0

    @pytest.mark.asyncio
    async def test_flush_calls_storage_callback(self):
        collector = MetricCollector()
        received: list[list[MetricSample]] = []

        async def capture(batch: list[MetricSample]) -> None:
            received.append(batch)

        collector.set_storage_callback(capture)
        samples = [make_sample(value=float(i)) for i in range(3)]
        await collector.record_batch(samples)
        await collector.flush()
        assert len(received) == 1
        assert len(received[0]) == 3

    @pytest.mark.asyncio
    async def test_flush_without_callback_does_not_raise(self):
        collector = MetricCollector()
        await collector.record(make_sample())
        # Should not raise even with no callback set
        await collector.flush()
        assert collector.get_buffer_size() == 0

    @pytest.mark.asyncio
    async def test_auto_flush_when_batch_size_reached(self):
        flushed: list[list[MetricSample]] = []

        async def capture(batch: list[MetricSample]) -> None:
            flushed.append(batch)

        collector = MetricCollector(batch_size=3)
        collector.set_storage_callback(capture)
        for i in range(3):
            await collector.record(make_sample(value=float(i)))
        # After 3 records with batch_size=3, buffer should be flushed
        assert collector.get_buffer_size() == 0
        assert len(flushed) == 1

    @pytest.mark.asyncio
    async def test_flush_passes_correct_sample_data(self):
        received: list[MetricSample] = []

        async def capture(batch: list[MetricSample]) -> None:
            received.extend(batch)

        collector = MetricCollector()
        collector.set_storage_callback(capture)
        sample = MetricSample(
            endpoint_id="ep-001",
            metric_type=MetricType.LCP,
            value=1500.0,
            timestamp=datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc),
            metadata={"page": "/home"},
        )
        await collector.record(sample)
        await collector.flush()
        assert received[0].endpoint_id == "ep-001"
        assert received[0].metric_type == MetricType.LCP
        assert received[0].value == 1500.0
        assert received[0].metadata == {"page": "/home"}

    @pytest.mark.asyncio
    async def test_concurrent_records_are_thread_safe(self):
        collector = MetricCollector(batch_size=1000)

        async def record_many() -> None:
            for i in range(50):
                await collector.record(make_sample(value=float(i)))

        await asyncio.gather(record_many(), record_many())
        assert collector.get_buffer_size() == 100


# ===========================================================================
# BaselineManager tests
# ===========================================================================


class TestBaselineCalculation:
    """BaselineManager computes statistical baselines from samples."""

    def test_calculate_baseline_returns_none_when_too_few_samples(self):
        manager = BaselineManager(min_samples=30)
        result = manager.calculate_baseline([100.0] * 5)
        assert result is None

    def test_calculate_baseline_returns_dict_with_required_keys(self):
        manager = BaselineManager(min_samples=5)
        values = [float(i) for i in range(1, 31)]
        result = manager.calculate_baseline(values)
        assert result is not None
        for key in ("p50", "p95", "p99", "mean", "stddev", "min", "max", "sample_count"):
            assert key in result, f"Missing key: {key}"

    def test_calculate_baseline_correct_min_max(self):
        manager = BaselineManager(min_samples=5)
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = manager.calculate_baseline(values)
        assert result is not None
        assert result["min"] == 10.0
        assert result["max"] == 50.0

    def test_calculate_baseline_correct_sample_count(self):
        manager = BaselineManager(min_samples=5)
        values = [float(i) for i in range(10)]
        result = manager.calculate_baseline(values)
        assert result is not None
        assert result["sample_count"] == 10

    def test_calculate_baseline_p50_is_median(self):
        manager = BaselineManager(min_samples=5)
        # Sorted: 1..10 -> median = 5.5
        values = [float(i) for i in range(1, 11)]
        result = manager.calculate_baseline(values)
        assert result is not None
        assert result["p50"] == pytest.approx(5.5, rel=0.01)

    def test_calculate_baseline_stddev_is_positive(self):
        manager = BaselineManager(min_samples=5)
        values = [100.0, 200.0, 300.0, 150.0, 250.0]
        result = manager.calculate_baseline(values)
        assert result is not None
        assert result["stddev"] > 0.0

    def test_calculate_baseline_single_unique_value_stddev_zero(self):
        manager = BaselineManager(min_samples=5)
        values = [100.0] * 10
        result = manager.calculate_baseline(values)
        assert result is not None
        assert result["stddev"] == pytest.approx(0.0, abs=1e-9)


class TestRegressionDetection:
    """BaselineManager identifies regressions against baselines."""

    def _make_baseline(
        self,
        p50: float = 200.0,
        p95: float = 400.0,
        p99: float = 600.0,
    ) -> dict:
        return {
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "mean": p50,
            "stddev": 50.0,
            "min": 100.0,
            "max": p99,
            "sample_count": 100,
        }

    def test_no_regression_when_within_threshold(self):
        manager = BaselineManager()
        baseline = self._make_baseline(p95=400.0)
        # current = 500 < 400 * 1.5 = 600
        result = manager.is_regression(500.0, baseline, "response_time")
        assert result["is_regression"] is False

    def test_regression_detected_when_exceeds_threshold(self):
        manager = BaselineManager()
        baseline = self._make_baseline(p95=400.0)
        # current = 700 > 400 * 1.5 = 600
        result = manager.is_regression(700.0, baseline, "response_time")
        assert result["is_regression"] is True

    def test_regression_result_has_required_keys(self):
        manager = BaselineManager()
        baseline = self._make_baseline()
        result = manager.is_regression(500.0, baseline, "response_time")
        for key in ("is_regression", "severity", "current", "baseline_p95", "delta_percent", "message"):
            assert key in result, f"Missing key: {key}"

    def test_severity_is_none_for_no_regression(self):
        manager = BaselineManager()
        baseline = self._make_baseline(p95=400.0)
        result = manager.is_regression(200.0, baseline, "response_time")
        assert result["severity"] == "none"

    def test_critical_severity_for_large_regression(self):
        manager = BaselineManager()
        baseline = self._make_baseline(p95=100.0)
        # current = 500 => 400% above p95=100, should be critical
        result = manager.is_regression(500.0, baseline, "response_time")
        assert result["is_regression"] is True
        assert result["severity"] == "critical"

    def test_availability_regression_logic(self):
        """Availability uses inverse logic: lower is worse."""
        manager = BaselineManager()
        # baseline p50=99.5% availability; current=95% -- degraded
        baseline = self._make_baseline(p50=99.5, p95=100.0, p99=100.0)
        result = manager.is_regression(95.0, baseline, "availability")
        assert result["is_regression"] is True

    def test_delta_percent_is_accurate(self):
        manager = BaselineManager()
        baseline = self._make_baseline(p95=200.0)
        # current=300 => delta = (300-200)/200 * 100 = 50%
        result = manager.is_regression(300.0, baseline, "response_time")
        assert result["delta_percent"] == pytest.approx(50.0, rel=0.01)


class TestBaselineComparison:
    """BaselineManager can compare two baselines to detect trends."""

    def _make_baseline(self, p50: float, p95: float) -> dict:
        return {
            "p50": p50,
            "p95": p95,
            "p99": p95,
            "mean": p50,
            "stddev": 10.0,
            "min": p50 - 20,
            "max": p95,
            "sample_count": 100,
        }

    def test_compare_stable_baselines(self):
        manager = BaselineManager()
        old = self._make_baseline(200.0, 400.0)
        new = self._make_baseline(202.0, 402.0)
        result = manager.compare_baselines(old, new)
        assert result["trend"] == "stable"

    def test_compare_improving_baselines(self):
        manager = BaselineManager()
        old = self._make_baseline(300.0, 600.0)
        new = self._make_baseline(200.0, 400.0)
        result = manager.compare_baselines(old, new)
        assert result["trend"] == "improving"

    def test_compare_degrading_baselines(self):
        manager = BaselineManager()
        old = self._make_baseline(200.0, 400.0)
        new = self._make_baseline(400.0, 800.0)
        result = manager.compare_baselines(old, new)
        assert result["trend"] == "degrading"

    def test_compare_returns_required_keys(self):
        manager = BaselineManager()
        old = self._make_baseline(200.0, 400.0)
        new = self._make_baseline(200.0, 400.0)
        result = manager.compare_baselines(old, new)
        for key in ("p50_delta_percent", "p95_delta_percent", "trend", "message"):
            assert key in result, f"Missing key: {key}"


# ===========================================================================
# AnomalyDetector tests
# ===========================================================================


class TestPointAnomalyDetection:
    """AnomalyDetector identifies statistically anomalous values."""

    def test_normal_value_not_anomaly(self):
        detector = AnomalyDetector(z_score_threshold=3.0)
        history = [100.0] * 20
        result = detector.detect_point_anomaly(101.0, history)
        assert result["is_anomaly"] is False

    def test_high_outlier_is_anomaly(self):
        detector = AnomalyDetector(z_score_threshold=3.0)
        # mean=100, stddev~0 so any different value is infinite z-score
        history = [100.0 + i * 0.1 for i in range(20)]
        result = detector.detect_point_anomaly(1000.0, history)
        assert result["is_anomaly"] is True
        assert result["direction"] == "high"

    def test_low_outlier_is_anomaly(self):
        detector = AnomalyDetector(z_score_threshold=3.0)
        history = [100.0 + i * 0.1 for i in range(20)]
        result = detector.detect_point_anomaly(-500.0, history)
        assert result["is_anomaly"] is True
        assert result["direction"] == "low"

    def test_result_contains_required_keys(self):
        detector = AnomalyDetector()
        history = [float(i) for i in range(15)]
        result = detector.detect_point_anomaly(7.0, history)
        for key in ("is_anomaly", "z_score", "value", "mean", "stddev", "direction"):
            assert key in result, f"Missing key: {key}"

    def test_insufficient_history_returns_not_anomaly(self):
        detector = AnomalyDetector(min_history=10)
        result = detector.detect_point_anomaly(999.0, [1.0, 2.0, 3.0])
        assert result["is_anomaly"] is False

    def test_z_score_direction_normal_for_mean_value(self):
        detector = AnomalyDetector(z_score_threshold=3.0)
        history = [100.0] * 15
        # Use value exactly at mean; stddev=0 so we treat as normal
        result = detector.detect_point_anomaly(100.0, history)
        assert result["direction"] == "normal"


class TestTrendAnomalyDetection:
    """AnomalyDetector compares recent trend to historical distribution."""

    def test_stable_trend_not_anomaly(self):
        detector = AnomalyDetector()
        historical = [100.0] * 30
        recent = [101.0, 100.0, 99.0, 100.5]
        result = detector.detect_trend_anomaly(recent, historical)
        assert result["is_anomaly"] is False

    def test_increasing_trend_detected(self):
        detector = AnomalyDetector(z_score_threshold=2.0)
        historical = [100.0 + i * 0.1 for i in range(30)]
        recent = [500.0, 510.0, 520.0, 530.0]
        result = detector.detect_trend_anomaly(recent, historical)
        assert result["is_anomaly"] is True
        assert result["direction"] == "increasing"

    def test_decreasing_trend_detected(self):
        detector = AnomalyDetector(z_score_threshold=2.0)
        historical = [100.0 + i * 0.1 for i in range(30)]
        recent = [-300.0, -310.0, -320.0, -330.0]
        result = detector.detect_trend_anomaly(recent, historical)
        assert result["is_anomaly"] is True
        assert result["direction"] == "decreasing"

    def test_result_contains_required_keys(self):
        detector = AnomalyDetector()
        result = detector.detect_trend_anomaly([100.0] * 5, [100.0] * 20)
        for key in ("is_anomaly", "recent_mean", "historical_mean", "shift_percent", "direction"):
            assert key in result, f"Missing key: {key}"


class TestAvailabilityDropDetection:
    """AnomalyDetector flags availability drops."""

    def test_full_availability_not_anomaly(self):
        detector = AnomalyDetector()
        result = detector.detect_availability_drop(100, 100, expected_rate=0.99)
        assert result["is_anomaly"] is False

    def test_low_availability_is_anomaly(self):
        detector = AnomalyDetector()
        result = detector.detect_availability_drop(90, 100, expected_rate=0.99)
        assert result["is_anomaly"] is True

    def test_current_rate_calculation(self):
        detector = AnomalyDetector()
        result = detector.detect_availability_drop(95, 100, expected_rate=0.99)
        assert result["current_rate"] == pytest.approx(0.95, rel=0.001)

    def test_deficit_percent_is_accurate(self):
        detector = AnomalyDetector()
        # current=0.95, expected=0.99 -> deficit = (0.99-0.95)/0.99 * 100
        result = detector.detect_availability_drop(95, 100, expected_rate=0.99)
        expected_deficit = (0.99 - 0.95) / 0.99 * 100
        assert result["deficit_percent"] == pytest.approx(expected_deficit, rel=0.01)

    def test_result_contains_required_keys(self):
        detector = AnomalyDetector()
        result = detector.detect_availability_drop(99, 100)
        for key in ("is_anomaly", "current_rate", "expected_rate", "deficit_percent"):
            assert key in result, f"Missing key: {key}"

    def test_zero_total_count_returns_not_anomaly(self):
        """Edge case: no probes yet, cannot determine anomaly."""
        detector = AnomalyDetector()
        result = detector.detect_availability_drop(0, 0, expected_rate=0.99)
        assert result["is_anomaly"] is False


# ===========================================================================
# WebVitalsCollector tests
# ===========================================================================


class TestWebVitalsEvaluation:
    """WebVitalsCollector.evaluate_web_vitals applies Google thresholds."""

    def test_all_good_vitals(self):
        vitals = {"lcp_ms": 1500.0, "fcp_ms": 1000.0, "cls": 0.05, "inp_ms": 150.0, "ttfb_ms": 200.0}
        result = WebVitalsCollector.evaluate_web_vitals(vitals)
        assert result["lcp"]["rating"] == "good"
        assert result["fcp"]["rating"] == "good"
        assert result["cls"]["rating"] == "good"
        assert result["inp"]["rating"] == "good"
        assert result["overall_rating"] == "good"

    def test_lcp_needs_improvement(self):
        vitals = {"lcp_ms": 3000.0, "fcp_ms": 1000.0, "cls": 0.05, "inp_ms": 150.0, "ttfb_ms": 200.0}
        result = WebVitalsCollector.evaluate_web_vitals(vitals)
        assert result["lcp"]["rating"] == "needs-improvement"

    def test_lcp_poor(self):
        vitals = {"lcp_ms": 5000.0, "fcp_ms": 1000.0, "cls": 0.05, "inp_ms": 150.0, "ttfb_ms": 200.0}
        result = WebVitalsCollector.evaluate_web_vitals(vitals)
        assert result["lcp"]["rating"] == "poor"

    def test_fcp_thresholds(self):
        # good < 1800ms
        vitals_good = {"lcp_ms": 1000.0, "fcp_ms": 1700.0, "cls": 0.05, "inp_ms": 150.0, "ttfb_ms": 100.0}
        assert WebVitalsCollector.evaluate_web_vitals(vitals_good)["fcp"]["rating"] == "good"
        # needs-improvement < 3000ms
        vitals_ni = {"lcp_ms": 1000.0, "fcp_ms": 2500.0, "cls": 0.05, "inp_ms": 150.0, "ttfb_ms": 100.0}
        assert WebVitalsCollector.evaluate_web_vitals(vitals_ni)["fcp"]["rating"] == "needs-improvement"
        # poor >= 3000ms
        vitals_poor = {"lcp_ms": 1000.0, "fcp_ms": 4000.0, "cls": 0.05, "inp_ms": 150.0, "ttfb_ms": 100.0}
        assert WebVitalsCollector.evaluate_web_vitals(vitals_poor)["fcp"]["rating"] == "poor"

    def test_cls_thresholds(self):
        # good < 0.1
        assert WebVitalsCollector.evaluate_web_vitals(
            {"lcp_ms": 1000.0, "fcp_ms": 1000.0, "cls": 0.05, "inp_ms": 100.0, "ttfb_ms": 100.0}
        )["cls"]["rating"] == "good"
        # needs-improvement < 0.25
        assert WebVitalsCollector.evaluate_web_vitals(
            {"lcp_ms": 1000.0, "fcp_ms": 1000.0, "cls": 0.15, "inp_ms": 100.0, "ttfb_ms": 100.0}
        )["cls"]["rating"] == "needs-improvement"
        # poor >= 0.25
        assert WebVitalsCollector.evaluate_web_vitals(
            {"lcp_ms": 1000.0, "fcp_ms": 1000.0, "cls": 0.30, "inp_ms": 100.0, "ttfb_ms": 100.0}
        )["cls"]["rating"] == "poor"

    def test_inp_thresholds(self):
        # good < 200ms
        assert WebVitalsCollector.evaluate_web_vitals(
            {"lcp_ms": 1000.0, "fcp_ms": 1000.0, "cls": 0.05, "inp_ms": 150.0, "ttfb_ms": 100.0}
        )["inp"]["rating"] == "good"
        # needs-improvement < 500ms
        assert WebVitalsCollector.evaluate_web_vitals(
            {"lcp_ms": 1000.0, "fcp_ms": 1000.0, "cls": 0.05, "inp_ms": 350.0, "ttfb_ms": 100.0}
        )["inp"]["rating"] == "needs-improvement"
        # poor >= 500ms
        assert WebVitalsCollector.evaluate_web_vitals(
            {"lcp_ms": 1000.0, "fcp_ms": 1000.0, "cls": 0.05, "inp_ms": 600.0, "ttfb_ms": 100.0}
        )["inp"]["rating"] == "poor"

    def test_overall_rating_worst_wins(self):
        """Overall rating is the worst rating among all vitals."""
        vitals = {"lcp_ms": 5000.0, "fcp_ms": 1000.0, "cls": 0.05, "inp_ms": 150.0, "ttfb_ms": 100.0}
        result = WebVitalsCollector.evaluate_web_vitals(vitals)
        assert result["overall_rating"] == "poor"

    def test_evaluate_returns_value_in_rating_dict(self):
        vitals = {"lcp_ms": 1500.0, "fcp_ms": 1000.0, "cls": 0.05, "inp_ms": 150.0, "ttfb_ms": 200.0}
        result = WebVitalsCollector.evaluate_web_vitals(vitals)
        assert result["lcp"]["value"] == 1500.0
        assert result["fcp"]["value"] == 1000.0
        assert result["cls"]["value"] == 0.05

    def test_inp_none_skipped_in_overall(self):
        """If INP is None it should be omitted from overall rating calculation."""
        vitals = {"lcp_ms": 1500.0, "fcp_ms": 1000.0, "cls": 0.05, "inp_ms": None, "ttfb_ms": 200.0}
        result = WebVitalsCollector.evaluate_web_vitals(vitals)
        assert result["overall_rating"] == "good"

    def test_injection_script_is_nonempty_string(self):
        script = WebVitalsCollector.get_injection_script()
        assert isinstance(script, str)
        assert len(script) > 100

    def test_injection_script_contains_performance_observer(self):
        script = WebVitalsCollector.get_injection_script()
        assert "PerformanceObserver" in script

    def test_injection_script_stores_on_window_tinaa(self):
        script = WebVitalsCollector.get_injection_script()
        assert "__TINAA_WEB_VITALS__" in script

    def test_extraction_script_references_tinaa_vitals(self):
        script = WebVitalsCollector.get_extraction_script()
        assert "__TINAA_WEB_VITALS__" in script


# ===========================================================================
# EndpointMonitor tests (HTTP probe with mocked httpx)
# ===========================================================================


class TestEndpointMonitorHttpProbe:
    """EndpointMonitor.probe_http collects metrics from HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_probe_http_returns_up_for_200(self):
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"OK"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.1

        with patch("tinaa.apm.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)

            result = await monitor.probe_http("ep-001", "https://example.com")

        assert result["status"] == "up"

    @pytest.mark.asyncio
    async def test_probe_http_returns_down_for_5xx(self):
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.content = b"Server Error"
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.5

        with patch("tinaa.apm.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)

            result = await monitor.probe_http(
                "ep-001", "https://example.com", expected_status=200
            )

        assert result["status"] == "down"
        assert result["status_code"] == 500

    @pytest.mark.asyncio
    async def test_probe_http_returns_response_time_ms(self):
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"OK"
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.25  # 250ms

        with patch("tinaa.apm.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)

            result = await monitor.probe_http("ep-001", "https://example.com")

        assert result["response_time_ms"] == pytest.approx(250.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_probe_http_records_metrics_in_collector(self):
        collector = MetricCollector(batch_size=1000)
        monitor = EndpointMonitor(collector)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"body data here"
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.1

        with patch("tinaa.apm.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)

            await monitor.probe_http("ep-002", "https://example.com")

        # Should have recorded at least response_time and status_code
        assert collector.get_buffer_size() >= 2

    @pytest.mark.asyncio
    async def test_probe_http_returns_error_on_timeout(self):
        import httpx as httpx_module

        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        with patch("tinaa.apm.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(side_effect=httpx_module.TimeoutException("timeout"))

            result = await monitor.probe_http("ep-001", "https://example.com")

        assert result["status"] == "down"
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_probe_http_result_has_required_keys(self):
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"OK"
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.1

        with patch("tinaa.apm.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)

            result = await monitor.probe_http("ep-001", "https://example.com")

        for key in ("status", "response_time_ms", "status_code", "ttfb_ms", "headers", "error"):
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_probe_http_degraded_for_slow_response(self):
        """Status is 'degraded' when response is 200 but very slow (> timeout/2)."""
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"slow"
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 20.0  # 20 seconds = degraded

        with patch("tinaa.apm.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)

            result = await monitor.probe_http(
                "ep-001", "https://example.com", timeout=30.0
            )

        assert result["status"] == "degraded"


class TestEndpointMonitorLifecycle:
    """EndpointMonitor starts and stops monitoring loops."""

    @pytest.mark.asyncio
    async def test_get_monitoring_status_empty_initially(self):
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)
        status = monitor.get_monitoring_status()
        assert isinstance(status, dict)
        assert len(status) == 0

    @pytest.mark.asyncio
    async def test_stop_monitoring_all_when_none_running(self):
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)
        # Should not raise
        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_stop_specific_endpoint(self):
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)
        # Inject a fake task
        fake_task = asyncio.create_task(asyncio.sleep(100))
        monitor._tasks["ep-test"] = fake_task
        await monitor.stop_monitoring("ep-test")
        assert "ep-test" not in monitor._tasks
        # Clean up
        fake_task.cancel()
        try:
            await fake_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_start_monitoring_registers_tasks(self):
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        endpoints = [
            {
                "id": "ep-001",
                "url": "https://example.com",
                "method": "GET",
                "type": "health",
                "interval_seconds": 1,
                "expected_status": 200,
            }
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"OK"
        mock_response.headers = {}
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.05

        with patch("tinaa.apm.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(return_value=mock_response)

            await monitor.start_monitoring(endpoints)
            await asyncio.sleep(0.05)
            assert "ep-001" in monitor._tasks
            await monitor.stop_monitoring()


# ===========================================================================
# Additional coverage: edge cases and error paths
# ===========================================================================


class TestMetricCollectorEdgeCases:
    """Additional MetricCollector tests for error paths."""

    @pytest.mark.asyncio
    async def test_flush_empty_buffer_is_noop(self):
        """Flushing an empty buffer should not call the callback."""
        called = []

        async def capture(batch):
            called.append(batch)

        collector = MetricCollector()
        collector.set_storage_callback(capture)
        await collector.flush()
        assert called == []

    @pytest.mark.asyncio
    async def test_flush_exception_in_callback_does_not_propagate(self):
        """A failing storage callback must not crash the collector."""
        async def failing_callback(batch):
            raise RuntimeError("storage unavailable")

        collector = MetricCollector()
        collector.set_storage_callback(failing_callback)
        await collector.record(make_sample())
        # Should not raise
        await collector.flush()
        # Buffer should be drained even if callback fails
        assert collector.get_buffer_size() == 0

    @pytest.mark.asyncio
    async def test_record_batch_auto_flush(self):
        """record_batch triggers flush when batch_size reached."""
        flushed = []

        async def capture(batch):
            flushed.append(len(batch))

        collector = MetricCollector(batch_size=3)
        collector.set_storage_callback(capture)
        await collector.record_batch([make_sample(value=float(i)) for i in range(3)])
        assert collector.get_buffer_size() == 0
        assert flushed == [3]


class TestBaselineEdgeCases:
    """Additional baseline edge cases."""

    def test_regression_minor_severity_boundary(self):
        """A small regression (10-50% above p95) should be 'minor'."""
        manager = BaselineManager()
        baseline = {
            "p50": 200.0, "p95": 300.0, "p99": 400.0,
            "mean": 200.0, "stddev": 30.0, "min": 100.0, "max": 400.0,
            "sample_count": 100,
        }
        # threshold = p95 * 1.5 = 300 * 1.5 = 450; current must exceed 450.
        # delta = (current - p95) / p95 * 100
        # For minor: delta in [10, 50): current = 300 + 33% of 300 = 399 but that's still < threshold.
        # With current=460: delta = (460-300)/300*100 = 53% => major (not minor).
        # Minor means: 10 <= delta_percent < 50. So: 300 + 10% = 330 but 330 < 450 (threshold).
        # The issue: with sensitivity=1.5, threshold=450. delta is vs p95=300.
        # current=460: delta=(460-300)/300*100=53% => major.
        # To get minor (10-50%), use sensitivity=1.0:
        result = manager.is_regression(330.0, baseline, "response_time", sensitivity=1.0)
        # threshold = 300 * 1.0 = 300; current=330 > 300 => is_regression=True
        # delta = (330-300)/300*100 = 10% => minor
        assert result["is_regression"] is True
        assert result["severity"] == "minor"

    def test_regression_major_severity_boundary(self):
        """A major regression (50-100% above p95) should be 'major'."""
        manager = BaselineManager()
        baseline = {
            "p50": 200.0, "p95": 200.0, "p99": 250.0,
            "mean": 200.0, "stddev": 20.0, "min": 100.0, "max": 250.0,
            "sample_count": 100,
        }
        # current = 200 * 1.5 = 300 triggers; delta=(400-200)/200*100=100 => critical
        # For major: delta in [50,100): current = 200*1.5 + 60% of 200 = 430 -> delta=115% (critical)
        # Let's use p95=300, current=600: delta=100% => critical
        # For major: p95=300, current=500: delta=66% => major
        baseline["p95"] = 300.0
        result = manager.is_regression(500.0, baseline, "response_time")
        assert result["is_regression"] is True
        assert result["severity"] == "major"

    def test_safe_pct_delta_zero_reference(self):
        """_safe_pct_delta returns 0 when reference is zero."""
        from tinaa.apm.baselines import _safe_pct_delta
        assert _safe_pct_delta(100.0, 0.0) == 0.0

    def test_percentile_single_value(self):
        """_percentile handles single-element list."""
        from tinaa.apm.baselines import _percentile
        assert _percentile([42.0], 50) == 42.0
        assert _percentile([42.0], 99) == 42.0

    def test_percentile_upper_clamp(self):
        """_percentile clamps to last element when rank exceeds list length."""
        from tinaa.apm.baselines import _percentile
        # p100 on 2 elements: rank = 1.0*(n-1) = 1, upper = 2 >= n=2 -> returns last
        result = _percentile([10.0, 20.0], 100)
        assert result == 20.0

    def test_performance_severity_none_below_minor_threshold(self):
        """_performance_severity returns 'none' for delta < 10%."""
        from tinaa.apm.baselines import _performance_severity
        assert _performance_severity(5.0) == "none"
        assert _performance_severity(0.0) == "none"

    def test_availability_severity_critical(self):
        """_availability_severity is 'critical' for drop >= 5%."""
        from tinaa.apm.baselines import _availability_severity
        # p50=100, current=90: drop=10, drop_pct=10 >= 5 => critical
        assert _availability_severity(90.0, 100.0) == "critical"

    def test_availability_severity_minor(self):
        """_availability_severity is 'minor' for drop < 2%."""
        from tinaa.apm.baselines import _availability_severity
        # p50=100, current=99.5: drop=0.5, drop_pct=0.5 < 2 => minor
        assert _availability_severity(99.5, 100.0) == "minor"


class TestAnomalyEdgeCases:
    """Additional anomaly detection edge cases."""

    def test_point_anomaly_high_direction(self):
        """High outlier direction label is correct."""
        detector = AnomalyDetector(z_score_threshold=2.0)
        history = [10.0 + i * 0.5 for i in range(20)]
        result = detector.detect_point_anomaly(200.0, history)
        assert result["is_anomaly"] is True
        assert result["direction"] == "high"

    def test_trend_anomaly_stable_direction_when_not_anomaly(self):
        """Non-anomalous trend direction is 'stable'."""
        detector = AnomalyDetector()
        historical = [100.0 + i * 1.0 for i in range(30)]
        recent = [105.0, 106.0, 107.0, 108.0]
        result = detector.detect_trend_anomaly(recent, historical)
        assert result["direction"] == "stable"

    def test_availability_drop_at_exact_expected_rate(self):
        """Availability exactly at expected_rate is not anomalous."""
        detector = AnomalyDetector()
        # 99/100 = 0.99 exactly matches expected
        result = detector.detect_availability_drop(99, 100, expected_rate=0.99)
        assert result["is_anomaly"] is False
        assert result["deficit_percent"] == pytest.approx(0.0, abs=1e-9)

    def test_trend_anomaly_insufficient_history_returns_early(self):
        """Too few historical samples returns a safe not-anomaly response."""
        detector = AnomalyDetector(min_history=10)
        result = detector.detect_trend_anomaly([200.0, 300.0], [1.0, 2.0])
        assert result["is_anomaly"] is False
        assert result["direction"] == "stable"

    def test_trend_anomaly_empty_recent_returns_early(self):
        """Empty recent values returns a safe not-anomaly response."""
        detector = AnomalyDetector(min_history=5)
        result = detector.detect_trend_anomaly([], [100.0] * 10)
        assert result["is_anomaly"] is False

    def test_availability_drop_zero_expected_rate(self):
        """expected_rate=0 should not divide by zero."""
        detector = AnomalyDetector()
        result = detector.detect_availability_drop(0, 10, expected_rate=0.0)
        assert result["deficit_percent"] == 0.0

    def test_safe_shift_pct_zero_historical(self):
        """_safe_shift_pct returns 0 when historical_mean is zero."""
        from tinaa.apm.anomaly import _safe_shift_pct
        assert _safe_shift_pct(100.0, 0.0) == 0.0

    def test_trend_direction_anomaly_but_small_shift(self):
        """_trend_direction returns 'stable' even for anomaly with tiny shift."""
        from tinaa.apm.anomaly import _trend_direction, _STABLE_SHIFT_PCT
        # shift < _STABLE_SHIFT_PCT but is_anomaly=True -> stable
        result = _trend_direction(1.0, True)
        assert result == "stable"


class TestEndpointMonitorRequestError:
    """EndpointMonitor handles httpx.RequestError (connection refused, DNS fail)."""

    @pytest.mark.asyncio
    async def test_probe_http_returns_down_on_request_error(self):
        import httpx as httpx_module

        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        with patch("tinaa.apm.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(
                side_effect=httpx_module.ConnectError("connection refused")
            )

            result = await monitor.probe_http("ep-fail", "https://unreachable.example")

        assert result["status"] == "down"
        assert result["error"] is not None
        assert "error" in result["error"].lower() or "connect" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_probe_http_already_monitored_endpoint_skipped(self):
        """start_monitoring skips an endpoint already in _tasks."""
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        fake_task = asyncio.create_task(asyncio.sleep(100))
        monitor._tasks["ep-dup"] = fake_task

        endpoints = [
            {
                "id": "ep-dup",
                "url": "https://example.com",
                "method": "GET",
                "type": "health",
                "interval_seconds": 60,
                "expected_status": 200,
            }
        ]
        await monitor.start_monitoring(endpoints)
        # Task should not have been replaced
        assert monitor._tasks["ep-dup"] is fake_task

        fake_task.cancel()
        try:
            await fake_task
        except asyncio.CancelledError:
            pass
        monitor._tasks.clear()

    @pytest.mark.asyncio
    async def test_get_monitoring_status_reports_running_tasks(self):
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        fake_task = asyncio.create_task(asyncio.sleep(100))
        monitor._tasks["ep-running"] = fake_task

        status = monitor.get_monitoring_status()
        assert status["ep-running"] == "running"

        fake_task.cancel()
        try:
            await fake_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_probe_http_returns_down_on_generic_exception(self):
        """Unexpected non-httpx exceptions are caught and return 'down'."""
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        with patch("tinaa.apm.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.request = AsyncMock(
                side_effect=ValueError("unexpected internal error")
            )

            result = await monitor.probe_http("ep-x", "https://example.com")

        assert result["status"] == "down"
        assert result["error"] is not None


class TestMonitoringLoop:
    """Test _monitoring_loop exception handling and cancellation."""

    @pytest.mark.asyncio
    async def test_monitoring_loop_handles_probe_exception_without_crash(self):
        """_monitoring_loop catches non-cancellation exceptions and continues."""
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        call_count = 0

        async def fake_probe_http(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("transient probe error")
            # Second call succeeds by returning a normal probe result
            return {"status": "up", "response_time_ms": 50.0, "status_code": 200,
                    "ttfb_ms": 50.0, "headers": {}, "error": None}

        endpoint = {
            "id": "ep-loop",
            "url": "https://example.com",
            "method": "GET",
            "type": "health",
            "interval_seconds": 0,
            "expected_status": 200,
        }

        with patch.object(monitor, "probe_http", side_effect=fake_probe_http):
            task = asyncio.create_task(monitor._monitoring_loop(endpoint))
            # Let the loop run at least two iterations
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_monitoring_loop_cancelled_error_propagates(self):
        """CancelledError is re-raised from _monitoring_loop."""
        collector = MetricCollector()
        monitor = EndpointMonitor(collector)

        async def blocking_probe(**kwargs):
            await asyncio.sleep(100)

        endpoint = {
            "id": "ep-cancel",
            "url": "https://example.com",
            "method": "GET",
            "type": "health",
            "interval_seconds": 60,
            "expected_status": 200,
        }

        with patch.object(monitor, "probe_http", side_effect=blocking_probe):
            task = asyncio.create_task(monitor._monitoring_loop(endpoint))
            await asyncio.sleep(0.02)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task


class TestMonitorHelpers:
    """Direct tests for private monitor helper functions."""

    def test_classify_http_status_up(self):
        from tinaa.apm.monitor import _classify_http_status
        assert _classify_http_status(200, 200, 100.0, 30.0, None) == "up"

    def test_classify_http_status_down_on_error(self):
        from tinaa.apm.monitor import _classify_http_status
        assert _classify_http_status(0, 200, 0.0, 30.0, "timeout") == "down"

    def test_classify_http_status_down_on_status_mismatch(self):
        from tinaa.apm.monitor import _classify_http_status
        assert _classify_http_status(404, 200, 100.0, 30.0, None) == "down"

    def test_classify_http_status_degraded(self):
        from tinaa.apm.monitor import _classify_http_status
        # timeout=30s, degraded threshold = 15000ms; response_time=16000 -> degraded
        assert _classify_http_status(200, 200, 16000.0, 30.0, None) == "degraded"

    def test_classify_page_status_up(self):
        from tinaa.apm.monitor import _classify_page_status
        vitals = {"overall_rating": "good"}
        assert _classify_page_status(5000.0, 30.0, vitals) == "up"

    def test_classify_page_status_degraded_slow_load(self):
        from tinaa.apm.monitor import _classify_page_status
        vitals = {"overall_rating": "good"}
        assert _classify_page_status(20000.0, 30.0, vitals) == "degraded"

    def test_classify_page_status_degraded_poor_vitals(self):
        from tinaa.apm.monitor import _classify_page_status
        vitals = {"overall_rating": "poor"}
        assert _classify_page_status(5000.0, 30.0, vitals) == "degraded"

    def test_classify_page_status_up_needs_improvement_vitals(self):
        from tinaa.apm.monitor import _classify_page_status
        vitals = {"overall_rating": "needs-improvement"}
        assert _classify_page_status(5000.0, 30.0, vitals) == "up"


class TestWebVitalsHelpers:
    """Test private web_vitals helper functions for full coverage."""

    def test_worst_rating_empty_list_returns_good(self):
        """No vitals measured -> overall is 'good' by default."""
        from tinaa.apm.web_vitals import _worst_rating
        assert _worst_rating([]) == "good"

    def test_worst_rating_single_poor(self):
        from tinaa.apm.web_vitals import _worst_rating
        assert _worst_rating(["poor"]) == "poor"

    def test_worst_rating_mixed(self):
        from tinaa.apm.web_vitals import _worst_rating
        assert _worst_rating(["good", "needs-improvement", "good"]) == "needs-improvement"

    def test_evaluate_web_vitals_no_vitals(self):
        """All-None vitals produces a result without per-metric keys."""
        vitals = {"lcp_ms": None, "fcp_ms": None, "cls": None, "inp_ms": None, "ttfb_ms": None}
        result = WebVitalsCollector.evaluate_web_vitals(vitals)
        assert result["overall_rating"] == "good"
        assert "lcp" not in result
