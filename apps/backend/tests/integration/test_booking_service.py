"""Integration tests for BookingService.

The critical test here is `test_double_booking_is_prevented`. This is the
single most important guarantee in the entire prototype: a confirmed booking
cannot overlap with another confirmed booking for the same resource.
"""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from auth.application.auth_service import AuthService
from auth.infrastructure.password_hasher import Argon2PasswordHasher
from auth.infrastructure.repositories import (
    RefreshTokenRepository,
    TenantRepository,
    UserRepository,
)
from auth.infrastructure.token_service import HS256TokenService
from booking.application.booking_service import BookingService
from booking.infrastructure.repositories import BookingRepository
from common.domain.exceptions import Conflict, NotFound
from common.domain.types import UserId
from common.infrastructure.db import Base
from customer.application.customer_service import CustomerService
from customer.infrastructure.repositories import CustomerRepository
from facility.application.facility_service import FacilityService
from facility.domain.entities import ResourceType
from facility.infrastructure.repositories import (
    AvailabilityRuleRepository,
    FacilityRepository,
    ResourceRepository,
)


pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh_test",
)


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=db_engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def seeded(session) -> dict:
    """Create a tenant + admin + customer + facility + resource.

    Returns a dict of domain objects useful for booking tests.
    """
    auth_svc = AuthService(
        session,
        password_hasher=Argon2PasswordHasher(),
        token_service=HS256TokenService(
            secret="integration-test-secret-must-be-long-enough",
            access_ttl=timedelta(minutes=15),
            refresh_ttl=timedelta(days=30),
        ),
        tenants=TenantRepository(session),
        users=UserRepository(session),
        refresh_tokens=RefreshTokenRepository(session),
    )
    tenant, admin = await auth_svc.register_tenant(
        tenant_name="Splashh",
        tenant_slug="splashh",
        primary_contact_email="c@s.com",
        admin_email="admin@s.com",
        admin_password="verysecurepassword123",
        admin_full_name="Admin",
    )

    # Create a member user (non-admin) so we can create a Customer profile
    member_pw_hash = Argon2PasswordHasher().hash("verysecurepassword123")
    from auth.domain.entities import User, UserRole

    member = User.create(
        tenant_id=tenant.id,
        email="member@s.com",
        password_hash=member_pw_hash,
        full_name="Test Member",
        roles=[UserRole.MEMBER],
    )
    member = await UserRepository(session).add(member)

    customer_svc = CustomerService(session, CustomerRepository(session))
    customer = await customer_svc.create_customer(
        tenant_id=tenant.id,
        user_id=member.id,
        full_name=member.full_name,
        email=member.email,
        phone="+919876543210",
    )

    facility_svc = FacilityService(
        session,
        FacilityRepository(session),
        ResourceRepository(session),
        AvailabilityRuleRepository(session),
    )
    facility = await facility_svc.create_facility(
        tenant_id=tenant.id,
        name="Splashh Koramangala",
        slug="koramangala",
        address_line1="123 Hosur Road",
        address_line2=None,
        city="Bangalore",
        state="Karnataka",
        postal_code="560029",
        country="IN",
        timezone_="Asia/Kolkata",
        phone="+919876543210",
    )
    resource = await facility_svc.create_resource(
        tenant_id=tenant.id,
        facility_id=facility.id,
        name="Court 1",
        slug="court-1",
        resource_type=ResourceType.COURT,
        capacity=2,
    )

    # Commit so the seeded data is visible to other sessions (e.g. the
    # concurrent-booking test which spawns 5 independent sessions).
    await session.commit()

    return {
        "tenant_id": tenant.id,
        "admin_id": admin.id,
        "member_id": member.id,
        "customer_id": customer.id,
        "facility_id": facility.id,
        "resource_id": resource.id,
    }


@pytest_asyncio.fixture
async def booking_service(session) -> BookingService:
    return BookingService(session, BookingRepository(session))


@pytest.mark.asyncio
class TestBookingCreation:
    async def test_create_booking_succeeds(
        self, booking_service: BookingService, seeded: dict
    ) -> None:
        start = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        end = datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc)
        booking = await booking_service.create_booking(
            tenant_id=seeded["tenant_id"],
            customer_id=seeded["customer_id"],
            resource_id=seeded["resource_id"],
            start_at=start,
            end_at=end,
            price_cents=50000,
        )
        assert booking.id is not None
        assert booking.status.value == "confirmed"

    async def test_double_booking_is_prevented(
        self, booking_service: BookingService, seeded: dict
    ) -> None:
        start = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        end = datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc)
        await booking_service.create_booking(
            tenant_id=seeded["tenant_id"],
            customer_id=seeded["customer_id"],
            resource_id=seeded["resource_id"],
            start_at=start,
            end_at=end,
        )
        with pytest.raises(Conflict):
            await booking_service.create_booking(
                tenant_id=seeded["tenant_id"],
                customer_id=seeded["customer_id"],
                resource_id=seeded["resource_id"],
                start_at=start,
                end_at=end,
            )

    async def test_overlapping_booking_is_prevented(
        self, booking_service: BookingService, seeded: dict
    ) -> None:
        # First booking 10:00-11:00
        await booking_service.create_booking(
            tenant_id=seeded["tenant_id"],
            customer_id=seeded["customer_id"],
            resource_id=seeded["resource_id"],
            start_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
        )
        # Overlapping booking 10:30-11:30 should fail
        with pytest.raises(Conflict):
            await booking_service.create_booking(
                tenant_id=seeded["tenant_id"],
                customer_id=seeded["customer_id"],
                resource_id=seeded["resource_id"],
                start_at=datetime(2026, 9, 1, 10, 30, tzinfo=timezone.utc),
                end_at=datetime(2026, 9, 1, 11, 30, tzinfo=timezone.utc),
            )

    async def test_adjacent_booking_is_allowed(
        self, booking_service: BookingService, seeded: dict
    ) -> None:
        # 10:00-11:00 then 11:00-12:00 should both succeed
        b1 = await booking_service.create_booking(
            tenant_id=seeded["tenant_id"],
            customer_id=seeded["customer_id"],
            resource_id=seeded["resource_id"],
            start_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
        )
        b2 = await booking_service.create_booking(
            tenant_id=seeded["tenant_id"],
            customer_id=seeded["customer_id"],
            resource_id=seeded["resource_id"],
            start_at=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        )
        assert b1.id != b2.id

    async def test_concurrent_bookings_only_one_succeeds(
        self, booking_service: BookingService, seeded: dict, session_factory
    ) -> None:
        """Spawn 5 concurrent bookings for the same slot. Exactly 1 should win."""
        from booking.infrastructure.repositories import BookingRepository
        from common.domain.exceptions import Conflict

        start = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        end = datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc)

        async def try_book() -> str:
            async with session_factory() as s:
                svc = BookingService(s, BookingRepository(s))
                try:
                    await svc.create_booking(
                        tenant_id=seeded["tenant_id"],
                        customer_id=seeded["customer_id"],
                        resource_id=seeded["resource_id"],
                        start_at=start,
                        end_at=end,
                    )
                    # Commit so the row is visible to the other concurrent
                    # sessions. Without this, the session rolls back on
                    # context exit and the SELECT FOR UPDATE lock is released
                    # without persisting the booking — every goroutine would
                    # then see a clean table and all 5 would succeed.
                    await s.commit()
                    return "ok"
                except Conflict:
                    await s.rollback()
                    return "conflict"

        results = await asyncio.gather(*[try_book() for _ in range(5)])
        ok_count = results.count("ok")
        conflict_count = results.count("conflict")
        assert ok_count == 1, f"Expected exactly 1 success, got {ok_count}: {results}"
        assert conflict_count == 4


@pytest.mark.asyncio
class TestBookingCancellation:
    async def test_cancel_confirmed_booking(
        self, booking_service: BookingService, seeded: dict
    ) -> None:
        booking = await booking_service.create_booking(
            tenant_id=seeded["tenant_id"],
            customer_id=seeded["customer_id"],
            resource_id=seeded["resource_id"],
            start_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
        )
        cancelled = await booking_service.cancel_booking(
            tenant_id=seeded["tenant_id"], booking_id=booking.id
        )
        assert cancelled.status.value == "cancelled"

    async def test_can_rebook_after_cancellation(
        self, booking_service: BookingService, seeded: dict
    ) -> None:
        start = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        end = datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc)
        b1 = await booking_service.create_booking(
            tenant_id=seeded["tenant_id"],
            customer_id=seeded["customer_id"],
            resource_id=seeded["resource_id"],
            start_at=start,
            end_at=end,
        )
        await booking_service.cancel_booking(
            tenant_id=seeded["tenant_id"], booking_id=b1.id
        )
        # The slot is now free; another booking should succeed
        b2 = await booking_service.create_booking(
            tenant_id=seeded["tenant_id"],
            customer_id=seeded["customer_id"],
            resource_id=seeded["resource_id"],
            start_at=start,
            end_at=end,
        )
        assert b2.id != b1.id

    async def test_cannot_cancel_twice(
        self, booking_service: BookingService, seeded: dict
    ) -> None:
        from common.domain.exceptions import InvariantViolation

        booking = await booking_service.create_booking(
            tenant_id=seeded["tenant_id"],
            customer_id=seeded["customer_id"],
            resource_id=seeded["resource_id"],
            start_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
        )
        await booking_service.cancel_booking(
            tenant_id=seeded["tenant_id"], booking_id=booking.id
        )
        with pytest.raises(InvariantViolation):
            await booking_service.cancel_booking(
                tenant_id=seeded["tenant_id"], booking_id=booking.id
            )
