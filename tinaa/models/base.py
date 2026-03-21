"""
SQLAlchemy declarative base with reusable mixins.

Provides:
- Base: DeclarativeBase for all ORM models
- UUIDPrimaryKeyMixin: UUID v4 primary key (auto-generated, init=False)
- TimestampMixin: created_at / updated_at with automatic population (init=False)

All ORM models should inherit as:

    class MyModel(UUIDPrimaryKeyMixin, TimestampMixin, Base, MappedAsDataclass, kw_only=True):
        ...

Using ``MappedAsDataclass`` with ``kw_only=True`` on each concrete class
ensures that:
1. Column ``default`` / ``default_factory`` values apply at Python object
   instantiation time (not only at INSERT).
2. Required and optional fields may appear in any order (kw_only removes
   Python dataclass positional-argument ordering constraints).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base for all TINAA models."""


class UUIDPrimaryKeyMixin(MappedAsDataclass):
    """
    Mixin that adds a UUID v4 primary key column named ``id``.

    The id is auto-generated at instantiation and excluded from the
    dataclass ``__init__`` (``init=False``).
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default_factory=uuid.uuid4,
        init=False,
        index=True,
    )


class TimestampMixin(MappedAsDataclass):
    """
    Mixin that adds ``created_at`` and ``updated_at`` timestamp columns.

    Both are populated at instantiation via ``default_factory`` and
    excluded from the dataclass ``__init__`` (``init=False``).
    ``updated_at`` is also refreshed on every UPDATE via ``onupdate``.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        init=False,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        init=False,
        nullable=False,
    )
