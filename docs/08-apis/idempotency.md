# API Idempotency

> This document covers idempotency keys for POST requests to ensure safe retries.

## Overview

**Idempotency** ensures that making the same request multiple times produces the same result. This is critical for POST requests where network failures may cause automatic retries.

## When to Use

| Method | Idempotent | Needs Idempotency Key |
|--------|------------|----------------------|
| GET | Yes | No |
| POST | No | Yes (bookings, payments) |
| PUT | Yes | Optional |
| PATCH | Yes | Optional |
| DELETE | Yes | No |

## Idempotency Key Header

```
Idempotency-Key: abc123-def456-ghi789
```

## Implementation

### Required Endpoints

- POST `/v1/bookings`
- POST `/v1/payments`
- POST `/v1/memberships`

### Middleware

```python
# src/common/middleware.py
from fastapi import Request
from common.idempotency import IdempotencyService


class IdempotencyMiddleware:
    """Handle idempotency keys."""

    async def dispatch(self, request: Request, call_next):
        # Only for POST/PUT/PATCH
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        # Get or generate key
        key = request.headers.get("Idempotency-Key")
        if not key:
            key = str(uuid4())

        tenant_id = getattr(request.state, "tenant_id", None)

        if tenant_id:
            service = request.app.state.idempotency_service

            # Check for existing response
            cached = await service.get(key, tenant_id)
            if cached:
                return JSONResponse(
                    status_code=cached["status_code"],
                    content=cached["response"],
                    headers={"Idempotency-Key": key},
                )

        # Store key for later
        request.state.idempotency_key = key

        response = await call_next(request)

        # Cache successful responses
        if 200 <= response.status_code < 300 and tenant_id:
            # ... cache logic ...

        return response
```

## Validation

```python
# Validate key format
class IdempotencyKey:
    @field_validator("idempotency_key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Idempotency-Key is required for POST requests")

        if len(v) < 16:
            raise ValueError("Idempotency-Key must be at least 16 characters")

        return v
```

## Conflict Detection

If same key but different body:

```python
# Check for body hash mismatch
async def dispatch(self, request: Request, call_next):
    existing = await service.get(key, tenant_id)

    if existing:
        existing_hash = existing.get("body_hash")
        request_hash = hash(request.body)

        if existing_hash != request_hash:
            return JSONResponse(
                status_code=409,
                content={
                    "type": "https://api.splashh.com/errors/idempotency_conflict",
                    "title": "Conflict",
                    "status": 409,
                    "detail": "Request with same key but different body",
                },
            )
```

## Response Headers

```
Idempotency-Key: abc123-def456
X-Idempotent-Replayed: true  # If replayed cached response
```

## TTL

| Resource | TTL |
|----------|-----|
| Bookings | 24 hours |
| Payments | 7 days |
| Memberships | 24 hours |

## Client Usage

```python
import requests
import uuid

# Generate key
key = str(uuid.uuid4())

# First request
response = requests.post(
    "https://api.splashh.com/v1/bookings",
    json={...},
    headers={"Idempotency-Key": key},
)

# Safe to retry with same key on network error
if response.status_code == 0:  # Network error
    response = requests.post(
        "https://api.splashh.com/v1/bookings",
        json={...},
        headers={"Idempotency-Key": key},
    )
```

## Testing

```python
# tests/api/test_idempotency.py
def test_idempotent_request(client):
    """Duplicate requests return same response."""
    key = "test-key-12345678901234"

    r1 = client.post("/v1/bookings", json={...}, headers={"Idempotency-Key": key})
    r2 = client.post("/v1/bookings", json={...}, headers={"Idempotency-Key": key})

    assert r1.json() == r2.json()
    assert r2.headers.get("X-Idempotent-Replayed") == "true"


def test_different_body_conflict(client):
    """Same key, different body returns 409."""
    key = "test-key-12345678901234"

    client.post("/v1/bookings", json={"a": 1}, headers={"Idempotency-Key": key})
    r = client.post("/v1/bookings", json={"a": 2}, headers={"Idempotency-Key": key})

    assert r.status_code == 409
```

## Related Documents

- [Backend Idempotency](../04-backend/idempotency.md)
- [Event Idempotency](../07-events/idempotency.md)
