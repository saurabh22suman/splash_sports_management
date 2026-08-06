# Test Data Management

> Test data should be reproducible, realistic, and isolated. We use factory_boy for object creation, scoped fixtures for lifecycle management, and anonymization for shared fixtures.

This document covers our test data strategy: factories, fixtures, scoping, anonymization, database seeding, and multi-tenant test data.

---

## Factories (factory_boy)

### Installation

```bash
pip install factory_boy
```

### Booking Factory

```python
# apps/backend/tests/factories.py
import factory
from datetime import datetime, timedelta
from booking.models import Booking, Facility, Customer


class FacilityFactory(factory.Factory):
    class Meta:
        model = Facility

    id = factory.Sequence(lambda n: f"facility-{n}")
    name = factory.Sequence(lambda n: f"Test Court {n}")
    type = "tennis_court"
    hourly_rate = 40.00
    tenant_id = "test-tenant"
    is_active = True


class CustomerFactory(factory.Factory):
    class Meta:
        model = Customer

    id = factory.Sequence(lambda n: f"customer-{n}")
    name = factory.Sequence(lambda n: f"Test Customer {n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.id}@example.com")
    phone = "+447700000000"
    tenant_id = "test-tenant"
    is_active = True


class BookingFactory(factory.Factory):
    class Meta:
        model = Booking

    id = factory.Sequence(lambda n: f"booking-{n}")
    tenant_id = "test-tenant"
    facility_id = factory.LazyAttribute(lambda _: "facility-1")
    customer_id = factory.LazyAttribute(lambda _: "customer-1")
    start_time = factory.LazyFunction(
        lambda: datetime.utcnow() + timedelta(days=1)
    )
    duration_minutes = 60
    status = "confirmed"
    created_at = factory.LazyFunction(datetime.utcnow)
```

### Using Factories

```python
def test_create_booking_with_factory():
    """Use factory to create test data."""
    facility = FacilityFactory(id="court-001")
    customer = CustomerFactory(id="cust-001")

    booking = BookingFactory(
        facility_id=facility.id,
        customer_id=customer.id,
        start_time=datetime(2024, 1, 15, 10, 0),
    )

    assert booking.id.startswith("booking-")
    assert booking.facility_id == "court-001"
```

---

## Fixtures

### Scoped Fixtures

```python
# conftest.py
import pytest


@pytest.fixture
def sample_booking():
    """Function-scoped: new booking each test."""
    return BookingFactory()


@pytest.fixture(scope="module")
def shared_tenant():
    """Module-scoped: shared tenant for all tests in module."""
    return {"id": "shared-tenant", "name": "Shared Test Tenant"}


@pytest.fixture(scope="session")
def test_config():
    """Session-scoped: test configuration."""
    return {
        "max_bookings_per_user": 10,
        "cancellation_window_hours": 24,
    }
```

### Fixture Best Practices

```python
# GOOD: Isolated data per test
@pytest.fixture
def new_booking():
    """Each test gets fresh booking data."""
    return BookingFactory.build()


# BAD: Shared state
booking_cache = {}


@pytest.fixture
def cached_booking():
    """Shared across tests - causes flakiness."""
    if "booking" not in booking_cache:
        booking_cache["booking"] = BookingFactory()
    return booking_cache["booking"]
```

---

## Anonymization

### Sensitive Data

```python
# GOOD: Anonymize PII in test data
class AnonymizedCustomerFactory(factory.Factory):
    class Meta:
        model = Customer

    id = factory.Sequence(lambda n: f"customer-{n}")
    name = "Test Customer"  # Generic
    email = factory.LazyAttribute(
        lambda obj: f"test-{obj.id}@example.com"  # Not real email
    )
    phone = "+447700000000"  # Test number
    # Don't use real personal data
```

### Shared Fixtures

```python
# For shared test fixtures - always anonymize
@pytest.fixture
def tenant_with_members():
    """All member data is anonymized."""
    return {
        "id": "test-tenant",
        "name": "Test Tenant",
        "members": [
            {"id": "m1", "name": "Member 1", "email": "member1@test.com"},
            {"id": "m2", "name": "Member 2", "email": "member2@test.com"},
        ],
    }
```

---

## Database Seeding

### Seed Script

```python
# apps/backend/tests/seed.py
def seed_test_database(db_session):
    """Seed database with test data."""
    # Create facilities
    facilities = []
    for i in range(10):
        facility = Facility(
            id=f"court-{i+1}",
            name=f"Court {i+1}",
            type="tennis_court",
            hourly_rate=40.00,
            tenant_id="test-tenant",
        )
        db_session.add(facility)
        facilities.append(facility)

    # Create customers
    customers = []
    for i in range(100):
        customer = Customer(
            id=f"customer-{i+1}",
            name=f"Customer {i+1}",
            email=f"customer{i+1}@test.com",
            tenant_id="test-tenant",
        )
        db_session.add(customer)
        customers.append(customer)

    db_session.commit()
    return {"facilities": facilities, "customers": customers}
```

### Use in Tests

```python
@pytest.fixture(scope="session")
def seeded_db(db_session):
    """Seed database once per session."""
    return seed_test_database(db_session)


def test_search_bookings(seeded_db):
    """Test with seeded data."""
    assert len(seeded_db["facilities"]) == 10
    assert len(seeded_db["customers"]) == 100
```

---

## Multi-Tenant Test Data

### Tenant Isolation

```python
@pytest.fixture
def tenant_a_data():
    """Test data for tenant A."""
    return {
        "tenant_id": "tenant-a",
        "facilities": [
            FacilityFactory(id="court-a1", tenant_id="tenant-a"),
            FacilityFactory(id="court-a2", tenant_id="tenant-a"),
        ],
        "customers": [
            CustomerFactory(id="cust-a1", tenant_id="tenant-a"),
        ],
    }


@pytest.fixture
def tenant_b_data():
    """Test data for tenant B."""
    return {
        "tenant_id": "tenant-b",
        "facilities": [
            FacilityFactory(id="court-b1", tenant_id="tenant-b"),
        ],
        "customers": [
            CustomerFactory(id="cust-b1", tenant_id="tenant-b"),
        ],
    }


def test_tenant_isolation(tenant_a_data, tenant_b_data):
    """Verify tenants cannot see each other's data."""
    # Query as tenant A
    bookings_a = repository.get_bookings(tenant_id="tenant-a")

    # Should only see tenant A's bookings
    assert all(b.tenant_id == "tenant-a" for b in bookings_a)

    # Query as tenant B
    bookings_b = repository.get_bookings(tenant_id="tenant-b")

    # Should only see tenant B's bookings
    assert all(b.tenant_id == "tenant-b" for b in bookings_b)
```

---

## Test Data Checklist

- [ ] Uses factories for object creation
- [ ] Fixtures are properly scoped
- [ ] No shared state between tests
- [ ] PII is anonymized
- [ ] Multi-tenant isolation is testable
- [ ] Database seeding is reproducible

---

## Anti-patterns

### 1. Hardcoded Test Data

```python
# BAD: Hardcoded values scattered everywhere
def test_booking_1():
    booking = Booking(facility_id="court-001", ...)  # Hardcoded

def test_booking_2():
    booking = Booking(facility_id="court-001", ...)  # Repeated
```

> **Anti-pattern** — Use factories instead of hardcoded values.

### 2. Real PII in Tests

```python
# BAD: Using real personal data
customer = Customer(
    name="John Smith",
    email="john.smith@real-email.com",
    phone="+447700123456",
)
```

> **Anti-pattern** — Never use real PII in tests.

### 3. Shared Mutable State

```python
# BAD: Global test data
test_data = {}


@pytest.fixture
def shared_data():
    return test_data  # Shared across tests
```

> **Anti-pattern** — Shared state causes test interdependencies.

---

## Summary

| Aspect | Approach |
|--------|----------|
| Object creation | factory_boy |
| Fixture scoping | Function/module/session |
| PII | Always anonymize |
| Database | Seed per test or session |
| Multi-tenancy | Separate tenant fixtures |

See also: [Unit Tests](unit-tests.md), [Integration Tests](integration-tests.md), [Factories](factories.md).
