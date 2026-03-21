"""
TINAA MSP data models package.

Re-exports all SQLAlchemy ORM models and Pydantic schemas for convenience.
"""

from tinaa.models.alert import (
    AlertConditionType,
    AlertEvent,
    AlertRule,
    AlertSeverity,
)
from tinaa.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from tinaa.models.endpoint import Endpoint, EndpointType
from tinaa.models.environment import Environment, EnvironmentType
from tinaa.models.metrics import MetricBaseline, MetricDatapoint, MetricType
from tinaa.models.organization import Organization
from tinaa.models.playbook import Playbook, PlaybookPriority, PlaybookSource
from tinaa.models.product import Product, ProductStatus
from tinaa.models.quality import QualityScoreSnapshot
from tinaa.models.test_run import (
    Deployment,
    DeploymentStatus,
    TestResult,
    TestResultStatus,
    TestRun,
    TestRunStatus,
    TestRunTrigger,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "Organization",
    "Product",
    "ProductStatus",
    "Environment",
    "EnvironmentType",
    "Endpoint",
    "EndpointType",
    "Playbook",
    "PlaybookPriority",
    "PlaybookSource",
    "TestRun",
    "TestResult",
    "Deployment",
    "TestRunTrigger",
    "TestRunStatus",
    "TestResultStatus",
    "DeploymentStatus",
    "MetricDatapoint",
    "MetricBaseline",
    "MetricType",
    "QualityScoreSnapshot",
    "AlertRule",
    "AlertEvent",
    "AlertConditionType",
    "AlertSeverity",
]
