# Unit Tests

> A unit test is a test that runs in isolation, has no I/O dependencies, and verifies one behavior. — The Splashh Testing Philosophy

This document covers our unit testing standards: pure domain tests with no I/O, fast execution (<10ms per test), descriptive naming, parametrization for variations, and fixture management with Faker. Senior engineers and QA use this as the reference for writing effective unit tests.

---

## What is a Unit Test

A unit test verifies a single piece of behavior in isolation:

- **No I/O** — No database calls, no HTTP requests, no file system access
- **Fast** — Executes in <10ms on a laptop
- **Isolated** — Does not depend on other tests
- **Deterministic** — Same input always produces same output

> **Rule** — Every unit test must be able to run in parallel with any other test without shared state.

---

## Test Structure

### One Assertion Per Test

```python
# BAD: Multiple assertions in one test
def test_booking_creation():
    booking = service.create_booking(...)
    assert booking.id is not None      # First thing
    assert booking.status == "confirmed"  # Second thing
    assert booking.customer_id == "c1"   # Third thing

# GOOD: One behavior per test
def test_booking_creation_returns_booking_with_id():
    booking = service.create_booking(...)
    assert booking.id is not None

def test_booking_creation_defaults_to_confirmed_status():
    booking = service.create_booking(...)
    assert booking.status == "confirmed"

def test_booking_creation_associates_customer():
    booking = service.create_booking(...)
    assert booking.customer_id == "c1"
```

> **Why** — When a test fails, you immediately know what broke. Multiple assertions blur the root cause.

### Descriptive Test Names

```python
# GOOD: Describes the scenario and expected behavior
def test_raises_slot_not_available_when_slot_already_booked():
    ...

def test_calculates_total_price_including_equipment_rental():
    ...

def test_cannot_cancel_booking_outside_cancellation_window():
    ...

# BAD: Cryptic or generic names
def test_create():
    ...

def test_booking():
    ...

def test_error1():
    ...
```

### Arrange-Act-Assert Pattern

```python
def test_calculates_correct_total_for_one_hour_tennis_court():
    # ARRANGE: Set up the inputs and mocks
    pricing = PricingService()
    facility = Facility(type="tennis_court", hourly_rate=Decimal("40.00"))

    # ACT: Execute the behavior under test
    total = pricing.calculate_total(
        facility=facility,
        duration_minutes=60
    )

    # ASSERT: Verify the expected outcome
    assert total == Decimal("40.00")
```

---

## Pure Domain Tests: No I/O

### What to Test Without Mocks

Unit tests should exercise pure domain logic:

```python
# GOOD: Pure domain logic - no mocks needed
from booking.entity import Booking
from datetime import datetime, timedelta


class TestBooking:
    def test_booking_duration_calculated_correctly(self):
        booking = Booking(
            id="b1",
            start_time=datetime(2024, 1, 15, 10, 0),
            end_time=datetime(2024, 1, 15, 11, 0),
        )
        assert booking.duration_minutes == 60

    def test_booking_is_within_cancellation_window_when_not_expired(self):
        booking = Booking(
            id="b1",
            start_time=datetime.utcnow() + timedelta(hours=2),
            created_at=datetime.utcnow(),
        )
        # 2 hours from now - well within 24-hour window
        assert booking.is_within_cancellation_window(hours=24) is True

    def test_booking_is_outside_cancellation_window_when_expired(self):
        booking = Booking(
            id="b1",
            start_time=datetime.utcnow() + timedelta(hours=1),
            created_at=datetime.utcnow() - timedelta(hours=25),
        )
        # Created 25 hours ago, starts in 1 hour = 26 hours elapsed
        # Outside 24-hour window
        assert booking.is_within_cancellation_window(hours=24) is False
```

### What to Mock

External dependencies should be mocked:

```python
# GOOD: Mocking external dependencies
from unittest.mock import MagicMock


def test_booking_service_creates_booking_via_repository():
    # ARRANGE
    mock_repo = MagicMock()
    mock_repo.get_bookings_in_slot.return_value = []  # No conflicts
    mock_repo.create.return_value = Booking(id="b1", ...)

    service = BookingService(repository=mock_repo)

    # ACT
    result = service.create_booking(tenant_id="t1", request=...)

    # ASSERT
    assert result.id == "b1"
    mock_repo.create.assert_called_once()
```

---

## Parametrized Tests

### Use `@pytest.mark.parametrize`

```python
import pytest
from decimal import Decimal


@pytest.mark.parametrize(
    "facility_type,hourly_rate,duration,expected",
    [
        ("tennis_court", Decimal("40.00"), 60, Decimal("40.00")),
        ("tennis_court", Decimal("40.00"), 30, Decimal("20.00")),
        ("badminton_court", Decimal("25.00"), 60, Decimal("25.00")),
        ("badminton_court", Decimal("25.00"), 120, Decimal("50.00")),
        ("squash_court", Decimal("20.00"), 90, Decimal("30.00")),
    ],
)
def test_calculates_correct_price_for_facility_type(
    facility_type, hourly_rate, duration, expected
):
    pricing = PricingService()
    facility = Facility(type=facility_type, hourly_rate=hourly_rate)

    total = pricing.calculate_total(facility=facility, duration_minutes=duration)

    assert total == expected
```

> **Why** — Parametrization removes duplication, makes it easy to add cases, and clearly documents the input/output matrix.

### Parametrize Error Cases

```python
@pytest.mark.parametrize(
    "invalid_input,expected_error",
    [
        ({"duration_minutes": 0}, ValueError),
        ({"duration_minutes": -1}, ValueError),
        ({"duration_minutes": None}, ValueError),
        ({"facility_id": ""}, ValueError),
        ({"facility_id": None}, ValueError),
    ],
)
def test_raises_error_for_invalid_input(invalid_input, expected_error):
    with pytest.raises(expected_error):
        BookingRequest(**invalid_input)
```

---

## Using Faker for Fixtures

### Install and Configure

```bash
pip install pytest-faker
```

### Faker in Fixtures

```python
# conftest.py
import pytest
from faker import Faker


@pytest.fixture
def fake():
    return Faker()


@pytest.fixture
def fake_tenant(fake):
    return {
        "id": fake.uuid4(),
        "name": fake.company(),
        "slug": fake.slug(),
    }


@pytest.fixture
def fake_customer(fake, fake_tenant):
    return {
        "id": fake.uuid4(),
        "tenant_id": fake_tenant["id"],
        "email": fake.email(),
        "name": fake.name(),
        "phone": fake.phone_number(),
    }


@pytest.fixture
def fake_facility(fake, fake_tenant):
    return {
        "id": fake.uuid4(),
        "tenant_id": fake_tenant["id"],
        "name": f"{fake.word()} Court {fake.random_int(1, 10)}",
        "type": fake.random_element(["tennis_court", "badminton_court", "squash_court"]),
        "hourly_rate": fake.pydecimal(min_value=10, max_value=100, right_digits=2),
    }
```

### Use Faker in Tests

```python
def test_creates_booking_for_customer(fake_customer, fake_facility):
    service = BookingService(repository=Mock())

    booking = service.create_booking(
        tenant_id=fake_facility["tenant_id"],
        request=CreateBookingRequest(
            facility_id=fake_facility["id"],
            customer_id=fake_customer["id"],
            start_time=datetime(2024, 1, 15, 10, 0),
            duration_minutes=60,
        ),
    )

    assert booking.customer_id == fake_customer["id"]
    assert booking.facility_id == fake_facility["id"]
```

---

## Test Naming Conventions

### Method: `test_<subject>_<condition>_<expected>`

| Test Name | Subject | Condition | Expected |
|-----------|---------|-----------|----------|
| `test_booking_cancelled_before_start_time` | booking | cancelled before start | succeeds |
| `test_booking_cancelled_after_no_show_window` | booking | cancelled after no-show | raises error |
| `test_member_renewal_applies_discount` | member renewal | with discount tier | applies discount |

### Class-Based Organization

```python
class TestBookingCancellation:
    """Tests for booking cancellation behavior."""

    def test_cancels_booking_when_within_window(self):
        ...

    def test_refunds_full_amount_when_cancelled_24h_before(self):
        ...

    def test_refunds_partial_amount_when_cancelled_12h_before(self):
        ...

    def test_raises_error_when_cancelled_after_start_time(self):
        ...


class TestPricingCalculation:
    """Tests for pricing logic."""

    def test_applies_member_discount(self):
        ...

    def test_applies_peak_hour_surcharge(self):
        ...
```

---

## Fast Execution (<10ms)

### Measure Test Time

```python
import pytest
import time


def test_is_fast():
    start = time.perf_counter()
    # ... test code ...
    elapsed = time.perf_counter() - start
    assert elapsed < 0.01  # 10ms
```

### Common Speed Issues

| Issue | Solution |
|-------|----------|
| Real DB calls | Mock the repository |
| Slow object creation | Use smaller test objects |
| Complex setup | Extract to fixtures |
| File I/O | Mock `pathlib` / `open` |

---

## Assertions

### Use Plain `assert`

```python
# GOOD: Plain assert with descriptive message
assert booking.status == "confirmed", "New booking should be confirmed by default"

# BAD: Overly complex assertion libraries
assert_that(booking).has_status("confirmed")
```

### Common Assertions

```python
# Equality
assert actual == expected
assert actual != unexpected

# Truthiness
assert result is not None
assert is_valid is True

# Collections
assert len(bookings) == 3
assert "error" in result.messages
assert any(b.id == "b1" for b in bookings)

# Exceptions
with pytest.raises(BookingNotFoundError):
    service.get_booking("nonexistent")

# Type checking
assert isinstance(booking, Booking)
```

---

## Unit Test Checklist

- [ ] No database calls (use mocks)
- [ ] No HTTP calls (use mocks)
- [ ] No file system access
- [ ] Executes in <10ms
- [ ] One assertion per test (or closely related)
- [ ] Descriptive test name explains scenario
- [ ] Uses parametrization for variations
- [ ] Uses Faker for realistic test data
- [ ] Tests happy path AND error paths

---

## Anti-patterns

### 1. Testing with Real Database

```python
# BAD: Hitting real DB
def test_creates_booking(self):
    db = get_real_database()
    service = BookingService(db)  # Couples test to DB
    booking = service.create_booking(...)
    assert booking.id is not None
```

> **Anti-pattern** — Real DB calls are slow and create test interdependencies.

### 2. No Error Path Tests

```python
# BAD: Only happy path
def test_creates_booking(self):
    booking = service.create_booking(...)
    assert booking is not None
```

> **Anti-pattern** — Users encounter errors more often than success. Untested error paths fail in production.

### 3. Brittle Tests

```python
# BAD: Testing implementation details
def test_cache_is_populated(self):
    service.create_booking(...)
    assert len(service._cache) > 0  # Breaks on refactor
```

> **Anti-pattern** — Testing internals creates fragile tests that break on legitimate refactoring.

---

## CI Integration

```yaml
# .github/workflows/unit-tests.yml
- name: Unit Tests
  run: |
    pytest apps/backend/src/ \
      --ignore=apps/backend/src/booking/tests/integration \
      -v --tb=short -x \
      --durations=10 \
      --maxfail=5
```

> **Rule** — Unit tests must pass before any PR merge. Build fails if any unit test fails.

---

## Summary

| Principle | Rule |
|-----------|------|
| Speed | <10ms per test |
| Scope | One behavior per test |
| I/O | None — mock everything |
| Naming | Descriptive: `test_<what>_<when>_<expected>` |
| Data | Faker for realistic fixtures |
| Errors | Test happy path AND error paths |

See also: [TDD Handbook](tdd-handbook.md), [Integration Tests](integration-tests.md), [Mocking Strategy](mocking-strategy.md), [Test Data Management](test-data-management.md).
