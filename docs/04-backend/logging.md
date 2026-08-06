# Logging

> This document covers structured JSON logging, required log fields, PII redaction, and OpenTelemetry correlation.

## Overview

We use **structlog** for structured JSON logging. Every log entry is a JSON object with a consistent schema, making it easy to query, filter, and analyze in our logging infrastructure (e.g., ELK, Datadog, Splunk).

## Setup

```python
# src/common/logging.py
import logging
import sys
from typing import Any
from uuid import uuid4

import structlog
from structlog.types import EventDict, Processor
from structlog.processors import JSONRenderer, TimeStamper, add_log_level

from common.config import get_settings


def add_timestamp(logger: Any, method: str, event: EventDict) -> EventDict:
    """Add ISO timestamp to log entries."""
    # TimeStamper handles this, but we ensure consistency
    return event


def configure_logging() -> None:
    """Configure structured logging."""
    settings = get_settings()

    # Configure structlog
    structlog.configure(
        processors=[
            # Context merging
            structlog.contextvars.merge_contextvars,
            # Add log level
            add_log_level,
            # Add timestamp
            TimeStamper(fmt="iso", utc=True),
            # Add request_id if present
            add_request_id,
            # Redact PII
            redact_pii,
            # Stack trace for errors
            structlog.processors.StackInfoRenderer(),
            # JSON rendering
            JSONRenderer() if not settings.DEBUG else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging_level_from_settings(settings)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def logging_level_from_settings(settings) -> int:
    """Map settings to logging level."""
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    return levels.get(settings.LOG_LEVEL.upper(), logging.INFO)


def add_request_id(logger: Any, method: str, event: EventDict) -> EventDict:
    """Add request_id from context if available."""
    from contextvars import ContextVar

    request_id_var: ContextVar = ContextVar("request_id", default=None)
    request_id = request_id_var.get()

    if request_id:
        event["request_id"] = request_id
    return event


def redact_pii(logger: Any, method: str, event: EventDict) -> EventDict:
    """Redact PII from log entries."""
    pii_fields = {
        "password": "***REDACTED***",
        "token": "***REDACTED***",
        "secret": "***REDACTED***",
        "credit_card": "***REDACTED***",
        "email": lambda v: v[0] + "***@" + v.split("@")[-1] if "@" in v else "***",
        "phone": lambda v: "***-***-" + v[-4:] if len(v) > 4 else "***-***-****",
    }

    def redact_value(key: str, value: Any) -> Any:
        if isinstance(value, dict):
            return {k: redact_value(k, v) for k, v in value.items()}
        if isinstance(value, list):
            return [redact_value(key, item) for item in value]
        if key.lower() in pii_fields:
            redact_fn = pii_fields[key.lower()]
            return redact_fn(value) if callable(redact_fn) else redact_fn
        return value

    return {k: redact_value(k, v) for k, v in event.items()}
```

## Required Fields

Every log entry MUST include:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO8601 | UTC timestamp |
| `level` | string | DEBUG, INFO, WARNING, ERROR |
| `message` | string | Human-readable message |
| `request_id` | UUID | Request correlation ID |
| `tenant_id` | UUID | Multi-tenant identifier |
| `user_id` | UUID | Authenticated user (if any) |
| `context` | object | Additional context |

```json
{
  "timestamp": "2024-01-15T10:30:00.123456Z",
  "level": "INFO",
  "message": "Booking created successfully",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
  "user_id": "770e8400-e29b-41d4-a716-446655440002",
  "context": {
    "booking_id": "880e8400-e29b-41d4-a716-446655440003",
    "facility_id": "990e8400-e29b-41d4-a716-446655440004"
  }
}
```

## Request Context

Set request context at the start of each request:

```python
# src/common/middleware.py
from contextvars import ContextVar
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from common.logging import get_logger

logger = get_logger(__name__)

request_id_var: ContextVar[str] = ContextVar("request_id", default=None)
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default=None)
user_id_var: ContextVar[str] = ContextVar("user_id", default=None)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request_id_var.set(request_id)

        # Extract tenant from JWT or header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            tenant_id_var.set(tenant_id)

        # Extract user from JWT
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            user_id_var.set(str(user_id))

        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)

        # Log response
        logger.info(
            "Request completed",
            status_code=response.status_code,
            duration_ms=...,  # Calculate duration
        )

        return response
```

## Logging in Services

```python
# src/booking/application/services.py
from common.logging import get_logger

logger = get_logger(__name__)


class BookingService:
    def create_booking(self, command: CreateBookingCommand) -> BookingResult:
        logger.info(
            "Creating booking",
            customer_id=str(command.customer_id),
            facility_id=str(command.facility_id),
            date=str(command.date),
        )

        try:
            booking = self._do_create_booking(command)
            logger.info(
                "Booking created successfully",
                booking_id=str(booking.id),
            )
            return booking
        except SlotNotAvailableError as e:
            logger.warning(
                "Booking failed: slot not available",
                facility_id=str(command.facility_id),
                date=str(command.date),
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "Booking failed: unexpected error",
                error=str(e),
                exc_info=True,  # Include stack trace
            )
            raise
```

## Log Levels by Environment

| Level | Production | Staging | Development |
|-------|------------|---------|-------------|
| DEBUG | No | No | Yes |
| INFO | Yes | Yes | Yes |
| WARNING | Yes | Yes | Yes |
| ERROR | Yes | Yes | Yes |
| CRITICAL | Yes | Yes | Yes |

## OpenTelemetry Correlation

```python
# src/common/logging.py
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


def add_trace_context(logger: Any, method: str, event: EventDict) -> EventDict:
    """Add OpenTelemetry trace context to logs."""
    span = trace.get_current_span()
    if span:
        ctx = span.get_span_context()
        event["trace_id"] = format(ctx.trace_id, "032x")
        event["span_id"] = format(ctx.span_id, "016x")

        # Also add to context for downstream
        event["trace_flags"] = format(ctx.trace_flags, "02d")

    return event
```

## Structured Logging with Context

```python
# Using bound loggers
from structlog import get_logger

logger = get_logger(__name__).bind(
    tenant_id=str(tenant_id),
    service="booking",
)


# All log entries from this logger will have tenant_id
logger.info("Processing booking", booking_id=str(booking_id))
```

## Query Examples

In your log aggregator (e.g., Elasticsearch, Datadog):

```sql
-- Find all errors for a specific tenant
SELECT * FROM logs
WHERE tenant_id = '660e8400-e29b-41d4-a716-446655440001'
  AND level = 'ERROR'
  AND timestamp > NOW() - INTERVAL '1 hour'

-- Find all logs for a specific request
SELECT * FROM logs
WHERE request_id = '550e8400-e29b-41d4-a716-446655440000'

-- Find all bookings created in the last day
SELECT * FROM logs
WHERE message LIKE '%Booking created%'
  AND timestamp > NOW() - INTERVAL '1 day'
```

## Anti-Patterns

1. **String formatting in logs** — Use structured fields, not f-strings
2. **Logging sensitive data** — Never log passwords, tokens, PII
3. **Missing context** — Always include tenant_id and request_id
4. **Logging without error context** — Include relevant IDs in error logs

## Related Documents

- [Configuration](configuration.md)
- [OpenAPI](openapi.md)
- [Observability](../11-performance/observability.md)
