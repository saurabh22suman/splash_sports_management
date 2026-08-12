"""Domain exception hierarchy.

Modules raise domain exceptions. The HTTP layer ([`common.interfaces.http.errors`](../interfaces/http/errors.py))
maps these to RFC 7807 problem responses.

> **Rule** — modules MUST raise domain exceptions, never HTTPException.
> Modules MUST NOT import FastAPI.
"""
from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base class for all domain errors."""

    code: str = "domain_error"
    http_status: int = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFound(DomainError):
    code = "not_found"
    http_status = 404


class Validation(DomainError):
    code = "validation_error"
    http_status = 422


class Conflict(DomainError):
    code = "conflict"
    http_status = 409


class Unauthorized(DomainError):
    code = "unauthorized"
    http_status = 401


class Forbidden(DomainError):
    code = "forbidden"
    http_status = 403


class RateLimited(DomainError):
    code = "rate_limited"
    http_status = 429


class InvariantViolation(DomainError):
    """Raised when a domain invariant is broken.

    Example: trying to book an already-booked slot.
    """

    code = "invariant_violation"
    http_status = 409


class ConcurrencyConflict(DomainError):
    """Raised when optimistic concurrency check fails.

    Example: version mismatch on aggregate update.
    """

    code = "concurrency_conflict"
    http_status = 409


class ExternalService(DomainError):
    """Raised when an external dependency (payment gateway, SMS) fails."""

    code = "external_service_error"
    http_status = 502
