"""
MetricDatapoint and MetricBaseline SQLAlchemy ORM models and Pydantic v2 schemas.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from tinaa.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MetricType(str, enum.Enum):
    """Category of performance / availability metric."""

    response_time = "response_time"
    ttfb = "ttfb"
    fcp = "fcp"
    lcp = "lcp"
    cls = "cls"
    inp = "inp"
    availability = "availability"
    error_rate = "error_rate"
    status_code = "status_code"


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class MetricDatapoint(UUIDPrimaryKeyMixin, Base, MappedAsDataclass, kw_only=True):
    """A single raw metric observation at a point in time."""

    __tablename__ = "metric_datapoints"

    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    metric_type: Mapped[MetricType] = mapped_column(
        Enum(MetricType, name="metric_type"),
        nullable=False,
        index=True,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default_factory=dict
    )

    # Relationships (excluded from dataclass init)
    endpoint: Mapped[Endpoint] = relationship(  # noqa: F821
        "Endpoint", back_populates="metric_datapoints", init=False
    )


class MetricBaseline(UUIDPrimaryKeyMixin, TimestampMixin, Base, MappedAsDataclass, kw_only=True):
    """Statistical baseline (p50/p95/p99) for a metric over a time window."""

    __tablename__ = "metric_baselines"

    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_type: Mapped[MetricType] = mapped_column(
        Enum(MetricType, name="metric_type_baseline"),
        nullable=False,
    )
    p50: Mapped[float] = mapped_column(Float, nullable=False)
    p95: Mapped[float] = mapped_column(Float, nullable=False)
    p99: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships (excluded from dataclass init)
    endpoint: Mapped[Endpoint] = relationship(  # noqa: F821
        "Endpoint", back_populates="metric_baselines", init=False
    )


# ---------------------------------------------------------------------------
# Pydantic v2 Schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class MetricDatapointCreate(BaseModel):
    """Schema for ingesting a new MetricDatapoint."""

    endpoint_id: uuid.UUID
    timestamp: datetime
    metric_type: MetricType
    value: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricDatapointResponse(BaseModel):
    """Schema returned when reading a MetricDatapoint."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    endpoint_id: uuid.UUID
    timestamp: datetime
    metric_type: MetricType
    value: float


class MetricBaselineCreate(BaseModel):
    """Schema for creating a MetricBaseline."""

    endpoint_id: uuid.UUID
    metric_type: MetricType
    p50: float
    p95: float
    p99: float
    sample_count: int = Field(..., ge=1)
    window_start: datetime
    window_end: datetime
    is_current: bool = True


class MetricBaselineResponse(BaseModel):
    """Schema returned when reading a MetricBaseline."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    endpoint_id: uuid.UUID
    metric_type: MetricType
    p50: float
    p95: float
    p99: float
    sample_count: int
    window_start: datetime
    window_end: datetime
    is_current: bool
    created_at: datetime
    updated_at: datetime
