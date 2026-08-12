"""Integration tests for AuthService.

These tests use a real Postgres database (via the conftest fixtures). They
exercise the full authentication flow: tenant registration, login, refresh
(with reuse detection), logout.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from auth.application.auth_service import AuthService
from auth.domain.entities import UserRole
from auth.infrastructure.password_hasher import Argon2PasswordHasher
from auth.infrastructure.repositories import (
    RefreshTokenRepository,
    TenantRepository,
    UserRepository,
)
from auth.infrastructure.token_service import HS256TokenService
from common.domain.exceptions import Conflict, Forbidden, Unauthorized
from common.infrastructure.db import Base


pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh_test",
)


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=db_engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def auth_service(session) -> AuthService:
    return AuthService(
        session=session,
        password_hasher=Argon2PasswordHasher(),
        token_service=HS256TokenService(
            secret="integration-test-secret-must-be-long-enough",
            access_ttl=timedelta(minutes=15),
            refresh_ttl=timedelta(days=30),
        ),
        tenants=TenantRepository(session),
        users=UserRepository(session),
        refresh_tokens=RefreshTokenRepository(session),
    )


async def _register_default_tenant(svc: AuthService) -> None:
    await svc.register_tenant(
        tenant_name="Splashh",
        tenant_slug="splashh",
        primary_contact_email="contact@splashh.dev",
        admin_email="admin@splashh.dev",
        admin_password="verysecurepassword123",
        admin_full_name="Admin User",
    )


@pytest.mark.asyncio
class TestRegisterTenant:
    async def test_creates_tenant_and_admin_user(self, auth_service: AuthService) -> None:
        tenant, admin = await auth_service.register_tenant(
            tenant_name="Splashh Sports",
            tenant_slug="splashh",
            primary_contact_email="contact@splashh.dev",
            admin_email="admin@splashh.dev",
            admin_password="verysecurepassword123",
            admin_full_name="Admin User",
        )
        assert tenant.id is not None
        assert tenant.slug == "splashh"
        assert admin.email == "admin@splashh.dev"
        assert admin.has_role(UserRole.TENANT_ADMIN)

    async def test_rejects_duplicate_slug(self, auth_service: AuthService) -> None:
        await _register_default_tenant(auth_service)
        with pytest.raises(Conflict):
            await auth_service.register_tenant(
                tenant_name="Splashh Two",
                tenant_slug="splashh",
                primary_contact_email="b@b.com",
                admin_email="b@b.com",
                admin_password="verysecurepassword123",
                admin_full_name="Admin",
            )


@pytest.mark.asyncio
class TestLogin:
    async def test_login_with_correct_credentials_returns_tokens(
        self, auth_service: AuthService
    ) -> None:
        await _register_default_tenant(auth_service)
        result = await auth_service.login(
            email="admin@splashh.dev", password="verysecurepassword123"
        )
        assert result.access_token
        assert result.refresh_token
        assert result.user_id is not None
        assert result.tenant_id is not None

    async def test_login_with_wrong_password_raises(self, auth_service: AuthService) -> None:
        await _register_default_tenant(auth_service)
        with pytest.raises(Unauthorized):
            await auth_service.login(email="admin@splashh.dev", password="wrongpassword")

    async def test_login_with_unknown_email_does_not_reveal_existence(
        self, auth_service: AuthService
    ) -> None:
        with pytest.raises(Unauthorized):
            await auth_service.login(email="ghost@nowhere.com", password="anything")

    async def test_login_locks_account_after_max_failures(self, auth_service: AuthService) -> None:
        await _register_default_tenant(auth_service)
        for _ in range(10):
            try:
                await auth_service.login(email="admin@splashh.dev", password="wrong")
            except Unauthorized:
                pass
        with pytest.raises(Forbidden):
            await auth_service.login(email="admin@splashh.dev", password="verysecurepassword123")


@pytest.mark.asyncio
class TestRefresh:
    async def test_refresh_rotates_tokens(self, auth_service: AuthService) -> None:
        await _register_default_tenant(auth_service)
        result1 = await auth_service.login(
            email="admin@splashh.dev", password="verysecurepassword123"
        )
        result2 = await auth_service.refresh(refresh_token=result1.refresh_token)
        assert result2.access_token != result1.access_token
        assert result2.refresh_token != result1.refresh_token

    async def test_refresh_reuse_revokes_family(self, auth_service: AuthService) -> None:
        await _register_default_tenant(auth_service)
        result = await auth_service.login(
            email="admin@splashh.dev", password="verysecurepassword123"
        )
        # First refresh — succeeds and rotates
        first = await auth_service.refresh(refresh_token=result.refresh_token)
        # Second use of the original token — reuse detected
        with pytest.raises(Unauthorized):
            await auth_service.refresh(refresh_token=result.refresh_token)
        # Even the freshly issued token should now be revoked
        with pytest.raises(Unauthorized):
            await auth_service.refresh(refresh_token=first.refresh_token)

    async def test_logout_revokes_family(self, auth_service: AuthService) -> None:
        await _register_default_tenant(auth_service)
        result = await auth_service.login(
            email="admin@splashh.dev", password="verysecurepassword123"
        )
        await auth_service.logout(refresh_token=result.refresh_token)
        with pytest.raises(Unauthorized):
            await auth_service.refresh(refresh_token=result.refresh_token)
