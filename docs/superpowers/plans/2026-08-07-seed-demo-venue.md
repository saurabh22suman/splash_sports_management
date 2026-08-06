# Seed Demo Venue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a runnable Python seed script (`apps/backend/scripts/seed_demo.py`) that idempotently creates a "Splash Sports Club" facility, one swimming-pool resource, and 7 availability rules for the first/only dev tenant — so the app is immediately demoable on a fresh dev DB.

**Architecture:** A standalone async Python script that opens a real DB session, looks up the first tenant, guards on facility slug for idempotency, then drives `FacilityService` to create the facility, pool, and 7 daily availability rules. Runs via `make -C apps/backend seed-demo`, which is wired into the root `pnpm seed:demo` script.

**Tech Stack:** Python 3.12, SQLAlchemy 2 (async), asyncpg, FastAPI app's existing `FacilityService`, uv (run), pytest + pytest-asyncio (integration tests against real Postgres), Makefile + pnpm.

## Global Constraints

These apply to every task. Copied verbatim from the spec:

- Idempotent on re-run via facility-slug check (`splash-sports-club`).
- Reuses `FacilityService.create_facility / create_resource / create_availability_rule` — no raw inserts.
- Targets the first tenant: `SELECT * FROM tenants ORDER BY created_at ASC LIMIT 1`.
- No-tenant case: `print "No tenant found. Run register-tenant first."` then `exit 1`.
- Already-seeded case: `print "Already seeded for tenant <slug>; nothing to do."` then `exit 0`.
- Service-layer exceptions bubble up with full traceback; script does not swallow.
- Repo conventions: `uv run` for Python, `PYTHONPATH=src` for backend imports.
- Test conventions: integration tests in `apps/backend/tests/integration/` against real Postgres via `TEST_DATABASE_URL` env (defaults to `postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh_test`).
- Default dev DB URL: `postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh` (no env override needed when running against dev DB).

## File Structure

| File | Responsibility |
|---|---|
| `apps/backend/scripts/seed_demo.py` | Standalone async seed script. Pure function `seed_demo(session, *, stdout=sys.stdout) -> int` returns exit code; thin `if __name__ == "__main__"` CLI wrapper bootstraps the session factory and exits with the returned code. |
| `apps/backend/tests/integration/test_seed_demo.py` | 3 integration tests covering happy path, idempotency, no-tenant. Reuses the `db_engine` / `session_factory` / `session` fixture pattern from `tests/integration/test_auth_service.py`. |
| `apps/backend/Makefile` | Add `seed-demo` target that runs the script with `PYTHONPATH=src`. |
| `package.json` (repo root) | Add `seed:demo` script → `make -C apps/backend seed-demo`. |

No production code is modified. `FacilityService` already exposes all methods we need (`create_facility`, `create_resource`, `create_availability_rule`). `TenantRepository` is unchanged — the script queries tenants via raw `select(TenantModel)` since `Tenant` is its own aggregate root (not scoped under another tenant).

---

## Task 1: Scaffold the script and write the happy-path test (RED)

**Files:**
- Create: `apps/backend/scripts/seed_demo.py`
- Create: `apps/backend/tests/integration/test_seed_demo.py`

**Step 1: Create the integration test file with the happy-path test**

`apps/backend/tests/integration/test_seed_demo.py`:

```python
"""Integration tests for the seed_demo script."""
from __future__ import annotations

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


async def test_seed_demo_creates_facility_pool_and_seven_rules(session, tenant, capsys):
    exit_code = await seed_demo(session)

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

    captured = capsys.readouterr()
    assert "Splash Sports Club" in captured.out
```

**Step 2: Create the empty script so the import resolves (still RED)**

`apps/backend/scripts/seed_demo.py`:

```python
"""Seed a demo 'Splash Sports Club' facility for the first/only dev tenant.

Idempotent: re-runs are no-ops once a facility with slug 'splash-sports-club'
exists for the target tenant.

Run via:
    make -C apps/backend seed-demo
or directly:
    PYTHONPATH=src uv run python apps/backend/scripts/seed_demo.py
"""
from __future__ import annotations

import sys
from typing import TextIO
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

# Exit codes
EXIT_OK = 0
EXIT_NO_TENANT = 1


async def seed_demo(session: AsyncSession, *, stdout: TextIO = sys.stdout) -> int:
    """Seed the demo facility. Returns the process exit code."""
    return EXIT_OK


if __name__ == "__main__":
    # CLI wrapper is added in Task 5.
    raise SystemExit("CLI not yet wired — see Task 5")
```

**Step 3: Run the test — verify it fails for the expected reason**

Run:
```bash
cd apps/backend && PYTHONPATH=src uv run pytest tests/integration/test_seed_demo.py::test_seed_demo_creates_facility_pool_and_seven_rules -v
```

Expected: FAIL with `AssertionError` on the first assert inside the test (no facility exists) — confirms the test exercises the path we want to implement.

**Step 4: Commit the failing test + empty script**

```bash
git -C /home/soloengine/Github/splash_sports_management add \
  apps/backend/scripts/seed_demo.py \
  apps/backend/tests/integration/test_seed_demo.py
git -C /home/soloengine/Github/splash_sports_management commit -m "test(seed): add failing happy-path test for seed_demo"
```

---

## Task 2: Implement the happy path (GREEN)

**Files:**
- Modify: `apps/backend/scripts/seed_demo.py`

**Step 1: Add new imports at the top of `seed_demo.py`**

The Task 1 stub imports `sys`, `TextIO`, `AsyncSession`. Add these new module-level imports directly below the existing ones:

```python
from datetime import time
from sqlalchemy import select

from auth.infrastructure.models import TenantModel
from facility.application.facility_service import FacilityService
from facility.domain.entities import ResourceType
from facility.infrastructure.models import (
    AvailabilityRuleModel,
    FacilityModel,
)
from facility.infrastructure.repositories import (
    AvailabilityRuleRepository,
    FacilityRepository,
    ResourceRepository,
)
```

**Step 2: Add module-level constants**

Insert after the imports, before the `seed_demo` function:

```python
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
```

(`AvailabilityRuleModel` is imported in case a future task needs to query rules; the current code only needs `FacilityModel`. You can drop `AvailabilityRuleModel` from the imports if your linter complains about unused imports.)

**Step 3: Replace the body of `seed_demo`**

In `apps/backend/scripts/seed_demo.py`, replace the body of `seed_demo` (the single `return EXIT_OK` line) with:

```python
    # 1. Pick the first/only tenant.
    tenant: TenantModel | None = (
        await session.execute(
            select(TenantModel).order_by(TenantModel.created_at.asc()).limit(1)
        )
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
```

**Step 2: Run the happy-path test — verify GREEN**

Run:
```bash
cd apps/backend && PYTHONPATH=src uv run pytest tests/integration/test_seed_demo.py::test_seed_demo_creates_facility_pool_and_seven_rules -v
```

Expected: PASS. If FAIL, re-read the assertion message — typically the issue is ordering (`order_by(TenantModel.created_at.asc())` requires the timestamps to be set on insert; the fixture sets them explicitly, so this is fine).

**Step 3: Run the full backend test suite to confirm no regressions**

Run:
```bash
cd apps/backend && PYTHONPATH=src uv run pytest -q
```

Expected: all existing tests still pass plus our new one.

**Step 4: Commit**

```bash
git -C /home/soloengine/Github/splash_sports_management add apps/backend/scripts/seed_demo.py
git -C /home/soloengine/Github/splash_sports_management commit -m "feat(seed): implement demo facility + pool + 7 availability rules"
```

---

## Task 3: Add the no-tenant test (RED → GREEN)

**Files:**
- Modify: `apps/backend/tests/integration/test_seed_demo.py`

**Step 1: Add the no-tenant test**

Append to `apps/backend/tests/integration/test_seed_demo.py`:

```python
async def test_seed_demo_returns_one_with_message_when_no_tenant(
    session, capsys
):
    exit_code = await seed_demo(session)

    assert exit_code == 1

    captured = capsys.readouterr()
    assert "No tenant found" in captured.out
```

**Step 2: Run the new test — verify it already passes**

Run:
```bash
cd apps/backend && PYTHONPATH=src uv run pytest tests/integration/test_seed_demo.py::test_seed_demo_returns_one_with_message_when_no_tenant -v
```

Expected: PASS. The implementation in Task 2 already handles this case; the test pins the behaviour so a future refactor can't quietly drop it.

(If the test fails because `select(TenantModel).order_by(...).limit(1)` somehow returns a row even on an empty table, that's a fixture-leak issue — re-check that the `db_engine` fixture in this test file drops and recreates all tables.)

**Step 3: Commit**

```bash
git -C /home/soloengine/Github/splash_sports_management add apps/backend/tests/integration/test_seed_demo.py
git -C /home/soloengine/Github/splash_sports_management commit -m "test(seed): pin no-tenant behavior of seed_demo"
```

---

## Task 4: Add the idempotency test (RED → GREEN)

**Files:**
- Modify: `apps/backend/tests/integration/test_seed_demo.py`

**Step 1: Add the idempotency test**

Append to `apps/backend/tests/integration/test_seed_demo.py`:

```python
async def test_seed_demo_is_noop_when_facility_already_seeded(
    session, tenant, capsys
):
    # First call seeds.
    first = await seed_demo(session)
    assert first == 0

    facility_count = (
        await session.execute(
            select(FacilityModel).where(FacilityModel.tenant_id == tenant.id)
        )
    ).scalars().all()
    resource_count = (
        await session.execute(select(ResourceModel))
    ).scalars().all()
    rule_count = (
        await session.execute(select(AvailabilityRuleModel))
    ).scalars().all()

    assert len(facility_count) == 1
    assert len(resource_count) == 1
    assert len(rule_count) == 7

    # Second call is a no-op.
    second = await seed_demo(session)

    assert second == 0

    # Counts unchanged.
    facility_count_2 = (
        await session.execute(
            select(FacilityModel).where(FacilityModel.tenant_id == tenant.id)
        )
    ).scalars().all()
    resource_count_2 = (
        await session.execute(select(ResourceModel))
    ).scalars().all()
    rule_count_2 = (
        await session.execute(select(AvailabilityRuleModel))
    ).scalars().all()

    assert len(facility_count_2) == 1
    assert len(resource_count_2) == 1
    assert len(rule_count_2) == 7

    captured = capsys.readouterr()
    assert "Already seeded" in captured.out
```

**Step 2: Run the idempotency test — verify it passes**

Run:
```bash
cd apps/backend && PYTHONPATH=src uv run pytest tests/integration/test_seed_demo.py::test_seed_demo_is_noop_when_facility_already_seeded -v
```

Expected: PASS. The slug check in Task 2's implementation already handles this case.

**Step 3: Run all three seed tests together — verify they pass in any order**

Run:
```bash
cd apps/backend && PYTHONPATH=src uv run pytest tests/integration/test_seed_demo.py -v
```

Expected: 3 passed.

**Step 4: Commit**

```bash
git -C /home/soloengine/Github/splash_sports_management add apps/backend/tests/integration/test_seed_demo.py
git -C /home/soloengine/Github/splash_sports_management commit -m "test(seed): pin idempotency of seed_demo on re-run"
```

---

## Task 5: Wire CLI entry point + Makefile + pnpm script, smoke-test

**Files:**
- Modify: `apps/backend/scripts/seed_demo.py` (add CLI wrapper)
- Modify: `apps/backend/Makefile` (add `seed-demo` target)
- Modify: `package.json` (add `seed:demo` script)

**Step 1: Replace the CLI placeholder block in `seed_demo.py`**

In `apps/backend/scripts/seed_demo.py`, replace the placeholder `if __name__ == "__main__":` block at the bottom of the file with:

```python
async def _main() -> int:
    """CLI entry point: bootstrap engine + session, run seed_demo, exit."""
    from common.infrastructure.db import init_engine, get_session_factory, dispose_engine
    from common.infrastructure.settings import get_settings

    settings = get_settings()
    await init_engine(settings)
    try:
        factory = get_session_factory()
        async with factory() as session:
            return await seed_demo(session)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(_main()))
```

**Step 2: Add the Makefile target**

In `apps/backend/Makefile`, after the existing `test:` target, add:

```make
seed-demo:
	PYTHONPATH=src uv run python scripts/seed_demo.py
```

(Use a literal TAB for indentation — Make requires it.)

**Step 3: Add the pnpm script**

In `package.json` at the repo root, inside `"scripts":`, add:

```json
"seed:demo": "make -C apps/backend seed-demo",
```

**Step 4: Smoke-test against the dev DB**

Pre-conditions: dev DB is up (the `splashh_postgres` container is healthy), and at least one tenant already exists (from earlier Playwright tests).

Run:
```bash
cd /home/soloengine/Github/splash_sports_management && pnpm seed:demo
```

Expected output (first run):
```
Seeded 'Splash Sports Club' + 1 pool + 7 availability rules for tenant demo-tenant.
```

Run again:
```bash
pnpm seed:demo
```

Expected output (re-run):
```
Already seeded for tenant demo-tenant; nothing to do.
```

If the dev DB has no tenant, expected output:
```
No tenant found. Run register-tenant first.
```
and exit code `1`. Confirm with `echo $?` immediately after.

**Step 5: Verify the seed is visible via the API**

The frontend's `/book` page lists facilities. If a customer logs in and visits `/book`, "Splash Sports Club" should appear in the list. (The frontend already lists active facilities for the current tenant — no frontend changes are needed for this verification.)

**Step 6: Run the full backend test suite one more time**

Run:
```bash
cd apps/backend && PYTHONPATH=src uv run pytest -q
```

Expected: all tests pass, including the 3 new ones in `test_seed_demo.py`.

**Step 7: Commit**

```bash
git -C /home/soloengine/Github/splash_sports_management add \
  apps/backend/scripts/seed_demo.py \
  apps/backend/Makefile \
  package.json
git -C /home/soloengine/Github/splash_sports_management commit -m "feat(seed): wire CLI, Makefile target, and pnpm seed:demo"
```

---

## Done Criteria

- [x] `apps/backend/scripts/seed_demo.py` exists and is runnable.
- [x] `pnpm seed:demo` works from the repo root.
- [x] First run against a DB with one tenant and no matching facility creates 1 facility + 1 resource + 7 availability rules.
- [x] Re-run is a no-op (no duplicate rows, "Already seeded" message, exit 0).
- [x] Run against a DB with no tenants prints "No tenant found. Run register-tenant first." and exits 1.
- [x] All 3 integration tests pass.
- [x] No production code modified (only new files + Makefile + root package.json).
- [x] Spec's data values used verbatim: address `123 Aquatic Drive`, slug `splash-sports-club`, hours 06:00–22:00, slot 60 min, capacity 20, attributes `{lanes:6, length_m:25, min_age:5}`.