"""
Metric collection module for TINAA APM.

Provides MetricSample dataclass, MetricType enum, and MetricCollector
which buffers samples and flushes them in batches to a configurable
storage callback.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Supported APM metric types."""

    RESPONSE_TIME = "response_time"
    TTFB = "ttfb"
    FCP = "fcp"
    LCP = "lcp"
    CLS = "cls"
    INP = "inp"
    AVAILABILITY = "availability"
    ERROR_RATE = "error_rate"
    STATUS_CODE = "status_code"
    DNS_TIME = "dns_time"
    TLS_TIME = "tls_time"
    DOWNLOAD_SIZE = "download_size"


@dataclass
class MetricSample:
    """A single metric observation tied to an endpoint."""

    endpoint_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    metadata: dict | None = None


# Type alias for the async storage callback
StorageCallback = Callable[[list[MetricSample]], Awaitable[None]]

# Threshold: if elapsed time exceeds this fraction of timeout, mark degraded
_DEGRADED_FRACTION = 0.5


class MetricCollector:
    """Collects and buffers metric samples for batch storage.

    Thread-safe via asyncio.Lock. Automatically flushes when the buffer
    reaches ``batch_size``.

    Args:
        flush_interval: Seconds between scheduled flushes (informational;
            callers drive explicit flushes or auto-flush on batch_size).
        batch_size: Auto-flush after this many buffered samples.
    """

    def __init__(self, flush_interval: int = 30, batch_size: int = 100) -> None:
        self._buffer: list[MetricSample] = []
        self._flush_interval = flush_interval
        self._batch_size = batch_size
        self._storage_callback: StorageCallback | None = None
        self._lock = asyncio.Lock()

    def set_storage_callback(self, callback: StorageCallback) -> None:
        """Register the async callback that receives flushed batches."""
        self._storage_callback = callback

    async def record(self, sample: MetricSample) -> None:
        """Buffer a single metric sample, auto-flushing if batch_size reached."""
        async with self._lock:
            self._buffer.append(sample)
            should_flush = len(self._buffer) >= self._batch_size

        if should_flush:
            await self.flush()

    async def record_batch(self, samples: list[MetricSample]) -> None:
        """Buffer multiple samples, auto-flushing if batch_size reached."""
        async with self._lock:
            self._buffer.extend(samples)
            should_flush = len(self._buffer) >= self._batch_size

        if should_flush:
            await self.flush()

    async def flush(self) -> None:
        """Drain the buffer and deliver samples to the storage callback."""
        async with self._lock:
            if not self._buffer:
                return
            batch = self._buffer[:]
            self._buffer.clear()

        if self._storage_callback is not None:
            try:
                await self._storage_callback(batch)
            except Exception:
                logger.exception("Storage callback failed during flush")

    def get_buffer_size(self) -> int:
        """Return the number of samples currently buffered."""
        return len(self._buffer)
