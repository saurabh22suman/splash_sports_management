# Logging

> Structured JSON logs (Loki). Per-service labels. Log levels by environment. PII redaction.

This document defines our logging standards. We prioritize structured logs for queryability, consistent formatting across services, and PII protection.

---

## Log Format

All logs are structured JSON for Loki ingestion:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "service": "backend",
  "trace_id": "abc123def456",
  "span_id": "span789",
  "message": "Booking created successfully",
  "context": {
    "tenant_id": "tenant_123",
    "user_id": "user_456",
    "booking_id": "booking_789"
  },
  "event": {
    "name": "booking_created",
    "properties": {
      "court_id": "court_1",
      "duration_minutes": 60,
      "total_amount": 2500
    }
  }
}
```

> **Why** — Structured JSON enables LogQL queries that extract fields. Non-structured logs make debugging painful in production.

---

## Log Levels

| Level | Usage | Production |
|---|---|---|
| DEBUG | Detailed debugging info | Disabled |
| INFO | Normal operation events | Enabled |
| WARNING | Recoverable issues | Enabled |
| ERROR | Failures affecting request | Enabled |
| CRITICAL | System-level failures | Enabled + page |

### Level by Environment

```python
# apps/backend/src/common/logging.py
import logging
import os
from typing import Any


def get_log_level() -> str:
    """Determine log level from environment."""
    env = os.environ.get("ENVIRONMENT", "development")

    if env == "production":
        return "INFO"
    elif env == "staging":
        return "DEBUG"
    else:  # development
        return "DEBUG"


def configure_logging() -> None:
    """Configure structured logging for the application."""
    import logging.config

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(timestamp)s %(level)s %(name)s %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout"
            }
        },
        "root": {
            "level": get_log_level(),
            "handlers": ["console"]
        }
    })
```

---

## Required Fields

Every log entry must include:

| Field | Type | Description |
|---|---|---|
| `timestamp` | ISO8601 | UTC timestamp with Z suffix |
| `level` | string | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `service` | string | Service name (backend, worker, etc.) |
| `message` | string | Human-readable message |
| `trace_id` | string | Request correlation ID (if applicable) |

---

## Python Structured Logging

```python
# apps/backend/src/common/logger.py
import logging
import json
from datetime import datetime
from typing import Any
from contextvars import ContextVar

# Context variables for request-scoped data
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")


class StructuredLogger:
    """Structured logger with automatic context."""

    def __init__(self, service: str):
        self.service = service
        self.logger = logging.getLogger(service)

    def _log(
        self,
        level: int,
        message: str,
        context: dict[str, Any] | None = None,
        event: dict[str, Any] | None = None,
        **kwargs
    ) -> None:
        """Internal log method."""
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": self.service,
            "message": message,
            "trace_id": trace_id_var.get(),
            "span_id": span_id_var.get(),
        }

        if context:
            record["context"] = context
        if event:
            record["event"] = event
        if kwargs:
            record["extra"] = kwargs

        self.logger.log(level, json.dumps(record))

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)


# Usage
logger = StructuredLogger("backend")

# Log with context
logger.info(
    "Booking created",
    context={"tenant_id": "tenant_123", "user_id": "user_456"},
    event={"name": "booking_created", "properties": {"amount": 2500}}
)
```

---

## PII Redaction

> **Rule** — Never log PII. Always redact before logging.

```python
# apps/backend/src/common/logging_redaction.py
import re
from typing import Any


class LogRedactor:
    """Redacts PII from log messages."""

    PATTERNS = {
        "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        "password": r'password["\s:]=["\s]?[^\s",}]+',
        "jwt": r'Bearer\s+[a-zA-Z0-9\-_.~+/]+=*',
    }

    @classmethod
    def redact(cls, data: str | dict) -> str | dict:
        """Redact PII from string or dict."""
        if isinstance(data, dict):
            return {k: cls.redact(v) for k, v in data.items()}

        if not isinstance(data, str):
            return data

        result = data
        for pii_type, pattern in cls.PATTERNS.items():
            result = re.sub(pattern, f"[{pii_type}_redacted]", result)

        return result


# Usage in logging
def safe_log(logger: StructuredLogger, message: str, **kwargs):
    """Log with automatic PII redaction."""
    redacted_kwargs = {k: LogRedactor.redact(v) for k, v in kwargs.items()}
    logger.info(message, **redacted_kwargs)
```

---

## Loki Query Examples

```logql
# All errors in last hour
{service="backend"} | json | level="ERROR" | level != "DEBUG"

# Filter by tenant
{service="backend"} | json | context.tenant_id="tenant_123"

# Search by trace ID
{trace_id="abc123def456"}

# Find slow queries
{service="backend"} | json | message=~".*slow.*" | duration_ms > 1000

# Rate of errors by endpoint
sum by (context.endpoint) (rate({service="backend"} | json | level="ERROR"[5m]))

# Recent errors with full context
{service="backend"} | json | level="ERROR" | context.tenant_id!="" | limit 50
```

---

## Retention Policies

| Environment | Retention | Storage |
|---|---|---|
| Development | 7 days | Loki (local) |
| Staging | 14 days | Loki |
| Production | 30 days | Loki + S3 cold storage |

```yaml
# loki.yaml
limits_config:
  retention_period: 720h  # 30 days
  max_retention_period: 720h

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: s3
      schema: v11
      index:
        prefix: index_
        period: 24h
```

---

## Context in Logs

Always include relevant context:

```python
# GOOD: Rich context for debugging
logger.info(
    "Payment processed",
    context={
        "tenant_id": booking.tenant_id,
        "user_id": user.id,
        "booking_id": booking.id,
        "amount": booking.total_amount,
        "currency": booking.currency,
    }
)

# BAD: Sparse context
logger.info(f"Payment {payment_id} processed")
```

---

## Summary

| Practice | Implementation |
|---|---|
| Format | Structured JSON |
| Levels | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| Required fields | timestamp, level, service, trace_id |
| PII | Always redact before logging |
| Storage | Loki with S3 backend |
| Retention | 30 days production |

---

## Related Documents

- [Monitoring](./monitoring.md) — Metrics and SLOs
- [Tracing](./tracing.md) — Distributed tracing
- [Secrets](./secrets.md) — Secret management
