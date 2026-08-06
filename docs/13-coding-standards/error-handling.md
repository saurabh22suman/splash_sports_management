# Error Handling

> Catch the narrowest exception. Never bare `except:`. Re-raise with context. Custom domain exceptions. Logging at the boundary.

This document defines our error handling patterns. We prioritize explicit error handling over generic catches, proper exception hierarchy, and meaningful error messages for debugging.

---

## Exception Hierarchy

We define a custom exception hierarchy:

```python
# apps/backend/src/common/exceptions.py
from typing import Any


class SplashhException(Exception):
    """Base exception for all Splashh errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


# Domain exceptions
class NotFoundError(SplashhException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier},
        )


class ValidationError(SplashhException):
    """Input validation failed."""

    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation failed for {field}: {message}",
            code="VALIDATION_ERROR",
            details={"field": field, "message": message},
        )


class ConflictError(SplashhException):
    """Resource conflict (e.g., duplicate)."""

    def __init__(self, resource: str, message: str):
        super().__init__(
            message=f"Conflict for {resource}: {message}",
            code="CONFLICT",
            details={"resource": resource},
        )


class PermissionError(SplashhException):
    """Permission denied."""

    def __init__(self, action: str, resource: str):
        super().__init__(
            message=f"Permission denied: cannot {action} {resource}",
            code="PERMISSION_DENIED",
            details={"action": action, "resource": resource},
        )


# Service-specific exceptions
class BookingNotFoundError(NotFoundError):
    def __init__(self, booking_id: str):
        super().__init__("Booking", booking_id)


class CourtNotFoundError(NotFoundError):
    def __init__(self, court_id: str):
        super().__init__("Court", court_id)


class SlotUnavailableError(ConflictError):
    def __init__(self, court_id: str, start_time: datetime):
        super().__init__(
            "Booking",
            f"Court {court_id} is not available at {start_time}",
        )
```

---

## Catch Narrow Exceptions

> **Rule** — Always catch the most specific exception possible.

```python
# GOOD: Specific exception handling
try:
    booking = await booking_repository.get(booking_id)
except BookingNotFoundError:
    raise HTTPException(status_code=404, detail="Booking not found")


# BAD: Catching too broad
try:
    booking = await booking_repository.get(booking_id)
except Exception:  # Too broad!
    raise HTTPException(status_code=404, detail="Booking not found")


# GOOD: Handle multiple specific exceptions
try:
    await process_payment(booking)
except PaymentDeclinedError as e:
    raise HTTPException(status_code=402, detail=str(e))
except PaymentGatewayError as e:
    logger.error(f"Payment gateway error: {e}")
    raise HTTPException(status_code=503, detail="Payment service unavailable")
```

---

## Never Bare Except

> **Anti-pattern** — Never use bare `except:`. It catches everything including `KeyboardInterrupt`.

```python
# BAD: Bare except
try:
    result = process_data()
except:  # Catches EVERYTHING including SystemExit!
    logger.error("Failed")
    return None


# GOOD: Catch specific exceptions
try:
    result = process_data()
except ValueError as e:
    logger.warning(f"Invalid input: {e}")
    return None
except RuntimeError as e:
    logger.error(f"Processing failed: {e}")
    return None


# GOOD: Catch base class if needed
try:
    result = process_data()
except SplashhException as e:  # Our custom base
    logger.error(f"Splashh error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```

---

## Re-raise with Context

When catching and re-raising, add context:

```python
# GOOD: Re-raise with context
try:
    booking = await booking_repository.get(booking_id)
except BookingNotFoundError:
    # Add context before re-raising
    logger.warning(f"Booking lookup failed for tenant {tenant_id}: {booking_id} not found")
    raise


# GOOD: Wrap with custom exception
try:
    await payment_gateway.charge(amount)
except StripeError as e:
    raise PaymentProcessingError(
        f"Failed to process payment: {e}"
    ) from e  # Preserve original exception chain


# BAD: Swallowing exceptions
try:
    booking = await booking_repository.get(booking_id)
except BookingNotFoundError:
    return None  # Lost information!


# GOOD: Use logger instead of swallowing
try:
    booking = await booking_repository.get(booking_id)
except BookingNotFoundError:
    logger.info(f"Booking {booking_id} not found, returning empty")
    return None
```

---

## Logging at the Boundary

Log errors at the layer where you handle them (usually API layer), not everywhere:

```python
# apps/backend/src/common/error_handlers.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging


logger = logging.getLogger(__name__)


@app.exception_handler(SplashhException)
async def splashh_exception_handler(request: Request, exc: SplashhException):
    """Handle all Splashh exceptions."""
    logger.warning(
        f"Request failed: {exc.code} - {exc.message}",
        extra={
            "path": str(request.url),
            "method": request.method,
            "details": exc.details,
        }
    )

    status_code = {
        "NOT_FOUND": 404,
        "VALIDATION_ERROR": 422,
        "CONFLICT": 409,
        "PERMISSION_DENIED": 403,
        "PAYMENT_REQUIRED": 402,
    }.get(exc.code, 500)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        f"Unexpected error: {type(exc).__name__}: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
        }
    )
```

---

## Error Response Format

Use RFC 7807 Problem Details for API errors:

```json
{
  "type": "https://api.splashh.com/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Validation failed for booking: end_time must be after start_time",
  "instance": "/api/v1/bookings",
  "errors": [
    {
      "field": "end_time",
      "message": "Must be after start_time"
    }
  ]
}
```

```python
# Error response model
from pydantic import BaseModel
from typing import Literal


class ErrorDetail(BaseModel):
    """Individual field error."""
    field: str
    message: str


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details."""
    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
    errors: list[ErrorDetail] | None = None
```

---

## Summary

| Pattern | Rule |
|---|---|
| Exception hierarchy | Custom base + domain-specific |
| Catch | Narrow as possible |
| Bare except | Never use |
| Re-raise | Add context, preserve chain |
| Logging | At boundary (API layer) |
| Response | RFC 7807 format |

---

## Related Documents

- [Python Style](./python-style.md) — Formatting rules
- [Documentation](./documentation.md) — Docstring standards
- [Code Review Checklist](./code-review-checklist.md) — Review standards
- [Error Responses](../08-apis/error-responses.md) — API error format
