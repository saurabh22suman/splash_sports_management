"""AuthService — orchestrates the authentication use cases.

This is the entry point for the auth module's HTTP layer. It coordinates
the password hasher, token service, and repositories. It does NOT touch HTTP
or framework concerns.

Use cases:
- register_tenant: create tenant + first admin user
- login: verify credentials, issue access + refresh tokens
- refresh: rotate refresh tokens with reuse detection
- logout: revoke refresh family
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from auth.domain.entities import RefreshToken, Tenant, User, UserRole
from auth.infrastructure.password_hasher import Argon2PasswordHasher
from auth.infrastructure.repositories import (
    RefreshTokenRepository,
    TenantRepository,
    UserRepository,
)
from auth.infrastructure.token_service import (
    HS256TokenService,
    RS256KeyPaths,
    RS256TokenService,
    TokenPair,
)
from common.domain.exceptions import Conflict, Forbidden, Unauthorized, Validation
from common.domain.types import TenantId, UserId
from customer.infrastructure.repositories import CustomerRepository


@dataclass(frozen=True, slots=True)
class LoginResult:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    user_id: UUID
    tenant_id: UUID
    roles: list[str]
    customer_id: UUID | None = None


class AuthService:
    """Authentication orchestration."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        password_hasher: Argon2PasswordHasher,
        token_service: HS256TokenService | RS256TokenService,
        tenants: TenantRepository,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        customers: CustomerRepository | None = None,
    ) -> None:
        self.session = session
        self.password_hasher = password_hasher
        self.token_service = token_service
        self.tenants = tenants
        self.users = users
        self.refresh_tokens = refresh_tokens
        self.customers = customers

    # ----------------- tenant + first admin -----------------

    async def register_tenant(
        self,
        *,
        tenant_name: str,
        tenant_slug: str,
        primary_contact_email: str,
        admin_email: str,
        admin_password: str,
        admin_full_name: str,
    ) -> tuple[Tenant, User]:
        """Create a tenant and its first TenantAdmin user."""
        if await self.tenants.get_by_slug(tenant_slug) is not None:
            raise Conflict("Tenant slug already exists", details={"slug": tenant_slug})

        tenant = Tenant.create(
            name=tenant_name,
            slug=tenant_slug,
            primary_contact_email=primary_contact_email,
        )
        tenant = await self.tenants.add(tenant)

        password_hash = self.password_hasher.hash(admin_password)
        admin = User.create(
            tenant_id=tenant.id,
            email=admin_email,
            password_hash=password_hash,
            full_name=admin_full_name,
            roles=[UserRole.TENANT_ADMIN],
        )
        admin = await self.users.add(admin)
        tenant.activate()
        # persist activation: a tiny update on the model
        from auth.infrastructure.models import TenantModel

        m = await self.session.get(TenantModel, tenant.id)
        if m is not None:
            m.status = tenant.status.value
            await self.session.flush()
        return tenant, admin

    # ----------------- login -----------------

    async def login(self, *, email: str, password: str) -> LoginResult:
        user = await self.users.get_by_email_global(email)
        if user is None:
            # Don't reveal whether email exists
            raise Unauthorized("Invalid credentials")

        if not user.is_active:
            raise Forbidden("Account is disabled")

        if user.is_locked():
            raise Forbidden(
                "Account temporarily locked",
                details={
                    "locked_until": user.locked_until.isoformat() if user.locked_until else None
                },
            )

        if not self.password_hasher.verify(user.password_hash, password):
            user.record_failed_login()
            await self.users.update(user)
            # Commit the lockout counter BEFORE raising — otherwise the
            # session rollback erases the failed-login increment.
            await self.session.commit()
            raise Unauthorized("Invalid credentials")

        user.record_successful_login()
        await self.users.update(user)

        pair, family_id = self._issue_pair(user)
        await self.persist_refresh(pair, user, family_id)

        # Look up customer_id for users with customer role
        customer_id = None
        if self.customers is not None and user.roles:
            user_roles = [r.value for r in user.roles]
            if "customer" in user_roles:
                customer = await self.customers.get_by_user(user.tenant_id, user.id)
                if customer is not None:
                    customer_id = customer.id

        return LoginResult(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            access_expires_at=pair.access_expires_at,
            refresh_expires_at=pair.refresh_expires_at,
            user_id=user.id,
            tenant_id=user.tenant_id,
            roles=[r.value for r in user.roles],
            customer_id=customer_id,
        )

    # ----------------- refresh (rotating) -----------------

    async def refresh(self, *, refresh_token: str) -> LoginResult:
        try:
            claims = self.token_service.decode_refresh(refresh_token)
        except Exception as exc:
            raise Unauthorized("Invalid refresh token") from exc

        # Tenant-scope the token lookup to prevent cross-tenant hash collision attacks
        tenant_id = UUID(claims["tenant_id"])
        token_hash = self._hash(refresh_token)
        record = await self.refresh_tokens.get_by_hash(tenant_id, token_hash)

        if record is None:
            # Reuse detected: revoke the entire family
            family_id = claims.get("family_id")
            if isinstance(family_id, str):
                await self.refresh_tokens.revoke_family(family_id)
                # Commit the revocation BEFORE raising. Otherwise the
                # `get_session` dependency's exception handler will roll
                # back this security-critical update.
                await self.session.commit()
            raise Unauthorized("Refresh token reuse detected; family revoked")

        if not record.is_active():
            # Already used or revoked — treat as reuse
            await self.refresh_tokens.revoke_family(record.family_id)
            # Commit the family revocation before raising (see above).
            await self.session.commit()
            raise Unauthorized("Refresh token no longer valid")

        user = await self.users.get_by_id(record.tenant_id, record.user_id)
        if user is None or not user.is_active:
            raise Unauthorized("User not found or disabled")

        # Rotate: mark current used, issue new pair in same family
        record.mark_used()
        await self.refresh_tokens.mark_used(record)

        pair, family_id = self._issue_pair(user, family_id=record.family_id)
        await self.persist_refresh(pair, user, family_id)

        # Look up customer_id for users with customer role
        customer_id = None
        if self.customers is not None and user.roles:
            user_roles = [r.value for r in user.roles]
            if "customer" in user_roles:
                customer = await self.customers.get_by_user(user.tenant_id, user.id)
                if customer is not None:
                    customer_id = customer.id

        return LoginResult(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            access_expires_at=pair.access_expires_at,
            refresh_expires_at=pair.refresh_expires_at,
            user_id=user.id,
            tenant_id=user.tenant_id,
            roles=[r.value for r in user.roles],
            customer_id=customer_id,
        )

    # ----------------- logout -----------------

    async def logout(self, *, refresh_token: str) -> None:
        try:
            claims = self.token_service.decode_refresh(refresh_token)
        except Exception as exc:
            # Logout is idempotent — silently accept invalid tokens
            return
        family_id = claims.get("family_id")
        if isinstance(family_id, str):
            await self.refresh_tokens.revoke_family(family_id)
            # Commit so the revocation survives the request boundary even
            # when the response handler is empty (204 No Content).
            await self.session.commit()

    # ----------------- helpers -----------------

    def _issue_pair(self, user: User, *, family_id: str | None = None) -> tuple[TokenPair, str]:
        """Issue access + refresh tokens. Returns (pair, family_id).

        Caller is responsible for persisting the refresh token record.
        """
        effective_family = family_id or self._family_id_from_token(
            self.token_service.issue(
                user_id=UserId(user.id),
                tenant_id=TenantId(user.tenant_id),
                roles=[r.value for r in user.roles],
                family_id=None,
            ).refresh_token
        )
        pair = self.token_service.issue(
            user_id=UserId(user.id),
            tenant_id=TenantId(user.tenant_id),
            roles=[r.value for r in user.roles],
            family_id=effective_family,
        )
        return pair, effective_family

    async def persist_refresh(self, pair: TokenPair, user: User, family_id: str) -> RefreshToken:
        record = RefreshToken(
            id=__import__("uuid").UUID(int=0),
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=self._hash(pair.refresh_token),
            family_id=family_id,
            issued_at=datetime.now(UTC),
            expires_at=pair.refresh_expires_at,
            used_at=None,
            revoked_at=None,
        )
        return await self.refresh_tokens.add(record)

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _family_id_from_token(token: str) -> str:
        try:
            import jwt

            claims = jwt.decode(token, options={"verify_signature": False})
            fid = claims.get("family_id")
            if isinstance(fid, str):
                return fid
        except Exception:
            pass
        return secrets.token_urlsafe(16)


def _read_keypair(key_paths: RS256KeyPaths) -> tuple[str, str]:
    return (
        Path(key_paths.private_key_path).read_text(encoding="utf-8").strip(),
        Path(key_paths.public_key_path).read_text(encoding="utf-8").strip(),
    )


def build_auth_service(session: AsyncSession, settings) -> AuthService:  # type: ignore[no-untyped-def]
    """Wire up the AuthService with all dependencies."""
    import datetime as dt

    if settings.jwt_algorithm == "RS256":
        key_paths = RS256TokenService.get_secret(settings.environment)
        if key_paths is None and settings.environment in {"development", "test"}:
            private_pem, public_pem = RS256TokenService.generate_ephemeral_keypair()
        elif key_paths is None:
            msg = (
                "JWT keys not configured for production. "
                "Set JWT_PRIVATE_KEY_PATH and JWT_PUBLIC_KEY_PATH."
            )
            raise RuntimeError(msg)
        else:
            private_pem, public_pem = _read_keypair(key_paths)
        token_service = RS256TokenService(
            private_key_pem=private_pem,
            public_key_pem=public_pem,
            access_ttl=dt.timedelta(seconds=settings.jwt_access_token_ttl_seconds),
            refresh_ttl=dt.timedelta(seconds=settings.jwt_refresh_token_ttl_seconds),
        )
    elif settings.jwt_algorithm == "HS256":
        if settings.environment not in {"development", "test"}:
            msg = "HS256 is forbidden in production. Use RS256."
            raise RuntimeError(msg)
        import os

        secret = os.environ.get("JWT_SECRET")
        if not secret or len(secret) < 32:
            msg = "JWT_SECRET must be set and ≥32 chars in HS256 dev/test mode"
            raise RuntimeError(msg)
        from auth.infrastructure.token_service import HS256TokenService

        token_service = HS256TokenService(
            secret=secret,
            access_ttl=dt.timedelta(seconds=settings.jwt_access_token_ttl_seconds),
            refresh_ttl=dt.timedelta(seconds=settings.jwt_refresh_token_ttl_seconds),
        )
    else:
        msg = f"Unsupported JWT algorithm: {settings.jwt_algorithm}"
        raise NotImplementedError(msg)

    return AuthService(
        session=session,
        password_hasher=Argon2PasswordHasher(),
        token_service=token_service,
        tenants=TenantRepository(session),
        users=UserRepository(session),
        refresh_tokens=RefreshTokenRepository(session),
        customers=CustomerRepository(session),
    )
