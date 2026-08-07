# Mock Data Seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a curated, idempotent Python seeder (`apps/backend/scripts/mock_data.py`) that populates a local DB with a `demo` tenant, 5 AU/NZ facilities, 4 users, 15 customers, and ~50 bookings across varied statuses — so stakeholder demos show populated data instead of empty pages.

**Architecture:** A standalone async Python module that opens a real DB session, drives the existing `FacilityService`, `BookingService`, `CustomerService`, and `AuthService` (or equivalent repositories) to create the documented shape, and returns counts of created/skipped entities. Wired into a new `--mock` flag on `seed_demo.py` and exposed as `pnpm seed:mock`.

**Tech Stack:** Python 3.12, SQLAlchemy 2 (async), asyncpg, the existing `FacilityService` / `BookingService` / `CustomerService` / `AuthService` / `UserRepository` / `TenantRepository`, uv (run), pytest + pytest-asyncio (integration tests against real Postgres), Makefile + pnpm.

## Global Constraints

These apply to every task. Copied verbatim from the spec:

- Idempotent: tenant-level gate (skip the whole seed if a tenant with slug `demo` exists, per spec's `test_seed_mock_data_skips_existing_demo_tenant`) + per-entity idempotency (each sub-function skips if its natural key already exists, as defense-in-depth for partial-seed scenarios).
- Reuses `FacilityService.create_facility / create_resource / create_availability_rule`, `BookingService.create_booking`, `CustomerService.create_customer`, `UserRepository.add`, `TenantRepository.add` — no raw SQL inserts.
- Tenant: slug `demo`, name `Demo Sports Club`, primary contact `admin@demo.splashh.dev`. Skip if any tenant with slug `demo` exists.
- Users: 1 admin (`admin@demo.splashh.dev`, role `tenant_admin`, password `Admin!Demo2026`) + 3 customer users (`alex@demo.splashh.dev`, `priya@demo.splashh.dev`, `jordan@demo.splashh.dev`, role `customer`, passwords `Customer!Demo1/2/3`). Skip if `(tenant_id, email)` already has a user.
- Customers: 15 hand-curated profiles. 3 share an email with the 3 customer users. Skip if `(tenant_id, email)` already has a customer.
- Facilities: 5 in AU/NZ (Sydney, Melbourne, Brisbane, Auckland, Gold Coast). Each gets 1 resource (pool/court/gym floor). 7 availability rules per resource (one per day-of-week). Skip facility if `(tenant_id, slug)` exists; skip resource if `(facility_id, slug)` exists; skip rule if `(resource_id, day_of_week)` already has a rule.
- Bookings: 3-8 per customer. Skip if `(customer_id, resource_id, start_at)` triple already exists. Status distribution: 60% CONFIRMED, 20% COMPLETED, 10% CANCELLED, 10% NO_SHOW. CONFIRMED split 80% next 14 days / 20% last 7 days; COMPLETED and NO_SHOW in last 30 days; CANCELLED split last 14 + next 14 days. Time slots clustered around 6-9am and 5-8pm. Duration 60 min. Currency AUD. Price 1500-5000 cents. ~30% get a note.
- Phone numbers: the spec lists `+61 4 1200 0001` style (with spaces). The customer entity's `phone` regex is `^\+?[1-9]\d{6,14}$` (no spaces). **Implementation must strip spaces before passing to `Customer.create`.** Document this in the module docstring.
- Argon2id hashing for passwords via `Argon2PasswordHasher.hash()`.
- Booking status transitions: `Booking.create()` always sets `CONFIRMED`. To seed a non-confirmed booking, call `bookings.add_safe()` (creates CONFIRMED), then mutate via `b.cancel(reason=...)` / `b.complete()` / `b.mark_no_show()` and persist via `bookings.update(b)`.
- Streamlit-style data shape: 5 facilities, 5 resources, 35 availability rules, 30+ bookings, 15 customers, 4 users, 1 tenant.
- CLI surface: `pnpm seed:mock` → `make -C apps/backend seed-mock` → `PYTHONPATH=src uv run python scripts/seed_demo.py --mock`.
- Stdout summary on success: tenant + admin credentials + facilities + customers + bookings counts.
- Repo conventions: `uv run` for Python, `PYTHONPATH=src` for backend imports.
- Test conventions: integration tests in `apps/backend/tests/integration/` against real Postgres via `TEST_DATABASE_URL` env (defaults to `postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh_test`).
- Default dev DB URL: `postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh` (no env override needed when running against dev DB).
- Use a fixed `random.Random(42)` seed so demo data is reproducible across runs.

## File Structure

| File | Responsibility |
|---|---|
| `apps/backend/scripts/mock_data.py` | New module: curated dataset constants (TENANT, ADMIN, CUSTOMER_USERS, DEMO_CUSTOMERS, FACILITIES, BOOKING_NOTES) + pure helpers (`_to_e164`, `_weighted_status`, `_pick_window`, `_pick_time_slot`) + DB helpers (`seed_tenant`, `seed_users`, `seed_customers`, `seed_facilities_and_resources`, `seed_bookings`) + async orchestrator `seed_mock_data(session, *, stdout) -> int`. |
| `apps/backend/scripts/seed_demo.py` | Modified: add `--mock` flag; `_main(mock: bool)` delegates to `seed_mock_data` or `seed_demo`. |
| `apps/backend/tests/integration/test_mock_data_seed.py` | New: 4 integration tests (happy path, idempotency, existing-tenant noop, status distribution). Reuses fixtures from `test_seed_demo.py`. |
| `apps/backend/Makefile` | Modified: add `seed-mock` target. |
| `package.json` (repo root) | Modified: add `seed:mock` script. |

No production code is modified. `FacilityService`, `BookingService`, `CustomerService`, `UserRepository`, `TenantRepository`, `Argon2PasswordHasher` already expose everything we need.

---

## Task 1: Module skeleton, constants, and pure helpers (RED)

**Files:**
- Create: `apps/backend/scripts/mock_data.py`
- Create: `apps/backend/tests/unit/test_mock_data_helpers.py`

**Step 1: Write the failing unit tests**

`apps/backend/tests/unit/test_mock_data_helpers.py`:

```python
"""Unit tests for pure helpers in mock_data.py."""
from __future__ import annotations

from datetime import datetime, timezone

from scripts.mock_data import (
    _to_e164,
    _weighted_status,
    _pick_window,
    _pick_time_slot,
)


def test_to_e164_strips_spaces():
    assert _to_e164("+61 4 1200 0001") == "+61412000001"


def test_to_e164_keeps_already_e164():
    assert _to_e164("+61412000001") == "+61412000001"


def test_weighted_status_returns_known_status():
    rng = __import__("random").Random(42)
    for _ in range(100):
        s = _weighted_status(rng)
        assert s in {"confirmed", "completed", "cancelled", "no_show"}


def test_weighted_status_distribution_within_tolerance():
    import random

    rng = random.Random(42)
    counts = {"confirmed": 0, "completed": 0, "cancelled": 0, "no_show": 0}
    for _ in range(1000):
        counts[_weighted_status(rng)] += 1
    # 60/20/10/10 distribution with reasonable tolerance
    assert 500 <= counts["confirmed"] <= 700
    assert 150 <= counts["completed"] <= 250
    assert 50 <= counts["cancelled"] <= 150
    assert 50 <= counts["no_show"] <= 150


def test_pick_window_for_confirmed_within_next_14_days():
    rng = __import__("random").Random(42)
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    start, _ = _pick_window("confirmed", rng, now)
    # next 14 days = 2026-08-07 to 2026-08-21
    assert now <= start <= datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


def test_pick_window_for_completed_in_past_30_days():
    rng = __import__("random").Random(42)
    now = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    start, _ = _pick_window("completed", rng, now)
    assert datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc) <= start < now


def test_pick_time_slot_returns_known_window():
    rng = __import__("random").Random(42)
    for _ in range(50):
        start = _pick_time_slot(rng, datetime(2026, 8, 7, 0, 0, tzinfo=timezone.utc))
        hour = start.hour
        # Morning cluster 6-9 or evening cluster 17-20
        assert 6 <= hour <= 9 or 17 <= hour <= 20, f"unexpected hour {hour}"
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src uv run pytest apps/backend/tests/unit/test_mock_data_helpers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.mock_data'`

**Step 3: Create the module skeleton with constants and helpers**

`apps/backend/scripts/mock_data.py`:

```python
"""Curated mock data for stakeholder demos.

Run via:
    make -C apps/backend seed-mock
or:
    pnpm seed:mock

Idempotent: re-runs are no-ops once the demo tenant + 5 facilities + 15 customers
are seeded. Re-runnable after destructive local testing without rebuilding the
demo from scratch.

Phone number format: the spec lists `+61 4 1200 0001` style with spaces. The
customer entity's `phone` regex (no spaces) requires E.164, so we strip spaces
in `_to_e164()` before passing to `Customer.create`.

Booking status transitions: `Booking.create()` always sets status to CONFIRMED.
For non-confirmed bookings, we call `bookings.add_safe()` (creates CONFIRMED),
then mutate via `b.cancel(reason=...)` / `b.complete()` / `b.mark_no_show()`
and persist via `bookings.update(b)`.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TextIO

# ----- Curated dataset constants (copied from spec) -----

TENANT_SLUG = "demo"
TENANT_NAME = "Demo Sports Club"
TENANT_CONTACT_EMAIL = "admin@demo.splashh.dev"

ADMIN_EMAIL = "admin@demo.splashh.dev"
ADMIN_PASSWORD = "Admin!Demo2026"
ADMIN_FULL_NAME = "Demo Admin"


@dataclass(frozen=True, slots=True)
class _UserSpec:
    email: str
    password: str
    full_name: str
    role: str  # "tenant_admin" | "customer"


CUSTOMER_USERS: tuple[_UserSpec, ...] = (
    _UserSpec("alex@demo.splashh.dev", "Customer!Demo1", "Alex Chen", "customer"),
    _UserSpec("priya@demo.splashh.dev", "Customer!Demo2", "Priya Patel", "customer"),
    _UserSpec("jordan@demo.splashh.dev", "Customer!Demo3", "Jordan Lee", "customer"),
)


@dataclass(frozen=True, slots=True)
class _CustomerSpec:
    full_name: str
    email: str
    phone: str


DEMO_CUSTOMERS: tuple[_CustomerSpec, ...] = (
    # 3 customers share emails with the customer users (so they can log in)
    _CustomerSpec("Alex Chen", "alex@demo.splashh.dev", "+61 4 1200 0001"),
    _CustomerSpec("Priya Patel", "priya@demo.splashh.dev", "+61 4 1200 0002"),
    _CustomerSpec("Jordan Lee", "jordan@demo.splashh.dev", "+61 4 1200 0003"),
    # 12 standalone customers
    _CustomerSpec("Sam Wilson", "sam@example.com", "+61 4 1200 0004"),
    _CustomerSpec("Maya Singh", "maya@example.com", "+61 4 1200 0005"),
    _CustomerSpec("Chris Brown", "chris@example.com", "+61 4 1200 0006"),
    _CustomerSpec("Taylor Reed", "taylor@example.com", "+61 4 1200 0007"),
    _CustomerSpec("Morgan Cole", "morgan@example.com", "+61 4 1200 0008"),
    _CustomerSpec("Riley Adams", "riley@example.com", "+61 4 1200 0009"),
    _CustomerSpec("Casey Bell", "casey@example.com", "+61 4 1200 0010"),
    _CustomerSpec("Drew Murphy", "drew@example.com", "+61 4 1200 0011"),
    _CustomerSpec("Skylar Hayes", "skylar@example.com", "+61 4 1200 0012"),
    _CustomerSpec("Quinn Foster", "quinn@example.com", "+61 4 1200 0013"),
    _CustomerSpec("Avery Stone", "avery@example.com", "+61 4 1200 0014"),
    _CustomerSpec("Reese Walsh", "reese@example.com", "+61 4 1200 0015"),
)


@dataclass(frozen=True, slots=True)
class _FacilitySpec:
    slug: str
    name: str
    city: str
    state: str
    postal_code: str
    country: str
    timezone: str
    phone: str
    resource_slug: str
    resource_name: str
    resource_type: str  # "pool" | "court" | "gym_floor"
    capacity: int
    attributes: dict[str, object]
    open_start_hour: int
    open_end_hour: int
    open_start_minute: int
    open_end_minute: int


FACILITIES: tuple[_FacilitySpec, ...] = (
    _FacilitySpec(
        slug="sydney-aquatic-centre",
        name="Sydney Aquatic Centre",
        city="Sydney",
        state="NSW",
        postal_code="2000",
        country="AU",
        timezone="Australia/Sydney",
        phone="+61 2 0000 0001",
        resource_slug="main-pool",
        resource_name="25m Indoor Pool",
        resource_type="pool",
        capacity=24,
        attributes={"lanes": 8, "length_m": 25, "min_age": 5},
        open_start_hour=6, open_start_minute=0,
        open_end_hour=21, open_end_minute=0,
    ),
    _FacilitySpec(
        slug="melbourne-swim-academy",
        name="Melbourne Swim Academy",
        city="Melbourne",
        state="VIC",
        postal_code="3000",
        country="AU",
        timezone="Australia/Melbourne",
        phone="+61 3 0000 0002",
        resource_slug="outdoor-pool",
        resource_name="50m Outdoor Pool",
        resource_type="pool",
        capacity=32,
        attributes={"lanes": 10, "length_m": 50, "min_age": 3},
        open_start_hour=5, open_start_minute=30,
        open_end_hour=22, open_end_minute=0,
    ),
    _FacilitySpec(
        slug="brisbane-sport-complex",
        name="Brisbane Sport Complex",
        city="Brisbane",
        state="QLD",
        postal_code="4000",
        country="AU",
        timezone="Australia/Brisbane",
        phone="+61 7 0000 0003",
        resource_slug="multi-sport-court",
        resource_name="Multi-Sport Court",
        resource_type="court",
        capacity=20,
        attributes={"surface": "timber", "lighting": True},
        open_start_hour=6, open_start_minute=0,
        open_end_hour=23, open_end_minute=0,
    ),
    _FacilitySpec(
        slug="auckland-marine-pool",
        name="Auckland Marine Pool",
        city="Auckland",
        state="Auckland",
        postal_code="1010",
        country="NZ",
        timezone="Pacific/Auckland",
        phone="+64 9 0000 0004",
        resource_slug="saltwater-pool",
        resource_name="Saltwater Pool",
        resource_type="pool",
        capacity=18,
        attributes={"lanes": 6, "length_m": 25, "min_age": 4},
        open_start_hour=7, open_start_minute=0,
        open_end_hour=20, open_end_minute=0,
    ),
    _FacilitySpec(
        slug="gold-coast-gym",
        name="Gold Coast Fitness",
        city="Gold Coast",
        state="QLD",
        postal_code="4217",
        country="AU",
        timezone="Australia/Brisbane",
        phone="+61 7 0000 0005",
        resource_slug="gym-floor",
        resource_name="Gym Floor",
        resource_type="gym_floor",
        capacity=40,
        attributes={"equipment_count": 60, "has_showers": True},
        open_start_hour=5, open_start_minute=0,
        open_end_hour=23, open_end_minute=0,
    ),
)


BOOKING_NOTES: tuple[str, ...] = (
    "Lane 3 reserved for swim club",
    "Birthday party — 8 kids",
    "Coach-led session",
    "Tournament practice",
    "Private 1-on-1 lesson",
)


BOOKING_STATUS_WEIGHTS: dict[str, float] = {
    "confirmed": 0.60,
    "completed": 0.20,
    "cancelled": 0.10,
    "no_show": 0.10,
}


RNG_SEED = 42


# ----- Pure helpers (unit-tested above) -----


def _to_e164(phone: str) -> str:
    """Strip spaces from a phone number to satisfy the customer entity's E.164 regex."""
    return phone.replace(" ", "")


def _weighted_status(rng: random.Random) -> str:
    """Pick a booking status according to BOOKING_STATUS_WEIGHTS."""
    statuses = list(BOOKING_STATUS_WEIGHTS.keys())
    weights = list(BOOKING_STATUS_WEIGHTS.values())
    return rng.choices(statuses, weights=weights, k=1)[0]


def _pick_window(
    status: str, rng: random.Random, now: datetime
) -> tuple[datetime, datetime]:
    """Pick a random (start_at, end_at) window for the given status.

    CONFIRMED:  80% next 14 days, 20% last 7 days
    COMPLETED:  last 30 days (ending before now)
    CANCELLED:  50% last 14 days, 50% next 14 days
    NO_SHOW:    last 30 days (ending before now)
    """
    if status == "confirmed":
        if rng.random() < 0.80:
            days_offset = rng.randint(0, 13)
        else:
            days_offset = rng.randint(-7, -1)
    elif status == "completed":
        days_offset = rng.randint(-30, -1)
    elif status == "cancelled":
        if rng.random() < 0.50:
            days_offset = rng.randint(-14, -1)
        else:
            days_offset = rng.randint(0, 13)
    elif status == "no_show":
        days_offset = rng.randint(-30, -1)
    else:
        raise ValueError(f"Unknown status: {status}")

    # Anchor on a random hour-at-midnight-on-day-N then layer in the time slot
    base_day = (now + timedelta(days=days_offset)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start = _pick_time_slot(rng, base_day)
    end = start + timedelta(minutes=60)
    return start, end


def _pick_time_slot(rng: random.Random, day: datetime) -> datetime:
    """Pick a time slot in the morning cluster (6-9am) or evening cluster (5-8pm)."""
    if rng.random() < 0.50:
        hour = rng.randint(6, 9)
    else:
        hour = rng.randint(17, 20)
    return day.replace(hour=hour, minute=0, second=0, microsecond=0)
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src uv run pytest apps/backend/tests/unit/test_mock_data_helpers.py -v`
Expected: 7 tests pass

**Step 5: Commit**

```bash
git add apps/backend/scripts/mock_data.py apps/backend/tests/unit/test_mock_data_helpers.py
git commit -m "feat(seed-mock): scaffold module with constants and pure helpers"
```

---

## Task 2: Tenant + users + customers (RED→GREEN)

**Files:**
- Modify: `apps/backend/scripts/mock_data.py` (append `seed_tenant`, `seed_users`, `seed_customers`)
- Create: `apps/backend/tests/integration/test_mock_data_seed.py` (write 2 tests now, write the rest in later tasks)

**Interfaces:**
- `seed_tenant(session, *, stdout=None) -> uuid.UUID` — returns the tenant id (created or existing)
- `seed_users(session, tenant_id, *, stdout=None) -> dict[str, uuid.UUID]` — returns `{email: user_id}`
- `seed_customers(session, tenant_id, user_ids_by_email, *, stdout=None) -> dict[str, uuid.UUID]` — returns `{email: customer_id}`

**Step 1: Write the failing integration test (Tenant + Users + Customers)**

`apps/backend/tests/integration/test_mock_data_seed.py`:

```python
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
from scripts.mock_data import seed_mock_data, seed_tenant, seed_users, seed_customers

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
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src uv run pytest apps/backend/tests/integration/test_mock_data_seed.py -v`
Expected: FAIL with `ImportError: cannot import name 'seed_tenant'`

**Step 3: Add `seed_tenant`, `seed_users`, `seed_customers` to `mock_data.py`**

Append to `apps/backend/scripts/mock_data.py`:

```python
# ----- DB helpers (integration-tested) -----

from auth.domain.entities import Tenant, User, UserRole  # noqa: E402
from auth.infrastructure.models import TenantModel, UserModel  # noqa: E402
from auth.infrastructure.password_hasher import Argon2PasswordHasher  # noqa: E402
from auth.infrastructure.repositories import TenantRepository, UserRepository  # noqa: E402
from customer.domain.entities import Customer  # noqa: E402
from customer.infrastructure.repositories import CustomerRepository  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402


async def seed_tenant(session: AsyncSession, *, stdout: TextIO | None = None) -> "uuid.UUID":
    """Idempotently create the demo tenant. Returns the tenant id."""
    result = await session.execute(
        select(TenantModel).where(TenantModel.slug == TENANT_SLUG)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing.id

    tenants = TenantRepository(session)
    tenant = Tenant.create(
        name=TENANT_NAME,
        slug=TENANT_SLUG,
        primary_contact_email=TENANT_CONTACT_EMAIL,
    )
    tenant = await tenants.add(tenant)
    # Activate (status moves ONBOARDING → ACTIVE)
    tenant.activate()
    m = await session.get(TenantModel, tenant.id)
    m.status = tenant.status.value
    await session.flush()
    return tenant.id


async def seed_users(
    session: AsyncSession, tenant_id, *, stdout: TextIO | None = None
) -> dict[str, "uuid.UUID"]:
    """Idempotently create the admin + 3 customer users. Returns {email: user_id}."""
    users_repo = UserRepository(session)
    hasher = Argon2PasswordHasher()

    # Admin user
    admin = await users_repo.get_by_email(tenant_id, ADMIN_EMAIL)
    if admin is None:
        admin = User.create(
            tenant_id=tenant_id,
            email=ADMIN_EMAIL,
            password_hash=hasher.hash(ADMIN_PASSWORD),
            full_name=ADMIN_FULL_NAME,
            roles=[UserRole.TENANT_ADMIN],
        )
        admin = await users_repo.add(admin)

    user_ids: dict[str, "uuid.UUID"] = {ADMIN_EMAIL: admin.id}

    # 3 customer users
    for spec in CUSTOMER_USERS:
        u = await users_repo.get_by_email(tenant_id, spec.email)
        if u is None:
            u = User.create(
                tenant_id=tenant_id,
                email=spec.email,
                password_hash=hasher.hash(spec.password),
                full_name=spec.full_name,
                roles=[UserRole(spec.role)],
            )
            u = await users_repo.add(u)
        user_ids[spec.email] = u.id

    return user_ids


async def seed_customers(
    session: AsyncSession,
    tenant_id,
    user_ids_by_email: dict[str, "uuid.UUID"],
    *,
    stdout: TextIO | None = None,
) -> dict[str, "uuid.UUID"]:
    """Idempotently create 15 customer profiles. Returns {email: customer_id}."""
    customers_repo = CustomerRepository(session)

    # Build a quick lookup of existing customers by email
    existing_rows = (
        await session.execute(
            select(CustomerModel).where(CustomerModel.tenant_id == tenant_id)
        )
    ).scalars().all()
    existing_by_email: dict[str, CustomerModel] = {c.email: c for c in existing_rows}

    customer_ids: dict[str, "uuid.UUID"] = {}
    for spec in DEMO_CUSTOMERS:
        if spec.email in existing_by_email:
            customer_ids[spec.email] = existing_by_email[spec.email].id
            continue

        # 3 customers share an email with the 3 customer users — link to that user
        user_id = user_ids_by_email.get(spec.email)
        if user_id is None:
            raise ValueError(
                f"No user found for customer {spec.email}; "
                f"ensure seed_users() ran first and this email is in CUSTOMER_USERS or matches a user"
            )

        customer = Customer.create(
            tenant_id=tenant_id,
            user_id=user_id,
            full_name=spec.full_name,
            email=spec.email,
            phone=_to_e164(spec.phone),
        )
        customer = await customers_repo.add(customer)
        customer_ids[spec.email] = customer.id

    return customer_ids
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src uv run pytest apps/backend/tests/integration/test_mock_data_seed.py -v`
Expected: 5 tests pass

**Step 5: Commit**

```bash
git add apps/backend/scripts/mock_data.py apps/backend/tests/integration/test_mock_data_seed.py
git commit -m "feat(seed-mock): add tenant, users, and customers seed functions"
```

---

## Task 3: Facilities + resources + availability rules (RED→GREEN)

**Files:**
- Modify: `apps/backend/scripts/mock_data.py` (append `seed_facilities_and_resources`)
- Modify: `apps/backend/tests/integration/test_mock_data_seed.py` (add 2 tests)

**Interfaces:**
- `seed_facilities_and_resources(session, tenant_id, *, stdout=None) -> dict[str, dict[str, uuid.UUID]]` — returns `{facility_slug: {"facility_id": ..., "resource_id": ...}}`

**Step 1: Add the failing tests**

Append to `apps/backend/tests/integration/test_mock_data_seed.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src uv run pytest apps/backend/tests/integration/test_mock_data_seed.py -v -k "facilities"`
Expected: FAIL with `ImportError: cannot import name 'seed_facilities_and_resources'`

**Step 3: Add `seed_facilities_and_resources` to `mock_data.py`**

Append to `apps/backend/scripts/mock_data.py`:

```python
from datetime import time  # noqa: E402

from facility.application.facility_service import FacilityService  # noqa: E402
from facility.domain.entities import ResourceType  # noqa: E402
from facility.infrastructure.models import AvailabilityRuleModel, FacilityModel, ResourceModel  # noqa: E402
from facility.infrastructure.repositories import (  # noqa: E402
    AvailabilityRuleRepository,
    FacilityRepository,
    ResourceRepository,
)


async def seed_facilities_and_resources(
    session: AsyncSession, tenant_id, *, stdout: TextIO | None = None
) -> dict[str, dict[str, "uuid.UUID"]]:
    """Idempotently create 5 facilities, 1 resource each, and 7 availability rules per resource.

    Returns {facility_slug: {"facility_id": ..., "resource_id": ...}}.
    """
    facilities_repo = FacilityRepository(session)
    resources_repo = ResourceRepository(session)
    rules_repo = AvailabilityRuleRepository(session)
    service = FacilityService(
        session=session,
        facilities=facilities_repo,
        resources=resources_repo,
        rules=rules_repo,
    )

    result: dict[str, dict[str, "uuid.UUID"]] = {}

    for spec in FACILITIES:
        # 1. Facility
        existing_facility = (
            await session.execute(
                select(FacilityModel).where(
                    FacilityModel.tenant_id == tenant_id,
                    FacilityModel.slug == spec.slug,
                )
            )
        ).scalar_one_or_none()
        if existing_facility is not None:
            facility_id = existing_facility.id
        else:
            facility = await service.create_facility(
                tenant_id=tenant_id,
                name=spec.name,
                slug=spec.slug,
                address_line1="1 Aquatic Drive",
                address_line2=None,
                city=spec.city,
                state=spec.state,
                postal_code=spec.postal_code,
                country=spec.country,
                timezone_=spec.timezone,
                phone=spec.phone,
            )
            facility_id = facility.id

        # 2. Resource
        existing_resource = (
            await session.execute(
                select(ResourceModel).where(
                    ResourceModel.facility_id == facility_id,
                    ResourceModel.slug == spec.resource_slug,
                )
            )
        ).scalar_one_or_none()
        if existing_resource is not None:
            resource_id = existing_resource.id
        else:
            resource = await service.create_resource(
                tenant_id=tenant_id,
                facility_id=facility_id,
                name=spec.resource_name,
                slug=spec.resource_slug,
                resource_type=ResourceType(spec.resource_type),
                capacity=spec.capacity,
                attributes=spec.attributes,
            )
            resource_id = resource.id

        # 3. Availability rules (one per day-of-week)
        existing_rules = (
            await session.execute(
                select(AvailabilityRuleModel).where(
                    AvailabilityRuleModel.resource_id == resource_id
                )
            )
        ).scalars().all()
        existing_days = {r.day_of_week for r in existing_rules}

        start_time = time(spec.open_start_hour, spec.open_start_minute)
        end_time = time(spec.open_end_hour, spec.open_end_minute)
        for day_of_week in range(7):
            if day_of_week in existing_days:
                continue
            await service.create_availability_rule(
                tenant_id=tenant_id,
                resource_id=resource_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                slot_duration_minutes=60,
            )

        result[spec.slug] = {"facility_id": facility_id, "resource_id": resource_id}

    return result
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src uv run pytest apps/backend/tests/integration/test_mock_data_seed.py -v -k "facilities"`
Expected: 3 tests pass

**Step 5: Commit**

```bash
git add apps/backend/scripts/mock_data.py apps/backend/tests/integration/test_mock_data_seed.py
git commit -m "feat(seed-mock): add facilities, resources, and availability rules"
```

---

## Task 4: Bookings (RED→GREEN)

**Files:**
- Modify: `apps/backend/scripts/mock_data.py` (append `seed_bookings`)
- Modify: `apps/backend/tests/integration/test_mock_data_seed.py` (add 3 tests)

**Interfaces:**
- `seed_bookings(session, tenant_id, customer_ids, resource_ids, *, stdout=None) -> dict[str, int]` — returns counts `{"created": N, "skipped": M, "confirmed": a, "completed": b, "cancelled": c, "no_show": d}`

**Step 1: Add the failing tests**

Append to `apps/backend/tests/integration/test_mock_data_seed.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src uv run pytest apps/backend/tests/integration/test_mock_data_seed.py -v -k "bookings"`
Expected: FAIL with `ImportError: cannot import name 'seed_bookings'`

**Step 3: Add `seed_bookings` to `mock_data.py`**

Append to `apps/backend/scripts/mock_data.py`:

```python
from booking.domain.entities import Booking, BookingStatus, CancellationReason  # noqa: E402
from booking.infrastructure.models import BookingModel  # noqa: E402
from booking.infrastructure.repositories import BookingRepository  # noqa: E402


async def seed_bookings(
    session: AsyncSession,
    tenant_id,
    customer_ids: dict[str, "uuid.UUID"],
    resource_ids: list["uuid.UUID"],
    *,
    stdout: TextIO | None = None,
) -> dict[str, int]:
    """Idempotently create 3-8 bookings per customer with the documented status distribution.

    Returns counts with keys: created, skipped, confirmed, completed, cancelled, no_show.
    """
    bookings_repo = BookingRepository(session)
    rng = random.Random(RNG_SEED)
    now = datetime.now(timezone.utc)

    # 1. Distribute total bookings across customers (3-8 each)
    customer_id_list = list(customer_ids.values())
    per_customer = [rng.randint(3, 8) for _ in customer_id_list]
    total = sum(per_customer)

    # 2. Pre-allocate status counts to match 60/20/10/10 distribution
    target = {
        "confirmed": round(total * 0.60),
        "completed": round(total * 0.20),
        "cancelled": round(total * 0.10),
        "no_show": total - round(total * 0.60) - round(total * 0.20) - round(total * 0.10),
    }
    # Materialize the status sequence
    status_sequence: list[str] = []
    for status, count in target.items():
        status_sequence.extend([status] * count)
    rng.shuffle(status_sequence)

    # 3. Detect existing bookings (natural key: customer_id, resource_id, start_at)
    existing_bookings = (
        await session.execute(
            select(BookingModel.customer_id, BookingModel.resource_id, BookingModel.start_at).where(
                BookingModel.tenant_id == tenant_id
            )
        )
    ).all()
    existing_keys = {
        (row.customer_id, row.resource_id, row.start_at) for row in existing_bookings
    }

    counts = {
        "created": 0,
        "skipped": 0,
        "confirmed": 0,
        "completed": 0,
        "cancelled": 0,
        "no_show": 0,
    }

    status_idx = 0
    for customer_id, n_bookings in zip(customer_id_list, per_customer, strict=True):
        for _ in range(n_bookings):
            if status_idx >= len(status_sequence):
                break
            status = status_sequence[status_idx]
            status_idx += 1

            start_at, end_at = _pick_window(status, rng, now)
            resource_id = rng.choice(resource_ids)

            key = (customer_id, resource_id, start_at)
            if key in existing_keys:
                counts["skipped"] += 1
                continue

            # ~30% of bookings get a note
            notes = rng.choice(BOOKING_NOTES) if rng.random() < 0.30 else None
            price_cents = rng.randint(1500, 5000)

            booking = Booking.create(
                tenant_id=tenant_id,
                customer_id=customer_id,
                resource_id=resource_id,
                start_at=start_at,
                end_at=end_at,
                price_cents=price_cents,
                currency="AUD",
                notes=notes,
            )
            try:
                booking = await bookings_repo.add_safe(booking)
            except Exception:
                # If resource is locked or overlap occurs (rare with curated customers),
                # skip and continue.
                counts["skipped"] += 1
                continue

            # Mutate status if needed
            if status == "completed":
                booking.complete()
                await bookings_repo.update(booking)
            elif status == "cancelled":
                booking.cancel(reason=CancellationReason.CUSTOMER_REQUEST)
                await bookings_repo.update(booking)
            elif status == "no_show":
                booking.mark_no_show()
                await bookings_repo.update(booking)

            existing_keys.add(key)
            counts["created"] += 1
            counts[status] += 1

    return counts
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src uv run pytest apps/backend/tests/integration/test_mock_data_seed.py -v -k "bookings"`
Expected: 3 tests pass

**Step 5: Commit**

```bash
git add apps/backend/scripts/mock_data.py apps/backend/tests/integration/test_mock_data_seed.py
git commit -m "feat(seed-mock): add bookings with status distribution"
```

---

## Task 5: Orchestrator + `--mock` CLI flag (RED→GREEN)

**Files:**
- Modify: `apps/backend/scripts/mock_data.py` (append `seed_mock_data`)
- Modify: `apps/backend/scripts/seed_demo.py` (add `--mock` flag and `_main` dispatcher)
- Modify: `apps/backend/tests/integration/test_mock_data_seed.py` (add 1 happy-path test)

**Interfaces:**
- `seed_mock_data(session, *, stdout=None) -> int` — orchestrator that runs all sub-seeders in order, prints stdout summary, returns exit code

**Step 1: Add the failing test**

Append to `apps/backend/tests/integration/test_mock_data_seed.py`:

```python
async def test_seed_mock_data_full_run_creates_documented_shape(session):
    stdout = io.StringIO()
    exit_code = await seed_mock_data(session, stdout=stdout)
    assert exit_code == 0

    from auth.infrastructure.models import TenantModel, UserModel
    from booking.infrastructure.models import BookingModel
    from customer.infrastructure.models import CustomerModel
    from facility.infrastructure.models import (
        AvailabilityRuleModel,
        FacilityModel,
        ResourceModel,
    )

    tenants = (await session.execute(select(TenantModel))).scalars().all()
    assert len(tenants) == 1
    assert tenants[0].slug == "demo"

    users = (await session.execute(select(UserModel))).scalars().all()
    assert len(users) == 4

    customers = (await session.execute(select(CustomerModel))).scalars().all()
    assert len(customers) == 15

    facilities = (await session.execute(select(FacilityModel))).scalars().all()
    assert len(facilities) == 5

    resources = (await session.execute(select(ResourceModel))).scalars().all()
    assert len(resources) == 5

    rules = (await session.execute(select(AvailabilityRuleModel))).scalars().all()
    assert len(rules) >= 35

    bookings = (await session.execute(select(BookingModel))).scalars().all()
    assert len(bookings) >= 30

    text = stdout.getvalue()
    assert "Demo Sports Club" in text
    assert "admin@demo.splashh.dev" in text
    assert "Admin!Demo2026" in text
```

**Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=src uv run pytest apps/backend/tests/integration/test_mock_data_seed.py -v -k "full_run"`
Expected: FAIL with `ImportError: cannot import name 'seed_mock_data'`

**Step 3: Add `seed_mock_data` orchestrator to `mock_data.py`**

Append to `apps/backend/scripts/mock_data.py`:

```python
async def seed_mock_data(session: AsyncSession, *, stdout: TextIO = None) -> int:
    """Orchestrator: seed tenant → users → customers → facilities → resources → rules → bookings.

    Tenant-level gate: if a tenant with slug `demo` already exists, the whole
    seed is a no-op (per spec's `test_seed_mock_data_skips_existing_demo_tenant`).
    Per-entity idempotency in the sub-functions is a defense-in-depth for the
    partial-seed case.

    Returns 0 on success (or already-seeded), 1 on unrecoverable error.
    """
    if stdout is None:
        import sys
        stdout = sys.stdout

    # Tenant-level gate
    existing_tenant = (
        await session.execute(
            select(TenantModel).where(TenantModel.slug == TENANT_SLUG)
        )
    ).scalar_one_or_none()
    if existing_tenant is not None:
        print(f"Demo tenant already exists; nothing to do.", file=stdout)
        return 0

    try:
        tenant_id = await seed_tenant(session, stdout=stdout)
        print(f"Demo tenant: demo (id={tenant_id})", file=stdout)

        user_ids = await seed_users(session, tenant_id, stdout=stdout)
        print(f"Users: {len(user_ids)} (admin + 3 customer)", file=stdout)
        print(f"Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}", file=stdout)

        customer_ids = await seed_customers(session, tenant_id, user_ids, stdout=stdout)
        print(f"Customers: {len(customer_ids)} created", file=stdout)

        fr = await seed_facilities_and_resources(session, tenant_id, stdout=stdout)
        facility_names = ", ".join(spec.name for spec in FACILITIES)
        print(f"Facilities: {len(fr)} created ({facility_names})", file=stdout)

        resource_ids = [ids["resource_id"] for ids in fr.values()]
        booking_counts = await seed_bookings(session, tenant_id, customer_ids, resource_ids, stdout=stdout)
        print(
            f"Bookings: {booking_counts['created']} created, "
            f"{booking_counts['skipped']} skipped "
            f"({booking_counts['confirmed']} confirmed, "
            f"{booking_counts['completed']} completed, "
            f"{booking_counts['cancelled']} cancelled, "
            f"{booking_counts['no_show']} no_show)",
            file=stdout,
        )

        await session.commit()
        return 0
    except Exception as exc:
        await session.rollback()
        print(f"Mock seed failed: {exc}", file=stdout)
        return 1
```

**Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=src uv run pytest apps/backend/tests/integration/test_mock_data_seed.py -v -k "full_run"`
Expected: PASS

**Step 5: Modify `seed_demo.py` to add `--mock` flag**

Replace `apps/backend/scripts/seed_demo.py`'s entire `if __name__ == "__main__"` block at the bottom (lines 150-153) with:

```python
if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Seed curated stakeholder demo data (5 facilities, 15 customers, ~50 bookings)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main(mock=args.mock)))
```

And replace the `_main()` function (lines 135-147) with:

```python
async def _main(*, mock: bool = False) -> int:
    """CLI entry point: bootstrap engine + session, delegate to mock or demo seed, exit."""
    from common.infrastructure.db import init_engine, get_session_factory, dispose_engine
    from common.infrastructure.settings import get_settings

    if mock:
        from scripts.mock_data import seed_mock_data

        settings = get_settings()
        await init_engine(settings)
        try:
            factory = get_session_factory()
            async with factory() as session:
                return await seed_mock_data(session)
        finally:
            await dispose_engine()

    settings = get_settings()
    await init_engine(settings)
    try:
        factory = get_session_factory()
        async with factory() as session:
            return await seed_demo(session)
    finally:
        await dispose_engine()
```

**Step 6: Manually run the CLI to verify the wiring**

Run: `PYTHONPATH=src uv run python apps/backend/scripts/seed_demo.py --mock`
Expected: stdout shows the documented summary, exit code 0.

**Step 7: Commit**

```bash
git add apps/backend/scripts/mock_data.py apps/backend/scripts/seed_demo.py apps/backend/tests/integration/test_mock_data_seed.py
git commit -m "feat(seed-mock): orchestrator + --mock CLI flag"
```

---

## Task 6: CLI surfaces (Makefile + package.json)

**Files:**
- Modify: `apps/backend/Makefile` (add `seed-mock` target)
- Modify: `package.json` (add `seed:mock` script)

**Step 1: Add the Makefile target**

Append to `apps/backend/Makefile` (after the existing `seed-demo:` block):

```makefile
seed-mock:
	PYTHONPATH=src uv run python scripts/seed_demo.py --mock
```

**Step 2: Add the package.json script**

Edit `package.json` to add `"seed:mock"` directly below the existing `"seed:demo"` line:

```json
"seed:mock": "make -C apps/backend seed-mock",
```

**Step 3: Run via the new CLI surface**

Run: `pnpm seed:mock`
Expected: stdout shows the documented summary, exit code 0.

**Step 4: Commit**

```bash
git add apps/backend/Makefile package.json
git commit -m "build(seed-mock): wire pnpm seed:mock and make seed-mock"
```

---

## Task 7: Full integration coverage + idempotency + existing-tenant tests

**Files:**
- Modify: `apps/backend/tests/integration/test_mock_data_seed.py` (add 4 tests)

**Step 1: Add the tests**

Append to `apps/backend/tests/integration/test_mock_data_seed.py`:

```python
async def test_seed_mock_data_is_idempotent(session):
    from auth.infrastructure.models import TenantModel, UserModel
    from booking.infrastructure.models import BookingModel
    from customer.infrastructure.models import CustomerModel
    from facility.infrastructure.models import (
        AvailabilityRuleModel,
        FacilityModel,
        ResourceModel,
    )

    first = await seed_mock_data(session)
    assert first == 0

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
    assert second == 0

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
    from datetime import datetime, timezone
    from uuid import uuid4

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

    exit_code = await seed_mock_data(session)
    assert exit_code == 0

    # Tenant is unchanged
    rows = (await session.execute(select(TenantModel))).scalars().all()
    assert len(rows) == 1
    assert rows[0].name == "Pre-existing Demo Tenant"

    # No new facilities, users, or bookings created under it
    from auth.infrastructure.models import UserModel
    from booking.infrastructure.models import BookingModel
    from facility.infrastructure.models import FacilityModel

    users = (await session.execute(select(UserModel))).scalars().all()
    assert len(users) == 0
    facilities = (await session.execute(select(FacilityModel))).scalars().all()
    assert len(facilities) == 0
    bookings = (await session.execute(select(BookingModel))).scalars().all()
    assert len(bookings) == 0


async def test_seed_mock_data_returns_nonzero_on_db_error(session):
    """If session.commit() raises, seed_mock_data returns 1 and rolls back."""
    from unittest.mock import AsyncMock

    # Replace commit with a function that raises
    original_commit = session.commit
    session.commit = AsyncMock(side_effect=RuntimeError("simulated DB failure"))

    exit_code = await seed_mock_data(session)
    assert exit_code == 1

    session.commit = original_commit


async def test_seed_mock_data_booking_status_distribution_via_full_run(session):
    from booking.infrastructure.models import BookingModel

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
```

**Step 2: Run all mock data tests to verify they pass**

Run: `PYTHONPATH=src uv run pytest apps/backend/tests/integration/test_mock_data_seed.py -v`
Expected: All 12 tests pass (3 tenant + 2 users + 1 customer + 3 facilities + 3 bookings + 1 full_run + 4 idempotency/existing-tenant/distribution/error)

**Step 3: Run the full backend test suite**

Run: `PYTHONPATH=src uv run pytest`
Expected: All tests pass (existing 65 + new 12 = 77 total)

**Step 4: Commit**

```bash
git add apps/backend/tests/integration/test_mock_data_seed.py
git commit -m "test(seed-mock): idempotency, existing-tenant, status distribution, error"
```

---

## Done criteria verification

Verify all items from the spec's "Done criteria":

- [ ] `pnpm seed:mock` against an empty DB creates the documented shape
  - Run: `docker compose down -v && docker compose up -d postgres && pnpm seed:mock`
  - Expected: stdout shows tenant + 5 facilities + 15 customers + 30+ bookings
- [ ] Re-running `pnpm seed:mock` is a no-op (counts unchanged)
  - Run: `pnpm seed:mock` twice
  - Expected: second run completes with same counts
- [ ] `pnpm --filter backend test` (incl. integration) stays green
  - Run: `PYTHONPATH=src uv run pytest`
  - Expected: all tests pass
- [ ] Login as `admin@demo.splashh.dev` → admin sees the 5 facilities
  - Manual: `curl -X POST http://localhost:8765/v1/auth/login -d '{"email":"admin@demo.splashh.dev","password":"Admin!Demo2026"}'`
  - Manual: use the returned token to fetch `/v1/facilities`; expect 5 entries
- [ ] Login as `alex@demo.splashh.dev` → customer sees their bookings
  - Manual: login as alex, fetch `/v1/customers/me/bookings`; expect 3-8 bookings
- [ ] `/book` shows 5 facility cards (not the empty state)
  - Manual: `pnpm dev` and visit `/book`; expect 5 cards
- [ ] Spec + plan committed to git
  - Run: `git log --oneline | grep -E "(mock-data-seed|seed-mock)"`

---

## Self-review

**1. Spec coverage:** Every section in the spec maps to a task:
- Spec scope → T1 (scaffold), T2 (entities), T3-T4 (entities), T5 (orchestrator)
- Spec seeding order → T5 (orchestrator runs in spec order)
- Spec curated data → T1 (constants), T2 (customers), T3 (facilities), T4 (bookings)
- Spec idempotency strategy → T2 (each entity getter-by-key check), T3 (same), T4 (natural key check)
- Spec CLI surface → T5 (--mock flag), T6 (Makefile + package.json)
- Spec stdout output → T5 (orchestrator prints the documented summary)
- Spec testing strategy → T1 (unit tests), T2-T4 (integration tests as we build), T7 (idempotency + error path)
- Spec done criteria → end-of-file checklist

**2. Placeholder scan:** No TBD/TODO/"implement later". All code blocks are complete. No "similar to Task N" — Tasks 2-4 each include the full code for their sub-functions.

**3. Type consistency:** All sub-functions return the documented `dict[str, uuid.UUID]` etc. The orchestrator in T5 matches the spec's stdout output. The CLI flag (`--mock`) matches the spec. The Makefile target name (`seed-mock`) and package.json script name (`seed:mock`) match the spec exactly.

**4. Implementation choices recorded:**
- Phone format: T1 calls out the `+61 4 1200 0001` → `+61412000001` conversion in `_to_e164()`.
- Booking status transitions: `Booking.create()` always sets CONFIRMED. T4 uses `add_safe()` then entity mutation for non-confirmed statuses.
- RNG seed: `random.Random(42)` for reproducibility.
- Test pattern: reuses the `db_engine` / `session_factory` / `session` fixture trio from `test_seed_demo.py`.

**5. Risks identified:**
- The `add_safe()` call inside `seed_bookings` could race on the same resource across the seed run. With 30+ bookings across 5 resources, the algorithm picks random resources per booking, so overlap is unlikely but possible. T4 catches this with a `try/except` that increments `skipped` and continues.
- The status distribution target uses `round()` which can drift by 1-2 bookings. The test ranges (50-70 / 15-25 / 5-15 / 5-15) absorb this.
- `seed_mock_data` is async; the orchestrator uses `session.commit()` at the end. If any sub-step throws, the rolled-back session leaves the DB untouched, which is the desired behavior for the error-path test.

**No fixes needed inline after self-review.**
