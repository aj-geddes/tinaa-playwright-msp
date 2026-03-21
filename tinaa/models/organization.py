"""
Organization SQLAlchemy ORM model and Pydantic v2 schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from tinaa.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base, MappedAsDataclass, kw_only=True):
    """Top-level tenant / customer entity."""

    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("slug", name="uq_organizations_slug"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    github_installation_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None
    )

    # Relationships (excluded from dataclass init)
    products: Mapped[list[Product]] = relationship(  # noqa: F821
        "Product",
        back_populates="organization",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )


# ---------------------------------------------------------------------------
# Pydantic v2 Schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class OrganizationCreate(BaseModel):
    """Schema for creating a new Organization."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    github_installation_id: Optional[int] = None


class OrganizationUpdate(BaseModel):
    """Schema for partially updating an Organization."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    github_installation_id: Optional[int] = None


class OrganizationResponse(BaseModel):
    """Schema returned when reading an Organization."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    github_installation_id: Optional[int]
    created_at: datetime
    updated_at: datetime
