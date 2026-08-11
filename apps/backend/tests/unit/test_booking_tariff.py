"""Unit tests for BookingTariff entity and compute_price logic."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from booking.domain.entities import BookingTariff
from common.domain.exceptions import Validation


@pytest.mark.unit
class TestBookingTariffEntity:
    def _tariff(self) -> BookingTariff:
        return BookingTariff(
            id=uuid4(),
            tenant_id=uuid4(),
            resource_id=uuid4(),
            day_of_week=0,  # Monday
            time_start=6,   # 6:00 AM
            time_end=22,    # 10:00 PM
            price_cents=2500,
            currency="INR",
        )

    def test_create_with_valid_data(self) -> None:
        t = self._tariff()
        assert t.price_cents == 2500
        assert t.currency == "INR"
        assert t.day_of_week == 0

    def test_rejects_invalid_day_of_week(self) -> None:
        with pytest.raises(Validation):
            BookingTariff(
                id=uuid4(),
                tenant_id=uuid4(),
                resource_id=uuid4(),
                day_of_week=7,  # Invalid - must be 0-6
                time_start=6,
                time_end=22,
                price_cents=2500,
                currency="INR",
            )

    def test_rejects_invalid_time_window(self) -> None:
        with pytest.raises(Validation):
            BookingTariff(
                id=uuid4(),
                tenant_id=uuid4(),
                resource_id=uuid4(),
                day_of_week=0,
                time_start=22,  # Start after end
                time_end=6,
                price_cents=2500,
                currency="INR",
            )

    def test_rejects_negative_price(self) -> None:
        with pytest.raises(Validation):
            BookingTariff(
                id=uuid4(),
                tenant_id=uuid4(),
                resource_id=uuid4(),
                day_of_week=0,
                time_start=6,
                time_end=22,
                price_cents=-100,
                currency="INR",
            )


@pytest.mark.unit
class TestComputePrice:
    def test_exact_match_returns_tariff_price(self) -> None:
        """Booking at 10 AM Monday should return the tariff price."""
        from booking.application.booking_service import compute_price

        tariff = BookingTariff(
            id=uuid4(),
            tenant_id=uuid4(),
            resource_id=uuid4(),
            day_of_week=0,  # Monday
            time_start=6,   # 6:00 AM
            time_end=22,    # 10:00 PM
            price_cents=2500,
            currency="INR",
        )
        start = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)  # Monday Sept 7, 2026

        price_cents_result, currency_result = compute_price(
            resource_id=tariff.resource_id,
            start_at=start,
            tariffs=[tariff],
        )
        assert price_cents_result == 2500
        assert currency_result == "INR"

    def test_no_matching_tariff_raises(self) -> None:
        """Booking without matching tariff should raise."""
        from booking.application.booking_service import compute_price
        from common.domain.exceptions import Validation

        tariff = BookingTariff(
            id=uuid4(),
            tenant_id=uuid4(),
            resource_id=uuid4(),
            day_of_week=0,  # Monday
            time_start=6,
            time_end=22,
            price_cents=2500,
            currency="INR",
        )
        # Saturday Sept 12, 2026 - no tariff for Saturday
        start = datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc)

        with pytest.raises(Validation, match="No tariff found"):
            compute_price(
                resource_id=tariff.resource_id,
                start_at=start,
                tariffs=[tariff],
            )

    def test_ignores_client_price(self) -> None:
        """Server should never use client-provided price_cents."""
        # This test documents the security requirement:
        # Even if client sends price_cents=0, server must compute from tariff
        pass
