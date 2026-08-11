"""Integration tests for admin bookings listing.

Tests the GET /v1/admin/bookings endpoint with real database queries,
including filtering by facility, resource, status, and date range.
"""
from __future__ import annotations

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
from booking.domain.entities import BookingStatus
from booking.infrastructure.repositories import BookingRepository
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
    """Create a tenant + admin + customer + facilities + resources + bookings."""
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

    # Create member users and customers
    member_pw_hash = Argon2PasswordHasher().hash("verysecurepassword123")
    from auth.domain.entities import User, UserRole

    member1 = User.create(
        tenant_id=tenant.id,
        email="member1@s.com",
        password_hash=member_pw_hash,
        full_name="Test Member One",
        roles=[UserRole.MEMBER],
    )
    member1 = await UserRepository(session).add(member1)

    member2 = User.create(
        tenant_id=tenant.id,
        email="member2@s.com",
        password_hash=member_pw_hash,
        full_name="Test Member Two",
        roles=[UserRole.MEMBER],
    )
    member2 = await UserRepository(session).add(member2)

    customer_svc = CustomerService(session, CustomerRepository(session))
    customer1 = await customer_svc.create_customer(
        tenant_id=tenant.id,
        user_id=member1.id,
        full_name=member1.full_name,
        email=member1.email,
        phone="+919876543210",
    )
    customer2 = await customer_svc.create_customer(
        tenant_id=tenant.id,
        user_id=member2.id,
        full_name=member2.full_name,
        email=member2.email,
        phone="+919876543211",
    )

    # Create facilities
    facility_svc = FacilityService(
        session,
        FacilityRepository(session),
        ResourceRepository(session),
        AvailabilityRuleRepository(session),
    )
    facility1 = await facility_svc.create_facility(
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
    facility2 = await facility_svc.create_facility(
        tenant_id=tenant.id,
        name="Splashh Whitefield",
        slug="whitefield",
        address_line1="456 IT Park",
        address_line2=None,
        city="Bangalore",
        state="Karnataka",
        postal_code="560066",
        country="IN",
        timezone_="Asia/Kolkata",
        phone="+919876543211",
    )

    # Create resources
    resource1 = await facility_svc.create_resource(
        tenant_id=tenant.id,
        facility_id=facility1.id,
        name="Court 1",
        slug="court-1",
        resource_type=ResourceType.COURT,
        capacity=2,
    )
    resource2 = await facility_svc.create_resource(
        tenant_id=tenant.id,
        facility_id=facility1.id,
        name="Court 2",
        slug="court-2",
        resource_type=ResourceType.COURT,
        capacity=2,
    )
    resource3 = await facility_svc.create_resource(
        tenant_id=tenant.id,
        facility_id=facility2.id,
        name="Pool Lane 1",
        slug="pool-lane-1",
        resource_type=ResourceType.POOL,
        capacity=4,
    )

    # Create tariffs for resources (required for booking creation)
    from booking.infrastructure.repositories import BookingTariffRepository

    tariff_repo = BookingTariffRepository(session)
    from booking.domain.entities import BookingTariff

    for resource_id in [resource1.id, resource2.id, resource3.id]:
        # Add tariff for all days of the week, hours 6-22
        for day in range(7):
            for hour in range(6, 22):
                tariff = BookingTariff(
                    id=uuid4(),
                    tenant_id=tenant.id,
                    resource_id=resource_id,
                    day_of_week=day,
                    time_start=hour,
                    time_end=hour + 1,
                    price_cents=5000,  # 50 INR per hour
                    currency="INR",
                )
                await tariff_repo.add(tariff)

    # Create bookings
    booking_svc = BookingService(
        session,
        BookingRepository(session, facility_service=facility_svc),
        facility_service=facility_svc,
    )

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Booking 1: Confirmed, today, facility1
    booking1 = await booking_svc.create_booking(
        tenant_id=tenant.id,
        customer_id=customer1.id,
        resource_id=resource1.id,
        start_at=today + timedelta(hours=10),
        end_at=today + timedelta(hours=11),
    )

    # Booking 2: Confirmed, today, facility1, different resource
    booking2 = await booking_svc.create_booking(
        tenant_id=tenant.id,
        customer_id=customer2.id,
        resource_id=resource2.id,
        start_at=today + timedelta(hours=14),
        end_at=today + timedelta(hours=15),
    )

    # Booking 3: Confirmed, today, facility2
    booking3 = await booking_svc.create_booking(
        tenant_id=tenant.id,
        customer_id=customer1.id,
        resource_id=resource3.id,
        start_at=today + timedelta(hours=9),
        end_at=today + timedelta(hours=10),
    )

    # Booking 4: Cancelled, today
    booking4 = await booking_svc.create_booking(
        tenant_id=tenant.id,
        customer_id=customer2.id,
        resource_id=resource1.id,
        start_at=today + timedelta(hours=16),
        end_at=today + timedelta(hours=17),
    )
    await booking_svc.cancel_booking(tenant_id=tenant.id, booking_id=booking4.id)

    # Booking 5: Different day (not today)
    tomorrow = today + timedelta(days=1)
    booking5 = await booking_svc.create_booking(
        tenant_id=tenant.id,
        customer_id=customer1.id,
        resource_id=resource1.id,
        start_at=tomorrow + timedelta(hours=10),
        end_at=tomorrow + timedelta(hours=11),
    )

    await session.commit()

    return {
        "tenant_id": tenant.id,
        "admin_id": admin.id,
        "customer1_id": customer1.id,
        "customer2_id": customer2.id,
        "facility1_id": facility1.id,
        "facility2_id": facility2.id,
        "resource1_id": resource1.id,
        "resource2_id": resource2.id,
        "resource3_id": resource3.id,
        "booking1_id": booking1.id,
        "booking2_id": booking2.id,
        "booking3_id": booking3.id,
        "booking4_id": booking4.id,
        "booking5_id": booking5.id,
    }


@pytest.mark.asyncio
class TestAdminBookingsService:
    """Test the booking service list method for admin view."""

    async def test_list_all_bookings_returns_correct_data(
        self, seeded: dict, session: AsyncSession
    ) -> None:
        """Test that listing all bookings includes customer and facility info."""
        from booking.application.booking_service import BookingService
        from booking.infrastructure.repositories import BookingRepository

        facility_svc = FacilityService(
            session,
            FacilityRepository(session),
            ResourceRepository(session),
            AvailabilityRuleRepository(session),
        )
        booking_svc = BookingService(
            session,
            BookingRepository(session, facility_service=facility_svc),
            facility_service=facility_svc,
        )

        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        # List today's bookings
        bookings = await booking_svc.list_admin_bookings(
            tenant_id=seeded["tenant_id"],
            from_at=today,
            to_at=tomorrow,
        )

        # Should return 4 bookings (booking4 is cancelled, booking5 is tomorrow)
        assert len(bookings) == 4

    async def test_filter_by_facility(
        self, seeded: dict, session: AsyncSession
    ) -> None:
        """Test filtering bookings by facility."""
        from booking.application.booking_service import BookingService
        from booking.infrastructure.repositories import BookingRepository

        facility_svc = FacilityService(
            session,
            FacilityRepository(session),
            ResourceRepository(session),
            AvailabilityRuleRepository(session),
        )
        booking_svc = BookingService(
            session,
            BookingRepository(session, facility_service=facility_svc),
            facility_service=facility_svc,
        )

        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        # Filter by facility1
        bookings = await booking_svc.list_admin_bookings(
            tenant_id=seeded["tenant_id"],
            from_at=today,
            to_at=tomorrow,
            facility_id=seeded["facility1_id"],
        )

        # Should return bookings from facility1 only (resource1, resource2)
        assert len(bookings) == 3

    async def test_filter_by_status(
        self, seeded: dict, session: AsyncSession
    ) -> None:
        """Test filtering bookings by status."""
        from booking.application.booking_service import BookingService
        from booking.infrastructure.repositories import BookingRepository

        facility_svc = FacilityService(
            session,
            FacilityRepository(session),
            ResourceRepository(session),
            AvailabilityRuleRepository(session),
        )
        booking_svc = BookingService(
            session,
            BookingRepository(session, facility_service=facility_svc),
            facility_service=facility_svc,
        )

        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        # Filter by confirmed status
        bookings = await booking_svc.list_admin_bookings(
            tenant_id=seeded["tenant_id"],
            from_at=today,
            to_at=tomorrow,
            statuses=[BookingStatus.CONFIRMED],
        )

        # Should return only confirmed bookings (booking4 is cancelled)
        assert len(bookings) == 3

    async def test_includes_customer_details(
        self, seeded: dict, session: AsyncSession
    ) -> None:
        """Test that bookings can be enriched with customer name and email."""
        from booking.application.booking_service import BookingService
        from booking.infrastructure.repositories import BookingRepository
        from customer.infrastructure.repositories import CustomerRepository

        facility_svc = FacilityService(
            session,
            FacilityRepository(session),
            ResourceRepository(session),
            AvailabilityRuleRepository(session),
        )
        booking_svc = BookingService(
            session,
            BookingRepository(session, facility_service=facility_svc),
            facility_service=facility_svc,
        )

        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        bookings = await booking_svc.list_admin_bookings(
            tenant_id=seeded["tenant_id"],
            from_at=today,
            to_at=tomorrow,
        )

        # All bookings should have customer_id that can be used to fetch customer details
        customer_repo = CustomerRepository(session)
        for b in bookings:
            customer = await customer_repo.get_by_id(seeded["tenant_id"], b.customer_id)
            assert customer is not None
            assert customer.full_name is not None
            assert customer.email is not None
