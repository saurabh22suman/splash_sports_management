"""JWT token service.

Two token types:
- Access token (JWT, 15min): stateless, includes user_id, tenant_id, roles.
- Refresh token (opaque-looking JWT, 30d, rotated on use): includes a family
  id so we can revoke the entire family on reuse detection.

> Per the handbook ([Refresh Token Rotation](../../../docs/09-security/refresh-token-rotation.md)),
> opaque tokens would normally be stored hashed server-side. For this prototype
> we use JWT with HS256 — the dev convenience is OK because this is the
> auth module's first iteration. Production deployment MUST switch to RS256 +
> opaque refresh tokens with hashed storage.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt

from common.domain.types import TenantId, UserId


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


class HS256TokenService:
    """HS256 JWT token service for development and tests.

    Production MUST use [`RS256TokenService`] (uses an asymmetric key pair).
    """

    def __init__(self, *, secret: str, access_ttl: timedelta, refresh_ttl: timedelta) -> None:
        if len(secret) < 32:
            msg = "JWT secret must be at least 32 chars"
            raise ValueError(msg)
        self._secret = secret
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl

    def issue(
        self,
        *,
        user_id: UserId,
        tenant_id: TenantId,
        roles: list[str],
        family_id: str | None = None,
    ) -> TokenPair:
        now = datetime.now(timezone.utc)
        access_exp = now + self._access_ttl
        refresh_exp = now + self._refresh_ttl
        family_id = family_id or secrets.token_urlsafe(16)
        jti = str(uuid4())

        access = self._encode(
            {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
                "roles": roles,
                "type": "access",
                "jti": jti,
                "iat": now,
                "exp": access_exp,
            }
        )
        # jti on refresh tokens too: iat/exp serialize to second precision in
        # JWT, so two refresh tokens issued in the same second with the same
        # family would be byte-identical and collide on the unique token_hash
        # constraint. jti guarantees per-issuance uniqueness.
        refresh = self._encode(
            {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
                "type": "refresh",
                "family_id": family_id,
                "jti": jti,
                "iat": now,
                "exp": refresh_exp,
            }
        )
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            access_expires_at=access_exp,
            refresh_expires_at=refresh_exp,
        )

    def decode_access(self, token: str) -> dict[str, object]:
        claims = self._decode(token)
        if claims.get("type") != "access":
            msg = "Not an access token"
            raise jwt.InvalidTokenError(msg)
        return claims

    def decode_refresh(self, token: str) -> dict[str, object]:
        claims = self._decode(token)
        if claims.get("type") != "refresh":
            msg = "Not a refresh token"
            raise jwt.InvalidTokenError(msg)
        return claims

    def _encode(self, claims: dict[str, object]) -> str:
        return jwt.encode(claims, self._secret, algorithm="HS256")

    def _decode(self, token: str) -> dict[str, object]:
        return jwt.decode(token, self._secret, algorithms=["HS256"])


def build_token_service(
    *, secret: str, access_ttl_seconds: int, refresh_ttl_seconds: int
) -> HS256TokenService:
    """Factory used by the FastAPI dependency."""
    return HS256TokenService(
        secret=secret,
        access_ttl=timedelta(seconds=access_ttl_seconds),
        refresh_ttl=timedelta(seconds=refresh_ttl_seconds),
    )
