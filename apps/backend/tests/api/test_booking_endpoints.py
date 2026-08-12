"""API tests for booking endpoints (F-16).

Tests the booking endpoints for:
- Schema validation (price_cents not in create, in response)
- Auth failures (no token, invalid token)
- RBAC failures (customer vs tenant_admin on check-in/complete)
- Validation failures (missing fields, invalid UUIDs)

Note: Full endpoint tests with happy path require integration testing with
a real database. These tests focus on the critical security and validation behaviors.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure proper env before imports - must match conftest.py
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh_test"
)
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ["JWT_SECRET"] = "test-secret-key-only-for-unit-tests-do-not-use-in-prod"

from common.infrastructure.settings import reset_settings_cache

reset_settings_cache()

# JWT test secret (must match conftest.py)
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
def mock_session() -> MagicMock:
    """Create a mock database session."""
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

    async def override_get_session() -> MagicMock:
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
def admin_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def customer_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def customer_id() -> UUID:
    return uuid4()


@pytest.fixture
def resource_id() -> UUID:
    return uuid4()


@pytest.fixture
def booking_id() -> UUID:
    return uuid4()


@pytest.fixture
def admin_token(tenant_id: UUID, admin_user_id: UUID) -> str:
    """Token for a tenant_admin user."""
    return _create_token(tenant_id, admin_user_id, ["tenant_admin"], JWT_TEST_SECRET)


@pytest.fixture
def customer_token(tenant_id: UUID, customer_user_id: UUID) -> str:
    """Token for a customer user."""
    return _create_token(tenant_id, customer_user_id, ["customer"], JWT_TEST_SECRET)


@pytest.fixture
def manager_token(tenant_id: UUID, admin_user_id: UUID) -> str:
    """Token for a manager user."""
    return _create_token(tenant_id, admin_user_id, ["manager"], JWT_TEST_SECRET)


@pytest.fixture
def staff_token(tenant_id: UUID, admin_user_id: UUID) -> str:
    """Token for a staff user."""
    return _create_token(tenant_id, admin_user_id, ["staff"], JWT_TEST_SECRET)


@pytest.fixture
def coach_token(tenant_id: UUID, admin_user_id: UUID) -> str:
    """Token for a coach user."""
    return _create_token(tenant_id, admin_user_id, ["coach"], JWT_TEST_SECRET)


@pytest.mark.asyncio
@pytest.mark.api
class TestBookingCreateSchema:
    """Tests for booking schema (F-05 security fix)."""

    def test_price_cents_removed_from_booking_create(self) -> None:
        """BookingCreate should NOT accept price_cents from client (security fix)."""
        from booking.interfaces.http.schemas import BookingCreate

        # After the fix, price_cents should not be in the schema
        assert "price_cents" not in BookingCreate.model_fields, (
            "price_cents must be removed from BookingCreate for F-05 fix"
        )

    def test_booking_out_includes_price_for_display(self) -> None:
        """BookingOut should include price_cents for UI display."""
        from booking.interfaces.http.schemas import BookingOut

        # The response should still include price for UI display
        assert "price_cents" in BookingOut.model_fields
        assert "currency" in BookingOut.model_fields


@pytest.mark.asyncio
@pytest.mark.api
class TestBookingCreateValidation:
    """Tests for POST /v1/booking validation."""

    async def test_create_booking_missing_customer_id(
        self,
        client: AsyncClient,
        admin_token: str,
        resource_id: UUID,
    ) -> None:
        """Validation failure: missing customer_id."""
        now = datetime.now(timezone.utc)
        start_at = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        end_at = start_at + timedelta(hours=1)

        resp = await client.post(
            "/v1/booking",
            json={
                "resource_id": str(resource_id),
                "start_at": start_at.isoformat(),
                "end_at": end_at.isoformat(),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    async def test_create_booking_missing_resource_id(
        self,
        client: AsyncClient,
        admin_token: str,
        customer_id: UUID,
    ) -> None:
        """Validation failure: missing resource_id."""
        now = datetime.now(timezone.utc)
        start_at = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        end_at = start_at + timedelta(hours=1)

        resp = await client.post(
            "/v1/booking",
            json={
                "customer_id": str(customer_id),
                "start_at": start_at.isoformat(),
                "end_at": end_at.isoformat(),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    async def test_create_booking_invalid_uuid(
        self,
        client: AsyncClient,
        admin_token: str,
    ) -> None:
        """Validation failure: invalid UUID format."""
        now = datetime.now(timezone.utc)
        start_at = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        end_at = start_at + timedelta(hours=1)

        resp = await client.post(
            "/v1/booking",
            json={
                "customer_id": "not-a-valid-uuid",
                "resource_id": "not-a-valid-uuid",
                "start_at": start_at.isoformat(),
                "end_at": end_at.isoformat(),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.api
class TestBookingAuth:
    """Tests for booking endpoint authentication."""

    async def test_create_booking_no_token_returns_401(
        self,
        client: AsyncClient,
        customer_id: UUID,
        resource_id: UUID,
    ) -> None:
        """Auth failure: no token returns 401."""
        now = datetime.now(timezone.utc)
        start_at = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        end_at = start_at + timedelta(hours=1)

        resp = await client.post(
            "/v1/booking",
            json={
                "customer_id": str(customer_id),
                "resource_id": str(resource_id),
                "start_at": start_at.isoformat(),
                "end_at": end_at.isoformat(),
            },
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    async def test_create_booking_invalid_token_returns_401(
        self,
        client: AsyncClient,
        customer_id: UUID,
        resource_id: UUID,
    ) -> None:
        """Auth failure: invalid token returns 401."""
        now = datetime.now(timezone.utc)
        start_at = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        end_at = start_at + timedelta(hours=1)

        resp = await client.post(
            "/v1/booking",
            json={
                "customer_id": str(customer_id),
                "resource_id": str(resource_id),
                "start_at": start_at.isoformat(),
                "end_at": end_at.isoformat(),
            },
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    async def test_get_booking_no_token_returns_401(
        self,
        client: AsyncClient,
        booking_id: UUID,
    ) -> None:
        """Auth failure: no token returns 401."""
        resp = await client.get(f"/v1/booking/{booking_id}")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    async def test_cancel_booking_no_token_returns_401(
        self,
        client: AsyncClient,
        booking_id: UUID,
    ) -> None:
        """Auth failure: no token returns 401."""
        resp = await client.post(
            f"/v1/booking/{booking_id}/cancel",
            json={"reason": "CUSTOMER_REQUEST"},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    async def test_checkin_no_token_returns_401(
        self,
        client: AsyncClient,
        booking_id: UUID,
    ) -> None:
        """Auth failure: no token returns 401."""
        resp = await client.post(f"/v1/booking/{booking_id}/check-in")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    async def test_complete_no_token_returns_401(
        self,
        client: AsyncClient,
        booking_id: UUID,
    ) -> None:
        """Auth failure: no token returns 401."""
        resp = await client.post(f"/v1/booking/{booking_id}/complete")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    async def test_list_by_customer_no_token_returns_401(
        self,
        client: AsyncClient,
        customer_id: UUID,
    ) -> None:
        """Auth failure: no token returns 401."""
        resp = await client.get(f"/v1/booking/by-customer/{customer_id}")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    async def test_list_by_resource_no_token_returns_401(
        self,
        client: AsyncClient,
        resource_id: UUID,
    ) -> None:
        """Auth failure: no token returns 401."""
        now = datetime.now(timezone.utc)
        from_at = now.isoformat()
        to_at = (now + timedelta(days=7)).isoformat()

        resp = await client.get(
            f"/v1/booking/by-resource/{resource_id}?from_at={from_at}&to_at={to_at}",
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.api
class TestBookingRBAC:
    """Tests for booking endpoint RBAC."""

    async def test_checkin_customer_forbidden(
        self,
        client: AsyncClient,
        customer_token: str,
        booking_id: UUID,
    ) -> None:
        """customer cannot check-in a booking (RBAC)."""
        resp = await client.post(
            f"/v1/booking/{booking_id}/check-in",
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    async def test_complete_customer_forbidden(
        self,
        client: AsyncClient,
        customer_token: str,
        booking_id: UUID,
    ) -> None:
        """customer cannot complete a booking (RBAC)."""
        resp = await client.post(
            f"/v1/booking/{booking_id}/complete",
            headers={"Authorization": f"Bearer {customer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
@pytest.mark.api
class TestBookingListValidation:
    """Tests for booking list endpoint validation."""

    async def test_list_by_resource_missing_params_returns_422(
        self,
        client: AsyncClient,
        admin_token: str,
        resource_id: UUID,
    ) -> None:
        """Validation failure: missing from_at and to_at."""
        resp = await client.get(
            f"/v1/booking/by-resource/{resource_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
