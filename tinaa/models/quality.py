"""
QualityScoreSnapshot SQLAlchemy ORM model and Pydantic v2 schemas.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from tinaa.models.base import Base, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------


class QualityScoreSnapshot(UUIDPrimaryKeyMixin, Base, MappedAsDataclass, kw_only=True):
    """
    Point-in-time quality score for a product, optionally scoped to an
    environment.
    """

    __tablename__ = "quality_score_snapshots"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    test_health_score: Mapped[float] = mapped_column(Float, nullable=False)
    performance_health_score: Mapped[float] = mapped_column(Float, nullable=False)
    security_posture_score: Mapped[float] = mapped_column(Float, nullable=False)
    accessibility_score: Mapped[float] = mapped_column(Float, nullable=False)
    environment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("environments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        default=None,
    )
    test_pass_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    coverage_breadth: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    availability: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    avg_response_time_ms: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=None
    )
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default_factory=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        init=False,
        nullable=False,
    )

    # Relationships (excluded from dataclass init)
    product: Mapped[Product] = relationship(  # noqa: F821
        "Product", back_populates="quality_snapshots", init=False
    )
    environment: Mapped[Optional[Environment]] = relationship(  # noqa: F821
        "Environment", back_populates="quality_snapshots", init=False, default=None
    )


# ---------------------------------------------------------------------------
# Pydantic v2 Schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class QualityScoreSnapshotCreate(BaseModel):
    """Schema for recording a new QualityScoreSnapshot."""

    product_id: uuid.UUID
    environment_id: Optional[uuid.UUID] = None
    score: float = Field(..., ge=0.0, le=100.0)
    test_health_score: float = Field(..., ge=0.0, le=100.0)
    performance_health_score: float = Field(..., ge=0.0, le=100.0)
    security_posture_score: float = Field(..., ge=0.0, le=100.0)
    accessibility_score: float = Field(..., ge=0.0, le=100.0)
    test_pass_rate: Optional[float] = None
    coverage_breadth: Optional[float] = None
    availability: Optional[float] = None
    avg_response_time_ms: Optional[float] = None
    details: dict[str, Any] = Field(default_factory=dict)


class QualityScoreSnapshotResponse(BaseModel):
    """Schema returned when reading a QualityScoreSnapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    environment_id: Optional[uuid.UUID]
    score: float
    test_health_score: float
    performance_health_score: float
    security_posture_score: float
    accessibility_score: float
    test_pass_rate: Optional[float]
    coverage_breadth: Optional[float]
    availability: Optional[float]
    avg_response_time_ms: Optional[float]
    details: dict[str, Any]
    created_at: datetime
