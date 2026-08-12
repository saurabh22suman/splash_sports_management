"""Structured logging via structlog.

JSON logs in production, pretty console logs in development. Every log record
includes the active request context (request_id, tenant_id, user_id) so logs
can be correlated without manual threading.

PII fields are redacted via the `redact_pii` processor.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


REDACT_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "set-cookie",
    "api_key",
    "apikey",
    "credit_card",
    "card_number",
    "cvv",
    "pan",
}


def _redact_pii(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Replace values for known-sensitive keys with `***`."""
    for key in list(event_dict.keys()):
        if key.lower() in REDACT_KEYS:
            event_dict[key] = "***"
    return event_dict


def _inject_context(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Add the active request context (request_id, tenant_id, user_id)."""
    from common.application.context import get_context

    ctx = get_context()
    if ctx is None:
        return event_dict
    event_dict.setdefault("request_id", ctx.request_id)
    if ctx.tenant_id is not None:
        event_dict.setdefault("tenant_id", str(ctx.tenant_id))
    if ctx.user_id is not None:
        event_dict.setdefault("user_id", str(ctx.user_id))
    return event_dict


def _shared_processors() -> list[Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        _inject_context,
        _redact_pii,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]


def configure_logging(level: str = "INFO", *, json_logs: bool | None = None) -> None:
    """Configure structlog + stdlib logging.

    Args:
        level: Minimum log level.
        json_logs: Force JSON logs (production) or console renderer (dev).
            Defaults to True outside development.
    """
    if json_logs is None:
        json_logs = True
    is_dev = level == "DEBUG" or not json_logs

    processors: list[Processor] = _shared_processors()
    if is_dev:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        context_class=dict,
        # stdlib LoggerFactory gives us loggers with a real `.name` attribute,
        # which `add_logger_name` and downstream stdlib handlers require.
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # stdlib root logger
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level),
        force=True,
    )

    # Quiet noisy libraries
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[return-value]
