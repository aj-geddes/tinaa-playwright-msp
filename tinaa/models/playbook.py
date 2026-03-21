"""
Playbook SQLAlchemy ORM model and Pydantic v2 schemas.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from tinaa.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PlaybookPriority(str, enum.Enum):
    """Priority / severity of a playbook."""

    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class PlaybookSource(str, enum.Enum):
    """How the playbook was created."""

    auto_generated = "auto_generated"
    manual = "manual"
    hybrid = "hybrid"


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------


class Playbook(UUIDPrimaryKeyMixin, TimestampMixin, Base, MappedAsDataclass, kw_only=True):
    """A sequence of test steps associated with a Product."""

    __tablename__ = "playbooks"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True, default=None)
    priority: Mapped[PlaybookPriority] = mapped_column(
        Enum(PlaybookPriority, name="playbook_priority"),
        nullable=False,
        default=PlaybookPriority.medium,
    )
    source: Mapped[PlaybookSource] = mapped_column(
        Enum(PlaybookSource, name="playbook_source"),
        nullable=False,
        default=PlaybookSource.manual,
    )
    trigger_on_deploy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    trigger_on_pr: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default=None)
    steps: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default_factory=list)
    assertions: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default_factory=list)
    performance_gates: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default_factory=dict
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    last_result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default=None)
    affected_paths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default_factory=list)

    # Relationships (excluded from dataclass init)
    product: Mapped[Product] = relationship(  # noqa: F821
        "Product", back_populates="playbooks", init=False
    )
    test_runs: Mapped[list[TestRun]] = relationship(  # noqa: F821
        "TestRun", back_populates="playbook", default_factory=list, init=False
    )


# ---------------------------------------------------------------------------
# Pydantic v2 Schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402


class PlaybookCreate(BaseModel):
    """Schema for creating a new Playbook."""

    product_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: PlaybookPriority = PlaybookPriority.medium
    source: PlaybookSource = PlaybookSource.manual
    trigger_on_deploy: bool = True
    trigger_on_pr: bool = True
    schedule_cron: Optional[str] = None
    steps: list[Any] = Field(default_factory=list)
    assertions: list[Any] = Field(default_factory=list)
    performance_gates: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    affected_paths: list[str] = Field(default_factory=list)


class PlaybookUpdate(BaseModel):
    """Schema for partially updating a Playbook."""

    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[PlaybookPriority] = None
    source: Optional[PlaybookSource] = None
    trigger_on_deploy: Optional[bool] = None
    trigger_on_pr: Optional[bool] = None
    schedule_cron: Optional[str] = None
    steps: Optional[list[Any]] = None
    assertions: Optional[list[Any]] = None
    performance_gates: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    affected_paths: Optional[list[str]] = None


class PlaybookResponse(BaseModel):
    """Schema returned when reading a Playbook."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    name: str
    description: Optional[str]
    priority: PlaybookPriority
    source: PlaybookSource
    trigger_on_deploy: bool
    trigger_on_pr: bool
    schedule_cron: Optional[str]
    steps: list[Any]
    assertions: list[Any]
    performance_gates: dict[str, Any]
    is_active: bool
    last_run_at: Optional[datetime]
    last_result: Optional[str]
    affected_paths: list[str]
    created_at: datetime
    updated_at: datetime
