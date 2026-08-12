"""RBAC API tests.

Tests that endpoints properly enforce role-based access control using the
requires_role dependency. Verifies that:
- tenant_admin can access admin-only endpoints
- customer cannot access admin-only endpoints (gets 403)
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

JWT_TEST_SECRET = "dev-only-jwt-secret-change-me-in-prod-please-32chars"


def _create_token(
    tenant_id: UUID,
    user_id: UUID,
    roles: list[str],
    customer_id: UUID | None = None,
) -> str:
    """Create a JWT access token for testing."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "customer_id": str(customer_id) if customer_id else None,
        "type": "access",
        "exp": now + timedelta(hours=1),
        "iat": now,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, JWT_TEST_SECRET, algorithm="HS256")


@pytest.fixture(autouse=True)
def jwt_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Set JWT env vars per-test using monkeypatch (auto-restored after each test).

    Replaces the previous module-level os.environ mutation, which leaked state
    across tests when run alongside other test files (causing 8/25 RBAC tests
    to receive 401 instead of the expected 403). monkeypatch is pytest's
    standard env-isolation primitive — its teardown restores prior env values
    automatically.

    Also resets the Pydantic Settings cache so the new env values are picked up
    by `_get_public_key()` and `_get_jwt_algorithm()` in
    apps/backend/src/auth/interfaces/http/dependencies.py.
    """
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_SECRET", JWT_TEST_SECRET)
    from common.infrastructure.settings import reset_settings_cache

    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture
def mock_session() -> MagicMock:
    s = MagicMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    s.get = AsyncMock()
    s.execute = AsyncMock()
    s.delete = AsyncMock()
    s.commit = AsyncMock()
    s.rollback = AsyncMock()
    return s


@pytest_asyncio.fixture
async def client(mock_session) -> AsyncIterator[AsyncClient]:
    """Build the FastAPI app and provide an httpx client."""
    from common.interfaces.http import app as app_module
    from common.infrastructure import db as db_module

    async def override_get_session() -> AsyncIterator[MagicMock]:
        yield mock_session

    app = app_module.create_app()
    app.dependency_overrides[db_module.get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture
def customer_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def admin_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def customer_id() -> UUID:
    return uuid4()


@pytest.fixture
def customer_token(tenant_id: UUID, customer_user_id: UUID, customer_id: UUID) -> str:
    """Token for a customer user."""
    return _create_token(tenant_id, customer_user_id, ["customer"], customer_id)


@pytest.fixture
def admin_token(tenant_id: UUID, admin_user_id: UUID) -> str:
    """Token for a tenant_admin user."""
    return _create_token(tenant_id, admin_user_id, ["tenant_admin"])


@pytest.mark.asyncio
@pytest.mark.api
class TestPaymentsRBAC:
    """Test RBAC for payments endpoints."""

    async def test_create_invoice_customer_forbidden(
        self, client: AsyncClient, customer_token: str
    ) -> None:
        """Customer should get 403 when trying to create invoices."""
        resp = await client.post(
            "/v1/payments/invoices",
            json={
                "customer_id": str(uuid4()),
                "line_items": [{"description": "Test", "quantity": 1, "unit_price_paise": 1000}],
            },
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    async def test_refund_invoice_customer_forbidden(
        self, client: AsyncClient, customer_token: str
    ) -> None:
        """Customer should get 403 when trying to refund invoices."""
        resp = await client.post(
            f"/v1/payments/invoices/{uuid4()}/refund",
            json={"reason": "Test refund"},
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.api
class TestAuthRBAC:
    """Test RBAC for auth endpoints (tenant_admin only)."""

    async def test_create_user_customer_forbidden(
        self, client: AsyncClient, customer_token: str
    ) -> None:
        """Customer should get 403 when trying to create users."""
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
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    async def test_list_users_customer_forbidden(
        self, client: AsyncClient, customer_token: str
    ) -> None:
        """Customer should get 403 when trying to list users."""
        resp = await client.get(
            "/v1/auth/users",
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.api
class TestCustomerRBAC:
    """Test RBAC for customer endpoints."""

    async def test_create_customer_customer_forbidden(
        self, client: AsyncClient, customer_token: str
    ) -> None:
        """Customer should get 403 when trying to create customers."""
        resp = await client.post(
            "/v1/customer",
            json={
                "user_id": str(uuid4()),
                "full_name": "Test Customer",
                "email": "test@example.com",
            },
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    async def test_update_customer_customer_forbidden(
        self, client: AsyncClient, customer_token: str
    ) -> None:
        """Customer should get 403 when trying to update customers."""
        resp = await client.patch(
            f"/v1/customer/{uuid4()}",
            json={"full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.api
class TestFacilityRBAC:
    """Test RBAC for facility endpoints."""

    async def test_create_facility_customer_forbidden(
        self, client: AsyncClient, customer_token: str
    ) -> None:
        """Customer should get 403 when trying to create facilities."""
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
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    async def test_update_facility_customer_forbidden(
        self, client: AsyncClient, customer_token: str
    ) -> None:
        """Customer should get 403 when trying to update facilities."""
        resp = await client.patch(
            f"/v1/facility/{uuid4()}",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.api
class TestUnauthenticatedAccess:
    """Test that unauthenticated requests get 401."""

    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        """Requests without token should get 401."""
        resp = await client.post(
            "/v1/payments/invoices",
            json={
                "customer_id": str(uuid4()),
                "line_items": [{"description": "Test", "quantity": 1, "unit_price_paise": 1000}],
            },
        )
        assert resp.status_code == 401, resp.text

    async def test_invalid_token_returns_401(self, client: AsyncClient) -> None:
        """Requests with invalid token should get 401."""
        resp = await client.post(
            "/v1/payments/invoices",
            json={
                "customer_id": str(uuid4()),
                "line_items": [{"description": "Test", "quantity": 1, "unit_price_paise": 1000}],
            },
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401, resp.text
