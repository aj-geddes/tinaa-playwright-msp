"""
TestRun, TestResult, and Deployment SQLAlchemy ORM models and Pydantic v2 schemas.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from tinaa.models.base import Base, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestRunTrigger(str, enum.Enum):
    """Event that initiated a test run."""

    deployment = "deployment"
    schedule = "schedule"
    manual = "manual"
    pr = "pr"
    anomaly = "anomaly"


class TestRunStatus(str, enum.Enum):
    """Current state of a test run."""

    queued = "queued"
    running = "running"
    passed = "passed"
    failed = "failed"
    error = "error"
    cancelled = "cancelled"


class TestResultStatus(str, enum.Enum):
    """Outcome of a single test step."""

    passed = "passed"
    failed = "failed"
    skipped = "skipped"
    error = "error"


class DeploymentStatus(str, enum.Enum):
    """Current state of a deployment."""

    pending = "pending"
    in_progress = "in_progress"
    success = "success"
    failure = "failure"
    error = "error"


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class TestRun(UUIDPrimaryKeyMixin, Base, MappedAsDataclass, kw_only=True):
    """
    A single execution of a Playbook (or ad-hoc run) against an Environment.

    Note: TestRun deliberately omits TimestampMixin because it has a
    single created_at (no updated_at) and no auto-update semantics.
    """

    __tablename__ = "test_runs"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("environments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger: Mapped[TestRunTrigger] = mapped_column(
        Enum(TestRunTrigger, name="test_run_trigger"),
        nullable=False,
    )
    status: Mapped[TestRunStatus] = mapped_column(
        Enum(TestRunStatus, name="test_run_status"),
        nullable=False,
        default=TestRunStatus.queued,
    )
    playbook_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("playbooks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        default=None,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, default=None)
    deployment_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, default=None)
    pr_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    results_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default_factory=dict
    )
    quality_score_before: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=None
    )
    quality_score_after: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    artifacts_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, default=None)
    error_message: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        init=False,
        nullable=False,
    )

    # Relationships (excluded from dataclass init)
    playbook: Mapped[Optional[Playbook]] = relationship(  # noqa: F821
        "Playbook", back_populates="test_runs", init=False, default=None
    )
    product: Mapped[Product] = relationship(  # noqa: F821
        "Product", back_populates="test_runs", init=False
    )
    environment: Mapped[Environment] = relationship(  # noqa: F821
        "Environment", back_populates="test_runs", init=False
    )
    results: Mapped[list[TestResult]] = relationship(
        "TestResult",
        back_populates="test_run",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )


class TestResult(UUIDPrimaryKeyMixin, Base, MappedAsDataclass, kw_only=True):
    """Result of a single step within a TestRun."""

    __tablename__ = "test_results"

    test_run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TestResultStatus] = mapped_column(
        Enum(TestResultStatus, name="test_result_status"),
        nullable=False,
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True, default=None)
    screenshot_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, default=None)
    console_logs: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default_factory=list)
    network_requests: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default_factory=list)
    performance_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default_factory=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        init=False,
        nullable=False,
    )

    # Relationships (excluded from dataclass init)
    test_run: Mapped[TestRun] = relationship("TestRun", back_populates="results", init=False)


class Deployment(UUIDPrimaryKeyMixin, Base, MappedAsDataclass, kw_only=True):
    """A deployment event that may trigger test runs."""

    __tablename__ = "deployments"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("environments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    ref: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus, name="deployment_status"),
        nullable=False,
        default=DeploymentStatus.pending,
    )
    deployment_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, default=None)
    github_deployment_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None
    )
    deployer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    triggered_test_runs: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default_factory=list
    )
    quality_score_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        init=False,
        nullable=False,
    )

    # Relationships (excluded from dataclass init)
    product: Mapped[Product] = relationship(  # noqa: F821
        "Product", back_populates="deployments", init=False
    )
    environment: Mapped[Environment] = relationship(  # noqa: F821
        "Environment", back_populates="deployments", init=False
    )


# ---------------------------------------------------------------------------
# Pydantic v2 Schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class TestRunCreate(BaseModel):
    """Schema for creating a new TestRun."""

    playbook_id: Optional[uuid.UUID] = None
    product_id: uuid.UUID
    environment_id: uuid.UUID
    trigger: TestRunTrigger
    status: TestRunStatus = TestRunStatus.queued
    commit_sha: Optional[str] = None
    deployment_url: Optional[str] = None
    pr_number: Optional[int] = None


class TestRunUpdate(BaseModel):
    """Schema for updating a TestRun."""

    status: Optional[TestRunStatus] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    results_summary: Optional[dict[str, Any]] = None
    quality_score_before: Optional[float] = None
    quality_score_after: Optional[float] = None
    artifacts_url: Optional[str] = None
    error_message: Optional[str] = None


class TestRunResponse(BaseModel):
    """Schema returned when reading a TestRun."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    playbook_id: Optional[uuid.UUID]
    product_id: uuid.UUID
    environment_id: uuid.UUID
    trigger: TestRunTrigger
    status: TestRunStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    commit_sha: Optional[str]
    deployment_url: Optional[str]
    pr_number: Optional[int]
    results_summary: dict[str, Any]
    quality_score_before: Optional[float]
    quality_score_after: Optional[float]
    artifacts_url: Optional[str]
    error_message: Optional[str]
    created_at: datetime


class TestResultCreate(BaseModel):
    """Schema for creating a new TestResult."""

    test_run_id: uuid.UUID
    step_index: int = Field(..., ge=0)
    step_name: str = Field(..., min_length=1, max_length=255)
    status: TestResultStatus
    duration_ms: int = Field(..., ge=0)
    error_message: Optional[str] = None
    screenshot_url: Optional[str] = None
    console_logs: list[Any] = Field(default_factory=list)
    network_requests: list[Any] = Field(default_factory=list)
    performance_data: dict[str, Any] = Field(default_factory=dict)


class TestResultResponse(BaseModel):
    """Schema returned when reading a TestResult."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    test_run_id: uuid.UUID
    step_index: int
    step_name: str
    status: TestResultStatus
    duration_ms: int
    error_message: Optional[str]
    screenshot_url: Optional[str]
    console_logs: list[Any]
    network_requests: list[Any]
    performance_data: dict[str, Any]
    created_at: datetime


class DeploymentCreate(BaseModel):
    """Schema for creating a new Deployment."""

    product_id: uuid.UUID
    environment_id: uuid.UUID
    commit_sha: str = Field(..., min_length=1, max_length=64)
    ref: str = Field(..., min_length=1, max_length=255)
    deployment_url: Optional[str] = None
    github_deployment_id: Optional[int] = None
    status: DeploymentStatus = DeploymentStatus.pending
    deployer: Optional[str] = None
    triggered_test_runs: list[Any] = Field(default_factory=list)


class DeploymentUpdate(BaseModel):
    """Schema for updating a Deployment."""

    deployment_url: Optional[str] = None
    status: Optional[DeploymentStatus] = None
    deployer: Optional[str] = None
    triggered_test_runs: Optional[list[Any]] = None
    quality_score_delta: Optional[float] = None


class DeploymentResponse(BaseModel):
    """Schema returned when reading a Deployment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    environment_id: uuid.UUID
    commit_sha: str
    ref: str
    deployment_url: Optional[str]
    github_deployment_id: Optional[int]
    status: DeploymentStatus
    deployer: Optional[str]
    triggered_test_runs: list[Any]
    quality_score_delta: Optional[float]
    created_at: datetime
