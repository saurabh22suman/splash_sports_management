# Phase 1 Quick Wins — F-22 + F-24 + F-25 Design

> **For agentic workers:** This is a design spec. After approval, use superpowers:writing-plans to produce three implementation plans (one per finding).

**Date:** 2026-08-12
**Status:** Design (pending user approval)
**Scope:** Three independent Phase 1 fixes — F-22 invoice race, F-24 idempotency dedup, F-25 availability rule validation. Each fix is small, contained, and shipped independently.

---

## Context

Phase 0 closed 17 of 19 P0s. The remaining 2 P0s (F-11, F-14) are deferred. To "move to development", the user wants to close known correctness bugs in Phase 1 work that are small enough to ship quickly.

Three independent fixes identified via parallel verification:

| Finding | Domain | Effort | Why now |
|---|---|---|---|
| F-22 Invoice race | Payments integrity | 1-2 days | Real concurrency bug; UNIQUE constraint only catches the duplicate, not the race |
| F-24 Idempotency dedup | Payments integrity | 1-2 days | Header required today; dedup logic never wired even though repo is injected |
| F-25 Availability rules | Booking correctness | 2-3 days | Bookings outside hours succeed; new `get_applicable_rules` repo method needed |

These three fixes are fully independent (different files, different domains, different tests). They can be implemented in parallel via three separate plans.

---

## F-22 — Invoice number race fix

### The bug

`apps/backend/src/payments/infrastructure/repositories.py:124-136` (`next_invoice_number`):

```python
async def next_invoice_number(self, tenant_id: UUID) -> str:
    result = await self._s.execute(
        select(InvoiceModel.invoice_number)
        .where(InvoiceModel.tenant_id == tenant_id)
        .order_by(InvoiceModel.created_at.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    if last is None:
        return "INV-000001"
    n = int(last.split("-")[-1]) + 1
    return f"INV-{n:06d}"
```

**Race window:**
1. Request A reads last invoice: "INV-000005"
2. Request B reads last invoice: "INV-000005" (before A persists)
3. Request A persists: "INV-000006"
4. Request B persists: "INV-000006" → UNIQUE constraint violation → 500 to client

The UNIQUE constraint on `(tenant_id, invoice_number)` catches the duplicate but produces a 500 error rather than a clean "retry" — and corrupts the second request's flow.

### Design

Use a PostgreSQL **transaction-scoped advisory lock** keyed by the tenant_id. This gives per-tenant serialization without schema changes or table locks.

**Implementation outline:**

```python
async def next_invoice_number(self, tenant_id: UUID) -> str:
    # Acquire per-tenant advisory lock (transaction-scoped; auto-released on commit/rollback)
    lock_key = int.from_bytes(tenant_id.bytes[:8], "big", signed=False)
    await self._s.execute(
        text("SELECT pg_advisory_xact_lock(:key)").bindparams(key=lock_key)
    )
    # Existing read-increment logic now safely serialized
    result = await self._s.execute(
        select(InvoiceModel.invoice_number)
        .where(InvoiceModel.tenant_id == tenant_id)
        .order_by(InvoiceModel.created_at.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    if last is None:
        return "INV-000001"
    n = int(last.split("-")[-1]) + 1
    return f"INV-{n:06d}"
```

**Why advisory lock:**
- Standard PostgreSQL pattern for per-tenant serialization
- No schema change (no counter table, no sequence)
- Lock auto-released on transaction end (no risk of leaks)
- Per-tenant, not global — different tenants don't block each other
- Works with the existing UNIQUE constraint as a defense-in-depth

**Tests:**
- `tests/integration/test_payments_repositories.py` — concurrent `next_invoice_number` for the same tenant produces unique numbers
- Test strategy: `asyncio.gather` 10 concurrent calls, assert all 10 numbers are unique and consecutive
- Verify existing single-tenant test still passes (no regression)

**Out of scope:**
- Replacing the `INV-` prefix scheme (e.g., ULIDs, time-based)
- Migration to a DB-generated sequence
- Concurrent cross-tenant tests (different tenants don't block each other; that's the feature)

---

## F-24 — Idempotency-Key deduplication

### The bug

`X-Idempotency-Key` header is enforced (returns 422 if missing), but the dedup logic is missing:

- `IdempotencyKeyRepository` is injected into `PaymentService` at `payments/interfaces/http/deps.py:93-97`
- No code calls `self._idem.get_by_key()` to check for cached responses
- No middleware (no `IdempotencyMiddleware` exists)
- No handling of `UniqueConstraintError` on the unique index `(tenant_id, idempotency_key)`

**Failure mode:** Customer double-clicks Pay → first request partially succeeds → client retries with same key → CRASH with 500 OR duplicate payment record.

### Design

Add an **inline pre-check + post-cache** pattern in the payment link creation endpoint. No middleware (overkill for one endpoint).

**Implementation outline:**

```python
# In the payment link endpoint, BEFORE the service call:
async def create_payment_link(...):
    idempotency_key = request.headers.get("X-Idempotency-Key")
    if idempotency_key:
        existing = await idempotency_repo.get_by_key(
            tenant_id=tenant_id, key=idempotency_key
        )
        if existing is not None:
            # Return cached response
            return JSONResponse(
                status_code=existing.response_status,
                content=existing.response_body,
            )

    # ... existing service call ...

    # AFTER successful service call, store the response:
    await idempotency_repo.save(
        tenant_id=tenant_id,
        key=idempotency_key,
        response_status=201,
        response_body=response.model_dump(),
    )
    return response
```

**Schema:** Need an idempotency table. Check if it exists via the migration history; if not, add via `alembic/versions/20260812_0008_idempotency_keys.py`.

**Tests:**
- `tests/api/test_payment_link_endpoint.py` — already has tests for header-required; add:
  - Two requests with same `X-Idempotency-Key` return the same response (no duplicate invoice)
  - Two requests with different `X-Idempotency-Key` produce independent operations
  - Cached response is returned even if the underlying payment service state changed

**Why not middleware:**
- Middleware is the right pattern when idempotency applies to many endpoints
- Currently only the payment link endpoint is in scope
- Inline keeps the blast radius small and the change reviewable

**Out of scope:**
- Refactoring every endpoint to use idempotency
- Generic middleware framework
- TTL / expiry on idempotency keys (let it be unbounded for now; matches the spec)
- Multi-tenant isolation hardening (already enforced by the unique index)

---

## F-25 — Availability rule validation

### The bug

`BookingService.create_booking()` (in `apps/backend/src/booking/application/booking_service.py:87-120`) does NOT validate against availability rules. The method:

1. Computes price
2. Creates a Booking domain object
3. Calls `bookings.add_safe()` (which only checks for overlapping bookings)

A customer can book a resource at any time, regardless of the resource's availability rules (e.g., Mon-Fri 9am-5pm). Bookings outside hours succeed.

### Design

**Step 1: Add `get_applicable_rules(resource_id, start_at, end_at)` to `AvailabilityRuleRepository`** (in `apps/backend/src/facility/infrastructure/repositories.py`).

```python
async def get_applicable_rules(
    self,
    *,
    tenant_id: UUID,
    resource_id: UUID,
    start_at: datetime,
    end_at: datetime,
) -> list[AvailabilityRule]:
    """Return availability rules whose time window overlaps [start_at, end_at)."""
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

**Step 2: Validate in `BookingService.create_booking()`** (after resource lock, before `add_safe()`).

```python
# After loading the resource, before creating the booking:
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
# Reject if any rule has status == "maintenance" or "closed"
invalid = [r for r in rules if r.status in ("maintenance", "closed")]
if invalid:
    raise ResourceUnavailableError(
        resource_id=resource_id,
        reasons=[r.status for r in invalid],
    )
```

**Step 3: Add `OutsideAvailabilityError` and `ResourceUnavailableError` to `booking/domain/errors.py`** (or extend existing exception hierarchy).

**Tests:**
- `tests/integration/test_booking_service.py` — add:
  - Booking within availability window → 201
  - Booking outside availability window → 422 with `OutsideAvailabilityError`
  - Booking during maintenance window → 422 with `ResourceUnavailableError`
  - Booking with no applicable rules → 422 (resource has no availability defined)

**Assumptions:**
- `AvailabilityRule` domain entity has `.status` field (`active`, `maintenance`, `closed`)
- `AvailabilityRuleModel` has `tenant_id`, `resource_id`, `start_at`, `end_at`, `status` columns
- Existing `availability_rule` table exists (verified by F-25 verification agent)

**Out of scope:**
- Recurring availability rules (e.g., "every Monday 9am-5pm") — current schema is one-off ranges
- Customer-facing availability UI (separate finding)
- Holiday/event overrides

---

## File structure

**Files modified:**

| Finding | File | Change |
|---|---|---|
| F-22 | `apps/backend/src/payments/infrastructure/repositories.py` | Add `pg_advisory_xact_lock` |
| F-22 | `apps/backend/tests/integration/test_payments_repositories.py` | Add concurrent test |
| F-24 | `apps/backend/src/payments/interfaces/http/router.py` | Add idempotency check + cache |
| F-24 | `apps/backend/src/payments/application/payment_service.py` (or deps.py) | Wire `IdempotencyKeyRepository` |
| F-24 | `apps/backend/alembic/versions/20260812_0008_idempotency_keys.py` | New migration (if table missing) |
| F-24 | `apps/backend/tests/api/test_payment_link_endpoint.py` | Add dedup tests |
| F-25 | `apps/backend/src/facility/infrastructure/repositories.py` | Add `get_applicable_rules` |
| F-25 | `apps/backend/src/booking/application/booking_service.py` | Add validation call |
| F-25 | `apps/backend/src/booking/domain/errors.py` | Add new exception types |
| F-25 | `apps/backend/tests/integration/test_booking_service.py` | Add availability tests |

**Files NOT modified:**
- No changes to `docs/CODEBASE_REVIEW.md` or `docs/FINDINGS_ROADMAP.md` — these are code fixes, not audit-doc updates
- No changes to `CHANGELOG.md` for code work (the spec already records the deferred state)
- No changes to the frontend (PWA), API client, or admin pages

---

## Approach

### Why three independent fixes

These three are fully orthogonal:
- F-22: payments infrastructure (row-level)
- F-24: payments HTTP (request-level)
- F-25: booking + facility (cross-context)

No shared files. No shared tests. No dependency between them. Implementing them in parallel is safe.

### Why not one combined PR

Per the user's pattern (Sub-projects A, B, C1), each finding has its own spec + plan + PR. Consistent with established process. The combined spec is the only deviation (lighter admin than three separate specs).

---

## Execution plan

After spec approval:
1. **Three implementation plans** — one per finding (each small, 1-2 tasks)
2. **Parallel execution** — three SDD workspaces, three subagent streams, parallel implementation
3. **Each plan** produces 1-2 commits (fix + tests; possibly migration)

The brainstorming skill's parallel-agent pattern is used here not for "parallel review" but for "parallel independent work" — each fix is independent and has its own implementer.

---

## Verification

- [ ] F-22: 10 concurrent `next_invoice_number` calls produce 10 unique consecutive numbers
- [ ] F-22: Existing single-tenant invoice test still passes
- [ ] F-24: Two requests with same `X-Idempotency-Key` return identical response
- [ ] F-24: Two requests with different keys produce distinct operations
- [ ] F-24: F-24 test header-required test still passes
- [ ] F-25: Booking within window → 201
- [ ] F-25: Booking outside window → 422
- [ ] F-25: Booking during maintenance → 422
- [ ] All backend tests still pass (no regression)

---

## Out of scope

- F-26 (membership enforcement) — blocked by F-17 (membership module doesn't exist)
- F-11 (Redis Streams) — architectural, deferred
- F-14 (backup scripts) — ops, deferred
- Recurring availability rules (F-25)
- Generic idempotency middleware (F-24)
- Any frontend changes

---

## Risk

**Low.** Each fix is a small, contained change:
- F-22: 1 method, 1 line of code added (`pg_advisory_xact_lock`); the rest is identical
- F-24: ~15 lines in router + 1 migration
- F-25: ~30 lines (new repo method + validation + new errors)

Each has a clear test surface. None touches multi-tenant isolation or auth.
