"""
Product SQLAlchemy ORM model and Pydantic v2 schemas.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from tinaa.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProductStatus(str, enum.Enum):
    """Lifecycle state of a product."""

    active = "active"
    paused = "paused"
    archived = "archived"


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base, MappedAsDataclass, kw_only=True):
    """A software product tracked by TINAA."""

    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("organization_id", "slug", name="uq_products_org_slug"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True, default=None)
    repository_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, default=None)
    repository_owner: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, default=None
    )
    repository_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    default_branch: Mapped[str] = mapped_column(String(100), nullable=False, default="main")
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    quality_score_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"),
        nullable=False,
        default=ProductStatus.active,
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default_factory=dict)

    # Relationships (excluded from dataclass init)
    organization: Mapped[Organization] = relationship(  # noqa: F821
        "Organization", back_populates="products", init=False
    )
    environments: Mapped[list[Environment]] = relationship(  # noqa: F821
        "Environment",
        back_populates="product",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )
    playbooks: Mapped[list[Playbook]] = relationship(  # noqa: F821
        "Playbook",
        back_populates="product",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )
    test_runs: Mapped[list[TestRun]] = relationship(  # noqa: F821
        "TestRun",
        back_populates="product",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )
    quality_snapshots: Mapped[list[QualityScoreSnapshot]] = relationship(  # noqa: F821
        "QualityScoreSnapshot",
        back_populates="product",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )
    alert_rules: Mapped[list[AlertRule]] = relationship(  # noqa: F821
        "AlertRule",
        back_populates="product",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )
    deployments: Mapped[list[Deployment]] = relationship(  # noqa: F821
        "Deployment",
        back_populates="product",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )


# ---------------------------------------------------------------------------
# Pydantic v2 Schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class ProductCreate(BaseModel):
    """Schema for creating a new Product."""

    organization_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    repository_url: Optional[str] = None
    repository_owner: Optional[str] = None
    repository_name: Optional[str] = None
    default_branch: str = "main"
    quality_score: Optional[float] = None
    quality_score_updated_at: Optional[datetime] = None
    status: ProductStatus = ProductStatus.active
    config: dict[str, Any] = Field(default_factory=dict)


class ProductUpdate(BaseModel):
    """Schema for partially updating a Product."""

    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    repository_url: Optional[str] = None
    repository_owner: Optional[str] = None
    repository_name: Optional[str] = None
    default_branch: Optional[str] = None
    quality_score: Optional[float] = None
    quality_score_updated_at: Optional[datetime] = None
    status: Optional[ProductStatus] = None
    config: Optional[dict[str, Any]] = None


class ProductResponse(BaseModel):
    """Schema returned when reading a Product."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    description: Optional[str]
    repository_url: Optional[str]
    repository_owner: Optional[str]
    repository_name: Optional[str]
    default_branch: str
    quality_score: Optional[float]
    quality_score_updated_at: Optional[datetime]
    status: ProductStatus
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
