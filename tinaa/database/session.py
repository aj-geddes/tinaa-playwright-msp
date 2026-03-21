"""
Async session helpers: context manager and FastAPI dependency.

Usage (context manager)::

    async with AsyncSessionContext() as session:
        result = await session.execute(select(Product))

Usage (FastAPI dependency injection)::

    @app.get("/products")
    async def list_products(session: AsyncSession = Depends(get_async_session)):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from tinaa.database.engine import create_async_engine_from_env, create_session_factory

# Module-level engine and session factory (lazy-initialised once per process).
_engine = create_async_engine_from_env()
_session_factory = create_session_factory(_engine)


class AsyncSessionContext:
    """
    Async context manager that yields a :class:`AsyncSession`.

    Commits on clean exit, rolls back and re-raises on any exception.

    Example::

        async with AsyncSessionContext() as session:
            session.add(MyModel(...))
            # commit happens automatically on __aexit__
    """

    async def __aenter__(self) -> AsyncSession:
        self._session: AsyncSession = _session_factory()
        return self._session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if exc_type is not None:
            await self._session.rollback()
        else:
            await self._session.commit()
        await self._session.close()


def get_session_factory():
    """
    Return the module-level async session factory.

    Intended for dependency injection in service registries and test
    fixtures that need direct access to the factory rather than a
    single session.  Equivalent to the module-level ``_session_factory``
    but accessed via a stable public API.

    Example::

        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(Product))
    """
    return _session_factory


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a transactional :class:`AsyncSession`.

    Inject via ``Depends(get_async_session)``; the session is committed on
    success and rolled back on any unhandled exception.
    """
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
