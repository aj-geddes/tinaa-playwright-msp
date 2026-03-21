"""
Endpoint SQLAlchemy ORM model and Pydantic v2 schemas.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from tinaa.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EndpointType(str, enum.Enum):
    """Classification of an HTTP endpoint."""

    page = "page"
    api = "api"
    health = "health"
    websocket = "websocket"


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------


class Endpoint(UUIDPrimaryKeyMixin, TimestampMixin, Base, MappedAsDataclass, kw_only=True):
    """A monitored URL / path within an Environment."""

    __tablename__ = "endpoints"

    environment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("environments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    endpoint_type: Mapped[Optional[EndpointType]] = mapped_column(
        Enum(EndpointType, name="endpoint_type"),
        nullable=True,
        default=None,
    )
    performance_budget_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None
    )
    lcp_budget_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    cls_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    expected_status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    is_monitored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_check_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    last_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default=None)

    # Relationships (excluded from dataclass init)
    environment: Mapped[Environment] = relationship(  # noqa: F821
        "Environment", back_populates="endpoints", init=False
    )
    metric_datapoints: Mapped[list[MetricDatapoint]] = relationship(  # noqa: F821
        "MetricDatapoint",
        back_populates="endpoint",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )
    metric_baselines: Mapped[list[MetricBaseline]] = relationship(  # noqa: F821
        "MetricBaseline",
        back_populates="endpoint",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )


# ---------------------------------------------------------------------------
# Pydantic v2 Schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class EndpointCreate(BaseModel):
    """Schema for creating a new Endpoint."""

    environment_id: uuid.UUID
    path: str = Field(..., min_length=1, max_length=512)
    method: str = Field(default="GET", max_length=10)
    endpoint_type: Optional[EndpointType] = None
    performance_budget_ms: Optional[int] = None
    lcp_budget_ms: Optional[int] = None
    cls_budget: Optional[float] = None
    expected_status_code: int = 200
    is_monitored: bool = True


class EndpointUpdate(BaseModel):
    """Schema for partially updating an Endpoint."""

    path: Optional[str] = None
    method: Optional[str] = None
    endpoint_type: Optional[EndpointType] = None
    performance_budget_ms: Optional[int] = None
    lcp_budget_ms: Optional[int] = None
    cls_budget: Optional[float] = None
    expected_status_code: Optional[int] = None
    is_monitored: Optional[bool] = None


class EndpointResponse(BaseModel):
    """Schema returned when reading an Endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    environment_id: uuid.UUID
    path: str
    method: str
    endpoint_type: Optional[EndpointType]
    performance_budget_ms: Optional[int]
    lcp_budget_ms: Optional[int]
    cls_budget: Optional[float]
    expected_status_code: int
    is_monitored: bool
    last_check_at: Optional[datetime]
    last_status: Optional[str]
    created_at: datetime
    updated_at: datetime
