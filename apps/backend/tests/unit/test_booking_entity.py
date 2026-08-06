"""Unit tests for Booking entity (no DB)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from booking.domain.entities import Booking, BookingStatus, CancellationReason
from common.domain.exceptions import InvariantViolation, Validation


@pytest.mark.unit
class TestBookingEntity:
    def _booking(self) -> Booking:
        return Booking.create(
            tenant_id=uuid4(),
            customer_id=uuid4(),
            resource_id=uuid4(),
            start_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
            price_cents=10000,
        )

    def test_create_with_valid_data(self) -> None:
        b = self._booking()
        assert b.status == BookingStatus.CONFIRMED
        assert b.price_cents == 10000
        assert b.currency == "INR"

    def test_rejects_end_before_start(self) -> None:
        with pytest.raises(Validation):
            Booking.create(
                tenant_id=uuid4(),
                customer_id=uuid4(),
                resource_id=uuid4(),
                start_at=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            )

    def test_rejects_naive_datetime(self) -> None:
        with pytest.raises(Validation):
            Booking.create(
                tenant_id=uuid4(),
                customer_id=uuid4(),
                resource_id=uuid4(),
                start_at=datetime(2026, 9, 1, 10, 0),  # no tz
                end_at=datetime(2026, 9, 1, 11, 0),
            )

    def test_rejects_negative_price(self) -> None:
        with pytest.raises(Validation):
            Booking.create(
                tenant_id=uuid4(),
                customer_id=uuid4(),
                resource_id=uuid4(),
                start_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
                price_cents=-1,
            )

    def test_overlaps_returns_true_for_overlap(self) -> None:
        b1 = self._booking()
        b2 = Booking.create(
            tenant_id=uuid4(),
            customer_id=uuid4(),
            resource_id=uuid4(),
            start_at=datetime(2026, 9, 1, 10, 30, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 1, 11, 30, tzinfo=timezone.utc),
        )
        assert b1.overlaps(b2) is True

    def test_overlaps_returns_false_for_adjacent(self) -> None:
        b1 = self._booking()
        b2 = Booking.create(
            tenant_id=uuid4(),
            customer_id=uuid4(),
            resource_id=uuid4(),
            start_at=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        )
        assert b1.overlaps(b2) is False

    def test_cancel_transitions_to_cancelled(self) -> None:
        b = self._booking()
        b.cancel(reason=CancellationReason.CUSTOMER_REQUEST)
        assert b.status == BookingStatus.CANCELLED
        assert b.cancellation_reason == CancellationReason.CUSTOMER_REQUEST
        assert b.cancelled_at is not None

    def test_cannot_cancel_twice(self) -> None:
        b = self._booking()
        b.cancel(reason=CancellationReason.CUSTOMER_REQUEST)
        with pytest.raises(InvariantViolation):
            b.cancel(reason=CancellationReason.CUSTOMER_REQUEST)
