"""
Alembic migration environment — async SQLAlchemy 2.0 edition.

DATABASE_URL resolution order:
  1. DATABASE_URL environment variable (overrides alembic.ini at runtime).
     postgresql:// is normalised to postgresql+asyncpg:// automatically.
  2. sqlalchemy.url in alembic.ini (default: sqlite+aiosqlite:///./tinaa.db).

All TINAA ORM models are imported below so they register with Base.metadata
before autogenerate inspects the schema.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from tinaa.models.base import Base

# ---------------------------------------------------------------------------
# Register all ORM models with Base.metadata so autogenerate detects them.
# ---------------------------------------------------------------------------
import tinaa.models.organization  # noqa: F401
import tinaa.models.product  # noqa: F401
import tinaa.models.environment  # noqa: F401
import tinaa.models.endpoint  # noqa: F401
import tinaa.models.playbook  # noqa: F401
import tinaa.models.test_run  # noqa: F401
import tinaa.models.metrics  # noqa: F401
import tinaa.models.quality  # noqa: F401
import tinaa.models.alert  # noqa: F401

# ---------------------------------------------------------------------------
# Alembic / logging config
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# DATABASE_URL override: production sets this env var; dev falls back to
# the sqlite+aiosqlite URL in alembic.ini.
# ---------------------------------------------------------------------------
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Normalise plain postgresql:// -> postgresql+asyncpg:// so alembic can
    # use the async driver even when the env var was set without the dialect.
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    config.set_main_option("sqlalchemy.url", database_url)


# ---------------------------------------------------------------------------
# Offline migrations (generates SQL without a live DB connection)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Emit migration SQL to stdout -- no DB connection required."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (requires a live async DB connection)
# ---------------------------------------------------------------------------

def do_run_migrations(connection: Connection) -> None:
    """Run migrations using an already-established sync connection handle."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine, open a connection, and run migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online mode -- drives the async migration coroutine."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
