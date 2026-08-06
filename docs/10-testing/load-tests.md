# Load Tests

> Load tests verify system behavior under concurrent load. Locust simulates realistic user behavior — booking searches, facility views, checkouts — at scale to identify bottlenecks before production traffic reveals them.

This document covers our load testing strategy: Locust scenarios, realistic user mix, booking load test (1000 concurrent users), stepped load patterns, soak tests, and reporting. These tests validate that the system meets performance SLAs under production-like load.

---

## What is a Load Test

A load test simulates:
- **Concurrent users** — Multiple users making requests simultaneously
- **Realistic behavior** — User flows, not just random URLs
- **Sustained load** — Minutes to hours of continuous traffic
- **Gradual ramp-up** — Stepped increase to identify scaling issues

> **Rule** — Load tests run before every major release and weekly in CI.

---

## Locust Setup

### Installation

```bash
pip install locust
```

### Basic Locustfile

```python
# apps/backend/tests/load/locustfile.py
from locust import HttpUser, task, between, events
import random


class BookingUser(HttpUser):
    """Simulates a customer booking sports facilities."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when user starts. Login once per user."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": f"user{random.randint(1, 1000)}@example.com",
                "password": "password123",
            },
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(3)
    def view_facilities(self):
        """Most common: browse facilities."""
        self.client.get(
            "/api/v1/facilities",
            headers=self.headers,
            name="/api/v1/facilities",
        )

    @task(2)
    def search_available_slots(self):
        """Second most common: check availability."""
        self.client.get(
            "/api/v1/facilities/court-001/availability?date=2024-01-15",
            headers=self.headers,
            name="/api/v1/facilities/[id]/availability",
        )

    @task(1)
    def create_booking(self):
        """Less common: actually book."""
        self.client.post(
            "/api/v1/bookings",
            json={
                "facility_id": f"court-{random.randint(1, 10)}",
                "customer_id": "customer-001",
                "start_time": "2024-01-15T10:00:00Z",
                "duration_minutes": 60,
            },
            headers=self.headers,
            name="/api/v1/bookings [POST]",
        )

    @task(1)
    def view_my_bookings(self):
        """Check existing bookings."""
        self.client.get(
            "/api/v1/bookings",
            headers=self.headers,
            name="/api/v1/bookings [GET]",
        )
```

---

## Realistic User Mix

### Weighted Task Distribution

```python
class RealisticUser(HttpUser):
    """User mix based on production analytics."""

    wait_time = between(2, 5)

    # Weighted by production traffic analysis
    @task(40)  # 40% - browsing
    def browse_facilities(self):
        self.client.get("/api/v1/facilities")

    @task(30)  # 30% - availability checks
    def check_availability(self):
        facility_id = random.choice(["court-001", "court-002", "court-003"])
        self.client.get(f"/api/v1/facilities/{facility_id}/availability")

    @task(15)  # 15% - viewing bookings
    def view_bookings(self):
        self.client.get("/api/v1/bookings")

    @task(10)  # 10% - making bookings
    def create_booking(self):
        self.client.post(
            "/api/v1/bookings",
            json={...},
        )

    @task(5)  # 5% - payments
    def process_payment(self):
        self.client.post("/api/v1/payments", json={...})
```

### Multi-Tenant Simulation

```python
class MultiTenantUser(HttpUser):
    """Simulate multiple tenants."""

    def on_start(self):
        # Random tenant selection
        self.tenant_id = random.choice([
            "tenant-splashh",
            "tenant-tennis-club",
            "tenant-gym",
            "tenant-community",
        ])
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Tenant-ID": self.tenant_id,
        }

    @task
    def tenant_isolated_request(self):
        self.client.get(
            f"/api/v1/facilities?tenant_id={self.tenant_id}",
            headers=self.headers,
        )
```

---

## Booking Load Test: 1000 Concurrent Users

### Test Scenario

```python
# apps/backend/tests/load/test_booking_load.py
from locust import HttpUser, task, between, constant, events
import random


class BookingLoadTest(HttpUser):
    """1000 concurrent users booking scenario."""

    wait_time = constant(1)  # High intensity

    def on_start(self):
        """Initialize user session."""
        # Login
        self.client.post("/api/v1/auth/login", json={
            "email": "loadtest@example.com",
            "password": "test123",
        })

    @task(10)
    def concurrent_booking_scenario(self):
        """Simulate concurrent booking attempts."""
        # 1. Check availability
        facility_id = random.choice(["court-001", "court-002", "court-003"])
        times = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
        time = random.choice(times)

        availability = self.client.get(
            f"/api/v1/facilities/{facility_id}/availability?date=2024-01-15"
        )

        # 2. If available, try to book
        if availability.status_code == 200:
            self.client.post(
                "/api/v1/bookings",
                json={
                    "facility_id": facility_id,
                    "customer_id": f"customer-{random.randint(1, 100)}",
                    "start_time": f"2024-01-15T{time}:00Z",
                    "duration_minutes": 60,
                },
            )

    @task(5)
    def read_operations(self):
        """Read-heavy workload."""
        self.client.get("/api/v1/facilities")
        self.client.get("/api/v1/bookings")
```

### Running the Load Test

```bash
# Run with 1000 users
locust -f apps/backend/tests/load/test_booking_load.py \
  --host=http://localhost:8000 \
  --users=1000 \
  --spawn-rate=50 \
  --run-time=10m \
  --headless \
  --html=report.html

# Web UI for interactive testing
locust -f apps/backend/tests/load/test_booking_load.py --host=http://localhost:8000
```

---

## Stepped Load Test

### Ramping Pattern

```python
# apps/backend/tests/load/stepped_load.py
from locust import HttpUser, task, between, constant_throughput
import time


class SteppedLoadUser(HttpUser):
    """Stepped load: ramp up over time."""

    wait_time = constant_throughput(1)  # 1 request per second per user

    @task
    def make_request(self):
        self.client.get("/api/v1/facilities")


# Run stepped load via CLI
# locust supports stepped load via --step-load and --step-users
```

```bash
# Stepped load: 100 -> 500 -> 1000 -> 500 -> 100 users
locust -f stepped_load.py \
  --host=http://localhost:8000 \
  --users=1000 \
  --spawn-rate=10 \
  --run-time=30m \
  --step-load \
  --step-users=100 \
  --step-time=5m
```

---

## Soak Test

### Extended Duration Test

```python
# apps/backend/tests/load/soak_test.py
from locust import HttpUser, task, between
import time


class SoakTest(HttpUser):
    """8-hour soak test to detect memory leaks."""

    wait_time = between(2, 5)

    @task
    def sustained_operations(self):
        # Mix of operations over 8 hours
        ops = [
            lambda: self.client.get("/api/v1/facilities"),
            lambda: self.client.get("/api/v1/bookings"),
            lambda: self.client.post("/api/v1/bookings", json={...}),
        ]

        import random
        random.choice(ops)()
```

```bash
# Run for 8 hours
locust -f soak_test.py \
  --host=http://localhost:8000 \
  --users=200 \
  --run-time=8h \
  --headless
```

---

## Test Data Setup

### Pre-populate Test Data

```python
# apps/backend/tests/load/test_data_setup.py
def setup_test_data():
    """Populate DB before load test."""
    import requests

    base_url = "http://localhost:8000"

    # Create facilities
    for i in range(20):
        requests.post(
            f"{base_url}/api/v1/facilities",
            json={
                "name": f"Court {i+1}",
                "type": "tennis_court",
                "hourly_rate": 40.00,
            },
        )

    # Create customers
    for i in range(1000):
        requests.post(
            f"{base_url}/api/v1/customers",
            json={
                "email": f"loadtest-{i}@example.com",
                "name": f"Load Test User {i}",
            },
        )

    # Pre-create some bookings
    for i in range(100):
        requests.post(
            f"{base_url}/api/v1/bookings",
            json={...},
        )


if __name__ == "__main__":
    setup_test_data()
```

---

## Reporting

### Metrics to Capture

| Metric | Target | Critical |
|--------|--------|----------|
| RPS (requests/second) | >500 | >1000 |
| Response time P50 | <100ms | <200ms |
| Response time P95 | <500ms | <1000ms |
| Response time P99 | <1s | <2s |
| Error rate | <0.1% | <1% |
| CPU usage | <70% | <85% |
| Memory usage | <80% | <90% |

### CI Load Test Result

```yaml
# .github/workflows/load-tests.yml
- name: Load Tests
  run: |
    locust -f apps/backend/tests/load/locustfile.py \
      --host=${{ secrets.STAGING_URL }} \
      --users=500 \
      --spawn-rate=20 \
      --run-time=5m \
      --headless \
      --html=load-report.html \
      --json

    # Assert SLAs
    python -c "
    import json
    with open('stats.json') as f:
        data = json.load(f)
    stats = data['stats']
    p99 = next(s for s in stats if s['name']=='Total')['response_time_percentile_99']
    if p99 > 1000:
        raise Exception(f'P99 response time {p99}ms exceeds 1000ms threshold')
    "
```

---

## Load Test Checklist

- [ ] Test data pre-populated
- [ ] Realistic user behavior modeled
- [ ] Multi-tenant isolation verified
- [ ] Stepped load tested
- [ ] Soak test (8h) passes
- [ ] Error rates <0.1%
- [ ] P95 <500ms
- [ ] P99 <1000ms

---

## Anti-patterns

### 1. Testing with Unrealistic Data

```python
# BAD: Always hitting same endpoint
@task
def always_same(self):
    self.client.get("/api/v1/facilities/1")  # Cached, unrealistic
```

> **Anti-pattern** — Load tests should reflect production traffic patterns, not synthetic hotspots.

### 2. No Warm-up Period

> **Anti-pattern** — Starting at full load immediately causes false failures. Ramp up gradually.

### 3. Ignoring Error Rates

> **Anti-pattern** — "It's slow but it works." Errors matter. 0.1% errors at 1000 RPS = 1 error per second.

---

## Summary

| Aspect | Rule |
|--------|------|
| Tool | Locust |
| Users | 1000 concurrent for booking tests |
| Duration | 10min normal, 8h soak |
| Ramp | 50 users/second |
| P95 target | <500ms |
| Error rate | <0.1% |

See also: [Performance Tests](performance-tests.md), [Load Testing](overview.md).
