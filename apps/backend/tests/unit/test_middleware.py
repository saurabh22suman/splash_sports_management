"""Tests for request context middleware and session handling.

F-23: Context leak when commit fails - if commit() throws, context
should be reset so the next request on the same connection has
a clean context (no tenant_id leak).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from common.application.context import (
    RequestContext,
    bind_context,
    get_context,
    reset_context,
)


class TestContextResetOnSessionClose:
    """Test that context is reset when session closes."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Reset context before and after each test."""
        reset_context()
        yield
        reset_context()

    @pytest.mark.asyncio
    async def test_context_reset_after_session_close(self) -> None:
        """Session cleanup should reset context."""
        from common.infrastructure import db

        ctx = RequestContext(request_id="test-123", tenant_id="tenant-1")
        bind_context(ctx)
        assert get_context() is not None
        assert get_context().tenant_id == "tenant-1"

        # Mock session that commits successfully
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        with patch.object(db, "get_session_factory") as mock_factory:
            mock_factory.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.return_value.__aexit__ = AsyncMock(return_value=None)

            session_gen = db.get_session()
            await session_gen.__anext__()  # Yield the session
            await session_gen.aclose()  # Triggers commit + finally

        # Context should be reset after session closes
        assert get_context() is None, "Context should be reset after session closes!"

    @pytest.mark.asyncio
    async def test_context_reset_when_commit_fails(self) -> None:
        """If commit fails, context should still be reset (F-23 fix)."""
        from common.infrastructure import db

        ctx = RequestContext(request_id="test-456", tenant_id="tenant-2")
        bind_context(ctx)
        assert get_context() is not None
        assert get_context().tenant_id == "tenant-2"

        # Mock session that fails on commit
        mock_session = MagicMock()
        mock_session.commit = AsyncMock(side_effect=Exception("DB error"))
        mock_session.rollback = AsyncMock()

        with patch.object(db, "get_session_factory") as mock_factory:
            mock_factory.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.return_value.__aexit__ = AsyncMock(return_value=None)

            session_gen = db.get_session()
            await session_gen.__anext__()  # Yield the session

            # Simulate what happens when code after yield raises
            # Use athrow to inject an exception into the generator after yield
            with pytest.raises(Exception, match="DB error"):
                await session_gen.athrow(type(Exception()), Exception("DB error"))

        # F-23: Context must be reset even when commit fails!
        assert get_context() is None, "Context should be reset even after commit fails!"

    @pytest.mark.asyncio
    async def test_no_tenant_leak_to_next_request(self) -> None:
        """F-23: Simulate request 1 fails, verify request 2 has clean context."""
        from common.infrastructure import db

        # === Request 1: Sets tenant context, then fails ===
        ctx1 = RequestContext(request_id="req-1", tenant_id="tenant-abc")
        bind_context(ctx1)

        mock_session = MagicMock()
        mock_session.commit = AsyncMock(side_effect=Exception("Connection lost"))
        mock_session.rollback = AsyncMock()

        with patch.object(db, "get_session_factory") as mock_factory:
            mock_factory.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.return_value.__aexit__ = AsyncMock(return_value=None)

            session_gen = db.get_session()
            await session_gen.__anext__()
            try:
                await session_gen.aclose()
            except Exception:
                pass

        # === Request 2: New request should have NO tenant context ===
        # Before fix: tenant_id would leak from request 1!
        ctx2 = get_context()
        assert ctx2 is None, "Context leaked! Next request has stale tenant_id"
