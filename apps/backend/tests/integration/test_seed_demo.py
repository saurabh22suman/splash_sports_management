"""Integration tests for the seed_demo script."""
from __future__ import annotations

import io
import os
from collections.abc import AsyncIterator
from datetime import datetime, time, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from auth.infrastructure.models import TenantModel
from common.infrastructure.db import Base
from facility.domain.entities import ResourceType
from facility.infrastructure.models import (
    AvailabilityRuleModel,
    FacilityModel,
    ResourceModel,
)

# Same fixture pattern as tests/integration/test_auth_service.py
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


@pytest_asyncio.fixture
async def tenant(session) -> TenantModel:
    now = datetime.now(timezone.utc)
    t = TenantModel(
        id=uuid4(),
        name="Demo Tenant",
        slug="demo-tenant",
        status="active",
        primary_contact_email="admin@example.com",
        created_at=now,
        updated_at=now,
    )
    session.add(t)
    await session.flush()
    return t


from scripts.seed_demo import seed_demo  # noqa: E402

pytestmark = pytest.mark.integration


async def test_seed_demo_creates_facility_pool_and_seven_rules(session, tenant):
    stdout = io.StringIO()
    exit_code = await seed_demo(session, stdout=stdout)

    assert exit_code == 0

    facility = (
        await session.execute(
            select(FacilityModel).where(
                FacilityModel.tenant_id == tenant.id,
                FacilityModel.slug == "splash-sports-club",
            )
        )
    ).scalar_one()
    assert facility.name == "Splash Sports Club"
    assert facility.country == "AU"
    assert facility.timezone == "Australia/Sydney"

    pool = (
        await session.execute(
            select(ResourceModel).where(ResourceModel.facility_id == facility.id)
        )
    ).scalar_one()
    assert pool.resource_type == ResourceType.POOL.value
    assert pool.capacity == 20
    assert pool.attributes == {"lanes": 6, "length_m": 25, "min_age": 5}

    rules = (
        (
            await session.execute(
                select(AvailabilityRuleModel).where(
                    AvailabilityRuleModel.resource_id == pool.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rules) == 7
    assert {r.day_of_week for r in rules} == set(range(7))
    for r in rules:
        assert r.start_time == time(6, 0)
        assert r.end_time == time(22, 0)
        assert r.slot_duration_minutes == 60

    assert "Splash Sports Club" in stdout.getvalue()
