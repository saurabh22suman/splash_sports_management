"""JWT token service.

Two token types:
- Access token (JWT, 15min): stateless, includes user_id, tenant_id, roles.
- Refresh token (opaque-looking JWT, 30d, rotated on use): includes a family
  id so we can revoke the entire family on reuse detection.

Production uses RS256 (asymmetric RSA key pair):
- Private key signs tokens (never leaves this service)
- Public key verifies tokens

Development/Test uses:
- RS256 with ephemeral keys (generated per-process in tests)
- HS256 with hardcoded secret (dev convenience only, NOT for production)
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import jwt

from common.domain.types import TenantId, UserId


@dataclass(frozen=True, slots=True)
class RS256KeyPaths:
    """Paths to RSA key files for RS256 JWT signing."""

    private_key_path: Path
    public_key_path: Path


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


class RS256TokenService:
    """RS256 JWT token service using asymmetric RSA key pair.

    Production uses RSA-2048+ keys stored in files. The private key never
    leaves this service - only used for signing. The public key is used
    for verification.

    For test environments, ephemeral keys can be generated per-process.
    """

    def __init__(
        self,
        *,
        private_key_pem: str,
        public_key_pem: str,
        access_ttl: timedelta,
        refresh_ttl: timedelta,
    ) -> None:
        self._private_key = private_key_pem
        self._public_key = public_key_pem
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl

    @staticmethod
    def get_secret(environment: str) -> RS256KeyPaths | None:
        """Get RSA key paths from environment variables.

        In production: raises RuntimeError if keys not configured.
        In test/development: returns None (caller should use ephemeral keys).
        """
        private_path = os.environ.get("JWT_PRIVATE_KEY_PATH")
        public_path = os.environ.get("JWT_PUBLIC_KEY_PATH")

        if not private_path or not public_path:
            if environment == "production":
                msg = "JWT private key path not configured. Set JWT_PRIVATE_KEY_PATH and JWT_PUBLIC_KEY_PATH."
                raise RuntimeError(msg)
            return None

        return RS256KeyPaths(
            private_key_path=Path(private_path),
            public_key_path=Path(public_path),
        )

    @staticmethod
    def generate_ephemeral_keypair() -> tuple[str, str]:
        """Generate ephemeral RSA keypair for tests.

        Uses RSA-2048 which is the minimum recommended key size.
        """
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        return private_pem, public_pem

    @staticmethod
    def from_key_paths(
        private_key_path: Path,
        public_key_path: Path,
        *,
        access_ttl: timedelta,
        refresh_ttl: timedelta,
    ) -> "RS256TokenService":
        """Factory to create RS256TokenService from key file paths."""
        if not private_key_path.is_file():
            msg = f"JWT private key not found: {private_key_path}"
            raise FileNotFoundError(msg)
        if not public_key_path.is_file():
            msg = f"JWT public key not found: {public_key_path}"
            raise FileNotFoundError(msg)

        private_pem = private_key_path.read_text(encoding="utf-8").strip()
        public_pem = public_key_path.read_text(encoding="utf-8").strip()

        return RS256TokenService(
            private_key_pem=private_pem,
            public_key_pem=public_pem,
            access_ttl=access_ttl,
            refresh_ttl=refresh_ttl,
        )

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
        return jwt.encode(claims, self._private_key, algorithm="RS256")

    def _decode(self, token: str) -> dict[str, object]:
        return jwt.decode(token, self._public_key, algorithms=["RS256"])
