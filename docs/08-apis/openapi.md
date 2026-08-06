# OpenAPI

> This document covers OpenAPI as the API contract, documentation, and client codegen.

## Overview

**OpenAPI** is the single source of truth for our API. It drives documentation, client SDKs, and validation.

## OpenAPI in FastAPI

```python
# src/main.py
from fastapi import FastAPI


app = FastAPI(
    title="Splashh Sports API",
    description="Sports club management platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add servers
    openapi_schema["servers"] = [
        {"url": "https://api.splashh.com/v1", "description": "Production"},
        {"url": "https://staging-api.splashh.com/v1", "description": "Staging"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema
```

## Documentation URLs

| URL | Description |
|-----|-------------|
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/openapi.json` | Raw OpenAPI JSON |

## Schema Examples

```python
# src/booking/interfaces/schemas.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class BookingOut(BaseModel):
    """Booking response schema."""
    model_config = {"from_attributes": True}

    id: UUID
    customer_id: UUID
    facility_id: UUID
    date: str = Field(..., examples=["2024-01-15"])
    start_time: str = Field(..., examples=["10:00"])
    end_time: str = Field(..., examples=["11:00"])
    status: str = Field(..., examples=["confirmed"])
    created_at: datetime
    version: int = Field(..., examples=[1])


# In router
@router.get(
    "/bookings/{booking_id}",
    response_model=BookingOut,
    responses={
        404: {"description": "Booking not found"},
        403: {"description": "Not authorized"},
    },
)
async def get_booking(booking_id: UUID):
    ...
```

## Client Codegen

### TypeScript

```bash
# Install
npm install @openapitools/openapi-typescript-codegen

# Generate
openapi-typescript-codegen \
  --input https://api.splashh.com/openapi.json \
  --output ./packages/api-client \
  --name SplashhClient
```

### Python

```bash
# Install
pip install openapi-python-client

# Generate
openapi-python-client generate \
  --url https://api.splashh.com/openapi.json \
  --path ./clients/python
```

### Generated Client Usage

```typescript
// TypeScript client
import { SplashhClient, Configuration } from './packages/api-client';

const config = new Configuration({
  basePath: 'https://api.splashh.com/v1',
  accessToken: 'my-token',
});

const client = new SplashhClient(config);
const bookings = await client.bookings.listBookings();
```

## Webhook Documentation

```yaml
# webhooks.yaml (part of OpenAPI)
components:
  webhooks:
    bookingConfirmed:
      post:
        requestBody:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BookingConfirmedEvent'
        responses:
          '200':
            description: Webhook received
```

## Validation

```bash
# Validate OpenAPI schema
npx @stoplight/spectral lint openapi.json \
  --ruleset .spectral.yaml
```

## Anti-Patterns

1. **No documentation** — Always document endpoints
2. **Missing examples** — Include request/response examples
3. **No version** — Version the API

## Related Documents

- [REST Design](rest-design.md)
- [Backend OpenAPI](../04-backend/openapi.md)
