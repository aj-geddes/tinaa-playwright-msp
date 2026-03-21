"""
Synthetic monitoring engine for TINAA APM.

Provides EndpointMonitor which probes HTTP API endpoints and web pages,
collects metrics into a MetricCollector, and manages background monitoring
loops.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime

import httpx

from tinaa.apm.collector import MetricCollector, MetricSample, MetricType

logger = logging.getLogger(__name__)

# A response slower than this fraction of timeout is marked "degraded"
_DEGRADED_FRACTION = 0.5

# HTTP status codes that are always considered errors regardless of expected_status
_SERVER_ERROR_MIN = 500
_SERVER_ERROR_MAX = 599


class EndpointMonitor:
    """Monitors endpoints for health, performance, and availability.

    Args:
        collector: MetricCollector instance to receive recorded samples.
    """

    def __init__(self, collector: MetricCollector) -> None:
        self._collector = collector
        self._running = False
        self._tasks: dict[str, asyncio.Task] = {}

    async def probe_http(
        self,
        endpoint_id: str,
        url: str,
        method: str = "GET",
        expected_status: int = 200,
        timeout: float = 30.0,
    ) -> dict:
        """Probe an HTTP endpoint and collect metrics.

        Collects response_time, status_code, ttfb, and download_size.

        Returns:
            dict with keys: status, response_time_ms, status_code, ttfb_ms,
            headers, error
        """
        now = datetime.now(tz=UTC)
        raw = await _execute_http_request(method, url, timeout)

        probe_status = _classify_http_status(
            status_code=raw["status_code"],
            expected_status=expected_status,
            response_time_ms=raw["response_time_ms"],
            timeout=timeout,
            error=raw["error"],
        )
        samples = _build_http_samples(
            endpoint_id=endpoint_id,
            timestamp=now,
            response_time_ms=raw["response_time_ms"],
            status_code=raw["status_code"],
            ttfb_ms=raw["ttfb_ms"],
            download_size=raw["download_size"],
            probe_status=probe_status,
        )
        await self._collector.record_batch(samples)

        return {
            "status": probe_status,
            "response_time_ms": raw["response_time_ms"],
            "status_code": raw["status_code"],
            "ttfb_ms": raw["ttfb_ms"],
            "headers": raw["headers"],
            "error": raw["error"],
        }

    async def probe_page(
        self,
        endpoint_id: str,
        url: str,
        timeout: float = 30.0,
    ) -> dict:
        """Probe a web page using Playwright and collect Web Vitals.

        Playwright is imported only when this method is called to avoid
        requiring the dependency for API-only probes.

        Returns:
            dict with keys: status, load_time_ms, web_vitals, console_errors,
            network_failures, resource_errors
        """
        from playwright.async_api import async_playwright  # noqa: PLC0415

        from tinaa.apm.web_vitals import WebVitalsCollector  # noqa: PLC0415

        now = datetime.now(tz=UTC)
        console_errors: list[str] = []
        network_failures: list[dict] = []
        resource_errors: list[str] = []
        load_time_ms: float = 0.0
        web_vitals_raw: dict = {}

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(args=["--no-sandbox"])
                page = await browser.new_page()

                # Collect console errors
                page.on(
                    "console",
                    lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
                )

                # Collect network failures
                page.on(
                    "requestfailed",
                    lambda req: network_failures.append(
                        {"url": req.url, "failure": req.failure or "unknown"}
                    ),
                )

                # Collect resource errors
                page.on(
                    "pageerror",
                    lambda exc: resource_errors.append(str(exc)),
                )

                import time  # noqa: PLC0415

                start = time.monotonic()
                await page.goto(url, timeout=timeout * 1000, wait_until="load")
                load_time_ms = (time.monotonic() - start) * 1000.0

                web_vitals_raw = await WebVitalsCollector.collect_from_page(page)
                await browser.close()

        except Exception as exc:
            logger.warning("probe_page failed for %s: %s", url, exc)
            probe_status = "down"
            vitals_evaluated = WebVitalsCollector.evaluate_web_vitals(
                {"lcp_ms": None, "fcp_ms": None, "cls": 0.0, "inp_ms": None, "ttfb_ms": None}
            )
            return {
                "status": probe_status,
                "load_time_ms": 0.0,
                "web_vitals": vitals_evaluated,
                "console_errors": console_errors,
                "network_failures": network_failures,
                "resource_errors": resource_errors,
            }

        vitals_evaluated = WebVitalsCollector.evaluate_web_vitals(web_vitals_raw)
        probe_status = _classify_page_status(
            load_time_ms=load_time_ms,
            timeout=timeout,
            web_vitals=vitals_evaluated,
        )

        # Record metrics
        samples: list[MetricSample] = [
            MetricSample(
                endpoint_id=endpoint_id,
                metric_type=MetricType.RESPONSE_TIME,
                value=load_time_ms,
                timestamp=now,
            )
        ]
        for metric_key, metric_type in (
            ("lcp_ms", MetricType.LCP),
            ("fcp_ms", MetricType.FCP),
            ("cls", MetricType.CLS),
            ("inp_ms", MetricType.INP),
        ):
            val = web_vitals_raw.get(metric_key)
            if val is not None:
                samples.append(
                    MetricSample(
                        endpoint_id=endpoint_id,
                        metric_type=metric_type,
                        value=val,
                        timestamp=now,
                    )
                )
        await self._collector.record_batch(samples)

        return {
            "status": probe_status,
            "load_time_ms": load_time_ms,
            "web_vitals": vitals_evaluated,
            "console_errors": console_errors,
            "network_failures": network_failures,
            "resource_errors": resource_errors,
        }

    async def start_monitoring(self, endpoints: list[dict]) -> None:
        """Launch background monitoring loops for each endpoint.

        Args:
            endpoints: List of endpoint configuration dicts with keys:
                id, url, method, type ("page"|"api"|"health"),
                interval_seconds, expected_status.
        """
        self._running = True
        for endpoint in endpoints:
            endpoint_id = endpoint["id"]
            if endpoint_id in self._tasks:
                logger.debug("Endpoint %s already monitored, skipping.", endpoint_id)
                continue
            task = asyncio.create_task(
                self._monitoring_loop(endpoint),
                name=f"monitor-{endpoint_id}",
            )
            self._tasks[endpoint_id] = task
            logger.info("Started monitoring endpoint %s (%s)", endpoint_id, endpoint["url"])

    async def stop_monitoring(self, endpoint_id: str | None = None) -> None:
        """Cancel a specific endpoint's monitoring task, or all tasks.

        Args:
            endpoint_id: UUID of endpoint to stop. Stops all when None.
        """
        if endpoint_id is not None:
            task = self._tasks.pop(endpoint_id, None)
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        else:
            for _eid, task in list(self._tasks.items()):
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            self._tasks.clear()
            self._running = False

    async def _monitoring_loop(self, endpoint: dict) -> None:
        """Run probe -> sleep -> probe cycle for a single endpoint."""
        endpoint_type = endpoint.get("type", "health")
        interval = endpoint.get("interval_seconds", 60)
        endpoint_id = endpoint["id"]
        url = endpoint["url"]

        while True:
            try:
                if endpoint_type == "page":
                    await self.probe_page(endpoint_id=endpoint_id, url=url)
                else:
                    await self.probe_http(
                        endpoint_id=endpoint_id,
                        url=url,
                        method=endpoint.get("method", "GET"),
                        expected_status=endpoint.get("expected_status", 200),
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Probe failed for endpoint %s", endpoint_id)

            await asyncio.sleep(interval)

    def get_monitoring_status(self) -> dict:
        """Return a snapshot of all active monitoring tasks.

        Returns:
            dict mapping endpoint_id to task status string.
        """
        return {
            eid: ("running" if not task.done() else "stopped") for eid, task in self._tasks.items()
        }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _execute_http_request(method: str, url: str, timeout: float) -> dict:
    """Execute an HTTP request and return raw timing/response data.

    Returns a dict with keys: status_code, response_time_ms, ttfb_ms,
    headers, download_size, error.
    """
    error: str | None = None
    status_code: int = 0
    response_time_ms: float = 0.0
    ttfb_ms: float = 0.0
    headers: dict = {}
    download_size: int = 0

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url)

        status_code = response.status_code
        elapsed_s = response.elapsed.total_seconds()
        response_time_ms = elapsed_s * 1000.0
        # httpx does not expose per-phase timing; approximate TTFB as elapsed
        ttfb_ms = response_time_ms
        headers = dict(response.headers)
        download_size = len(response.content)

    except httpx.TimeoutException as exc:
        error = f"Timeout: {exc}"
    except httpx.RequestError as exc:
        error = f"Request error: {exc}"
    except Exception as exc:
        error = f"Unexpected error: {exc}"

    return {
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "ttfb_ms": ttfb_ms,
        "headers": headers,
        "download_size": download_size,
        "error": error,
    }


def _classify_http_status(
    status_code: int,
    expected_status: int,
    response_time_ms: float,
    timeout: float,
    error: str | None,
) -> str:
    if error is not None or status_code == 0:
        return "down"
    if status_code != expected_status:
        return "down"
    degraded_threshold_ms = timeout * _DEGRADED_FRACTION * 1000.0
    if response_time_ms >= degraded_threshold_ms:
        return "degraded"
    return "up"


def _classify_page_status(
    load_time_ms: float,
    timeout: float,
    web_vitals: dict,
) -> str:
    degraded_threshold_ms = timeout * _DEGRADED_FRACTION * 1000.0
    if load_time_ms >= degraded_threshold_ms:
        return "degraded"
    overall = web_vitals.get("overall_rating", "good")
    if overall == "poor":
        return "degraded"
    return "up"


def _build_http_samples(
    endpoint_id: str,
    timestamp: datetime,
    response_time_ms: float,
    status_code: int,
    ttfb_ms: float,
    download_size: int,
    probe_status: str,
) -> list[MetricSample]:
    samples = [
        MetricSample(
            endpoint_id=endpoint_id,
            metric_type=MetricType.RESPONSE_TIME,
            value=response_time_ms,
            timestamp=timestamp,
        ),
        MetricSample(
            endpoint_id=endpoint_id,
            metric_type=MetricType.STATUS_CODE,
            value=float(status_code),
            timestamp=timestamp,
        ),
    ]
    if ttfb_ms > 0:
        samples.append(
            MetricSample(
                endpoint_id=endpoint_id,
                metric_type=MetricType.TTFB,
                value=ttfb_ms,
                timestamp=timestamp,
            )
        )
    if download_size > 0:
        samples.append(
            MetricSample(
                endpoint_id=endpoint_id,
                metric_type=MetricType.DOWNLOAD_SIZE,
                value=float(download_size),
                timestamp=timestamp,
            )
        )
    availability = 1.0 if probe_status == "up" else 0.0
    samples.append(
        MetricSample(
            endpoint_id=endpoint_id,
            metric_type=MetricType.AVAILABILITY,
            value=availability,
            timestamp=timestamp,
        )
    )
    return samples
