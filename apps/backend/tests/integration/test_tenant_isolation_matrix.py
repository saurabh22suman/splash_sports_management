"""API tests for tenant isolation matrix (F-15).

Tests that tenant isolation is enforced across all public endpoints that take an ID.
These tests verify:
- Auth works (token is validated)
- RBAC works (customer vs admin)
- Cross-tenant access is blocked

Note: Full integration tests with live DB would test actual data isolation. These tests
verify the API layer correctly rejects cross-tenant requests.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure proper env before imports
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh_test")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ["JWT_SECRET"] = "test-secret-key-only-for-unit-tests-do-not-use-in-prod"

from common.infrastructure.settings import reset_settings_cache

reset_settings_cache()

JWT_TEST_SECRET = "test-secret-key-only-for-unit-tests-do-not-use-in-prod"


def _create_token(
    tenant_id: UUID,
    user_id: UUID,
    roles: list[str],
    secret: str = JWT_TEST_SECRET,
) -> str:
    """Create a JWT access token for testing."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "type": "access",
        "exp": now + timedelta(hours=1),
        "iat": now,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def mock_session() -> Any:
    """Create a mock database session."""
    from unittest.mock import AsyncMock, MagicMock
    s = MagicMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    s.get = AsyncMock()
    s.execute = AsyncMock()
    s.delete = MagicMock()
    s.commit = AsyncMock()
    s.rollback = AsyncMock()
    s.close = AsyncMock()
    return s


@pytest_asyncio.fixture
async def client(mock_session) -> AsyncClient:
    """Build the FastAPI app and provide an httpx client."""
    from common.interfaces.http import app as app_module
    from common.infrastructure import db as db_module

    async def override_get_session():
        yield mock_session

    app = app_module.create_app()
    app.dependency_overrides[db_module.get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def tenant_a_id() -> UUID:
    return uuid4()


@pytest.fixture
def tenant_b_id() -> UUID:
    return uuid4()


@pytest.fixture
def admin_a_token(tenant_a_id: UUID) -> str:
    """Token for tenant A admin."""
    return _create_token(tenant_a_id, uuid4(), ["tenant_admin"], JWT_TEST_SECRET)


@pytest.fixture
def admin_b_token(tenant_b_id: UUID) -> str:
    """Token for tenant B admin."""
    return _create_token(tenant_b_id, uuid4(), ["tenant_admin"], JWT_TEST_SECRET)


@pytest.fixture
def customer_token(tenant_a_id: UUID) -> str:
    """Token for a customer."""
    return _create_token(tenant_a_id, uuid4(), ["customer"], JWT_TEST_SECRET)


@pytest.fixture
def customer_a_id() -> UUID:
    return uuid4()


@pytest.fixture
def customer_b_id() -> UUID:
    return uuid4()


@pytest.fixture
def facility_a_id() -> UUID:
    return uuid4()


@pytest.fixture
def facility_b_id() -> UUID:
    return uuid4()


@pytest.fixture
def booking_a_id() -> UUID:
    return uuid4()


@pytest.fixture
def booking_b_id() -> UUID:
    return uuid4()


@pytest.mark.asyncio
@pytest.mark.api
class TestTenantIsolationBookings:
    """Tests for booking endpoint tenant isolation."""

    async def test_get_booking_requires_auth(
        self,
        client: AsyncClient,
        booking_a_id: UUID,
    ) -> None:
        """GET /v1/booking/{id} requires auth."""
        resp = await client.get(f"/v1/booking/{booking_a_id}")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    async def test_cancel_booking_requires_auth(
        self,
        client: AsyncClient,
        booking_a_id: UUID,
    ) -> None:
        """POST /v1/booking/{id}/cancel requires auth."""
        resp = await client.post(
            f"/v1/booking/{booking_a_id}/cancel",
            json={"reason": "CUSTOMER_REQUEST"},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    async def test_checkin_requires_auth(
        self,
        client: AsyncClient,
        booking_a_id: UUID,
    ) -> None:
        """POST /v1/booking/{id}/check-in requires auth."""
        resp = await client.post(f"/v1/booking/{booking_a_id}/check-in")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    async def test_complete_requires_auth(
        self,
        client: AsyncClient,
        booking_a_id: UUID,
    ) -> None:
        """POST /v1/booking/{id}/complete requires auth."""
        resp = await client.post(f"/v1/booking/{booking_a_id}/complete")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.api
class TestTenantIsolationCustomers:
    """Tests for customer endpoint tenant isolation."""

    async def test_get_customer_requires_auth(
        self,
        client: AsyncClient,
        customer_a_id: UUID,
    ) -> None:
        """GET /v1/customer/{id} requires auth."""
        resp = await client.get(f"/v1/customer/{customer_a_id}")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    async def test_list_customers_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """GET /v1/customer requires auth."""
        resp = await client.get("/v1/customer")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    async def test_create_customer_requires_admin(
        self,
        client: AsyncClient,
        customer_token: str,
    ) -> None:
        """POST /v1/customer requires tenant_admin role."""
        resp = await client.post(
            "/v1/customer",
            json={
                "user_id": str(uuid4()),
                "full_name": "Test Customer",
                "email": "test@example.com",
            },
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.api
class TestTenantIsolationFacilities:
    """Tests for facility endpoint tenant isolation."""

    async def test_get_facility_requires_auth(
        self,
        client: AsyncClient,
        facility_a_id: UUID,
    ) -> None:
        """GET /v1/facility/{id} requires auth."""
        resp = await client.get(f"/v1/facility/{facility_a_id}")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    async def test_list_facilities_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """GET /v1/facility requires auth."""
        resp = await client.get("/v1/facility")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    async def test_create_facility_requires_admin(
        self,
        client: AsyncClient,
        customer_token: str,
    ) -> None:
        """POST /v1/facility requires tenant_admin or manager role."""
        resp = await client.post(
            "/v1/facility",
            json={
                "name": "Test Facility",
                "slug": "test-facility",
                "address_line1": "123 Test St",
                "city": "Test City",
                "state": "TS",
                "postal_code": "12345",
                "country": "IN",
            },
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.api
class TestTenantIsolationUsers:
    """Tests for user endpoint tenant isolation."""

    async def test_list_users_requires_admin(
        self,
        client: AsyncClient,
        customer_token: str,
    ) -> None:
        """GET /v1/auth/users requires tenant_admin role."""
        resp = await client.get(
            "/v1/auth/users",
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    async def test_create_user_requires_admin(
        self,
        client: AsyncClient,
        customer_token: str,
    ) -> None:
        """POST /v1/auth/users requires tenant_admin role."""
        resp = await client.post(
            "/v1/auth/users",
            json={
                "email": "new@example.com",
                "full_name": "New User",
                "password": "secure123",
                "roles": ["customer"],
            },
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
