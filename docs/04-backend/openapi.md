# OpenAPI

> This document covers OpenAPI generation from FastAPI, custom metadata, client codegen, and documentation.

## Overview

We use **FastAPI's built-in OpenAPI support** as the single source of truth for our API contract. OpenAPI drives documentation, client SDKs, and API testing.

## OpenAPI Configuration

```python
# src/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


app = FastAPI(
    title="Splashh Sports API",
    description="Sports club management platform API",
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "api@splashh.com",
    },
    license_info={
        "name": "Proprietary",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


def custom_openapi():
    """Custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add custom info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://splashh.com/logo.png"
    }

    # Add servers
    openapi_schema["servers"] = [
        {
            "url": "https://api.splashh.com/v1",
            "description": "Production server",
        },
        {
            "url": "https://staging-api.splashh.com/v1",
            "description": "Staging server",
        },
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
```

## Custom Schema Metadata

### Tags

```python
# src/booking/interfaces/router.py
from fastapi import APIRouter

router = APIRouter(tags=["Bookings"])


@router.get("/bookings", tags=["Bookings", "Read"])
@router.post("/bookings", tags=["Bookings", "Write"])
```

### Operation IDs

```python
@router.get(
    "/bookings/{booking_id}",
    operation_id="getBooking",
)
async def get_booking(booking_id: UUID):
    ...
```

### Descriptions

```python
@router.post(
    "/bookings",
    summary="Create a booking",
    description="""
Create a new booking for a facility time slot.

## Permissions
- `booking:write` - Create bookings
- `booking:read` - View bookings

## Rate Limiting
This endpoint is rate limited to 100 requests per minute.

## Idempotency
Use the `Idempotency-Key` header for safe retries.
    """,
)
async def create_booking(...):
    ...
```

## Request/Response Examples

```python
# src/booking/interfaces/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    facility_id: UUID
    date: str = Field(..., examples=["2024-01-15"])
    start_time: str = Field(..., examples=["10:00"])
    end_time: str = Field(..., examples=["11:00"])
    status: str = Field(..., examples=["confirmed"])
    version: int = Field(..., examples=[1])
    created_at: str = Field(..., examples=["2024-01-10T10:30:00Z"])


# In router
@router.get(
    "/bookings/{booking_id}",
    response_model=BookingOut,
    responses={
        404: {
            "description": "Booking not found",
            "content": {
                "application/json": {
                    "example": {
                        "type": "https://api.splashh.com/errors/not_found",
                        "title": "NotFoundError",
                        "status": 404,
                        "detail": "Booking with ID abc-123 not found"
                    }
                }
            }
        }
    }
)
```

## Documentation UI

### Swagger UI

```
GET /docs
```

### ReDoc

```
GET /redoc
```

## Client Codegen

### TypeScript

```bash
# Install generator
npm install @openapitools/openapi-typescript-codegen

# Generate client
openapi-typescript-codegen \
  --input https://api.splashh.com/openapi.json \
  --output ./packages/api-client \
  --name SplashhClient
```

### Python

```bash
# Install generator
pip install openapi-python-client

# Generate client
openapi-python-client generate \
  --url https://api.splashh.com/openapi.json \
  --path ./clients/python
```

## OpenAPI Validation in CI

```yaml
# .github/workflows/validate-openapi.yml
- name: Validate OpenAPI Schema
  run: |
    # Check schema is valid JSON
    python -c "import json; json.load(open('openapi.json'))"

    # Validate with spectral (optional)
    npx @stoplight/spectral lint openapi.json \
      --ruleset .spectral.yaml
```

## Schema Organization

```python
# src/booking/interfaces/schemas.py
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import date, time, datetime


# Request Schemas
class BookingCreate(BaseModel):
    """Create booking request."""
    customer_id: UUID
    facility_id: UUID
    date: date
    start_time: time
    end_time: time
    notes: Optional[str] = None


# Response Schemas
class BookingOut(BaseModel):
    """Booking response."""
    id: UUID
    customer_id: UUID
    facility_id: UUID
    date: date
    start_time: time
    end_time: time
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class BookingListOut(BaseModel):
    """Paginated booking list."""
    items: List[BookingOut]
    next_cursor: Optional[str] = None
    has_more: bool = False
```

## Testing with OpenAPI

```python
# tests/api/test_openapi.py
import pytest
from fastapi.testclient import TestClient


def test_openapi_schema_valid(client: TestClient):
    """Test that OpenAPI schema is valid."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert "openapi" in schema
    assert schema["openapi"].startswith("3.")


def test_endpoints_documented(client: TestClient):
    """Test all endpoints are in OpenAPI."""
    schema = client.get("/openapi.json").json()

    paths = list(schema["paths"].keys())
    assert "/v1/bookings" in paths
    assert "/v1/bookings/{booking_id}" in paths


def test_schema_examples(client: TestClient):
    """Test response examples are present."""
    schema = client.get("/openapi.json").json()

    # Check booking endpoint has examples
    booking_response = schema["paths"]["/v1/bookings/{booking_id}"]["get"]["responses"]["200"]
    assert "content" in booking_response
    assert "application/json" in booking_response["content"]
    assert "schema" in booking_response["content"]["application/json"]
```

## Integration with API Gateways

```yaml
# Kong declarative config
_format_version: "3.0"
services:
  - name: splashh-api
    url: https://api.splashh.com
    routes:
      - name: api-route
        paths:
          - /v1
        plugins:
          - name: cors
          - name: rate-limiting
            config:
              minute: 100
```

## Related Documents

- [REST Design](../08-apis/rest-design.md)
- [OpenAPI Documentation](https://fastapi.tiangolo.com/advanced/openapi-callbacks/)
- [Client Codegen](https://openapi-generator.tech/)
