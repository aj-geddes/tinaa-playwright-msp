"""TINAA Quality Score Engine.

Provides composite quality scoring, deployment gates, and trend analysis
for the Testing + APM managed service platform.
"""

from tinaa.quality.gates import QualityGate, QualityGateConfig
from tinaa.quality.scorer import (
    AccessibilityInput,
    PerformanceHealthInput,
    QualityScorer,
    QualityWeights,
    SecurityPostureInput,
    TestHealthInput,
)
from tinaa.quality.trends import QualityTrendAnalyzer

__all__ = [
    "AccessibilityInput",
    "PerformanceHealthInput",
    "QualityGate",
    "QualityGateConfig",
    "QualityScorer",
    "QualityTrendAnalyzer",
    "QualityWeights",
    "SecurityPostureInput",
    "TestHealthInput",
]
