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
from scripts.mock_data import seed_tenant, seed_users, seed_customers, seed_facilities_and_resources

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
