# Mutation Testing

> Mutation testing verifies test quality by introducing small changes (mutations) to the code and checking if tests catch them. A test suite with low mutation coverage has weak tests — they pass regardless of whether the code is correct.

This document covers our mutation testing strategy: mutmut usage, targeting domain code, achieving >70% mutation score, and CI integration. These tests ensure our tests actually verify behavior, not just execute code.

---

## What is Mutation Testing

Mutation testing works by:
1. **Mutating** — Changing code slightly (swap `+` to `-`, `==` to `!=`, etc.)
2. **Running tests** — If tests still pass, mutation survived
3. **Scoring** — Mutation score = caught mutations / total mutations

> **Rule** — Domain code must achieve >70% mutation score.

---

## mutmut Setup

### Installation

```bash
pip install mutmut
```

### Configuration

```toml
# pyproject.toml
[tool.mutmut]
runner = "pytest"
```

---

## Running Mutation Tests

### Basic Execution

```bash
# Run mutation testing on booking module
mutmut run --source=apps/backend/src/booking --tests=apps/backend/tests/unit/booking

# Show results
mutmut show

# Show specific mutation
mutmut show 42
```

### With Coverage

```bash
# Run only on code covered by tests
mutmut run --source=apps/backend/src/booking \
  --tests=apps/backend/tests/unit/booking \
  --coverage-data=coverage.json
```

---

## Interpreting Results

### Mutation Types

| Mutation | Original | Mutated | Detected By |
|----------|----------|---------|-------------|
| Number change | `x == 5` | `x == 6` | Test asserts specific value |
| Boolean flip | `if x > 0:` | `if x <= 0:` | Test checks sign |
| Arithmetic | `a + b` | `a - b` | Test checks calculation |
| Comparison | `x == y` | `x != y` | Test checks equality |
| Return value | `return True` | `return False` | Test checks return value |

### Scoring

```text
Mutation testing results:
- 150 mutations tested
- 115 mutations killed (76.7%)
- 35 mutations survived (23.3%)
- 5 timeouts

Mutation score: 76.7% (target: >70%)
```

---

## CI Integration

### GitHub Actions

```yaml
# .github/workflows/mutation-tests.yml
- name: Mutation Tests
  run: |
    # Run mutation tests on domain code
    mutmut run \
      --source=apps/backend/src/booking \
      --tests=apps/backend/tests/unit/ \
      --pytest-args="-v --tb=short"

    # Fail if below threshold
    mutmut check --minimum=70 || exit 1

- name: Upload Mutation Results
  uses: actions/upload-artifact@v4
  with:
    name: mutation-results
    path: .mutmut/
```

---

## What to Mutate

### Target: Domain Code

```python
# apps/backend/src/booking/domain/booking.py
# MUTATE THIS - business logic
class Booking:
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time

    @property
    def duration_minutes(self):
        # Business logic - mutate this
        return (self.end_time - self.start_time).total_seconds() / 60

    def is_within_cancellation_window(self, hours=24):
        # Business logic - mutate this
        return (self.start_time - datetime.utcnow()).total_seconds() / 3600 < hours
```

### Not Target: Infrastructure

```python
# DON'T MUTATE - infrastructure
class BookingRepository:
    def get_by_id(self, id):
        return self.session.query(Booking).filter_by(id=id).first()  # Don't mutate

    def save(self, booking):
        self.session.add(booking)  # Don't mutate
        self.session.commit()  # Don't mutate
```

---

## Example: Booking Domain

```python
# apps/backend/tests/unit/domain/test_booking_mutations.py
import pytest
from datetime import datetime, timedelta


class TestBookingDomainMutations:
    """Tests that catch mutations in booking domain logic."""

    def test_duration_calculation(self):
        """Mutation: changing duration calculation should fail."""
        booking = Booking(
            start_time=datetime(2024, 1, 15, 10, 0),
            end_time=datetime(2024, 1, 15, 11, 0),
        )
        assert booking.duration_minutes == 60

    def test_duration_zero_for_same_time(self):
        """Mutation: changing to return wrong value should fail."""
        booking = Booking(
            start_time=datetime(2024, 1, 15, 10, 0),
            end_time=datetime(2024, 1, 15, 10, 0),
        )
        assert booking.duration_minutes == 0

    def test_cancellation_window_true_for_future(self):
        """Mutation: flipping comparison should fail."""
        booking = Booking(
            start_time=datetime.utcnow() + timedelta(hours=2),
        )
        assert booking.is_within_cancellation_window(hours=24) is True

    def test_cancellation_window_false_for_past(self):
        """Mutation: flipping comparison should fail."""
        booking = Booking(
            start_time=datetime.utcnow() - timedelta(hours=1),
        )
        assert booking.is_within_cancellation_window(hours=24) is False
```

---

## Achieving >70% Score

### Strategy

1. **Test assertions, not just calls** — Don't just call functions; assert on results
2. **Test edge cases** — Zero, negative, null, boundary values
3. **Test error paths** — Verify exceptions are raised
4. **Use specific assertions** — Don't use generic checks

### Good vs. Bad

```python
# BAD: Doesn't catch mutations
def test_booking_created():
    service.create_booking(...)
    # No assertion - doesn't catch anything

# GOOD: Catches mutations
def test_booking_created_with_correct_status():
    booking = service.create_booking(...)
    assert booking.status == "confirmed"  # Catches status mutation

# GOOD: Catches calculation mutations
def test_duration_is_60_minutes():
    booking = Booking(start=t1, end=t2)
    assert booking.duration_minutes == 60  # Catches arithmetic mutation
```

---

## Common Issues

### Slow Tests

```bash
# Too slow - don't mutate entire codebase
mutmut run --source=apps/backend/src

# Fast - target specific domain
mutmut run --source=apps/backend/src/booking/domain
```

### Unstable Mutations

```python
# Mutation testing can be flaky with:
# - Timing-dependent code
# - Random number generation
# - External API calls

# Solution: Make code deterministic or skip mutations
@pytest.mark.skip_mutations
def test_current_time_booking():
    ...
```

---

## Mutation Testing Checklist

- [ ] Domain code targeted
- [ ] >70% mutation score achieved
- [ ] CI fails below threshold
- [ ] Tests assert specific values
- [ ] Edge cases covered

---

## Anti-patterns

### 1. Testing Without Assertions

```python
# BAD: No assertions - mutations survive
def test_booking():
    service.create_booking(...)
    # No assertion = mutation not caught
```

> **Anti-pattern** — Tests without assertions don't verify behavior.

### 2. Too Generic Assertions

```python
# BAD: Too generic - mutations survive
def test_booking():
    result = service.create_booking(...)
    assert result  # Just checks not None
```

> **Anti-pattern** — Weak assertions let mutations pass.

### 3. Mutating Infrastructure

```python
# BAD: Mutating DB queries
def test_mutation(self):
    # Changing this doesn't test business logic
    assert session.query(Booking).first()
```

> **Anti-pattern** — Mutations in infrastructure code don't indicate test quality.

---

## Summary

| Aspect | Rule |
|--------|------|
| Tool | mutmut |
| Target | Domain code only |
| Threshold | >70% mutation score |
| CI gate | Fail below threshold |
| Assertion | Specific, not generic |

See also: [Coverage Strategy](coverage-strategy.md), [Unit Tests](unit-tests.md).
