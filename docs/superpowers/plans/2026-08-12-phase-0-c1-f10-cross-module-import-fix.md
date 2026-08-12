# Phase 0 C1 — F-10 Cross-Module Import Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the ADR-0001 violation at `booking/infrastructure/repositories.py:248` so the bounded-context architecture test suite passes, with no regression to existing booking tests.

**Architecture:** Replace the in-method SQL JOIN against `ResourceModel` with a call to `FacilityService.list_resources()` followed by an `IN`-filter on resource IDs. Reuses existing service method (no new code in `facility_service.py`). The booking repository already has `facility_service` injected via `booking_service.py:84-85`.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x async, pytest, FastAPI dependency injection.

## Global Constraints

- Only `apps/backend/src/booking/infrastructure/repositories.py` is modified.
- No changes to `apps/backend/src/facility/application/facility_service.py` — `list_resources()` exists and is reused.
- No changes to `BookingRepository.__init__` — `facility_service` is already an optional injected attribute.
- Architecture tests `tests/architecture/test_module_boundaries.py` (currently 2/2 FAIL) must pass after Task 1.
- Booking tests `tests/api/test_booking_endpoints.py`, `tests/integration/test_booking_service.py`, `tests/unit/test_booking_entity.py` (currently 32/32 PASS) must remain green.
- Sub-project B baseline (`tests/unit/test_booking_tariff.py` + `tests/payments/`) must remain green.
- All 3 P0 tasks land on `main` directly (matches Sub-projects A and B pattern; no worktree).
- All commands run from repo root unless otherwise noted.

---

## File Structure

This plan modifies 2 files across 3 tasks.

| File | Responsibility | Task |
|---|---|---|
| `apps/backend/src/booking/infrastructure/repositories.py:246-252` | Replace SQL JOIN with `FacilityService.list_resources()` + `IN`-filter | Task 1 |
| `docs/CODEBASE_REVIEW.md` (F-10 row, line 686) | Mark F-10 as `✅ Resolved` with closing commit SHA | Task 3 |
| (no new files; no new production code outside the one repository method) | — | — |

---

## Tasks

### Task 1: Refactor `BookingRepository.list_admin_bookings` to remove cross-module import

**Files:**
- Modify: `apps/backend/src/booking/infrastructure/repositories.py:246-252` (replace JOIN block in `list_admin_bookings`)

**Interfaces:**
- Consumes: nothing (no prior task in this plan)
- Produces: a refactored `list_admin_bookings` method that no longer imports `facility.infrastructure.models` and instead delegates to `self.facility_service.list_resources()`

**Current code (lines 246-252):**

```python
        if facility_id:
            # Join with resources to filter by facility
            from facility.infrastructure.models import ResourceModel

            stmt = stmt.join(ResourceModel, BookingModel.resource_id == ResourceModel.id).where(
                ResourceModel.facility_id == facility_id
            )
```

**Reference signature (already exists, do not change):**

```python
# apps/backend/src/facility/application/facility_service.py:116
async def list_resources(self, *, tenant_id: UUID, facility_id: UUID) -> list[Resource]:
    ...
```

The `Resource` domain entity has `.id: UUID` (verified by reading `apps/backend/src/facility/domain/entities.py`).

---

- [ ] **Step 1: Establish the baseline failure**

Confirm the architecture tests fail at HEAD:

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/architecture/test_module_boundaries.py -v --tb=line 2>&1 | tail -10
```

Expected: **2 failed**. Specifically:
- `test_booking_does_not_import_facility_infrastructure` fails with message: `Booking module violates bounded context boundary by importing from facility.infrastructure: - booking/infrastructure/repositories.py:248: from facility.infrastructure.models import ResourceModel`

- [ ] **Step 2: Verify the booking tests pass at HEAD**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/api/test_booking_endpoints.py tests/integration/test_booking_service.py tests/unit/test_booking_entity.py --tb=no -q 2>&1 | tail -3
```

Expected: `32 passed, 0 failed`. If the count differs (e.g., a test was renamed), record the actual baseline count for comparison in Step 5.

- [ ] **Step 3: Replace the JOIN block**

Edit `apps/backend/src/booking/infrastructure/repositories.py`. Replace lines 246-252 (the `if facility_id:` block) with:

```python
        if facility_id:
            # F-10 fix: Use FacilityService instead of importing facility.infrastructure.models
            # (ADR-0001 — bounded-context isolation)
            if self.facility_service is None:
                raise RuntimeError(
                    "BookingRepository.facility_service is required when filtering by facility_id. "
                    "Inject FacilityService via BookingService(facility_service=...)."
                )
            resources = await self.facility_service.list_resources(
                tenant_id=tenant_id, facility_id=facility_id
            )
            resource_ids = [r.id for r in resources]
            if not resource_ids:
                return []
            stmt = stmt.where(BookingModel.resource_id.in_(resource_ids))
```

Notes:
- `self.facility_service` is already an optional attribute on `BookingRepository` (set by `booking_service.py:84-85`).
- The early-return on empty `resource_ids` preserves current behavior (a JOIN against an empty resources table also returns zero rows).
- The replacement is functionally equivalent to the JOIN — same rows are returned.

- [ ] **Step 4: Verify the architecture tests now pass**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/architecture/test_module_boundaries.py -v 2>&1 | tail -8
```

Expected: **2 passed**. Both `test_booking_does_not_import_facility_infrastructure` and `test_no_bounded_context_imports_infrastructure_cross_boundary` pass.

- [ ] **Step 5: Verify the booking tests still pass (no regression)**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/api/test_booking_endpoints.py tests/integration/test_booking_service.py tests/unit/test_booking_entity.py --tb=short -q 2>&1 | tail -5
```

Expected: **all tests pass**. The count should match the baseline from Step 2 (32 if unchanged). **0 failed.**

If any test fails: most likely cause is `facility_service` not being injected in a test that exercises the `facility_id` branch. Check whether the failing test calls `list_admin_bookings` with a `facility_id` argument; if so, update the test's `BookingRepository(session, facility_service=...)` injection (pattern shown in `tests/integration/test_booking_service.py:196,301`).

- [ ] **Step 6: Verify the violation is gone via grep**

```bash
cd /home/soloengine/Github/splash_sports_management
grep -rn "from facility.infrastructure.models" apps/backend/src/booking/
```

Expected: **no output**.

- [ ] **Step 7: Verify Sub-project B baseline preserved**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/unit/test_booking_tariff.py tests/payments/test_webhook_endpoint.py tests/payments/test_webhook_service.py tests/payments/test_refund_endpoint.py tests/payments/test_refund_service.py tests/payments/test_payment_link_endpoint.py tests/payments/test_payment_link_service.py tests/payments/test_repositories.py tests/payments/test_invoice_endpoints.py tests/payments/test_invoice_service.py tests/payments/test_value_objects.py tests/payments/test_idempotency_store.py tests/payments/test_entities.py tests/payments/test_payments_events.py tests/payments/test_provider.py --tb=no -q 2>&1 | tail -3
```

Expected: `68 passed` (or the baseline count from Sub-project B). **0 failed.**

- [ ] **Step 8: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/src/booking/infrastructure/repositories.py
git commit -m "fix(booking): remove ADR-0001 violation via FacilityService delegation (F-10)

The list_admin_bookings method imported facility.infrastructure.models
inline to JOIN bookings with resources. This crossed the bounded-context
boundary. Replace the JOIN with a FacilityService.list_resources() call
followed by an IN-filter on resource IDs.

Architecture test tests/architecture/test_module_boundaries.py now passes
(2/2); was 0/2. All 32 booking tests still green."
```

---

### Task 2: Verify no regressions on broader test surface

**Files:**
- (no file changes — verification only)

**Interfaces:**
- Consumes: Task 1's refactored `BookingRepository.list_admin_bookings`
- Produces: evidence that no other test in the backend suite was affected (for the audit doc update in Task 3)

---

- [ ] **Step 1: Run the full backend test suite (excluding known-baseline failures)**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest --ignore=tests/unit/test_domain_types.py --tb=no -q 2>&1 | tail -10
```

Expected: **no new failures** beyond the documented baseline (test_domain_types.py 27 fails + aiosqlite/responses env errors). If a test fails that was passing before Task 1, investigate and fix before proceeding.

`tests/unit/test_domain_types.py` is excluded because its 27 failures are pre-existing baseline failures caused by F-40 (Pydantic vs pure-Python types) — see `docs/CODEBASE_REVIEW.md` Appendix C.

- [ ] **Step 2: Capture the test summary for the audit commit message**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest --ignore=tests/unit/test_domain_types.py --tb=no -q 2>&1 | tail -3
```

Expected: a one-line summary like `XXX passed, YYY skipped in ...`. Record the "passed" number — it goes into the audit doc commit message in Task 3.

- [ ] **Step 3: No commit (verification gate only)**

This task produces no commit. The verification is a precondition for Task 3.

---

### Task 3: Update audit doc to mark F-10 resolved

**Files:**
- Modify: `docs/CODEBASE_REVIEW.md:686` (F-10 status cell)

**Interfaces:**
- Consumes: closing commit SHA from Task 1
- Produces: F-10 row marked `✅ Resolved` with the closing commit SHA

**Finding reference (from `docs/CODEBASE_REVIEW.md:686`):**
- F-10 — Architecture, **P0** — "Cross-module DB model import"

**Wording for the status cell** (mirror the existing resolved style at lines 677-680, 681, 683, 684):

```
✅ Resolved (`<sha>`) — replaced in-method SQL JOIN against facility.infrastructure.models with FacilityService.list_resources() call; architecture test now passes
```

Where `<sha>` is the short SHA from Task 1's commit.

---

- [ ] **Step 1: Read the current F-10 row**

```bash
grep -n "F-10 | " docs/CODEBASE_REVIEW.md
```

Expected: 1 line ending in `| ❌ Open |`.

- [ ] **Step 2: Capture the closing commit SHA**

```bash
cd /home/soloengine/Github/splash_sports_management
git log -1 --format="%h" -- apps/backend/src/booking/infrastructure/repositories.py
```

Expected: a 7-character short SHA. Use this in Step 3.

- [ ] **Step 3: Mark F-10 resolved**

Edit `docs/CODEBASE_REVIEW.md`. Find the F-10 row (line 686) and replace its trailing `| ❌ Open |` with:

```
| ✅ Resolved (`<sha>`) — replaced in-method SQL JOIN against facility.infrastructure.models with FacilityService.list_resources() call; architecture test now passes |
```

Replace `<sha>` with the value from Step 2.

Use the Edit tool with the exact existing row (copy from Step 1's grep output) as `old_string`.

- [ ] **Step 4: Verify the row updated cleanly**

```bash
grep -n "F-10 | " docs/CODEBASE_REVIEW.md
```

Expected: 1 line ending with `✅ Resolved`.

- [ ] **Step 5: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add docs/CODEBASE_REVIEW.md
git commit -m "docs(review): mark F-10 resolved — booking module no longer imports facility.infrastructure"
```

---

## Verification (after all tasks land)

- [ ] `grep -rn "from facility.infrastructure.models" apps/backend/src/booking/` returns no output
- [ ] `cd apps/backend && PYTHONPATH=src pytest tests/architecture/test_module_boundaries.py` → 2 passed
- [ ] `cd apps/backend && PYTHONPATH=src pytest tests/api/test_booking_endpoints.py tests/integration/test_booking_service.py tests/unit/test_booking_entity.py` → 32 passed (no regression)
- [ ] `cd apps/backend && PYTHONPATH=src pytest tests/unit/test_booking_tariff.py tests/payments/` → 68+ passed (Sub-project B baseline)
- [ ] `docs/CODEBASE_REVIEW.md` F-10 row shows `✅ Resolved` with the closing commit SHA
- [ ] No `apps/backend/src/facility/**` files modified (facility_service reused as-is)

## Out of scope for this plan

- Renaming `get_by_razorpay_payment_id_for_any_tenant()` in payments (F-07 hardening suggestion) — deferred to "Payment trust hardening" follow-up
- Other bounded-context dependency violations (if any) beyond `booking → facility.infrastructure.models` — none detected by `grep`; audit-complete
- F-11, F-12, F-13 — separate sub-sub-projects (C2, C3, C4)
- Implementing `FacilityService.get_facility_names(...)`/`lock_resource_for_update(...)` from scratch — they already exist
