"""
Async SQLAlchemy engine and session factory.

Environment variables:
    DATABASE_URL: Full async database URL.
                  Defaults to ``sqlite+aiosqlite:///./tinaa.db`` (dev).
                  Use ``postgresql+asyncpg://...`` in production.
    DB_POOL_SIZE: Connection pool size (ignored for SQLite). Default 5.
    DB_MAX_OVERFLOW: Max overflow connections. Default 10.
    DB_POOL_TIMEOUT: Seconds to wait for a connection. Default 30.
    DB_ECHO: Set to "true" to log all SQL statements. Default false.
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./tinaa.db"

_SQLITE_CONNECT_ARGS: dict[str, object] = {"check_same_thread": False}


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def create_async_engine_from_env() -> AsyncEngine:
    """
    Build an :class:`AsyncEngine` from the ``DATABASE_URL`` environment
    variable (or the default SQLite URL if unset).

    PostgreSQL (asyncpg) connections automatically receive pooling parameters
    from ``DB_POOL_SIZE``, ``DB_MAX_OVERFLOW``, and ``DB_POOL_TIMEOUT``.
    SQLite connections use ``StaticPool`` to avoid cross-thread issues in tests.
    """
    database_url: str = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    echo: bool = os.environ.get("DB_ECHO", "false").lower() == "true"

    is_sqlite = database_url.startswith("sqlite")

    if is_sqlite:
        return create_async_engine(
            database_url,
            echo=echo,
            connect_args=_SQLITE_CONNECT_ARGS,
        )

    # PostgreSQL / asyncpg
    pool_size: int = int(os.environ.get("DB_POOL_SIZE", "5"))
    max_overflow: int = int(os.environ.get("DB_MAX_OVERFLOW", "10"))
    pool_timeout: int = int(os.environ.get("DB_POOL_TIMEOUT", "30"))

    return create_async_engine(
        database_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Return an :class:`async_sessionmaker` bound to *engine*.

    Sessions are configured with:
    - ``expire_on_commit=False`` so that ORM objects remain usable after
      ``session.commit()`` in async code.
    - ``autoflush=False`` for explicit control over when writes are sent.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
