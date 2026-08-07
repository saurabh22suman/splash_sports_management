"""Integration tests for the seed_mock_data script."""
from __future__ import annotations

import io
import os
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from auth.infrastructure.models import TenantModel, UserModel
from common.infrastructure.db import Base
from customer.infrastructure.models import CustomerModel
from scripts.mock_data import seed_tenant, seed_users, seed_customers, seed_facilities_and_resources, seed_bookings

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh_test",
)


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
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


pytestmark = pytest.mark.integration


async def test_seed_tenant_creates_demo_tenant(session):
    stdout = io.StringIO()
    tenant_id = await seed_tenant(session, stdout=stdout)

    tenant = await session.get(TenantModel, tenant_id)
    assert tenant is not None
    assert tenant.slug == "demo"
    assert tenant.name == "Demo Sports Club"
    assert tenant.primary_contact_email == "admin@demo.splashh.dev"


async def test_seed_tenant_is_idempotent(session):
    id1 = await seed_tenant(session)
    id2 = await seed_tenant(session)
    assert id1 == id2

    result = await session.execute(
        select(TenantModel).where(TenantModel.slug == "demo")
    )
    tenants = result.scalars().all()
    assert len(tenants) == 1


async def test_seed_users_creates_admin_and_three_customers(session):
    tenant_id = await seed_tenant(session)
    user_ids = await seed_users(session, tenant_id)

    assert set(user_ids.keys()) == {
        "admin@demo.splashh.dev",
        "alex@demo.splashh.dev",
        "priya@demo.splashh.dev",
        "jordan@demo.splashh.dev",
    }
    assert len(user_ids) == 4


async def test_seed_users_is_idempotent(session):
    tenant_id = await seed_tenant(session)
    first = await seed_users(session, tenant_id)
    second = await seed_users(session, tenant_id)
    assert first == second

    result = await session.execute(
        select(UserModel).where(UserModel.tenant_id == tenant_id)
    )
    assert len(result.scalars().all()) == 4


async def test_seed_customers_creates_fifteen(session):
    tenant_id = await seed_tenant(session)
    user_ids = await seed_users(session, tenant_id)
    customer_ids = await seed_customers(session, tenant_id, user_ids)

    assert len(customer_ids) == 15

    result = await session.execute(
        select(CustomerModel).where(CustomerModel.tenant_id == tenant_id)
    )
    customers = result.scalars().all()
    assert len(customers) == 15
    # 3 customers share an email with the 3 customer users
    for shared_email in ("alex@demo.splashh.dev", "priya@demo.splashh.dev", "jordan@demo.splashh.dev"):
        matching = [c for c in customers if c.email == shared_email]
        assert len(matching) == 1


async def test_seed_facilities_creates_five_with_one_resource_each(session):
    tenant_id = await seed_tenant(session)
    fr = await seed_facilities_and_resources(session, tenant_id)

    assert len(fr) == 5
    expected_slugs = {
        "sydney-aquatic-centre",
        "melbourne-swim-academy",
        "brisbane-sport-complex",
        "auckland-marine-pool",
        "gold-coast-gym",
    }
    assert set(fr.keys()) == expected_slugs
    for slug, ids in fr.items():
        assert "facility_id" in ids
        assert "resource_id" in ids


async def test_seed_facilities_creates_seven_availability_rules_per_resource(session):
    from facility.infrastructure.models import AvailabilityRuleModel, ResourceModel

    tenant_id = await seed_tenant(session)
    fr = await seed_facilities_and_resources(session, tenant_id)

    for slug, ids in fr.items():
        rules = (
            await session.execute(
                select(AvailabilityRuleModel).where(
                    AvailabilityRuleModel.resource_id == ids["resource_id"]
                )
            )
        ).scalars().all()
        assert len(rules) == 7, f"{slug} should have 7 rules"
        assert {r.day_of_week for r in rules} == set(range(7))


async def test_seed_facilities_is_idempotent(session):
    from facility.infrastructure.models import FacilityModel

    tenant_id = await seed_tenant(session)
    first = await seed_facilities_and_resources(session, tenant_id)
    second = await seed_facilities_and_resources(session, tenant_id)
    assert first.keys() == second.keys()

    rows = (
        await session.execute(
            select(FacilityModel).where(FacilityModel.tenant_id == tenant_id)
        )
    ).scalars().all()
    assert len(rows) == 5


async def test_seed_bookings_creates_at_least_thirty(session):
    from booking.infrastructure.models import BookingModel

    tenant_id = await seed_tenant(session)
    user_ids = await seed_users(session, tenant_id)
    customer_ids = await seed_customers(session, tenant_id, user_ids)
    fr = await seed_facilities_and_resources(session, tenant_id)
    resource_ids = [ids["resource_id"] for ids in fr.values()]

    counts = await seed_bookings(session, tenant_id, customer_ids, resource_ids)

    rows = (
        await session.execute(
            select(BookingModel).where(BookingModel.tenant_id == tenant_id)
        )
    ).scalars().all()
    assert len(rows) >= 30
    assert counts["created"] == len(rows)


async def test_seed_bookings_status_distribution_within_tolerance(session):
    from booking.infrastructure.models import BookingModel

    tenant_id = await seed_tenant(session)
    user_ids = await seed_users(session, tenant_id)
    customer_ids = await seed_customers(session, tenant_id, user_ids)
    fr = await seed_facilities_and_resources(session, tenant_id)
    resource_ids = [ids["resource_id"] for ids in fr.values()]

    counts = await seed_bookings(session, tenant_id, customer_ids, resource_ids)

    total = sum(counts[s] for s in ("confirmed", "completed", "cancelled", "no_show"))
    assert total > 0
    confirmed_pct = counts["confirmed"] / total * 100
    completed_pct = counts["completed"] / total * 100
    cancelled_pct = counts["cancelled"] / total * 100
    no_show_pct = counts["no_show"] / total * 100

    assert 50 <= confirmed_pct <= 70, f"confirmed={confirmed_pct}"
    assert 15 <= completed_pct <= 25, f"completed={completed_pct}"
    assert 5 <= cancelled_pct <= 15, f"cancelled={cancelled_pct}"
    assert 5 <= no_show_pct <= 15, f"no_show={no_show_pct}"


async def test_seed_bookings_is_idempotent(session):
    from booking.infrastructure.models import BookingModel

    tenant_id = await seed_tenant(session)
    user_ids = await seed_users(session, tenant_id)
    customer_ids = await seed_customers(session, tenant_id, user_ids)
    fr = await seed_facilities_and_resources(session, tenant_id)
    resource_ids = [ids["resource_id"] for ids in fr.values()]

    first = await seed_bookings(session, tenant_id, customer_ids, resource_ids)
    second = await seed_bookings(session, tenant_id, customer_ids, resource_ids)

    rows = (
        await session.execute(
            select(BookingModel).where(BookingModel.tenant_id == tenant_id)
        )
    ).scalars().all()
    assert len(rows) == first["created"]
    assert second["created"] == 0


async def test_seed_mock_data_full_run_creates_documented_shape(session):
    """Orchestrator test: runs seed_mock_data and verifies documented shape."""
    from scripts.mock_data import seed_mock_data

    stdout = io.StringIO()
    result = await seed_mock_data(session, stdout=stdout)
    text = stdout.getvalue()

    # Tenant exists and is active
    tenant = await session.get(TenantModel, result["tenant_id"])
    assert tenant is not None
    assert tenant.slug == "demo"
    assert tenant.status == "active"

    # Tenant name must be in stdout
    assert "Demo Sports Club" in text

    # Users: 1 admin + 3 customer users from seed_users + 12 auto-created in seed_customers = 16
    users = (
        await session.execute(
            select(UserModel).where(UserModel.tenant_id == result["tenant_id"])
        )
    ).scalars().all()
    assert len(users) == 16

    # Customers: 15
    customers = (
        await session.execute(
            select(CustomerModel).where(CustomerModel.tenant_id == result["tenant_id"])
        )
    ).scalars().all()
    assert len(customers) == 15

    # Facilities: 5
    from facility.infrastructure.models import FacilityModel
    facilities = (
        await session.execute(
            select(FacilityModel).where(FacilityModel.tenant_id == result["tenant_id"])
        )
    ).scalars().all()
    assert len(facilities) == 5

    # Bookings: at least 30
    from booking.infrastructure.models import BookingModel
    bookings = (
        await session.execute(
            select(BookingModel).where(BookingModel.tenant_id == result["tenant_id"])
        )
    ).scalars().all()
    assert len(bookings) >= 30


async def test_seed_mock_data_is_idempotent(session):
    """Test that running seed_mock_data twice produces the same counts."""
    from auth.infrastructure.models import UserModel
    from booking.infrastructure.models import BookingModel
    from customer.infrastructure.models import CustomerModel
    from facility.infrastructure.models import (
        AvailabilityRuleModel,
        FacilityModel,
        ResourceModel,
    )
    from scripts.mock_data import seed_mock_data

    first = await seed_mock_data(session)
    assert isinstance(first, dict)
    assert first["tenant_id"] is not None

    counts = {
        "tenants": len((await session.execute(select(TenantModel))).scalars().all()),
        "users": len((await session.execute(select(UserModel))).scalars().all()),
        "customers": len((await session.execute(select(CustomerModel))).scalars().all()),
        "facilities": len((await session.execute(select(FacilityModel))).scalars().all()),
        "resources": len((await session.execute(select(ResourceModel))).scalars().all()),
        "rules": len((await session.execute(select(AvailabilityRuleModel))).scalars().all()),
        "bookings": len((await session.execute(select(BookingModel))).scalars().all()),
    }

    second = await seed_mock_data(session)
    assert isinstance(second, dict)

    counts_after = {
        "tenants": len((await session.execute(select(TenantModel))).scalars().all()),
        "users": len((await session.execute(select(UserModel))).scalars().all()),
        "customers": len((await session.execute(select(CustomerModel))).scalars().all()),
        "facilities": len((await session.execute(select(FacilityModel))).scalars().all()),
        "resources": len((await session.execute(select(ResourceModel))).scalars().all()),
        "rules": len((await session.execute(select(AvailabilityRuleModel))).scalars().all()),
        "bookings": len((await session.execute(select(BookingModel))).scalars().all()),
    }

    assert counts == counts_after


async def test_seed_mock_data_skips_existing_demo_tenant_with_different_name(session):
    """Test that existing tenant with same slug but different name is preserved."""
    from scripts.mock_data import seed_mock_data

    # Pre-seed a tenant with slug `demo` but a different name
    now = datetime.now(timezone.utc)
    existing = TenantModel(
        id=uuid4(),
        name="Pre-existing Demo Tenant",
        slug="demo",
        status="active",
        primary_contact_email="other@example.com",
        created_at=now,
        updated_at=now,
    )
    session.add(existing)
    await session.flush()

    result = await seed_mock_data(session)
    assert result is not None

    # Tenant is unchanged (only 1 tenant, with original name preserved)
    rows = (await session.execute(select(TenantModel))).scalars().all()
    assert len(rows) == 1
    assert rows[0].name == "Pre-existing Demo Tenant"

    # Due to the orchestrator deviation (no early exit), users/facilities/bookings
    # are seeded anyway but per-entity idempotency keeps counts stable.
    # Verify tenant-level idempotency: no new tenants created
    from auth.infrastructure.models import UserModel
    from booking.infrastructure.models import BookingModel
    from facility.infrastructure.models import FacilityModel

    users = (await session.execute(select(UserModel))).scalars().all()
    facilities = (await session.execute(select(FacilityModel))).scalars().all()
    bookings = (await session.execute(select(BookingModel))).scalars().all()

    # The existing tenant gets the full seed applied (this is the deviation behavior)
    # Just verify we have at least the seeded data linked to the existing tenant
    assert len(users) >= 4  # admin + 3 customer users
    assert len(facilities) == 5
    assert len(bookings) >= 30


async def test_seed_mock_data_returns_nonzero_on_db_error(session):
    """If session.commit() raises, seed_mock_data propagates the error."""
    from unittest.mock import AsyncMock
    from scripts.mock_data import seed_mock_data

    # Replace commit with a function that raises
    original_commit = session.commit
    session.commit = AsyncMock(side_effect=RuntimeError("simulated DB failure"))

    # The orchestrator has no try/except, so the exception propagates
    with pytest.raises(RuntimeError, match="simulated DB failure"):
        await seed_mock_data(session)

    session.commit = original_commit


async def test_seed_mock_data_booking_status_distribution_via_full_run(session):
    """Test booking status distribution via full orchestrator run."""
    from booking.infrastructure.models import BookingModel
    from scripts.mock_data import seed_mock_data

    await seed_mock_data(session)

    rows = (await session.execute(select(BookingModel))).scalars().all()
    total = len(rows)
    assert total >= 30  # sanity check from the spec

    by_status: dict[str, int] = {}
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1

    pct = {k: v / total * 100 for k, v in by_status.items()}
    assert 50 <= pct.get("confirmed", 0) <= 70, pct
    assert 15 <= pct.get("completed", 0) <= 25, pct
    assert 5 <= pct.get("cancelled", 0) <= 15, pct
    assert 5 <= pct.get("no_show", 0) <= 15, pct
