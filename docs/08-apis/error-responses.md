# Error Responses

> This document covers RFC 7807 Problem Details format, error response structure, and examples.

## Overview

All API errors follow **RFC 7807 Problem Details for HTTP APIs**. This provides a standardized error format that clients can parse consistently.

## RFC 7807 Structure

```json
{
  "type": "https://api.splashh.com/errors/not_found",
  "title": "NotFoundError",
  "status": 404,
  "detail": "Booking with ID abc-123 not found",
  "instance": "/v1/bookings/abc-123",
  "errors": [
    {
      "field": "booking_id",
      "message": "Booking not found",
      "code": "not_found"
    }
  ],
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | URI identifying error type |
| `title` | string | Yes | Short error title |
| `status` | number | Yes | HTTP status code |
| `detail` | string | Yes | Human-readable description |
| `instance` | string | No | Request URI that caused error |
| `errors` | array | No | Detailed field errors |
| `request_id` | string | No | Correlation ID |

## Error Types

| Type | Title | Status | Description |
|------|-------|--------|-------------|
| `validation_error` | Validation Error | 400 | Request validation failed |
| `not_found` | NotFoundError | 404 | Resource not found |
| `conflict` | ConflictError | 409 | State conflict |
| `authorization_error` | AuthorizationError | 403 | Forbidden |
| `authentication_error` | AuthenticationError | 401 | Unauthorized |
| `rate_limit_exceeded` | RateLimitError | 429 | Too many requests |
| `internal_error` | InternalError | 500 | Server error |

## Response Examples

### Validation Error (400)

```json
{
  "type": "https://api.splashh.com/errors/validation_error",
  "title": "Validation Error",
  "status": 400,
  "detail": "Request validation failed",
  "instance": "/v1/bookings",
  "errors": [
    {
      "field": "customer_id",
      "message": "field required",
      "code": "missing"
    },
    {
      "field": "date",
      "message": "invalid date format",
      "code": "invalid"
    },
    {
      "field": "end_time",
      "message": "end_time must be after start_time",
      "code": "value_error"
    }
  ]
}
```

### Not Found (404)

```json
{
  "type": "https://api.splashh.com/errors/not_found",
  "title": "NotFoundError",
  "status": 404,
  "detail": "Booking with ID abc-123 not found",
  "instance": "/v1/bookings/abc-123"
}
```

### Conflict (409)

```json
{
  "type": "https://api.splashh.com/errors/conflict",
  "title": "ConflictError",
  "status": 409,
  "detail": "Slot not available for the requested time",
  "instance": "/v1/bookings"
}
```

### Rate Limit (429)

```json
{
  "type": "https://api.splashh.com/errors/rate_limit_exceeded",
  "title": "RateLimitError",
  "status": 429,
  "detail": "Rate limit exceeded. Try again later.",
  "instance": "/v1/bookings",
  "retry_after": 60
}
```

### Server Error (500)

```json
{
  "type": "https://api.splashh.com/errors/internal_error",
  "title": "InternalError",
  "status": 500,
  "detail": "An unexpected error occurred",
  "instance": "/v1/bookings/abc-123",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Implementation

### Error Response Schema

```python
# src/common/schemas.py
from typing import Optional, List
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str
    message: str
    code: str


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details."""
    type: str
    title: str
    status: int
    detail: str
    instance: Optional[str] = None
    errors: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None
    retry_after: Optional[int] = None
```

### Exception Handler

```python
# src/common/exceptions.py
from fastapi import Request
from fastapi.responses import JSONResponse


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = {
        NotFoundError: 404,
        ValidationError: 400,
        ConflictError: 409,
        AuthorizationError: 403,
        AuthenticationError: 401,
        RateLimitError: 429,
    }.get(type(exc), 500)

    content = {
        "type": f"https://api.splashh.com/errors/{exc.code}",
        "title": exc.__class__.__name__,
        "status": status_code,
        "detail": exc.message,
        "instance": str(request.url),
    }

    if hasattr(exc, "errors"):
        content["errors"] = exc.errors

    if hasattr(request.state, "request_id"):
        content["request_id"] = request.state.request_id

    return JSONResponse(status_code=status_code, content=content)
```

## Client Handling

```python
// JavaScript example
async function handleApiError(response) {
  const error = await response.json();

  switch (error.status) {
    case 400:
      // Show validation errors
      error.errors?.forEach(e => {
        showFieldError(e.field, e.message);
      });
      break;

    case 404:
      // Show not found message
      showToast(error.detail);
      break;

    case 429:
      // Retry after delay
      const retryAfter = error.retry_after || 60;
      setTimeout(() => retryRequest(), retryAfter * 1000);
      break;

    case 500:
      // Log and show generic error
      console.error("Server error", error.request_id);
      showToast("An unexpected error occurred");
      break;
  }
}
```

## Anti-Patterns

1. **Non-RFC format** — Inconsistent error structures
2. **Leaking internals** — Stack traces in production
3. **Missing error codes** — Unclear error types
4. **No request_id** — Impossible to debug

## Related Documents

- [REST Design](rest-design.md)
- [Status Codes](status-codes.md)
- [Error Handling](../04-backend/error-handling.md)
