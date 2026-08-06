# Response Time Goals

> Per-endpoint SLOs. P50/P95/P99 targets. Hot path critical: P95 < 100ms. Admin: P95 < 500ms.

This document establishes response time targets for the Splashh Sports Platform. We define SLOs (Service Level Objectives) for different endpoint categories.

---

## SLO Targets by Tier

| Tier | Description | P50 | P95 | P99 |
|------|-------------|------|-----|-----|
| Critical | Booking, auth, payments | 50ms | 100ms | 200ms |
| High | Facility lookups, member data | 100ms | 200ms | 500ms |
| Standard | Lists, search | 200ms | 500ms | 1s |
| Admin | Reports, exports | 500ms | 2s | 5s |
| Background | Webhooks, async | N/A | 30s | 60s |

---

## Endpoint SLOs

### Critical Tier (P95 < 100ms)

```python
# Fast paths - must be highly optimized
CRITICAL_ENDPOINTS = [
    # Authentication
    "POST /api/v1/auth/login",
    "POST /api/v1/auth/refresh",
    "POST /api/v1/auth/logout",

    # Booking hot path
    "POST /api/v1/bookings",           # Create booking
    "GET /api/v1/bookings/{id}",       # Get booking
    "DELETE /api/v1/bookings/{id}",   # Cancel booking
    "GET /api/v1/bookings/available", # Check availability

    # Payments
    "POST /api/v1/payments/process",
]
```

### High Tier (P95 < 200ms)

```python
# Important but can be slightly slower
HIGH_ENDPOINTS = [
    # User data
    "GET /api/v1/members/me",
    "PUT /api/v1/members/me",

    # Facilities
    "GET /api/v1/facilities",
    "GET /api/v1/facilities/{id}",

    # Membership
    "GET /api/v1/memberships/current",
    "POST /api/v1/memberships/renew",
]
```

### Standard Tier (P95 < 500ms)

```python
# Standard CRUD operations
STANDARD_ENDPOINTS = [
    # Lists
    "GET /api/v1/bookings",
    "GET /api/v1/members",
    "GET /api/v1/facilities",

    # Search
    "GET /api/v1/search",
]
```

### Admin Tier (P95 < 2s)

```python
# Admin operations
ADMIN_ENDPOINTS = [
    # Reports
    "GET /api/v1/admin/reports/revenue",
    "GET /api/v1/admin/reports/usage",

    # Exports
    "GET /api/v1/admin/export/bookings",
    "GET /api/v1/admin/export/members",

    # Bulk operations
    "POST /api/v1/admin/members/bulk-import",
]
```

---

## Measuring SLOs

```python
# apps/backend/src/common/middleware/timing.py
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000

        # Log timing
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
        )

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response
```

---

## SLO Dashboard Queries

### Prometheus Metrics

```promql
# P50 latency
histogram_quantile(0.50,
  rate(http_request_duration_seconds_bucket[5m])
)

# P95 latency
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket[5m])
)

# P99 latency
histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket[5m])
)

# By endpoint
sum by (endpoint) (
  rate(http_request_duration_seconds_bucket[5m])
)
```

---

## Alerting

```yaml
# alerts.yml - Prometheus alerting rules
groups:
  - name: latency
    rules:
      - alert: HighP95Latency
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket{service="api"}[5m])
          ) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High P95 latency detected"

      - alert: CriticalP95Latency
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket{service="api", endpoint=~"/api/v1/bookings.*"}[5m])
          ) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Booking endpoint P95 latency above 100ms"
```

---

## Performance Budget by Endpoint

| Endpoint Category | Database Queries | External API Calls | Cache OK |
|------------------|-----------------|-------------------|----------|
| Critical | <= 2 | 0 | Required |
| High | <= 5 | <= 1 | Recommended |
| Standard | <= 10 | <= 2 | Optional |
| Admin | <= 20 | <= 3 | Optional |

---

## Trade-offs

| Target | What we gain | What we give up |
|--------|--------------|-----------------|
| 100ms P95 | Great UX | More optimization effort |
| 500ms P95 | Reasonable UX | Some complexity saved |
| 2s P95 | Simple backend | Slower admin experience |

---

## Related Documents

- [Observability](observability.md) — Metrics and alerting
- [Performance Budgets](performance-budgets.md) — CI performance checks
- [Database Optimization](database-optimization.md) — Query performance
