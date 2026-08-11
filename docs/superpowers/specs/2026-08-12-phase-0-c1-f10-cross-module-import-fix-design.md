# Phase 0 C1 — F-10 Cross-Module Import Fix Design

> **For agentic workers:** This is a design spec. After approval, use superpowers:writing-plans to produce an implementation plan.

**Date:** 2026-08-12
**Status:** Design (pending user approval)
**Scope:** Sub-sub-project C1 of Sub-project C — close P0 finding F-10 (ADR-0001 violation: `booking` imports `facility.infrastructure.models`).

---

## Context

The Phase 0 audit (`docs/CODEBASE_REVIEW.md`, 2026-08-11) flagged F-10 as a P0 architectural issue: the `booking` bounded-context module reaches into `facility.infrastructure.models` for an ORM model it does not own.

Unlike Sub-projects A and B (where the code was already shipped and only the audit doc was stale), F-10 has a **real, verified violation** that is actively breaking the architecture test suite.

**Verified state (2026-08-12):**
- `tests/architecture/test_module_boundaries.py` — 2 tests, **both FAIL** with the explicit message:
  > Booking module violates bounded context boundary by importing from facility.infrastructure:
  > - booking/infrastructure/repositories.py:248: from facility.infrastructure.models import ResourceModel
- `tests/api/test_booking_endpoints.py` + `tests/integration/test_booking_service.py` + `tests/unit/test_booking_entity.py` — 32/32 booking tests pass.
- All helper methods the audit said needed creating **already exist** in `FacilityService` (lines 172, 211, 230, 249). The 3-5 day audit estimate assumed they needed to be built; they don't.

This means the actual work is **much smaller** than the audit estimates (~1-2 hours), but the impact is real — two architecture tests will start passing.

---

## Goal

Remove the single ADR-0001 violation at `booking/infrastructure/repositories.py:248` so the architecture test suite passes, without changing booking query semantics. Then mark F-10 as `✅ Resolved` in the audit doc.

---

## Why this is real work (verification evidence)

### The violation

`apps/backend/src/booking/infrastructure/repositories.py:248`:
```python
if facility_id:
    # Join with resources to filter by facility
    from facility.infrastructure.models import ResourceModel  # ← ADR-0001 violation

    stmt = stmt.join(ResourceModel, BookingModel.resource_id == ResourceModel.id).where(
        ResourceModel.facility_id == facility_id
    )
```

This is the only cross-module `.infrastructure.models` import in the `booking` module (verified via `grep -rn "from facility.infrastructure.models" apps/backend/src/booking/`). The audit doc cites lines 81 and 152 as additional violations; those line numbers are stale — the violation has consolidated to one location.

### Why the audit's "new methods on FacilityService" work is unnecessary

The audit said:
> New methods on `FacilityService`: `get_facility_names(tenant_id, ids: list[UUID]) -> dict[UUID, str]`, `lock_resource_for_update(...)`

Both already exist (verified by reading `apps/backend/src/facility/application/facility_service.py:172, 211, 230, 249`):
- `lock_resource_for_update(*, tenant_id, resource_id)` — line 172
- `get_resource_names(*, tenant_id, resource_ids)` — line 211
- `get_facility_names(*, tenant_id, facility_ids)` — line 230
- `get_resource_and_facility_names(*, tenant_id, resource_ids)` — line 249

For this fix we only need `FacilityService.list_resources(*, tenant_id, facility_id) -> list[Resource]` (line 116), which also exists. **No new code is needed in `facility_service.py`.**

### Why the fix is small

`BookingRepository` already has `facility_service` injected. From `apps/backend/src/booking/application/booking_service.py:84-85`:
```python
if facility_service is not None:
    self.bookings.facility_service = facility_service
```

So the repository can call `self.facility_service.list_resources(...)` directly. The only change is to swap a SQL JOIN (5 lines) for a service call (4-5 lines). Net diff: ~10 lines, all in one method.

---

## Architecture

**Refactor strategy:** Replace the in-line SQL JOIN against `ResourceModel` with a two-step query:

1. Call `FacilityService.list_resources(tenant_id=tenant_id, facility_id=facility_id)` to fetch matching `Resource` domain entities.
2. Extract their IDs into a list.
3. If the list is empty, return early (no bookings can match).
4. Otherwise, filter the bookings query with `BookingModel.resource_id.in_(resource_ids)`.

This is functionally equivalent to the JOIN: the JOIN filters bookings whose resource belongs to a given facility, and the `.in_()` filter does the same.

**Why not use `FacilityService.get_facility_names(...)` instead?** That method is designed for batch ID lookup (given IDs, return names). The booking query starts from the other direction: given a facility, find all bookings. `list_resources()` is the right shape.

### Trade-off considered

An alternative is to fetch `resource_ids` from the `FacilityRepository` directly (intra-context path: `booking` → `facility.infrastructure.repositories`). This is **also** an ADR-0001 violation (any `infrastructure.*` import across contexts is forbidden). The `FacilityService` path is the only allowed direction.

---

## Components

**Files modified (1 file):**
- `apps/backend/src/booking/infrastructure/repositories.py:246-252` (replace JOIN block in `list_admin_bookings`)

**Files NOT modified:**
- `apps/backend/src/facility/application/facility_service.py` — `list_resources()` exists and works
- `apps/backend/src/booking/application/booking_service.py` — already injects `facility_service` into the repository
- `apps/backend/src/booking/infrastructure/models.py` — no change
- `tests/**` — no new tests; existing architecture tests serve as the acceptance gate
- `apps/web-pwa/**` — no frontend change

**Acceptance gate (pre-existing tests, no new code):**
- `tests/architecture/test_module_boundaries.py::test_booking_does_not_import_facility_infrastructure` — currently fails, will pass
- `tests/architecture/test_module_boundaries.py::test_no_bounded_context_imports_infrastructure_cross_boundary` — currently fails, will pass

---

## Data flow

Before (current, ADR-0001 violation):
```
BookingRepository.list_admin_bookings(tenant_id, facility_id)
  → SQL JOIN bookings ⨝ resources ON bookings.resource_id = resources.id
  → WHERE resources.facility_id = :facility_id
  → returns BookingModel rows
```

After (refactored, ADR-0001 compliant):
```
BookingRepository.list_admin_bookings(tenant_id, facility_id)
  → FacilityService.list_resources(tenant_id=tenant_id, facility_id=facility_id)
      → returns list[Resource] (Resource is a domain entity)
  → resource_ids = [r.id for r in resources]
  → if not resource_ids: return []
  → SQL SELECT bookings WHERE resource_id IN (:resource_ids)
  → returns BookingModel rows
```

The result set is identical (a JOIN with a `WHERE` filter produces the same rows as an `IN` filter on the same IDs). The difference is two round-trips (one to fetch resource IDs, one to fetch bookings) instead of one JOIN — acceptable for the admin-list query which is not on the hot path.

---

## Error handling

- **Empty facility (no resources):** return `[]` early. Matches current behavior (a JOIN against an empty resources table produces zero rows anyway).
- **`FacilityService.list_resources` raises NotFound or Validation:** propagate as-is. The booking repository should not swallow these — they're real errors.
- **No new exception types introduced.** The behavior surface is identical to the JOIN version.

---

## Testing

**Acceptance (architecture tests must pass):**
```bash
cd apps/backend
PYTHONPATH=src pytest tests/architecture/test_module_boundaries.py -v
# Expected: 2 passed (currently 2 failed)
```

**Regression (booking tests must stay green):**
```bash
cd apps/backend
PYTHONPATH=src pytest tests/api/test_booking_endpoints.py tests/integration/test_booking_service.py tests/unit/test_booking_entity.py --tb=short
# Expected: 32 passed
```

**Cross-context blast radius (Sub-project B baseline preserved):**
```bash
cd apps/backend
PYTHONPATH=src pytest tests/unit/test_booking_tariff.py tests/payments/ --tb=no -q
# Expected: 68+ passed (Sub-project B baseline)
```

**Static check (the violation must be gone):**
```bash
grep -rn "from facility.infrastructure.models" apps/backend/src/booking/
# Expected: no output
```

---

## Verification (definition of done)

- [ ] `booking/infrastructure/repositories.py` no longer imports `facility.infrastructure.models` (verified via grep)
- [ ] Architecture test `test_booking_does_not_import_facility_infrastructure` passes
- [ ] Architecture test `test_no_bounded_context_imports_infrastructure_cross_boundary` passes
- [ ] All 32 booking tests still pass (no regression)
- [ ] Sub-project B baseline (68+ payment tests) still green
- [ ] `docs/CODEBASE_REVIEW.md` F-10 row updated to `✅ Resolved` with closing commit SHA

---

## Out of scope (deferred to other sub-sub-projects)

- **F-11, F-12, F-13** — separate sub-sub-projects in Sub-project C (C2, C3, C4)
- **F-10 hardening beyond the single violation** — e.g., extracting `BookingRepository` JOINs into a shared query helper. The audit didn't ask for it; the architecture test only catches direct `.infrastructure.models` imports. YAGNI.
- **F-14 dependency rule** (`tests/architecture/`) — already enforced by the existing tests, no new architecture test needed.

---

## Risk

**Very low.** The refactor is in a single method, reuses an existing service method, and produces identical results. The architecture tests are precise: they enumerate every `.infrastructure.models` import in the booking module, so if the violation is gone, the test passes; if it isn't, the test fails with the exact file:line.
