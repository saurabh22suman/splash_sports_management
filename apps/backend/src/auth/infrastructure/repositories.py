"""Auth repositories.

One repository per aggregate:
- TenantRepository
- UserRepository
- RefreshTokenRepository

Each exposes domain-meaningful methods. They never leak SQLAlchemy models
upward; the application layer works with domain entities only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.domain.entities import RefreshToken, Tenant, TenantStatus, User, UserRole
from auth.infrastructure.models import RefreshTokenModel, TenantModel, UserModel
from common.infrastructure.mixins import uuid_pk
from common.infrastructure.repository import BaseRepository


def _tenant_to_domain(m: TenantModel) -> Tenant:
    return Tenant(
        id=m.id,
        name=m.name,
        slug=m.slug,
        status=TenantStatus(m.status),
        primary_contact_email=m.primary_contact_email,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _user_to_domain(m: UserModel) -> User:
    return User(
        id=m.id,
        tenant_id=m.tenant_id,
        email=m.email,
        password_hash=m.password_hash,
        full_name=m.full_name,
        roles=[UserRole(r) for r in (m.roles or [])],
        is_active=m.is_active,
        failed_login_count=m.failed_login_count,
        locked_until=m.locked_until,
        last_login_at=m.last_login_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _refresh_to_domain(m: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=m.id,
        tenant_id=m.tenant_id,
        user_id=m.user_id,
        token_hash=m.token_hash,
        family_id=m.family_id,
        issued_at=m.issued_at,
        expires_at=m.expires_at,
        used_at=m.used_at,
        revoked_at=m.revoked_at,
    )


class TenantRepository(BaseRepository[Tenant]):
    model = TenantModel

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        stmt = select(TenantModel).where(TenantModel.id == tenant_id)
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return _tenant_to_domain(m) if m else None

    async def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(TenantModel).where(TenantModel.slug == slug)
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return _tenant_to_domain(m) if m else None

    async def add(self, tenant: Tenant) -> Tenant:
        m = TenantModel(
            name=tenant.name,
            slug=tenant.slug,
            status=tenant.status.value,
            primary_contact_email=tenant.primary_contact_email,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return _tenant_to_domain(m)


class UserRepository(BaseRepository[User]):
    model = UserModel

    async def get_by_id(self, tenant_id: UUID, user_id: UUID) -> User | None:
        m = await super().get(tenant_id, user_id)
        return _user_to_domain(m) if m else None

    async def get_by_email(self, tenant_id: UUID, email: str) -> User | None:
        stmt = select(UserModel).where(
            UserModel.tenant_id == tenant_id, UserModel.email == email.lower().strip()
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return _user_to_domain(m) if m else None

    async def get_by_email_global(self, email: str) -> User | None:
        """Lookup a user by email across all tenants. Used at login.

        In production we recommend passing tenant_slug alongside email so the
        lookup is scoped. For v1 we allow cross-tenant email lookup because
        emails are globally unique in practice.
        """
        stmt = select(UserModel).where(UserModel.email == email.lower().strip())
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return _user_to_domain(m) if m else None

    async def add(self, user: User) -> User:
        m = UserModel(
            tenant_id=user.tenant_id,
            email=user.email,
            password_hash=user.password_hash,
            full_name=user.full_name,
            roles=[r.value for r in user.roles],
            is_active=user.is_active,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return _user_to_domain(m)

    async def update(self, user: User) -> User:
        m = await self.session.get(UserModel, user.id)
        if m is None:
            raise LookupError(user.id)
        m.password_hash = user.password_hash
        m.roles = [r.value for r in user.roles]
        m.is_active = user.is_active
        m.failed_login_count = user.failed_login_count
        m.locked_until = user.locked_until
        m.last_login_at = user.last_login_at
        await self.session.flush()
        # Refresh to load server-updated columns (e.g. `updated_at` from onupdate=func.now())
        # so subsequent attribute access doesn't trigger lazy-load IO.
        await self.session.refresh(m)
        return _user_to_domain(m)

    async def list_by_tenant(self, tenant_id: UUID) -> list[User]:
        stmt = (
            select(UserModel)
            .where(UserModel.tenant_id == tenant_id)
            .order_by(UserModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [_user_to_domain(m) for m in result.scalars().all()]


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshTokenModel

    async def get_by_hash(self, tenant_id: UUID, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.tenant_id == tenant_id,
            RefreshTokenModel.token_hash == token_hash,
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return _refresh_to_domain(m) if m else None

    async def add(self, token: RefreshToken) -> RefreshToken:
        m = RefreshTokenModel(
            tenant_id=token.tenant_id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            family_id=token.family_id,
            expires_at=token.expires_at,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return _refresh_to_domain(m)

    async def mark_used(self, token: RefreshToken, now: datetime | None = None) -> None:
        m = await self.session.get(RefreshTokenModel, token.id)
        if m is None:
            return
        m.used_at = now or datetime.now(UTC)
        await self.session.flush()

    async def revoke_family(self, family_id: str, now: datetime | None = None) -> int:
        """Revoke every token in a family. Returns count revoked."""
        from sqlalchemy import update

        now = now or datetime.now(UTC)
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.family_id == family_id, RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0
