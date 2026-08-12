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

BookingTariff defines the price for a resource based on:
- day_of_week (0=Monday, 6=Sunday)
- time of day (hour, e.g., 6 = 6:00 AM to 7:00 AM)
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


@dataclass(slots=True)
class BookingTariff:
    """Price rule for a resource by day-of-week and time-of-day.

    This is the authoritative source of truth for booking prices.
    The server computes price from this table instead of accepting
    client-controlled price_cents (P0 security fix for F-05).
    """

    id: UUID
    tenant_id: UUID
    resource_id: UUID
    day_of_week: int  # 0=Monday, 6=Sunday
    time_start: int  # Hour of day (0-23) - start of the time slot
    time_end: int  # Hour of day (0-23) - end of the time slot (exclusive)
    price_cents: int
    currency: str
    # Computed duration_hours: time_end - time_start (typically 1 hour slots)

    def __post_init__(self) -> None:
        # Validate day_of_week
        if not (0 <= self.day_of_week <= 6):
            raise Validation("day_of_week must be 0-6 (Monday-Sunday)")
        # Validate time window
        if not (0 <= self.time_start <= 23):
            raise Validation("time_start must be 0-23")
        if not (0 <= self.time_end <= 23):
            raise Validation("time_end must be 0-23")
        if self.time_start >= self.time_end:
            raise Validation("time_start must be before time_end")
        # Validate price
        if self.price_cents < 0:
            raise Validation("price_cents cannot be negative")
        # Validate currency
        if not self.currency or len(self.currency) != 3:
            raise Validation("currency must be a 3-letter ISO 4217 code")
