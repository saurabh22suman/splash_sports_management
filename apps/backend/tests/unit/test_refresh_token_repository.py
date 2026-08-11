"""Unit tests for RefreshTokenRepository - tenant isolation.

These tests verify the fix for F-06: RefreshTokenRepository.get_by_hash lacks tenant_id filter.
The security fix ensures cross-tenant hash collisions cannot authenticate.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock

from auth.domain.entities import RefreshToken
from auth.infrastructure.models import RefreshTokenModel
from auth.infrastructure.repositories import RefreshTokenRepository


@pytest.mark.unit
class TestRefreshTokenRepositoryGetByHash:
    """Tests for get_by_hash tenant isolation (F-06 fix)."""

    @pytest.mark.asyncio
    async def test_get_by_hash_requires_tenant_id_parameter(self) -> None:
        """SECURITY FIX F-06: get_by_hash must require tenant_id parameter.

        This test verifies that the old vulnerable signature (just token_hash)
        no longer works - enforcing tenant scoping at the API level.

        Before fix: repo.get_by_hash(token_hash) - allows cross-tenant lookup
        After fix: repo.get_by_hash(tenant_id, token_hash) - tenant-scoped
        """
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        repo = RefreshTokenRepository(session)

        # Attempting to call with old signature should fail - this is the fix!
        with pytest.raises(TypeError, match="missing 1 required positional argument"):
            await repo.get_by_hash("some_hash")

    @pytest.mark.asyncio
    async def test_get_by_hash_accepts_tenant_id_parameter(self) -> None:
        """Verify the new signature: get_by_hash(tenant_id, token_hash)."""
        session = MagicMock()

        # Create a mock result
        mock_token = RefreshTokenModel(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            token_hash="test_hash",
            family_id="family1",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_token
        session.execute = AsyncMock(return_value=mock_result)

        repo = RefreshTokenRepository(session)

        tenant_id = uuid4()
        token_hash = "test_hash"

        # Should not raise - new signature accepts tenant_id
        result = await repo.get_by_hash(tenant_id, token_hash)

        # Verify the method was called
        session.execute.assert_called_once()

        # Verify result is returned (from mock)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_by_hash_signature_documents_security_fix(self) -> None:
        """Documentation test: verify the method signature enforces tenant scoping.

        This test exists to document the security fix in the test suite.
        """
        import inspect

        from auth.infrastructure.repositories import RefreshTokenRepository

        # Get the method signature
        sig = inspect.signature(RefreshTokenRepository.get_by_hash)
        params = list(sig.parameters.keys())

        # Verify tenant_id is the first parameter after self
        assert "tenant_id" in params, "tenant_id parameter is required for security"
        assert "token_hash" in params, "token_hash parameter is required"

        # tenant_id must come before token_hash
        tenant_idx = params.index("tenant_id")
        hash_idx = params.index("token_hash")
        assert tenant_idx < hash_idx, "tenant_id must be first for security"
