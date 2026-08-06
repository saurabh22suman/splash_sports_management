# Performance Tests

> Performance tests measure execution time and throughput at the function level. pytest-benchmark provides micro-benchmarking for individual functions; we track regressions in CI to prevent performance degradation over time.

This document covers our micro-benchmarking strategy: pytest-benchmark usage, tracking regressions, acceptable performance windows, and CI integration. These tests catch algorithmic complexity issues before they reach production.

---

## What is a Performance Test

A performance test:
- Measures **execution time** of a single function
- Runs **multiple iterations** to get statistical significance
- Tracks **regressions** across commits
- Is **deterministic** — same input = same output

> **Rule** — Every performance-critical function (pricing, scheduling, search) must have benchmarks.

---

## pytest-benchmark Setup

### Installation

```bash
pip install pytest-benchmark
```

### Configuration

```ini
# pytest.ini
[tool:pytest]
benchmark_only = false
benchmark_autosave = true
benchmark_json = benchmark.json
benchmark_json_pretty = true
```

---

## Basic Benchmark Tests

### Simple Function Benchmark

```python
# apps/backend/tests/performance/test_pricing.py
import pytest
from decimal import Decimal
from booking.pricing import PricingEngine


class TestPricingPerformance:
    """Benchmarks for pricing calculations."""

    def test_calculate_total_price(self, benchmark):
        """Benchmark: calculate total price for booking."""
        engine = PricingEngine()
        pricing_request = {
            "facility_type": "tennis_court",
            "duration_minutes": 60,
            "member_tier": "premium",
        }

        result = benchmark(engine.calculate_total, pricing_request)
        assert result["total"] == Decimal("45.00")

    def test_apply_discount(self, benchmark):
        """Benchmark: apply membership discount."""
        engine = PricingEngine()

        result = benchmark(
            engine.apply_discount,
            base_amount=Decimal("100.00"),
            member_tier="premium",
        )
        assert result == Decimal("80.00")

    def test_calculate_peak_surcharge(self, benchmark):
        """Benchmark: calculate peak hour surcharge."""
        engine = PricingEngine()

        result = benchmark(
            engine.calculate_peak_surcharge,
            hour=18,  # Peak hour
            day_type="weekday",
        )
        assert result == Decimal("10.00")
```

### Complex Algorithm Benchmark

```python
# apps/backend/tests/performance/test_scheduling.py
import pytest
from datetime import datetime, timedelta
from booking.scheduler import SlotScheduler


class TestSchedulerPerformance:
    """Benchmarks for slot scheduling algorithm."""

    def test_find_available_slots_one_day(self, benchmark):
        """Benchmark: find available slots for one day."""
        scheduler = SlotScheduler()
        facility_id = "court-001"
        date = datetime(2024, 1, 15)

        # 20 existing bookings scattered through the day
        existing_bookings = [
            {
                "start_time": datetime(2024, 1, 15, 9, 0),
                "duration_minutes": 60,
            },
            {
                "start_time": datetime(2024, 1, 15, 11, 0),
                "duration_minutes": 60,
            },
            # ... more bookings
        ]

        result = benchmark(
            scheduler.find_available_slots,
            facility_id=facility_id,
            date=date,
            duration_minutes=60,
            existing_bookings=existing_bookings,
        )

        assert len(result) > 0

    def test_find_available_slots_one_week(self, benchmark):
        """Benchmark: find available slots for entire week."""
        scheduler = SlotScheduler()

        result = benchmark(
            scheduler.find_available_slots,
            facility_id="court-001",
            start_date=datetime(2024, 1, 15),
            end_date=datetime(2024, 1, 22),
            duration_minutes=60,
        )

        assert len(result) > 0
```

---

## Benchmark with Fixtures

```python
# apps/backend/tests/performance/conftest.py
import pytest
from faker import Faker


@pytest.fixture
def sample_bookings():
    """Generate sample bookings for benchmarking."""
    fake = Faker()
    Faker.seed(12345)

    bookings = []
    for i in range(100):
        bookings.append({
            "id": fake.uuid4(),
            "start_time": fake.date_time_between(
                start_date="2024-01-01",
                end_date="2024-12-31",
            ),
            "duration_minutes": fake.random_int(30, 120),
            "facility_id": fake.random_element(["court-001", "court-002", "court-003"]),
        })
    return bookings


@pytest.fixture
def large_booking_list(sample_bookings):
    """Generate 1000 bookings for stress testing."""
    fake = Faker()
    Faker.seed(12345)

    bookings = []
    for i in range(1000):
        bookings.append({
            "id": fake.uuid4(),
            "start_time": fake.date_time_between(
                start_date="2024-01-01",
                end_date="2024-12-31",
            ),
            "duration_minutes": fake.random_int(30, 120),
            "facility_id": f"court-{fake.random_int(1, 10)}",
        })
    return bookings


# Use in benchmarks
def test_search_bookings_by_facility(self, benchmark, large_booking_list):
    """Benchmark: search through 1000 bookings."""
    from booking.repository import BookingRepository

    repo = BookingRepository(session=mock_session)

    result = benchmark(
        repo.search,
        bookings=large_booking_list,
        facility_id="court-005",
    )

    assert len(result) > 0
```

---

## Tracking Regressions

### Performance Regression Test

```python
# apps/backend/tests/performance/test_regression.py
import pytest


class TestPerformanceRegression:
    """Track performance regressions over time."""

    def test_booking_creation_performance(self, benchmark):
        """Regression: booking creation should not exceed 50ms."""
        from booking.service import BookingService
        from unittest.mock import MagicMock

        service = BookingService(repository=MagicMock())

        result = benchmark(service.create_booking, "tenant-001", {...})

        # Assert performance target
        assert result.stats.mean < 0.050  # 50ms

    def test_pricing_calculation_performance(self, benchmark):
        """Regression: pricing should not exceed 10ms."""
        from booking.pricing import PricingEngine

        engine = PricingEngine()

        result = benchmark(engine.calculate_total, {...})

        assert result.stats.mean < 0.010  # 10ms
```

### CI Performance Gate

```yaml
# .github/workflows/performance.yml
- name: Performance Tests
  run: |
    pytest apps/backend/tests/performance/ \
      --benchmark-json=benchmark.json \
      --benchmark-compare \
      --benchmark-fail=min:100ms \
      -v

- name: Compare Benchmark
  uses: benchmark-action/github-action-benchmark@v1
  with:
    tool: 'pytest'
    input-file: 'benchmark.json'
    output-file: 'benchmark.md'
    alert-threshold: '150%'
    comment-alerts: true
```

---

## Performance Targets

### Target Table

| Component | Target | Max Acceptable |
|-----------|--------|----------------|
| Pricing calculation | <10ms | 20ms |
| Slot availability check | <50ms | 100ms |
| Booking creation | <100ms | 200ms |
| List bookings (100 items) | <200ms | 500ms |
| Search bookings | <500ms | 1000ms |
| Auth token validation | <5ms | 10ms |

---

## Profiling Integration

### cProfile Integration

```python
import pytest
import cProfile
import pstats
from io import StringIO


def test_profile_pricing_calculation():
    """Profile: identify hotspots in pricing."""
    profiler = cProfile.Profile()
    profiler.enable()

    # Run the function
    engine = PricingEngine()
    for _ in range(1000):
        engine.calculate_total({...})

    profiler.disable()

    # Analyze results
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)

    output = s.getvalue()
    assert "calculate_total" in output
```

### Memory Profiling

```python
# Test memory usage
import tracemalloc


def test_memory_usage():
    """Profile: track memory allocation in booking creation."""
    tracemalloc.start()

    engine = PricingEngine()
    for _ in range(1000):
        engine.calculate_total({...})

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Assert memory is reasonable
    assert peak < 100 * 1024 * 1024  # 100MB
```

---

## Anti-patterns

### 1. Unreliable Benchmarks

```python
# BAD: Benchmark affected by I/O or network
def test_slow_benchmark(self, benchmark):
    result = benchmark(requests.get, "http://slow-api.com")  # Unstable
```

> **Anti-pattern** — Benchmarks must be deterministic. External I/O introduces noise.

### 2. Ignoring Warm-up

```python
# BAD: Not accounting for warm-up
def test_benchmark_without_warmup(self, benchmark):
    # First call is always slower due to JIT/imports
    result = benchmark(slow_function)  # Skewed results
```

> **Anti-pattern** — pytest-benchmark handles warm-up, but always verify results stabilize.

### 3. No Regression Tracking

> **Anti-pattern** — Running benchmarks without storing results means regressions go unnoticed.

---

## CI Integration

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 0 * * *'  # Daily baseline

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install pytest pytest-benchmark

      - name: Save baseline
        if: github.event_name == 'schedule'
        run: |
          pytest apps/backend/tests/performance/ \
            --benchmark-save=baseline

      - name: Compare with baseline
        if: github.event_name == 'push'
        run: |
          pytest apps/backend/tests/performance/ \
            --benchmark-compare=baseline \
            --benchmark-fail=min:150% \
            -v

      - name: Store benchmark data
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-data
          path: benchmark.json
```

---

## Summary

| Aspect | Rule |
|--------|------|
| Tool | pytest-benchmark |
| Run frequency | Every commit + daily baseline |
| Regression threshold | 150% of baseline |
| CI gate | Fail if >150% of baseline |
| Storage | Store historical benchmarks |

See also: [Load Tests](load-tests.md), [Performance Optimization](../11-performance/overview.md).
