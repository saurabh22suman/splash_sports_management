"""Booking repository — the heart of double-booking prevention.

The `add_safe` method is the **only** way to insert a booking. It acquires
a row-level lock on the resource, then checks for any overlapping confirmed
bookings, before inserting.

> See [Booking Flow](../../../docs/02-architecture/flow-booking.md) for the
> full design rationale.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from booking.domain.entities import Booking, BookingStatus, CancellationReason
from booking.infrastructure.models import BookingModel
from common.domain.exceptions import Conflict, InvariantViolation, NotFound
from common.infrastructure.repository import BaseRepository


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
        cancellation_reason=CancellationReason(m.cancellation_reason) if m.cancellation_reason else None,
        cancelled_at=m.cancelled_at,
        checked_in_at=m.checked_in_at,
        completed_at=m.completed_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class BookingRepository(BaseRepository[Booking]):
    model = BookingModel

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
        from facility.infrastructure.models import ResourceModel

        # 1. Lock the resource row. This serializes concurrent bookings
        #    against the same resource.
        resource_lock = (
            select(ResourceModel)
            .where(
                ResourceModel.id == booking.resource_id,
                ResourceModel.tenant_id == booking.tenant_id,
            )
            .with_for_update()
        )
        resource = (await self.session.execute(resource_lock)).scalar_one_or_none()
        if resource is None:
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
        m.cancellation_reason = booking.cancellation_reason.value if booking.cancellation_reason else None
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
    ) -> list[Booking]:
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
            stmt = stmt.where(
                BookingModel.status.in_([s.value for s in statuses])
            )
        result = await self.session.execute(stmt)
        return [_to_domain(m) for m in result.scalars().all()]

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
