# Integration Tests

> Integration tests verify that components work together. Unlike unit tests, they use real infrastructure — real PostgreSQL, real Redis — but remain isolated per test via transactional rollback.

This document covers our integration testing strategy: testcontainers for real databases, one integration test per repository and service, transactional rollback per test, and test data factories. These tests bridge the gap between fast unit tests and slow end-to-end tests.

---

## What is an Integration Test

An integration test:
- Uses **real** PostgreSQL and Redis (via testcontainers)
- Tests **composition** of multiple components (repository + service)
- Uses **transactional rollback** to ensure isolation
- Is **slower** than unit tests (100ms-2s) but **faster** than e2e tests

> **Rule** — Every repository and service must have corresponding integration tests that verify behavior against real infrastructure.

---

## Testcontainers Setup

### Dependencies

```bash
pip install pytest-testcontainers
```

### PostgreSQL Container

```python
# apps/backend/tests/integration/conftest.py
import pytest
import sqlalchemy
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for the test session."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def postgres_url(postgres_container):
    """Get the PostgreSQL connection URL."""
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session")
def engine(postgres_url):
    """Create SQLAlchemy engine connected to test DB."""
    engine = sqlalchemy.create_engine(postgres_url)
    yield engine
    engine.dispose()
```

### Redis Container

```python
@pytest.fixture(scope="session")
def redis_container():
    """Start a Redis container for the test session."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture
def redis_client(redis_container):
    """Get a Redis client connected to test Redis."""
    import redis
    client = redis.Redis(
        host=redis_container.host,
        port=redis_container.port,
        decode_responses=True,
    )
    yield client
    client.flushdb()  # Clear after each test
```

---

## Transactional Rollback

### The Pattern

Each test runs in a transaction that is rolled back after the test completes:

```python
# conftest.py - session-scoped engine with function-scoped transactions
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session(engine):
    """Create a new DB session for each test with rollback."""
    connection = engine.connect()
    transaction = connection.begin()

    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.rollback()
    session.close()
    transaction.rollback()
    connection.close()
```

### Why Rollback

- **Isolation** — No test affects another
- **Speed** — No cleanup needed between tests
- **Reliability** — No leftover data causes flaky tests

---

## One Integration Test Per Repository + Service

### Repository Test

```python
# apps/backend/src/booking/tests/integration/test_booking_repository.py
import pytest
from datetime import datetime, timedelta
from booking.repository import BookingRepository
from booking.models import Booking


class TestBookingRepository:
    """Integration tests for BookingRepository with real PostgreSQL."""

    @pytest.fixture
    def repo(self, db_session):
        return BookingRepository(session=db_session)

    def test_create_and_retrieve_booking(self, repo):
        """Happy path: create a booking and retrieve it."""
        # ACT
        booking = repo.create(
            tenant_id="tenant-001",
            facility_id="court-001",
            customer_id="customer-001",
            start_time=datetime(2024, 1, 15, 10, 0),
            duration_minutes=60,
            status="confirmed",
        )

        # ASSERT
        retrieved = repo.get_by_id(booking.id)
        assert retrieved is not None
        assert retrieved.id == booking.id
        assert retrieved.facility_id == "court-001"
        assert retrieved.status == "confirmed"

    def test_get_bookings_in_slot_returns_conflicts(self, repo):
        """Integration: query returns overlapping bookings."""
        # ARRANGE: Create two bookings that overlap
        slot_time = datetime(2024, 1, 15, 10, 0)
        repo.create(
            tenant_id="tenant-001",
            facility_id="court-001",
            customer_id="customer-001",
            start_time=slot_time,
            duration_minutes=60,
            status="confirmed",
        )
        repo.create(
            tenant_id="tenant-001",
            facility_id="court-001",
            customer_id="customer-002",
            start_time=slot_time,
            duration_minutes=60,
            status="confirmed",
        )

        # ACT
        conflicts = repo.get_bookings_in_slot(
            tenant_id="tenant-001",
            facility_id="court-001",
            start_time=slot_time,
            duration_minutes=60,
        )

        # ASSERT
        assert len(conflicts) == 2

    def test_update_booking_status(self, repo):
        """Integration: status update persists."""
        # ARRANGE
        booking = repo.create(
            tenant_id="tenant-001",
            facility_id="court-001",
            customer_id="customer-001",
            start_time=datetime(2024, 1, 15, 10, 0),
            duration_minutes=60,
            status="confirmed",
        )

        # ACT
        repo.update_status(booking.id, "cancelled")

        # ASSERT
        updated = repo.get_by_id(booking.id)
        assert updated.status == "cancelled"

    def test_delete_soft_deletes_booking(self, repo):
        """Integration: delete sets deleted_at timestamp."""
        # ARRANGE
        booking = repo.create(
            tenant_id="tenant-001",
            facility_id="court-001",
            customer_id="customer-001",
            start_time=datetime(2024, 1, 15, 10, 0),
            duration_minutes=60,
            status="confirmed",
        )

        # ACT
        repo.delete(booking.id)

        # ASSERT
        deleted = repo.get_by_id(booking.id)
        assert deleted is None  # Soft delete hides it

        # Verify it's actually soft-deleted (check raw table)
        from booking.models import Booking
        raw = db_session.query(Booking).filter_by(id=booking.id).first()
        assert raw.deleted_at is not None
```

### Service Test

```python
# apps/backend/src/booking/tests/integration/test_booking_service.py
from datetime import datetime, timedelta


class TestBookingServiceWithRepository:
    """Integration tests for BookingService using real repository."""

    @pytest.fixture
    def service(self, db_session):
        from booking.repository import BookingRepository
        from booking.service import BookingService

        repo = BookingRepository(session=db_session)
        return BookingService(repository=repo)

    def test_create_booking_with_real_repository(self, service):
        """End-to-end: create booking through service with real DB."""
        # ACT
        result = service.create_booking(
            tenant_id="tenant-001",
            request=CreateBookingRequest(
                facility_id="court-001",
                customer_id="customer-001",
                start_time=datetime(2024, 1, 15, 10, 0),
                duration_minutes=60,
            ),
        )

        # ASSERT
        assert result.id is not None
        assert result.status == "confirmed"

    def test_booking_conflict_detected_via_real_repo(self, service):
        """Integration: service detects conflict through repository."""
        # ARRANGE: Create first booking
        service.create_booking(
            tenant_id="tenant-001",
            request=CreateBookingRequest(
                facility_id="court-001",
                customer_id="customer-001",
                start_time=datetime(2024, 1, 15, 10, 0),
                duration_minutes=60,
            ),
        )

        # ACT & ASSERT: Second booking fails
        with pytest.raises(SlotNotAvailableError):
            service.create_booking(
                tenant_id="tenant-001",
                request=CreateBookingRequest(
                    facility_id="court-001",
                    customer_id="customer-002",
                    start_time=datetime(2024, 1, 15, 10, 0),
                    duration_minutes=60,
                ),
            )
```

---

## Test Data Factories

### Factory Pattern

```python
# apps/backend/tests/integration/factories.py
import factory
from datetime import datetime, timedelta
from booking.models import Booking, Facility, Customer
from membership.models import Member, Subscription


class FacilityFactory(factory.Factory):
    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"facility-{n}")
    tenant_id = "tenant-001"
    name = factory.Sequence(lambda n: f"Test Court {n}")
    type = "tennis_court"
    hourly_rate = 40.00
    is_active = True


class CustomerFactory(factory.Factory):
    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"customer-{n}")
    tenant_id = "tenant-001"
    name = factory.Sequence(lambda n: f"Test Customer {n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.id}@example.com")
    phone = "+447000000000"
    is_active = True


class BookingFactory(factory.Factory):
    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"booking-{n}")
    tenant_id = "tenant-001"
    facility_id = factory.LazyAttribute(lambda _: "facility-1")
    customer_id = factory.LazyAttribute(lambda _: "customer-1")
    start_time = factory.LazyFunction(
        lambda: datetime.utcnow() + timedelta(days=1)
    )
    duration_minutes = 60
    status = "confirmed"
    created_at = factory.LazyFunction(datetime.utcnow)
```

### Using Factories in Tests

```python
def test_get_bookings_for_facility(self, repo, db_session):
    """Integration: query bookings for specific facility."""
    # ARRANGE: Create test data using factories
    facility_id = "test-court-1"

    # Insert facilities and bookings directly
    db_session.execute(
        insert(facility_table).values([
            {"id": facility_id, "tenant_id": "t1", "name": "Court 1", "type": "tennis"}
        ])
    )
    db_session.execute(
        insert(booking_table).values([
            {
                "id": "b1",
                "tenant_id": "t1",
                "facility_id": facility_id,
                "customer_id": "c1",
                "start_time": datetime(2024, 1, 15, 10, 0),
                "duration_minutes": 60,
                "status": "confirmed",
            },
            {
                "id": "b2",
                "tenant_id": "t1",
                "facility_id": facility_id,
                "customer_id": "c2",
                "start_time": datetime(2024, 1, 15, 14, 0),
                "duration_minutes": 60,
                "status": "confirmed",
            },
        ])
    )
    db_session.commit()

    # ACT
    bookings = repo.get_bookings_for_facility(facility_id)

    # ASSERT
    assert len(bookings) == 2
```

---

## Redis Integration Tests

```python
# apps/backend/tests/integration/test_cache_repository.py
import pytest
from datetime import timedelta


class TestCacheRepository:
    """Integration tests for Redis caching."""

    @pytest.fixture
    def cache_repo(self, redis_client):
        from booking.cache import BookingCacheRepository
        return BookingCacheRepository(redis=redis_client)

    def test_set_and_get_booking(self, cache_repo):
        """Integration: store and retrieve booking from Redis."""
        # ACT
        cache_repo.set_booking("booking-123", {"status": "confirmed"}, ttl=3600)

        # ASSERT
        result = cache_repo.get_booking("booking-123")
        assert result["status"] == "confirmed"

    def test_delete_removes_booking(self, cache_repo):
        """Integration: delete removes cached booking."""
        # ARRANGE
        cache_repo.set_booking("booking-123", {"status": "confirmed"})

        # ACT
        cache_repo.delete_booking("booking-123")

        # ASSERT
        result = cache_repo.get_booking("booking-123")
        assert result is None

    def test_ttl_expiry(self, cache_repo):
        """Integration: entry expires after TTL."""
        # ACT
        cache_repo.set_booking("booking-123", {"status": "confirmed"}, ttl=1)

        # ASSERT
        import time
        time.sleep(1.1)

        result = cache_repo.get_booking("booking-123")
        assert result is None
```

---

## Multi-Tenant Isolation

### Testing Tenant Separation

```python
def test_bookings_isolated_by_tenant(self, repo):
    """Integration: tenants cannot see each other's bookings."""
    # ARRANGE: Bookings in different tenants
    repo.create(
        tenant_id="tenant-001",
        facility_id="court-001",
        customer_id="customer-001",
        start_time=datetime(2024, 1, 15, 10, 0),
        duration_minutes=60,
        status="confirmed",
    )
    repo.create(
        tenant_id="tenant-002",
        facility_id="court-001",
        customer_id="customer-002",
        start_time=datetime(2024, 1, 15, 10, 0),
        duration_minutes=60,
        status="confirmed",
    )

    # ACT: Query as tenant-001
    bookings = repo.get_bookings_for_tenant("tenant-001")

    # ASSERT: Only tenant-001's bookings returned
    assert len(bookings) == 1
    assert bookings[0].tenant_id == "tenant-001"
```

---

## Test Execution

### Running Integration Tests

```bash
# Run only integration tests
pytest apps/backend/src/booking/tests/integration/ -v

# Run with coverage
pytest apps/backend/src/booking/tests/integration/ \
  --cov=booking.repository \
  --cov=booking.service \
  --cov-fail-under=80

# Run in parallel (requires pytest-xdist)
pytest apps/backend/src/booking/tests/integration/ -n auto
```

### CI Configuration

```yaml
# .github/workflows/integration-tests.yml
- name: Integration Tests
  services:
    postgres:
      image: postgres:15-alpine
      env:
        POSTGRES_PASSWORD: test
      ports:
        - 5432:5432
    redis:
      image: redis:7-alpine
      ports:
        - 6379:6379
  run: |
    pytest apps/backend/src/booking/tests/integration/ \
      --cov=booking \
      --cov-report=xml \
      -v --tb=short
```

---

## Integration Test Checklist

- [ ] Uses real PostgreSQL (testcontainers)
- [ ] Uses real Redis (testcontainers)
- [ ] Each test runs in isolated transaction (rollback)
- [ ] One test per repository method
- [ ] One test per service method
- [ ] Tests error paths (not found, conflict, validation)
- [ ] Tests multi-tenant isolation
- [ ] Uses factories for test data
- [ ] Executes in <2 seconds per test

---

## Anti-patterns

### 1. No Rollback

```python
# BAD: Creating data without cleanup
def test_creates_booking(self, db_session):
    repo.create(...)  # Data persists after test
    # No teardown - next test sees leftover data
```

> **Anti-pattern** — Causes flaky tests that fail unpredictably.

### 2. Testing Unit Logic in Integration Tests

```python
# BAD: Testing pure logic in integration suite
def test_calculates_duration(self, db_session):
    booking = Booking(start_time=t1, end_time=t2)
    assert booking.duration == 60  # Pure calculation, not integration
```

> **Anti-pattern** — Duplicate unit test coverage. Integration tests should test component composition.

### 3. Skipping Integration Tests

> **Anti-pattern** — "Unit tests are enough." Integration tests catch issues unit tests miss: SQL queries, transaction boundaries, foreign key constraints, Redis serialization.

---

## Summary

| Aspect | Rule |
|--------|------|
| Database | Real PostgreSQL via testcontainers |
| Cache | Real Redis via testcontainers |
| Isolation | Transactional rollback per test |
| Scope | One test per repository/service method |
| Data | Factories for reproducibility |
| Speed | <2s per test |
| Coverage | 80%+ on repository/service code |

See also: [Unit Tests](unit-tests.md), [API Tests](api-tests.md), [Test Data Management](test-data-management.md), [Testing Diamond](testing-diamond.md).
