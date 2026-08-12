"""Booking repository — the heart of double-booking prevention.

The `add_safe` method is the **only** way to insert a booking. It acquires
a row-level lock on the resource, then checks for any overlapping confirmed
bookings, before inserting.

> See [Booking Flow](../../../docs/02-architecture/flow-booking.md) for the
> full design rationale.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from booking.domain.entities import Booking, BookingStatus, BookingTariff, CancellationReason
from booking.infrastructure.models import BookingModel, BookingTariffModel
from common.domain.exceptions import Conflict, InvariantViolation, NotFound
from common.infrastructure.repository import BaseRepository

if TYPE_CHECKING:
    from facility.application.facility_service import FacilityService


def _to_domain(m: BookingModel) -> Booking:
    return Booking(
        id=m.id,
        tenant_id=m.tenant_id,
        customer_id=m.customer_id,
        resource_id=m.resource_id,
        start_at=m.start_at,
        end_at=m.end_at,
        status=BookingStatus(m.status),
        price_cents=m.price_cents,
        currency=m.currency,
        notes=m.notes,
        cancellation_reason=CancellationReason(m.cancellation_reason)
        if m.cancellation_reason
        else None,
        cancelled_at=m.cancelled_at,
        checked_in_at=m.checked_in_at,
        completed_at=m.completed_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class BookingRepository(BaseRepository[Booking]):
    model = BookingModel

    def __init__(
        self,
        session: AsyncSession,
        facility_service: FacilityService | None = None,
    ) -> None:
        super().__init__(session)
        self.facility_service = facility_service

    async def get_by_id(self, tenant_id: UUID, booking_id: UUID) -> Booking | None:
        m = await super().get(tenant_id, booking_id)
        return _to_domain(m) if m else None

    async def add(self, booking: Booking) -> Booking:
        """Insert a new booking.

        Use [`add_safe`] for the canonical booking flow that prevents double-
        booking. Direct use of `add` is for tests and migrations only.
        """
        m = BookingModel(
            tenant_id=booking.tenant_id,
            customer_id=booking.customer_id,
            resource_id=booking.resource_id,
            start_at=booking.start_at,
            end_at=booking.end_at,
            status=booking.status.value,
            price_cents=booking.price_cents,
            currency=booking.currency,
            notes=booking.notes,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return _to_domain(m)

    async def add_safe(self, booking: Booking) -> Booking:
        """Insert a new booking with double-booking prevention.

        Acquires a row-level lock on the resource row (SELECT FOR UPDATE),
        then asserts no overlapping confirmed booking exists. This is the
        canonical booking creation path.
        """
        # 1. Lock the resource row via FacilityService. This serializes
        #    concurrent bookings against the same resource.
        if self.facility_service is None:
            raise RuntimeError(
                "FacilityService is required for add_safe. "
                "Please inject it via the repository constructor."
            )
        try:
            await self.facility_service.lock_resource_for_update(
                tenant_id=booking.tenant_id,
                resource_id=booking.resource_id,
            )
        except NotFound:
            raise NotFound(
                "Resource not found",
                details={"resource_id": str(booking.resource_id)},
            )

        # 2. Check for overlapping CONFIRMED bookings on the same resource.
        overlap_stmt = select(
            exists().where(
                BookingModel.tenant_id == booking.tenant_id,
                BookingModel.resource_id == booking.resource_id,
                BookingModel.status == BookingStatus.CONFIRMED.value,
                BookingModel.start_at < booking.end_at,
                BookingModel.end_at > booking.start_at,
            )
        )
        has_overlap = (await self.session.execute(overlap_stmt)).scalar() is True
        if has_overlap:
            raise Conflict(
                "Resource is already booked for this time slot",
                details={
                    "resource_id": str(booking.resource_id),
                    "start_at": booking.start_at.isoformat(),
                    "end_at": booking.end_at.isoformat(),
                },
            )

        # 3. Insert.
        return await self.add(booking)

    async def update(self, booking: Booking) -> Booking:
        m = await self.session.get(BookingModel, booking.id)
        if m is None:
            raise LookupError(booking.id)
        m.status = booking.status.value
        m.price_cents = booking.price_cents
        m.notes = booking.notes
        m.cancellation_reason = (
            booking.cancellation_reason.value if booking.cancellation_reason else None
        )
        m.cancelled_at = booking.cancelled_at
        m.checked_in_at = booking.checked_in_at
        m.completed_at = booking.completed_at
        await self.session.flush()
        # Refresh to load server-updated columns (e.g. `updated_at` from onupdate=func.now())
        # so subsequent attribute access doesn't trigger lazy-load IO.
        await self.session.refresh(m)
        return _to_domain(m)

    async def list_for_customer(
        self,
        tenant_id: UUID,
        customer_id: UUID,
        *,
        statuses: list[BookingStatus] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[Booking, str | None, str | None]]:
        """Returns (booking, facility_name, resource_name) tuples for richer UI."""
        # Fetch bookings first
        stmt = (
            select(BookingModel)
            .where(
                BookingModel.tenant_id == tenant_id,
                BookingModel.customer_id == customer_id,
            )
            .order_by(BookingModel.start_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if statuses:
            stmt = stmt.where(BookingModel.status.in_([s.value for s in statuses]))

        result = await self.session.execute(stmt)
        bookings = [_to_domain(m) for m in result.scalars().all()]

        if not bookings:
            return [(b, None, None) for b in bookings]

        # Get resource and facility names via FacilityService
        resource_ids = list({b.resource_id for b in bookings})

        if self.facility_service:
            names_map = await self.facility_service.get_resource_and_facility_names(
                tenant_id=tenant_id,
                resource_ids=resource_ids,
            )
            return [
                (
                    b,
                    names_map.get(b.resource_id, (None, None))[1],
                    names_map.get(b.resource_id, (None, None))[0],
                )
                for b in bookings
            ]

        # No facility service - return bookings without names
        return [(b, None, None) for b in bookings]

    async def list_for_resource(
        self,
        tenant_id: UUID,
        resource_id: UUID,
        *,
        from_at: datetime,
        to_at: datetime,
        statuses: list[BookingStatus] | None = None,
    ) -> list[Booking]:
        stmt = (
            select(BookingModel)
            .where(
                BookingModel.tenant_id == tenant_id,
                BookingModel.resource_id == resource_id,
                BookingModel.start_at < to_at,
                BookingModel.end_at > from_at,
            )
            .order_by(BookingModel.start_at)
        )
        if statuses:
            stmt = stmt.where(BookingModel.status.in_([s.value for s in statuses]))
        result = await self.session.execute(stmt)
        return [_to_domain(m) for m in result.scalars().all()]

    async def list_admin_bookings(
        self,
        tenant_id: UUID,
        *,
        from_at: datetime,
        to_at: datetime,
        facility_id: UUID | None = None,
        resource_id: UUID | None = None,
        statuses: list[BookingStatus] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Booking]:
        """List bookings for admin view with optional filters.

        This method returns bookings within a date range, optionally filtered
        by facility, resource, and/or status.
        """
        stmt = (
            select(BookingModel)
            .where(
                BookingModel.tenant_id == tenant_id,
                BookingModel.start_at < to_at,
                BookingModel.end_at > from_at,
            )
            .order_by(BookingModel.start_at)
            .limit(limit)
            .offset(offset)
        )

        if facility_id:
            # F-10 fix: Use FacilityService instead of importing facility.infrastructure.models
            # (ADR-0001 — bounded-context isolation)
            if self.facility_service is None:
                raise RuntimeError(
                    "BookingRepository.facility_service is required when filtering by facility_id. "
                    "Inject FacilityService via BookingService(facility_service=...)."
                )
            resources = await self.facility_service.list_resources(
                tenant_id=tenant_id, facility_id=facility_id
            )
            resource_ids = [r.id for r in resources]
            if not resource_ids:
                return []
            stmt = stmt.where(BookingModel.resource_id.in_(resource_ids))

        if resource_id:
            stmt = stmt.where(BookingModel.resource_id == resource_id)

        if statuses:
            stmt = stmt.where(BookingModel.status.in_([s.value for s in statuses]))

        result = await self.session.execute(stmt)
        return [_to_domain(m) for m in result.scalars().all()]


def _tariff_to_domain(m: BookingTariffModel) -> BookingTariff:
    return BookingTariff(
        id=m.id,
        tenant_id=m.tenant_id,
        resource_id=m.resource_id,
        day_of_week=m.day_of_week,
        time_start=m.time_start,
        time_end=m.time_end,
        price_cents=m.price_cents,
        currency=m.currency,
    )


class BookingTariffRepository:
    """Repository for managing booking tariff prices."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_resource(
        self,
        tenant_id: UUID,
        resource_id: UUID,
    ) -> list[BookingTariff]:
        """Get all tariffs for a resource."""
        stmt = select(BookingTariffModel).where(
            BookingTariffModel.tenant_id == tenant_id,
            BookingTariffModel.resource_id == resource_id,
        )
        result = await self.session.execute(stmt)
        return [_tariff_to_domain(m) for m in result.scalars().all()]

    async def add(self, tariff: BookingTariff) -> BookingTariff:
        """Create a new tariff."""
        m = BookingTariffModel(
            tenant_id=tariff.tenant_id,
            resource_id=tariff.resource_id,
            day_of_week=tariff.day_of_week,
            time_start=tariff.time_start,
            time_end=tariff.time_end,
            price_cents=tariff.price_cents,
            currency=tariff.currency,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return _tariff_to_domain(m)
