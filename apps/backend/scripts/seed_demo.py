"""Seed a demo 'Splash Sports Club' facility for the first/only dev tenant.

Idempotent: re-runs are no-ops once a facility with slug 'splash-sports-club'
exists for the target tenant.

Run via:
    make -C apps/backend seed-demo
or directly:
    PYTHONPATH=src uv run python apps/backend/scripts/seed_demo.py

For mock data seeding (full dataset):
    PYTHONPATH=src uv run python apps/backend/scripts/seed_demo.py --mock
"""

from __future__ import annotations

import sys
import argparse
from typing import TextIO

from datetime import time
from sqlalchemy import select

from auth.infrastructure.models import TenantModel
from facility.application.facility_service import FacilityService
from facility.domain.entities import ResourceType
from facility.infrastructure.models import FacilityModel
from facility.infrastructure.repositories import (
    AvailabilityRuleRepository,
    FacilityRepository,
    ResourceRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession

# Exit codes
EXIT_OK = 0
EXIT_NO_TENANT = 1


# Module-level constants (the spec's seeded values)
FACILITY_SLUG = "splash-sports-club"
FACILITY_NAME = "Splash Sports Club"
FACILITY_ADDRESS_LINE1 = "123 Aquatic Drive"
FACILITY_CITY = "Sydney"
FACILITY_STATE = "NSW"
FACILITY_POSTAL_CODE = "2000"
FACILITY_COUNTRY = "AU"
FACILITY_TIMEZONE = "Australia/Sydney"
FACILITY_PHONE = "+61 2 0000 0000"

RESOURCE_SLUG = "main-pool"
RESOURCE_NAME = "Main Pool"
RESOURCE_CAPACITY = 20
RESOURCE_ATTRIBUTES: dict[str, object] = {"lanes": 6, "length_m": 25, "min_age": 5}

OPENING_START = time(6, 0)
OPENING_END = time(22, 0)
SLOT_MINUTES = 60


async def seed_demo(session: AsyncSession, *, stdout: TextIO = sys.stdout) -> int:
    """Seed the demo facility. Returns the process exit code."""
    # 1. Pick the first/only tenant.
    tenant: TenantModel | None = (
        await session.execute(select(TenantModel).order_by(TenantModel.created_at.asc()).limit(1))
    ).scalar_one_or_none()
    if tenant is None:
        print("No tenant found. Run register-tenant first.", file=stdout)
        return EXIT_NO_TENANT

    # 2. Idempotency: skip if the demo facility already exists for this tenant.
    existing = (
        await session.execute(
            select(FacilityModel).where(
                FacilityModel.tenant_id == tenant.id,
                FacilityModel.slug == FACILITY_SLUG,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        print(
            f"Already seeded for tenant {tenant.slug}; nothing to do.",
            file=stdout,
        )
        return EXIT_OK

    # 3. Build the service with the same repos the API uses.
    service = FacilityService(
        session=session,
        facilities=FacilityRepository(session),
        resources=ResourceRepository(session),
        rules=AvailabilityRuleRepository(session),
    )

    facility = await service.create_facility(
        tenant_id=tenant.id,
        name=FACILITY_NAME,
        slug=FACILITY_SLUG,
        address_line1=FACILITY_ADDRESS_LINE1,
        address_line2=None,
        city=FACILITY_CITY,
        state=FACILITY_STATE,
        postal_code=FACILITY_POSTAL_CODE,
        country=FACILITY_COUNTRY,
        timezone_=FACILITY_TIMEZONE,
        phone=FACILITY_PHONE,
    )

    pool = await service.create_resource(
        tenant_id=tenant.id,
        facility_id=facility.id,
        name=RESOURCE_NAME,
        slug=RESOURCE_SLUG,
        resource_type=ResourceType.POOL,
        capacity=RESOURCE_CAPACITY,
        attributes=RESOURCE_ATTRIBUTES,
    )

    for day_of_week in range(7):
        await service.create_availability_rule(
            tenant_id=tenant.id,
            resource_id=pool.id,
            day_of_week=day_of_week,
            start_time=OPENING_START,
            end_time=OPENING_END,
            slot_duration_minutes=SLOT_MINUTES,
        )

    await session.commit()

    print(
        f"Seeded '{FACILITY_NAME}' + 1 pool + 7 availability rules for tenant {tenant.slug}.",
        file=stdout,
    )
    return EXIT_OK


async def _main(mock: bool = False) -> int:
    """CLI entry point: bootstrap engine + session, run seed script, exit."""
    from common.infrastructure.db import init_engine, get_session_factory, dispose_engine
    from common.infrastructure.settings import get_settings

    if mock:
        from scripts.mock_data import seed_mock_data

    settings = get_settings()
    await init_engine(settings)
    try:
        factory = get_session_factory()
        async with factory() as session:
            if mock:
                await seed_mock_data(session)
                return EXIT_OK
            return await seed_demo(session)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    import asyncio

    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Seed full mock data (tenant, users, customers, facilities, bookings)",
    )
    args = parser.parse_args()

    raise SystemExit(asyncio.run(_main(mock=args.mock)))
