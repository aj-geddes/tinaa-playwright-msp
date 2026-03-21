"""
Environment SQLAlchemy ORM model and Pydantic v2 schemas.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from tinaa.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EnvironmentType(str, enum.Enum):
    """Classification of an environment."""

    production = "production"
    staging = "staging"
    development = "development"
    preview = "preview"


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------


class Environment(UUIDPrimaryKeyMixin, TimestampMixin, Base, MappedAsDataclass, kw_only=True):
    """A deployment environment for a Product (production, staging, etc.)."""

    __tablename__ = "environments"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    env_type: Mapped[EnvironmentType] = mapped_column(
        Enum(EnvironmentType, name="environment_type"),
        nullable=False,
    )
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    monitoring_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

    # Relationships (excluded from dataclass init)
    product: Mapped[Product] = relationship(  # noqa: F821
        "Product", back_populates="environments", init=False
    )
    endpoints: Mapped[list[Endpoint]] = relationship(  # noqa: F821
        "Endpoint",
        back_populates="environment",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )
    test_runs: Mapped[list[TestRun]] = relationship(  # noqa: F821
        "TestRun", back_populates="environment", default_factory=list, init=False
    )
    quality_snapshots: Mapped[list[QualityScoreSnapshot]] = relationship(  # noqa: F821
        "QualityScoreSnapshot",
        back_populates="environment",
        default_factory=list,
        init=False,
    )
    deployments: Mapped[list[Deployment]] = relationship(  # noqa: F821
        "Deployment",
        back_populates="environment",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )


# ---------------------------------------------------------------------------
# Pydantic v2 Schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class EnvironmentCreate(BaseModel):
    """Schema for creating a new Environment.

    ``product_id`` is intentionally absent — the service layer injects it from
    the URL/path parameter so callers never need to supply it explicitly.
    """

    name: str = Field(..., min_length=1, max_length=100)
    env_type: EnvironmentType = EnvironmentType.staging
    base_url: str = Field(..., min_length=1, max_length=512)
    is_active: bool = True
    monitoring_interval_seconds: int = Field(default=300, ge=1)


class EnvironmentUpdate(BaseModel):
    """Schema for partially updating an Environment."""

    name: Optional[str] = None
    env_type: Optional[EnvironmentType] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None
    monitoring_interval_seconds: Optional[int] = None


class EnvironmentResponse(BaseModel):
    """Schema returned when reading an Environment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    name: str
    env_type: EnvironmentType
    base_url: str
    is_active: bool
    monitoring_interval_seconds: int
    created_at: datetime
    updated_at: datetime
