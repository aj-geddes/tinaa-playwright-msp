"""
TINAA APM — Application Performance Monitoring layer.

Fuses synthetic monitoring with Web Vitals collection, baseline management,
and statistical anomaly detection.
"""

from tinaa.apm.anomaly import AnomalyDetector
from tinaa.apm.baselines import BaselineManager
from tinaa.apm.collector import MetricCollector, MetricSample, MetricType
from tinaa.apm.monitor import EndpointMonitor
from tinaa.apm.web_vitals import WebVitalsCollector

__all__ = [
    "MetricCollector",
    "MetricSample",
    "MetricType",
    "BaselineManager",
    "AnomalyDetector",
    "WebVitalsCollector",
    "EndpointMonitor",
]
