# Versioning

> This document covers API versioning strategies, data model versioning, and deprecation policies.

## Overview

We version both the **API** (for client compatibility) and **data models** (for internal evolution). API versioning uses URL prefix strategy; data model versioning follows additive principles.

## API Versioning

### URL Prefix Strategy

> **Rule** — Use URL path versioning (`/v1/`, `/v2/`).

```python
# src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Splashh Sports API",
    version="1.0.0",
)

# Register v1 routers
from booking.v1.router import router as booking_router_v1
from booking.v2.router import router as booking_router_v2

app.include_router(booking_router_v1, prefix="/v1")
app.include_router(booking_router_v2, prefix="/v2")
```

### Version Discovery

```python
# src/booking/v1/router.py
from fastapi import APIRouter

router = APIRouter(tags=["Bookings v1"])


@router.get("/bookings")
async def list_bookings():
    """List bookings - v1 implementation."""
    return [...]
```

### Version Negotiation (Optional)

```python
# Accept header versioning (not preferred)
from fastapi import Header


@router.get("/bookings")
async def list_bookings(
    accept_version: str = Header("v1", alias="Accept-Version"),
):
    if accept_version == "v2":
        return list_bookings_v2()
    return list_bookings_v1()
```

> **Guideline** — URL prefix is preferred over header versioning for simplicity and visibility.

## Data Model Versioning

### Additive Only

> **Rule** — Data model changes must be additive. Never remove or rename fields in a breaking way.

| Change Type | Allowed | Example |
|-------------|---------|---------|
| Add field | Yes | Add `notes` to Booking |
| Add optional field | Yes | Add `metadata` (nullable) |
| Add new enum value | Yes | Add `NO_SHOW` status |
| Deprecate field | Yes | Mark `old_field` as deprecated |
| Remove field | No | - |
| Rename field | No | - |
| Change type | No | - |

### Deprecation

```python
# src/booking/domain/entities.py
from pydantic import Field
from typing import Optional, Deprecated


class Booking:
    # Deprecated field - still works but shows warning
    old_facility_ref: Optional[str] = Field(
        None,
        deprecated=True,
        description="Use facility_id instead",
    )

    # New field
    facility_id: UUID
```

### Response Versioning

```python
# src/booking/interfaces/schemas.py
from pydantic import BaseModel, Field
from datetime import datetime


class BookingOutV1(BaseModel):
    """v1 booking output - no facility details."""
    id: UUID
    facility_id: UUID
    status: str


class BookingOutV2(BaseModel):
    """v2 booking output - includes facility details."""
    id: UUID
    facility_id: UUID
    facility_name: str  # NEW in v2
    facility_type: str  # NEW in v2
    status: str
    metadata: Optional[dict] = None  # NEW in v2
```

## Deprecation Policy

### Timeline

| Phase | Duration | Behavior |
|-------|----------|----------|
| Active | - | Full support |
| Deprecated | 6 months | Works, shows warning in docs |
| Sunset | After 6 months | Returns 410 Gone |
| Removed | After 12 months | Endpoint deleted |

### Sunset Header

```python
# src/common/responses.py
from datetime import datetime, timedelta
from fastapi import Response


def add_deprecation_headers(response: Response, sunset_date: datetime):
    """Add deprecation and sunset headers."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = sunset_date.isoformat()
    response.headers["Link"] = f'<{new_version_url}>; rel="successor-version"'
```

### Sunset Endpoint

```python
# src/booking/v1/router.py
from datetime import datetime, timedelta

SUNSET_DATE = datetime(2024, 7, 1)


@router.get("/bookings", deprecated=True)
async def list_bookings_deprecated():
    """DEPRECATED: Use /v2/bookings instead."""
    # Return 410 for deprecated endpoints
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=410,
        content={
            "type": "https://api.splashh.com/errors/endpoint_gone",
            "title": "Endpoint Deprecated",
            "detail": "This endpoint has been deprecated. Use /v2/bookings instead.",
            "sunset": SUNSET_DATE.isoformat(),
        },
        headers={
            "Deprecation": "true",
            "Sunset": SUNSET_DATE.isoformat(),
            "Link": "<https://api.splashh.com/v2/bookings>; rel=\"successor-version\"",
        },
    )
```

## Versioning Strategy

### When to Bump Version

| Trigger | Version Bump |
|---------|---------------|
| Remove endpoint | Major (v1 -> v2) |
| Remove required field | Major |
| Change field type | Major |
| Add endpoint | Minor (v1.0 -> v1.1) |
| Add optional field | Minor |
| Add enum value | Minor |

### Migration Guide

For major version bumps, provide migration documentation:

```markdown
## v1 to v2 Migration Guide

### Changes
1. `GET /bookings` now returns `facility_name` and `facility_type`
2. New field `metadata` added to responses

### Client Actions
1. Update clients to handle new fields (backward compatible)
2. Use `/v2/bookings` for new features
3. v1 will be supported until July 2024
```

## Testing Versions

```python
# tests/api/test_versioning.py
import pytest
from fastapi.testclient import TestClient


def test_v1_endpoint(client: TestClient):
    response = client.get("/v1/bookings")
    assert response.status_code == 200


def test_v2_endpoint(client: TestClient):
    response = client.get("/v2/bookings")
    assert response.status_code == 200


def test_deprecated_endpoint_returns_410(client: TestClient):
    response = client.get("/v1/bookings/deprecated")
    assert response.status_code == 410
    assert "Sunset" in response.headers
```

## Related Documents

- [API Versioning](../08-apis/versioning.md)
- [OpenAPI](openapi.md)
- [REST Design](../08-apis/rest-design.md)
