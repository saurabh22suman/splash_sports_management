"""Tests for TokenService (JWT access + opaque refresh)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from auth.infrastructure.token_service import HS256TokenService, TokenPair
from common.domain.types import TenantId, UserId


@pytest.mark.unit
class TestHS256TokenService:
    def _service(self) -> HS256TokenService:
        return HS256TokenService(
            secret="unit-test-secret-must-be-long-enough-for-hs256",
            access_ttl=timedelta(minutes=15),
            refresh_ttl=timedelta(days=30),
        )

    def test_issue_returns_access_and_refresh_tokens(self) -> None:
        svc = self._service()
        user_id = UserId(uuid4())
        tenant_id = TenantId(uuid4())
        pair = svc.issue(user_id=user_id, tenant_id=tenant_id, roles=["member"])
        assert isinstance(pair, TokenPair)
        assert pair.access_token
        assert pair.refresh_token
        assert pair.access_expires_at > datetime.now(timezone.utc)

    def test_access_token_decodes_with_expected_claims(self) -> None:
        svc = self._service()
        user_id = UserId(uuid4())
        tenant_id = TenantId(uuid4())
        pair = svc.issue(user_id=user_id, tenant_id=tenant_id, roles=["member"])
        claims = jwt.decode(
            pair.access_token,
            "unit-test-secret-must-be-long-enough-for-hs256",
            algorithms=["HS256"],
        )
        assert claims["sub"] == str(user_id)
        assert claims["tenant_id"] == str(tenant_id)
        assert claims["roles"] == ["member"]
        assert claims["type"] == "access"
        assert "exp" in claims and "iat" in claims and "jti" in claims

    def test_refresh_token_has_different_claims(self) -> None:
        svc = self._service()
        user_id = UserId(uuid4())
        tenant_id = TenantId(uuid4())
        pair = svc.issue(user_id=user_id, tenant_id=tenant_id, roles=["admin"])
        claims = jwt.decode(
            pair.refresh_token,
            "unit-test-secret-must-be-long-enough-for-hs256",
            algorithms=["HS256"],
        )
        assert claims["type"] == "refresh"
        assert claims["sub"] == str(user_id)

    def test_decode_access_token_validates_signature(self) -> None:
        svc = self._service()
        pair = svc.issue(user_id=UserId(uuid4()), tenant_id=TenantId(uuid4()), roles=["member"])
        claims = svc.decode_access(pair.access_token)
        assert claims["type"] == "access"

    def test_decode_refresh_token_validates_signature(self) -> None:
        svc = self._service()
        pair = svc.issue(user_id=UserId(uuid4()), tenant_id=TenantId(uuid4()), roles=["member"])
        claims = svc.decode_refresh(pair.refresh_token)
        assert claims["type"] == "refresh"

    def test_decode_rejects_tampered_token(self) -> None:
        svc = self._service()
        pair = svc.issue(user_id=UserId(uuid4()), tenant_id=TenantId(uuid4()), roles=["member"])
        tampered = pair.access_token[:-2] + ("xx" if pair.access_token[-2:] != "xx" else "yy")
        with pytest.raises(jwt.InvalidTokenError):
            svc.decode_access(tampered)

    def test_decode_rejects_expired_token(self) -> None:
        svc = HS256TokenService(
            secret="unit-test-secret-must-be-long-enough-for-hs256",
            access_ttl=timedelta(seconds=-1),
            refresh_ttl=timedelta(days=30),
        )
        pair = svc.issue(user_id=UserId(uuid4()), tenant_id=TenantId(uuid4()), roles=["member"])
        with pytest.raises(jwt.ExpiredSignatureError):
            svc.decode_access(pair.access_token)
