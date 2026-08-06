# Property-Based Testing

> Property-based testing verifies properties — statements about what must be true for all inputs — rather than specific examples. Hypothesis generates hundreds of inputs to find edge cases that manually-written tests miss.

This document covers our property-based testing strategy: Hypothesis for Python, Schemathesis for API fuzzing, property design, shrinking, and CI integration.

---

## What is Property-Based Testing

### Example: Traditional Test

```python
# Traditional: specific example
def test_booking_duration():
    booking = Booking(
        start_time=datetime(2024, 1, 15, 10, 0),
        end_time=datetime(2024, 1, 15, 11, 0),
    )
    assert booking.duration_minutes == 60
```

### Property-Based Test

```python
# Property: must hold for ALL inputs
from hypothesis import given, strategies as st


@given(
    start_time=st.datetimes(min_value=datetime(2020, 1, 1)),
    end_time=st.datetimes(min_value=datetime(2020, 1, 1)),
)
def test_duration_is_never_negative(start_time, end_time):
    """Duration property: end must be after start."""
    # Skip invalid inputs (end before start)
    if end_time <= start_time:
        return

    booking = Booking(start_time=start_time, end_time=end_time)
    assert booking.duration_minutes >= 0
```

---

## Hypothesis Setup

### Installation

```bash
pip install hypothesis
```

### Basic Usage

```python
from hypothesis import given, strategies as st


@given(st.integers(min_value=1, max_value=100))
def test_booking_duration_multiples_of_15(duration):
    """Booking duration should be in 15-minute increments."""
    # This will fail for durations not divisible by 15
    # and Hypothesis will shrink to find the smallest failing case
    assert duration % 15 == 0, f"Duration {duration} not in 15-min increments"


@given(st.lists(st.integers(min_value=1, max_value=100), min_size=1, max_size=10))
def test_total_price_never_exceeds_max(prices):
    """Total price for multiple bookings should not exceed maximum."""
    from booking.pricing import PricingService
    service = PricingService()

    total = sum(service.calculate_price(p) for p in prices)

    assert total <= 10000, f"Total {total} exceeds maximum"
```

---

## Schemathesis for API Fuzzing

### Installation

```bash
pip install schemathesis
```

### API Property Testing

```python
# tests/property/test_api_schema.py
import schemathesis
from hypothesis import settings


# Load OpenAPI spec
schema = schemathesis.from_path("apps/backend/src/openapi.yaml")


@schema.parametrize()
@settings(max_examples=100)
def test_api_conforms_to_schema(case):
    """Property: API responses always conform to OpenAPI schema."""
    response = case.call()

    # Schemathesis verifies response matches schema
    assert response.status_code < 500, f"Server error: {response.status_code}"
```

### Specific Endpoint Testing

```python
# Test booking endpoint specifically
@schema.parametrize(endpoint="/api/v1/bookings", method="POST")
@settings(max_examples=50)
def test_booking_endpoint_accepts_valid_input(case):
    """Property: Valid booking requests are accepted."""
    # Generate valid request
    case.body = {
        "facility_id": "court-001",
        "customer_id": "customer-001",
        "start_time": "2024-01-15T10:00:00Z",
        "duration_minutes": 60,
    }

    response = case.call()

    assert response.status_code in [200, 201, 400, 422], \
        f"Unexpected status: {response.status_code}"
```

---

## Property Design

### Properties for Booking Domain

```python
from hypothesis import given, settings


class TestBookingProperties:
    """Property-based tests for booking domain."""

    @given(
        start_time=st.datetimes(
            min_value=datetime(2024, 1, 1),
            max_value=datetime(2024, 12, 31),
        ),
        duration=st.integers(min_value=15, max_value=240),
    )
    @settings(max_examples=100)
    def test_end_time_calculated_correctly(self, start_time, duration):
        """Property: end_time = start_time + duration."""
        booking = Booking(start_time=start_time, duration_minutes=duration)

        expected_end = start_time + timedelta(minutes=duration)
        assert booking.end_time == expected_end

    @given(
        bookings=st.lists(
            st.builds(
                Booking,
                start_time=st.datetimes(min_value=datetime(2024, 1, 1)),
                duration_minutes=st.sampled_from([30, 60, 90, 120]),
            ),
            min_size=2,
            max_size=10,
        )
    )
    def test_no_double_booking(self, bookings):
        """Property: same facility/time cannot have two bookings."""
        # Filter to same facility
        facility_bookings = [b for b in bookings if b.facility_id == "court-001"]

        # Check for overlaps
        for i, b1 in enumerate(facility_bookings):
            for b2 in facility_bookings[i + 1:]:
                # If both confirmed and overlapping, that's a problem
                if b1.overlaps(b2):
                    # Property: at least one must not be confirmed
                    assert not (b1.is_confirmed and b2.is_confirmed)

    @given(
        amount=st.decimals(min_value=0, max_value=1000, places=2),
        discount=st.floats(min_value=0, max_value=1),
    )
    def test_discount_never_exceeds_100_percent(self, amount, discount):
        """Property: discount percentage is always between 0 and 1."""
        from booking.pricing import PricingService

        service = PricingService()
        discounted = service.apply_discount(amount, discount)

        # After discount, amount should never be negative
        assert discounted >= 0
        assert discounted <= amount
```

---

## Shrinking

Hypothesis automatically shrinks failing inputs to minimal examples:

```
Falsifying example: test_duration_is_never_negative(start_time=datetime(2020, 1, 1, 0, 0), end_time=datetime(2020, 1, 1, 0, 0))
```

Instead of failing on a complex datetime, Hypothesis finds the simplest failing case.

---

## CI Integration

### Running Property Tests

```bash
# Run with Hypothesis
pytest tests/property/ -v

# With coverage
pytest tests/property/ --cov=booking --cov-report=html
```

### CI Configuration

```yaml
# .github/workflows/property-tests.yml
- name: Property-Based Tests
  run: |
    pytest tests/property/ \
      --hypothesis-show-statistics \
      -v
```

### Statistics Output

```
stats:
  number of passing examples: 100
  number of failing examples: 0
  number of interesting rejected examples: 0
```

---

## Common Properties

| Property | Example |
|----------|---------|
| Idempotency | `f(f(x)) == f(x)` |
| Invariants | `x + y >= x` |
| Reversibility | `f_inverse(f(x)) == x` |
| Commutativity | `f(x, y) == f(y, x)` |
| Associativity | `f(f(x, y), z) == f(x, f(y, z))` |

---

## Property-Based Testing Checklist

- [ ] Core domain logic has property tests
- [ ] Edge cases covered (empty, null, negative)
- [ ] API fuzzing with Schemathesis
- [ ] CI includes property tests
- [ ] Failing examples are investigated

---

## Anti-patterns

### 1. Testing Trivial Properties

```python
# BAD: Property that's always true
@given(st.integers())
def test_integer_is_integer(x):
    assert isinstance(x, int)  # Always true
```

> **Anti-pattern** — Property must actually verify something meaningful.

### 2. No Shrinking

```python
# BAD: Disable shrinking, hiding the problem
@given(st.integers())
@settings(database=None)  # No shrinking
def test_no_shrinking(x):
    ...
```

> **Anti-pattern** — Shrinking helps find minimal failing cases.

### 3. Only Property Tests

> **Anti-pattern** — Property tests don't replace example-based tests. Use both.

---

## Summary

| Tool | Use Case |
|------|----------|
| Hypothesis | Python property testing |
| Schemathesis | API fuzzing from OpenAPI |
| pytest-hypothesis | Integration with pytest |

Property-based testing finds edge cases that manual testing misses. Use for critical domain logic and API contracts.

See also: [Unit Tests](unit-tests.md), [API Tests](api-tests.md), [Integration Tests](integration-tests.md).
