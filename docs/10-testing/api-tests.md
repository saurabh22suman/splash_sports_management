# API Tests

> API tests verify the HTTP contract between client and server. They use httpx AsyncClient against the FastAPI application, cover happy path and error paths, validate authentication/authorization, and use the real database for realistic behavior.

This document covers our API testing strategy: FastAPI TestClient usage, happy path coverage, error validation, auth/authz testing, response snapshotting, and realistic test data. These tests verify the contract that external consumers depend on.

---

## What is an API Test

An API test:
- Makes **real HTTP requests** to the FastAPI application
- Uses **httpx AsyncClient** (or TestClient for sync tests)
- Tests the **HTTP contract** — request format, response format, status codes
- Uses **real database** (not mocks) for authenticity
- Verifies **authentication and authorization**

> **Rule** — Every API endpoint must have corresponding API tests that verify the HTTP contract.

---

## Test Setup

### FastAPI TestClient

```python
# apps/backend/tests/api/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db


# Create test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Create fresh DB for each test with rollback."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.rollback()
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create FastAPI test client."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for test user."""
    # Create test user and get token
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

---

## Happy Path Tests

### Basic CRUD Operations

```python
# apps/backend/tests/api/test_bookings.py
import pytest
from datetime import datetime, timedelta


class TestBookingEndpoints:
    """API tests for /api/v1/bookings endpoints."""

    def test_create_booking_returns_201(self, client, auth_headers):
        """Happy path: create booking returns 201 with booking data."""
        # ARRANGE
        payload = {
            "facility_id": "court-001",
            "customer_id": "customer-001",
            "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "duration_minutes": 60,
        }

        # ACT
        response = client.post(
            "/api/v1/bookings",
            json=payload,
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["facility_id"] == "court-001"
        assert data["status"] == "confirmed"

    def test_get_booking_returns_200(self, client, auth_headers):
        """Happy path: get booking returns full booking details."""
        # ARRANGE: Create booking first
        create_response = client.post(
            "/api/v1/bookings",
            json={
                "facility_id": "court-001",
                "customer_id": "customer-001",
                "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "duration_minutes": 60,
            },
            headers=auth_headers,
        )
        booking_id = create_response.json()["id"]

        # ACT
        response = client.get(
            f"/api/v1/bookings/{booking_id}",
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 200
        assert response.json()["id"] == booking_id

    def test_list_bookings_returns_200(self, client, auth_headers):
        """Happy path: list bookings returns paginated results."""
        # ACT
        response = client.get(
            "/api/v1/bookings?limit=10&offset=0",
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    def test_update_booking_returns_200(self, client, auth_headers):
        """Happy path: update booking returns modified booking."""
        # ARRANGE: Create booking
        create_response = client.post(
            "/api/v1/bookings",
            json={
                "facility_id": "court-001",
                "customer_id": "customer-001",
                "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "duration_minutes": 60,
            },
            headers=auth_headers,
        )
        booking_id = create_response.json()["id"]

        # ACT
        response = client.patch(
            f"/api/v1/bookings/{booking_id}",
            json={"status": "cancelled"},
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_delete_booking_returns_204(self, client, auth_headers):
        """Happy path: delete booking returns 204."""
        # ARRANGE: Create booking
        create_response = client.post(
            "/api/v1/bookings",
            json={
                "facility_id": "court-001",
                "customer_id": "customer-001",
                "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "duration_minutes": 60,
            },
            headers=auth_headers,
        )
        booking_id = create_response.json()["id"]

        # ACT
        response = client.delete(
            f"/api/v1/bookings/{booking_id}",
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 204
```

---

## Error Path Tests

### Validation Errors

```python
    def test_create_booking_missing_required_field_returns_422(self, client, auth_headers):
        """Validation: missing required field returns 422."""
        # ARRANGE: Missing customer_id
        payload = {
            "facility_id": "court-001",
            "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "duration_minutes": 60,
        }

        # ACT
        response = client.post(
            "/api/v1/bookings",
            json=payload,
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("customer_id" in str(e["loc"]) for e in errors)

    def test_create_booking_invalid_field_type_returns_422(self, client, auth_headers):
        """Validation: wrong field type returns 422."""
        # ARRANGE: duration_minutes should be int, not string
        payload = {
            "facility_id": "court-001",
            "customer_id": "customer-001",
            "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "duration_minutes": "sixty",  # Invalid type
        }

        # ACT
        response = client.post(
            "/api/v1/bookings",
            json=payload,
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 422

    def test_create_booking_invalid_time_format_returns_422(self, client, auth_headers):
        """Validation: invalid ISO timestamp returns 422."""
        # ARRANGE
        payload = {
            "facility_id": "court-001",
            "customer_id": "customer-001",
            "start_time": "not-a-timestamp",
            "duration_minutes": 60,
        }

        # ACT
        response = client.post(
            "/api/v1/bookings",
            json=payload,
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 422
```

### Not Found Errors

```python
    def test_get_nonexistent_booking_returns_404(self, client, auth_headers):
        """Error: booking not found returns 404."""
        # ACT
        response = client.get(
            "/api/v1/bookings/nonexistent-id",
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_nonexistent_booking_returns_404(self, client, auth_headers):
        """Error: update missing booking returns 404."""
        # ACT
        response = client.patch(
            "/api/v1/bookings/nonexistent-id",
            json={"status": "cancelled"},
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 404
```

### Conflict Errors

```python
    def test_create_duplicate_booking_returns_409(self, client, auth_headers):
        """Error: slot already booked returns 409."""
        # ARRANGE: Create first booking
        start_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
        client.post(
            "/api/v1/bookings",
            json={
                "facility_id": "court-001",
                "customer_id": "customer-001",
                "start_time": start_time,
                "duration_minutes": 60,
            },
            headers=auth_headers,
        )

        # ACT: Try to create conflicting booking
        response = client.post(
            "/api/v1/bookings",
            json={
                "facility_id": "court-001",
                "customer_id": "customer-002",
                "start_time": start_time,
                "duration_minutes": 60,
            },
            headers=auth_headers,
        )

        # ASSERT
        assert response.status_code == 409
        assert "not available" in response.json()["detail"].lower()
```

---

## Authentication Tests

### Missing Auth

```python
    def test_create_booking_without_auth_returns_401(self, client):
        """Auth: missing token returns 401."""
        # ACT
        response = client.post(
            "/api/v1/bookings",
            json={
                "facility_id": "court-001",
                "customer_id": "customer-001",
                "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "duration_minutes": 60,
            },
        )

        # ASSERT
        assert response.status_code == 401
```

### Invalid Token

```python
    def test_create_booking_with_invalid_token_returns_401(self, client):
        """Auth: invalid token returns 401."""
        # ACT
        response = client.post(
            "/api/v1/bookings",
            json={
                "facility_id": "court-001",
                "customer_id": "customer-001",
                "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "duration_minutes": 60,
            },
            headers={"Authorization": "Bearer invalid-token"},
        )

        # ASSERT
        assert response.status_code == 401
```

### Expired Token

```python
    def test_create_booking_with_expired_token_returns_401(self, client):
        """Auth: expired token returns 401."""
        # ARRANGE: Use expired token (would need to generate one)
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # expired

        # ACT
        response = client.post(
            "/api/v1/bookings",
            json={
                "facility_id": "court-001",
                "customer_id": "customer-001",
                "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "duration_minutes": 60,
            },
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        # ASSERT
        assert response.status_code == 401
```

---

## Authorization Tests

### Tenant Isolation

```python
class TestTenantIsolation:
    """API tests for multi-tenant authorization."""

    def test_cannot_access_other_tenant_booking(self, client):
        """Authz: user cannot access another tenant's booking."""
        # ARRANGE: User from tenant-001
        token_tenant1 = get_token_for_tenant("tenant-001")
        # Booking from tenant-002
        booking_id = create_booking_in_tenant("tenant-002")

        # ACT
        response = client.get(
            f"/api/v1/bookings/{booking_id}",
            headers={"Authorization": f"Bearer {token_tenant1}"},
        )

        # ASSERT
        assert response.status_code == 404  # Not found (not 403 - don't leak existence)

    def test_cannot_create_booking_for_other_tenant(self, client):
        """Authz: user cannot create booking in another tenant."""
        # ARRANGE: User from tenant-001
        token_tenant1 = get_token_for_tenant("tenant-001")

        # ACT: Try to book in tenant-002's facility
        response = client.post(
            "/api/v1/bookings",
            json={
                "facility_id": "court-in-tenant-2",
                "customer_id": "customer-001",
                "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "duration_minutes": 60,
            },
            headers={"Authorization": f"Bearer {token_tenant1}"},
        )

        # ASSERT
        assert response.status_code in [404, 403]
```

### Role-Based Access

```python
    def test_member_cannot_access_admin_endpoint(self, client):
        """Authz: member role cannot access admin endpoints."""
        # ARRANGE: Member token
        member_token = get_token_with_role("member")

        # ACT
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {member_token}"},
        )

        # ASSERT
        assert response.status_code == 403

    def test_admin_can_access_admin_endpoint(self, client):
        """Authz: admin role can access admin endpoints."""
        # ARRANGE: Admin token
        admin_token = get_token_with_role("admin")

        # ACT
        response = client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # ASSERT
        assert response.status_code == 200
```

---

## Response Validation

### Schema Validation

```python
def test_create_booking_response_matches_schema(self, client, auth_headers):
    """Response: booking creation returns valid schema."""
    # ACT
    response = client.post(
        "/api/v1/bookings",
        json={
            "facility_id": "court-001",
            "customer_id": "customer-001",
            "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "duration_minutes": 60,
        },
        headers=auth_headers,
    )

    # ASSERT
    assert response.status_code == 201
    data = response.json()

    # Validate response schema
    assert "id" in data
    assert "tenant_id" in data
    assert "facility_id" in data
    assert "customer_id" in data
    assert "start_time" in data
    assert "end_time" in data
    assert "duration_minutes" in data
    assert "status" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Validate types
    assert isinstance(data["id"], str)
    assert isinstance(data["duration_minutes"], int)
    assert data["status"] in ["pending", "confirmed", "cancelled", "completed"]
```

---

## AsyncClient for Async Endpoints

```python
# For async FastAPI endpoints
import pytest
import httpx
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def async_client():
    """Async client for async endpoint testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_async_endpoint(async_client, auth_headers):
    """Test async booking search endpoint."""
    # ARRANGE
    await seed_test_data(async_client, auth_headers)

    # ACT
    response = await async_client.get(
        "/api/v1/bookings/search?facility_type=tennis",
        headers=auth_headers,
    )

    # ASSERT
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
```

---

## Test Execution

### Running API Tests

```bash
# Run all API tests
pytest apps/backend/tests/api/ -v

# Run specific endpoint tests
pytest apps/backend/tests/api/test_bookings.py -v

# Run with coverage
pytest apps/backend/tests/api/ \
  --cov=apps/backend/src/booking/router \
  --cov-fail-under=80
```

### CI Configuration

```yaml
# .github/workflows/api-tests.yml
- name: API Tests
  services:
    postgres:
      image: postgres:15-alpine
      env:
        POSTGRES_PASSWORD: test
      ports:
        - 5432:5432
  run: |
    pytest apps/backend/tests/api/ \
      --cov=apps.backend.src \
      --cov-report=xml \
      --cov-report=term-missing \
      -v --tb=short
```

---

## API Test Checklist

- [ ] Happy path returns correct status code
- [ ] Response body matches documented schema
- [ ] Validation errors return 422 with details
- [ ] Not found errors return 404
- [ ] Conflict errors return 409
- [ ] Auth failures return 401
- [ ] Authz failures return 403
- [ ] Tenant isolation is enforced
- [ ] Role-based access is enforced
- [ ] Response times are acceptable (<200ms)

---

## Anti-patterns

### 1. Testing with Mocks

```python
# BAD: Using mocks in API tests defeats the purpose
def test_create_booking(self, client):
    with mock.patch("service.create_booking") as mock_create:
        mock_create.return_value = {"id": "123"}
        response = client.post("/api/v1/bookings", json={...})

    assert response.json()["id"] == "123"
```

> **Anti-pattern** — API tests should test the real stack, not mocks. Mocks belong in unit tests.

### 2. Skipping Error Paths

```python
# BAD: Only testing happy path
def test_create_booking(self, client, auth_headers):
    response = client.post("/api/v1/bookings", json={...}, headers=auth_headers)
    assert response.status_code == 201
```

> **Anti-pattern** — Error paths are where production failures happen. Every error case needs a test.

### 3. Not Testing Auth

```python
# BAD: Not testing authentication
def test_create_booking(self, client):
    response = client.post("/api/v1/bookings", json={...})
    assert response.status_code == 201  # Should require auth!
```

> **Anti-pattern** — Unauthenticated endpoints are security vulnerabilities.

---

## Summary

| Aspect | Rule |
|--------|------|
| Client | httpx TestClient / AsyncClient |
| Database | Real PostgreSQL (not mocks) |
| Coverage | Every endpoint + every error code |
| Auth | All auth paths tested |
| Authz | Tenant + role isolation tested |
| Validation | 422 for invalid input |
| Schema | Response matches documented contract |

See also: [Unit Tests](unit-tests.md), [Integration Tests](integration-tests.md), [Contract Tests](contract-tests.md), [UI Tests](ui-tests.md).
