"""
AlertRule and AlertEvent SQLAlchemy ORM models and Pydantic v2 schemas.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from tinaa.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AlertConditionType(str, enum.Enum):
    """Type of condition that can trigger an alert."""

    quality_score_drop = "quality_score_drop"
    test_failure = "test_failure"
    performance_regression = "performance_regression"
    endpoint_down = "endpoint_down"
    security_issue = "security_issue"


class AlertSeverity(str, enum.Enum):
    """Severity of a triggered alert event."""

    critical = "critical"
    warning = "warning"
    info = "info"


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class AlertRule(UUIDPrimaryKeyMixin, TimestampMixin, Base, MappedAsDataclass, kw_only=True):
    """A rule that, when matched, generates an AlertEvent."""

    __tablename__ = "alert_rules"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    condition_type: Mapped[AlertConditionType] = mapped_column(
        Enum(AlertConditionType, name="alert_condition_type"),
        nullable=False,
    )
    threshold: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default_factory=dict)
    channels: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default_factory=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Relationships (excluded from dataclass init)
    product: Mapped[Product] = relationship(  # noqa: F821
        "Product", back_populates="alert_rules", init=False
    )
    events: Mapped[list[AlertEvent]] = relationship(
        "AlertEvent",
        back_populates="alert_rule",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )


class AlertEvent(UUIDPrimaryKeyMixin, Base, MappedAsDataclass, kw_only=True):
    """A triggered alert notification."""

    __tablename__ = "alert_events"

    alert_rule_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity"),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default_factory=dict)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        init=False,
        nullable=False,
    )

    # Relationships (excluded from dataclass init)
    alert_rule: Mapped[AlertRule] = relationship("AlertRule", back_populates="events", init=False)


# ---------------------------------------------------------------------------
# Pydantic v2 Schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class AlertRuleCreate(BaseModel):
    """Schema for creating a new AlertRule."""

    product_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    condition_type: AlertConditionType
    threshold: dict[str, Any] = Field(default_factory=dict)
    channels: list[Any] = Field(default_factory=list)
    is_active: bool = True


class AlertRuleUpdate(BaseModel):
    """Schema for partially updating an AlertRule."""

    name: Optional[str] = None
    condition_type: Optional[AlertConditionType] = None
    threshold: Optional[dict[str, Any]] = None
    channels: Optional[list[Any]] = None
    is_active: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    """Schema returned when reading an AlertRule."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    name: str
    condition_type: AlertConditionType
    threshold: dict[str, Any]
    channels: list[Any]
    is_active: bool
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AlertEventCreate(BaseModel):
    """Schema for recording a new AlertEvent."""

    alert_rule_id: uuid.UUID
    severity: AlertSeverity
    message: str = Field(..., min_length=1, max_length=1024)
    details: dict[str, Any] = Field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None


class AlertEventResponse(BaseModel):
    """Schema returned when reading an AlertEvent."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_rule_id: uuid.UUID
    severity: AlertSeverity
    message: str
    details: dict[str, Any]
    acknowledged: bool
    acknowledged_by: Optional[str]
    resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime
