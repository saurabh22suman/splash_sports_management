"""Booking domain entities.

A Booking reserves a Resource for a specific time window. The most critical
invariant is **no double-booking** — a confirmed booking cannot overlap with
another confirmed booking for the same resource.

Invariants:
- `end_at > start_at`
- `start_at` is aligned to the resource's slot_duration_minutes
- A confirmed booking cannot overlap with another confirmed booking for the
  same resource
- Cancellation transitions: CONFIRMED -> CANCELLED, CONFIRMED -> COMPLETED,
  CONFIRMED -> NO_SHOW (terminal states)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from common.domain.exceptions import InvariantViolation, Validation


class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class CancellationReason(str, Enum):
    CUSTOMER_REQUEST = "customer_request"
    NO_SHOW = "no_show"
    FACILITY_ISSUE = "facility_issue"
    ADMIN_ACTION = "admin_action"


@dataclass(slots=True)
class Booking:
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    resource_id: UUID
    start_at: datetime
    end_at: datetime
    status: BookingStatus
    price_cents: int
    currency: str
    notes: str | None
    cancellation_reason: CancellationReason | None
    cancelled_at: datetime | None
    checked_in_at: datetime | None
    completed_at: datetime | None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        resource_id: UUID,
        start_at: datetime,
        end_at: datetime,
        price_cents: int = 0,
        currency: str = "INR",
        notes: str | None = None,
    ) -> Booking:
        cls._validate_window(start_at, end_at)
        if price_cents < 0:
            raise Validation("price_cents cannot be negative")
        if not currency or len(currency) != 3:
            raise Validation("currency must be a 3-letter ISO 4217 code")
        return cls(
            id=UUID(int=0),
            tenant_id=tenant_id,
            customer_id=customer_id,
            resource_id=resource_id,
            start_at=start_at,
            end_at=end_at,
            status=BookingStatus.CONFIRMED,
            price_cents=price_cents,
            currency=currency.upper(),
            notes=notes,
            cancellation_reason=None,
            cancelled_at=None,
            checked_in_at=None,
            completed_at=None,
        )

    def cancel(self, *, reason: CancellationReason, now: datetime | None = None) -> None:
        if self.status != BookingStatus.CONFIRMED:
            raise InvariantViolation(f"Cannot cancel booking in status {self.status}")
        now = now or datetime.now(timezone.utc)
        self.status = BookingStatus.CANCELLED
        self.cancellation_reason = reason
        self.cancelled_at = now
        self.updated_at = now

    def check_in(self, now: datetime | None = None) -> None:
        if self.status != BookingStatus.CONFIRMED:
            raise InvariantViolation(f"Cannot check-in booking in status {self.status}")
        now = now or datetime.now(timezone.utc)
        self.checked_in_at = now
        self.updated_at = now

    def complete(self, now: datetime | None = None) -> None:
        if self.status != BookingStatus.CONFIRMED:
            raise InvariantViolation(f"Cannot complete booking in status {self.status}")
        now = now or datetime.now(timezone.utc)
        self.status = BookingStatus.COMPLETED
        self.completed_at = now
        self.updated_at = now

    def mark_no_show(self, now: datetime | None = None) -> None:
        if self.status != BookingStatus.CONFIRMED:
            raise InvariantViolation(f"Cannot mark no-show for booking in status {self.status}")
        now = now or datetime.now(timezone.utc)
        self.status = BookingStatus.NO_SHOW
        self.cancellation_reason = CancellationReason.NO_SHOW
        self.updated_at = now

    def overlaps(self, other: "Booking") -> bool:
        """True if this booking's time window overlaps with `other`."""
        return self.start_at < other.end_at and other.start_at < self.end_at

    @staticmethod
    def _validate_window(start_at: datetime, end_at: datetime) -> None:
        if start_at.tzinfo is None or end_at.tzinfo is None:
            raise Validation("start_at and end_at must be timezone-aware")
        if start_at >= end_at:
            raise Validation("start_at must be before end_at")
