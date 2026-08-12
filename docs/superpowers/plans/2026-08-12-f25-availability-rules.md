# F-25 Booking Availability Rule Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject bookings that fall outside any availability rule for the resource, or fall within a maintenance/closed window, with a 422 error.

**Architecture:** Add a new repository method `get_applicable_rules(resource_id, start_at, end_at)` to `AvailabilityRuleRepository`. Call it from `BookingService.create_booking()` after the resource is loaded and before the booking is persisted. Reject with new domain exceptions if no rules match or any rule is `maintenance`/`closed`.

**Tech Stack:** FastAPI, SQLAlchemy 2 (async), PostgreSQL 16, pytest.

## Global Constraints

- The validation happens in `BookingService.create_booking()` AFTER acquiring the resource lock and BEFORE calling `bookings.add_safe()`.
- The new repo method `get_applicable_rules` returns a list of `AvailabilityRule` domain entities whose time window overlaps `[start_at, end_at)`.
- Two new domain exceptions: `OutsideAvailabilityError` (no rules match) and `ResourceUnavailableError` (rule has status `maintenance` or `closed`).
- The HTTP layer translates these to 422 responses (verify the existing exception-to-status mapping in the booking router).
- "No rules defined" is treated as "outside availability" (the resource has no schedule, so booking is rejected).
- The existing `.status` field on `AvailabilityRule` and `AvailabilityRuleModel` is assumed to be one of `active`, `maintenance`, `closed`. If the schema is different, the implementer reports and stops.
- No frontend changes. No new API endpoint. Just validation in the existing flow.

**Pre-flight verification (run before starting Task 1):**
- Run `find apps/backend/src/facility/infrastructure -name "repositories.py" -exec grep -n "AvailabilityRuleRepository\|class AvailabilityRule" {} \;` to find the repo.
- Run `cat apps/backend/src/facility/infrastructure/models.py | grep -A 20 "class AvailabilityRuleModel"` to confirm the schema.
- Run `cat apps/backend/src/booking/application/booking_service.py | head -120` to confirm the validation point.
- Run `cat apps/backend/src/booking/domain/errors.py 2>&1 | head -30` to see existing exception types.

---

## File Structure

| File | Type | Responsibility |
|---|---|---|
| `apps/backend/src/facility/infrastructure/repositories.py` | Modify | Add `get_applicable_rules` method to `AvailabilityRuleRepository` |
| `apps/backend/src/booking/application/booking_service.py` | Modify | Add validation call in `create_booking` |
| `apps/backend/src/booking/domain/errors.py` | Modify (or create) | Add `OutsideAvailabilityError` and `ResourceUnavailableError` |
| `apps/backend/tests/unit/test_availability_rule_repository.py` | Create | Unit test for `get_applicable_rules` |
| `apps/backend/tests/integration/test_booking_service.py` | Modify | Add availability validation tests |

---

### Task 1: Add `get_applicable_rules` to `AvailabilityRuleRepository`

**Files:**
- Modify: `apps/backend/src/facility/infrastructure/repositories.py` (add method)
- Create: `apps/backend/tests/unit/test_availability_rule_repository.py` (add unit test)

**Interfaces:**
- Consumes: `AvailabilityRuleRepository` (existing class)
- Produces: `async def get_applicable_rules(*, tenant_id: UUID, resource_id: UUID, start_at: datetime, end_at: datetime) -> list[AvailabilityRule]`

- [ ] **Step 1: Locate the existing `AvailabilityRuleRepository` and its schema**

```bash
grep -n "class AvailabilityRuleRepository\|class AvailabilityRuleModel\|AvailabilityRuleModel\." apps/backend/src/facility/infrastructure/repositories.py
grep -n "status\b" apps/backend/src/facility/infrastructure/models.py | head -10
```

Expected: the class is found; the model has a `status` column.

- [ ] **Step 2: Write the failing unit test**

Create `apps/backend/tests/unit/test_availability_rule_repository.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from common.infrastructure.db import AsyncSessionLocal
from facility.domain.entities import AvailabilityRule
from facility.infrastructure.models import AvailabilityRuleModel, ResourceModel, TenantModel
from facility.infrastructure.repositories import AvailabilityRuleRepository


@pytest.mark.asyncio
async def test_get_applicable_rules_returns_overlapping_ranges():
    """F-25: returns rules whose time window overlaps [start_at, end_at)."""
    tenant_id = uuid4()
    resource_id = uuid4()

    # Three rules: one before, one overlapping, one after
    async with AsyncSessionLocal() as session:
        session.add(TenantModel(id=tenant_id, name=f"t-{tenant_id}"))
        session.add(ResourceModel(id=resource_id, tenant_id=tenant_id, name="Court 1"))
        # Rule 1: 09:00-11:00 (overlaps 10:00-12:00)
        session.add(AvailabilityRuleModel(
            tenant_id=tenant_id,
            resource_id=resource_id,
            start_at=datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 1, 11, 0, tzinfo=timezone.utc),
            status="active",
        ))
        # Rule 2: 13:00-14:00 (does NOT overlap 10:00-12:00)
        session.add(AvailabilityRuleModel(
            tenant_id=tenant_id,
            resource_id=resource_id,
            start_at=datetime(2026, 9, 1, 13, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 1, 14, 0, tzinfo=timezone.utc),
            status="active",
        ))
        await session.commit()

        repo = AvailabilityRuleRepository(session)
        results = await repo.get_applicable_rules(
            tenant_id=tenant_id,
            resource_id=resource_id,
            start_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        )

    # Only the overlapping rule should be returned
    assert len(results) == 1
    assert results[0].start_at == datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)
```

**Note:** Adjust the model field names (e.g., `start_at` vs `start_time`) to match the actual schema. Read `AvailabilityRuleModel` to confirm.

- [ ] **Step 3: Run the test to verify it fails**

Run:
```bash
cd apps/backend && PYTHONPATH=src pytest tests/unit/test_availability_rule_repository.py -v --tb=short 2>&1 | tail -15
```

Expected: FAIL — `get_applicable_rules` method does not exist (`AttributeError` or `TypeError`).

- [ ] **Step 4: Implement `get_applicable_rules`**

Add this method to `AvailabilityRuleRepository` in `apps/backend/src/facility/infrastructure/repositories.py`:

```python
async def get_applicable_rules(
    self,
    *,
    tenant_id: UUID,
    resource_id: UUID,
    start_at: datetime,
    end_at: datetime,
) -> list[AvailabilityRule]:
    """Return availability rules whose [start_at, end_at) overlaps [start_at, end_at).

    Used by BookingService to validate that a booking falls within at
    least one active rule.
    """
    stmt = (
        select(AvailabilityRuleModel)
        .where(
            AvailabilityRuleModel.tenant_id == tenant_id,
            AvailabilityRuleModel.resource_id == resource_id,
            AvailabilityRuleModel.start_at < end_at,
            AvailabilityRuleModel.end_at > start_at,
        )
    )
    result = await self._s.execute(stmt)
    return [_to_domain(m) for m in result.scalars().all()]
```

If the existing `AvailabilityRuleRepository` uses a different session attribute name (e.g., `self.session` instead of `self._s`), adjust accordingly.

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
cd apps/backend && PYTHONPATH=src pytest tests/unit/test_availability_rule_repository.py -v --tb=short 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/src/facility/infrastructure/repositories.py \
    apps/backend/tests/unit/test_availability_rule_repository.py
git commit -m "feat(facility): add get_applicable_rules to AvailabilityRuleRepository (F-25 step 1)"
```

---

### Task 2: Validate availability rules in `BookingService.create_booking()`

**Files:**
- Modify: `apps/backend/src/booking/domain/errors.py` (add new exceptions)
- Modify: `apps/backend/src/booking/application/booking_service.py` (add validation)
- Modify: `apps/backend/tests/integration/test_booking_service.py` (add validation tests)

**Interfaces:**
- Consumes: `AvailabilityRuleRepository.get_applicable_rules` (from Task 1)
- Consumes: `BookingService.create_booking` (existing)
- Produces: two new domain exceptions: `OutsideAvailabilityError`, `ResourceUnavailableError`

- [ ] **Step 1: Add the new exceptions**

In `apps/backend/src/booking/domain/errors.py` (create if it doesn't exist), add:

```python
class BookingValidationError(Exception):
    """Base class for booking validation errors."""
    pass


class OutsideAvailabilityError(BookingValidationError):
    """Booking time falls outside any availability rule for the resource."""

    def __init__(self, resource_id, start_at, end_at):
        self.resource_id = resource_id
        self.start_at = start_at
        self.end_at = end_at
        super().__init__(
            f"No availability rule covers {start_at}..{end_at} for resource {resource_id}"
        )


class ResourceUnavailableError(BookingValidationError):
    """Booking time falls within a maintenance/closed window."""

    def __init__(self, resource_id, reasons):
        self.resource_id = resource_id
        self.reasons = reasons
        super().__init__(
            f"Resource {resource_id} unavailable: {reasons}"
        )
```

- [ ] **Step 2: Locate the validation point in `BookingService.create_booking()`**

```bash
grep -n "async def create_booking\|add_safe\|await self.bookings" apps/backend/src/booking/application/booking_service.py
```

Expected: the create_booking method is found. Record the line number. The validation call must be inserted AFTER the resource is loaded and before `add_safe()`.

- [ ] **Step 3: Write the failing integration test**

Add this test to `apps/backend/tests/integration/test_booking_service.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from booking.domain.errors import OutsideAvailabilityError, ResourceUnavailableError
from booking.application.booking_service import BookingService


@pytest.mark.asyncio
async def test_create_booking_outside_availability_raises(
    seeded_tenant: UUID,
    seeded_resource: UUID,
    booking_service: BookingService,
):
    """F-25: booking outside any availability rule raises OutsideAvailabilityError."""
    customer_id = uuid4()
    # No availability rules defined for the resource → should reject
    with pytest.raises(OutsideAvailabilityError):
        await booking_service.create_booking(
            tenant_id=seeded_tenant,
            customer_id=customer_id,
            resource_id=seeded_resource,
            start_at=datetime(2099, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2099, 1, 1, 12, 0, tzinfo=timezone.utc),
        )


@pytest.mark.asyncio
async def test_create_booking_during_maintenance_raises(
    seeded_tenant: UUID,
    seeded_resource_with_maintenance: UUID,
    booking_service: BookingService,
):
    """F-25: booking during a maintenance window raises ResourceUnavailableError."""
    customer_id = uuid4()
    with pytest.raises(ResourceUnavailableError):
        await booking_service.create_booking(
            tenant_id=seeded_tenant,
            customer_id=customer_id,
            resource_id=seeded_resource_with_maintenance,
            start_at=datetime(2099, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2099, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
```

**Note:** Adjust the fixture names (`seeded_tenant`, `seeded_resource`, `seeded_resource_with_maintenance`, `booking_service`) to match the existing test conventions. Read 30 lines of the existing test file to align.

- [ ] **Step 4: Skip running this test until the validation is added**

The test will fail because the validation doesn't exist yet. That's the expected RED state. Proceed to Step 5.

- [ ] **Step 5: Add the validation in `BookingService.create_booking()`**

In `apps/backend/src/booking/application/booking_service.py`, locate the `create_booking` method. After the resource is loaded and BEFORE `add_safe()` is called, add:

```python
from booking.domain.errors import OutsideAvailabilityError, ResourceUnavailableError

# Inside create_booking, after the resource is loaded:
rules = await self.availability_repo.get_applicable_rules(
    tenant_id=tenant_id,
    resource_id=resource_id,
    start_at=start_at,
    end_at=end_at,
)
if not rules:
    raise OutsideAvailabilityError(
        resource_id=resource_id,
        start_at=start_at,
        end_at=end_at,
    )
unavailable = [r for r in rules if r.status in ("maintenance", "closed")]
if unavailable:
    raise ResourceUnavailableError(
        resource_id=resource_id,
        reasons=[r.status for r in unavailable],
    )
```

**Note:** If `BookingService` does not already have `self.availability_repo`, you need to inject it. Check the constructor (`__init__`) and add it as a dependency. If the existing constructor uses a different pattern, follow that pattern.

- [ ] **Step 6: Run the test to verify it passes**

Run:
```bash
cd apps/backend && PYTHONPATH=src pytest tests/integration/test_booking_service.py -v --tb=short 2>&1 | tail -20
```

Expected: PASS — both new tests pass; existing tests still pass.

- [ ] **Step 7: Run the full booking test suite to confirm no regression**

Run:
```bash
cd apps/backend && PYTHONPATH=src pytest tests/api/test_booking_endpoints.py tests/integration/test_booking_service.py tests/unit/test_booking_entity.py -q --tb=short 2>&1 | tail -10
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/src/booking/application/booking_service.py \
    apps/backend/src/booking/domain/errors.py \
    apps/backend/tests/integration/test_booking_service.py
git commit -m "feat(booking): reject bookings outside availability rules (F-25)"
```

---

## Verification (after all tasks land)

- [ ] F-25: Booking with no availability rules → 422 (`OutsideAvailabilityError`)
- [ ] F-25: Booking outside availability window → 422 (`OutsideAvailabilityError`)
- [ ] F-25: Booking during maintenance → 422 (`ResourceUnavailableError`)
- [ ] F-25: Booking within active window → 201 (success)
- [ ] F-25: Existing booking tests still pass (no regression)

## Out of scope for this plan

- Recurring availability rules (e.g., "every Monday 9am-5pm")
- Customer-facing availability UI
- Holiday/event overrides
- F-22 (invoice race), F-24 (idempotency) — separate plans
