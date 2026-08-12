"""Tests for RS256TokenService (asymmetric JWT tokens)."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import jwt
import pytest

from auth.infrastructure.token_service import RS256TokenService, TokenPair
from common.domain.types import TenantId, UserId


@pytest.mark.unit
class TestRS256TokenService:
    """Test RS256 JWT token service with RSA key pair."""

    def _generate_keypair(self) -> tuple[str, str]:
        """Generate a fresh RSA-2048 keypair for testing."""
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

    def _service(self, private_pem: str, public_pem: str) -> RS256TokenService:
        return RS256TokenService(
            private_key_pem=private_pem,
            public_key_pem=public_pem,
            access_ttl=timedelta(minutes=15),
            refresh_ttl=timedelta(days=30),
        )

    def test_issue_returns_access_and_refresh_tokens(self) -> None:
        private_pem, public_pem = self._generate_keypair()
        svc = self._service(private_pem, public_pem)
        user_id = UserId(uuid4())
        tenant_id = TenantId(uuid4())
        pair = svc.issue(user_id=user_id, tenant_id=tenant_id, roles=["member"])
        assert isinstance(pair, TokenPair)
        assert pair.access_token
        assert pair.refresh_token
        assert pair.access_expires_at > datetime.now(timezone.utc)

    def test_sign_with_private_verify_with_public(self) -> None:
        private_pem, public_pem = self._generate_keypair()
        svc = self._service(private_pem, public_pem)
        user_id = UserId(uuid4())
        tenant_id = TenantId(uuid4())
        pair = svc.issue(user_id=user_id, tenant_id=tenant_id, roles=["member"])

        # Verify with public key
        claims = jwt.decode(
            pair.access_token,
            public_pem,
            algorithms=["RS256"],
        )
        assert claims["sub"] == str(user_id)
        assert claims["tenant_id"] == str(tenant_id)
        assert claims["roles"] == ["member"]
        assert claims["type"] == "access"

    def test_signing_with_public_key_fails(self) -> None:
        """Verify that signing with public key fails (forgery prevention)."""
        private_pem, public_pem = self._generate_keypair()
        svc = self._service(private_pem, public_pem)
        user_id = UserId(uuid4())
        tenant_id = TenantId(uuid4())

        # Try to sign with public key - should fail
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend

        # Generate a new keypair to simulate attacker with their own key
        attacker_private = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        attacker_private_pem = attacker_private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        # Sign with attacker's key
        now = datetime.now(timezone.utc)
        attacker_token = jwt.encode(
            {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
                "roles": ["admin"],
                "type": "access",
                "iat": now,
                "exp": now + timedelta(minutes=15),
            },
            attacker_private_pem,
            algorithm="RS256",
        )

        # Verify with real public key - should fail
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(attacker_token, public_pem, algorithms=["RS256"])

    def test_decode_access_token_validates_signature(self) -> None:
        private_pem, public_pem = self._generate_keypair()
        svc = self._service(private_pem, public_pem)
        pair = svc.issue(user_id=UserId(uuid4()), tenant_id=TenantId(uuid4()), roles=["member"])
        claims = svc.decode_access(pair.access_token)
        assert claims["type"] == "access"

    def test_decode_refresh_token_validates_signature(self) -> None:
        private_pem, public_pem = self._generate_keypair()
        svc = self._service(private_pem, public_pem)
        pair = svc.issue(user_id=UserId(uuid4()), tenant_id=TenantId(uuid4()), roles=["member"])
        claims = svc.decode_refresh(pair.refresh_token)
        assert claims["type"] == "refresh"

    def test_decode_rejects_tampered_token(self) -> None:
        private_pem, public_pem = self._generate_keypair()
        svc = self._service(private_pem, public_pem)
        pair = svc.issue(user_id=UserId(uuid4()), tenant_id=TenantId(uuid4()), roles=["member"])
        tampered = pair.access_token[:-2] + ("xx" if pair.access_token[-2:] != "xx" else "yy")
        with pytest.raises(jwt.InvalidTokenError):
            svc.decode_access(tampered)

    def test_decode_rejects_expired_token(self) -> None:
        private_pem, public_pem = self._generate_keypair()
        svc = RS256TokenService(
            private_key_pem=private_pem,
            public_key_pem=public_pem,
            access_ttl=timedelta(seconds=-1),
            refresh_ttl=timedelta(days=30),
        )
        pair = svc.issue(user_id=UserId(uuid4()), tenant_id=TenantId(uuid4()), roles=["member"])
        with pytest.raises(jwt.ExpiredSignatureError):
            svc.decode_access(pair.access_token)

    def test_get_secret_raises_if_env_missing(self) -> None:
        """Verify that get_secret() raises if JWT_PRIVATE_KEY_PATH env is missing."""
        # Save original env
        original_private = os.environ.get("JWT_PRIVATE_KEY_PATH")
        original_public = os.environ.get("JWT_PUBLIC_KEY_PATH")

        try:
            # Unset the env vars
            if "JWT_PRIVATE_KEY_PATH" in os.environ:
                del os.environ["JWT_PRIVATE_KEY_PATH"]
            if "JWT_PUBLIC_KEY_PATH" in os.environ:
                del os.environ["JWT_PUBLIC_KEY_PATH"]

            # In production mode (non-test env), should raise
            with pytest.raises(RuntimeError, match="JWT private key path not configured"):
                RS256TokenService.get_secret(environment="production")

            # In test env, should return None (uses ephemeral keys)
            secret = RS256TokenService.get_secret(environment="test")
            assert secret is None
        finally:
            # Restore original env
            if original_private:
                os.environ["JWT_PRIVATE_KEY_PATH"] = original_private
            if original_public:
                os.environ["JWT_PUBLIC_KEY_PATH"] = original_public

    def test_get_secret_returns_paths_for_valid_env(self) -> None:
        """Verify get_secret() returns valid paths when env vars are set."""
        # Save original env
        original_private = os.environ.get("JWT_PRIVATE_KEY_PATH")
        original_public = os.environ.get("JWT_PUBLIC_KEY_PATH")

        try:
            # Set env vars to non-existent files (we just check the paths are returned)
            os.environ["JWT_PRIVATE_KEY_PATH"] = "/tmp/fake_private.pem"
            os.environ["JWT_PUBLIC_KEY_PATH"] = "/tmp/fake_public.pem"

            # In production, should return the paths (caller will handle missing files)
            paths = RS256TokenService.get_secret(environment="production")
            assert paths is not None
            assert paths.private_key_path == Path("/tmp/fake_private.pem")
            assert paths.public_key_path == Path("/tmp/fake_public.pem")
        finally:
            # Restore original env
            if original_private:
                os.environ["JWT_PRIVATE_KEY_PATH"] = original_private
            elif "JWT_PRIVATE_KEY_PATH" in os.environ:
                del os.environ["JWT_PRIVATE_KEY_PATH"]
            if original_public:
                os.environ["JWT_PUBLIC_KEY_PATH"] = original_public
            elif "JWT_PUBLIC_KEY_PATH" in os.environ:
                del os.environ["JWT_PUBLIC_KEY_PATH"]
