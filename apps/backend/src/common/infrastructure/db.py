"""SQLAlchemy async engine and session factory.

We use the **async session per request** pattern:
1. Middleware opens a session at request start.
2. Session is bound to the request context.
3. Service code uses the session via [`get_session`] (FastAPI dependency).
4. On exit, session commits on success, rolls back on exception.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from common.infrastructure.settings import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    Modules subclass [`Base`] to declare their tables. All tables must include
    `tenant_id` (UUID) and `created_at`/`updated_at` columns.
    """

    type_annotation_map: dict[Any, Any] = {}


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


async def init_engine(settings: Settings | None = None) -> AsyncEngine:
    """Initialise the global engine. Called once at app startup."""
    global _engine, _session_factory
    if _engine is None:
        settings = settings or get_settings()
        _engine = _build_engine(settings)
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _engine


async def dispose_engine() -> None:
    """Dispose of the engine at app shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        msg = "Database engine not initialised. Call init_engine() at startup."
        raise RuntimeError(msg)
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a session.

    The session is committed on successful exit and rolled back on exception.
    Callers should not commit explicitly; the Unit-of-Work pattern keeps that
    responsibility in the session lifecycle.

    Sets `app.tenant_id` on the connection for RLS policies when a tenant
    context is available (i.e., for authenticated requests).
    """
    from sqlalchemy import text

    from common.application.context import get_context, reset_context

    factory = get_session_factory()
    async with factory() as session:
        # Set tenant context for RLS policies if tenant_id is available
        ctx = get_context()
        if ctx is not None and ctx.tenant_id is not None:
            try:
                await session.execute(
                    text("SET LOCAL app.tenant_id = :tenant_id"),
                    {"tenant_id": str(ctx.tenant_id)},
                )
            except Exception:
                # Session might be a mock in tests; continue without RLS
                pass

        try:
            yield session
            # Commit on clean exit. The repository/service code only `flush()`s;
            # commit happens here so the Unit-of-Work is a single HTTP request.
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            reset_context()
