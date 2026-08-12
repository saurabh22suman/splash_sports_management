# F-22 Invoice Number Race Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the read-then-write race in `next_invoice_number` so concurrent invoice creation for the same tenant produces unique numbers instead of triggering the UNIQUE constraint 500.

**Architecture:** Add a PostgreSQL transaction-scoped advisory lock keyed by `tenant_id` at the start of `next_invoice_number`. The existing read-increment logic stays; the lock serializes concurrent calls per tenant without schema changes.

**Tech Stack:** FastAPI, SQLAlchemy 2 (async), PostgreSQL 16 advisory locks (`pg_advisory_xact_lock`), pytest.

## Global Constraints

- The fix is in `apps/backend/src/payments/infrastructure/repositories.py:next_invoice_number`. No other file is modified.
- Lock key: derived from the first 8 bytes of `tenant_id.bytes` interpreted as a big-endian unsigned int. Standard pattern.
- Lock is auto-released on transaction commit/rollback (no manual unlock).
- The existing UNIQUE constraint on `(tenant_id, invoice_number)` stays as defense-in-depth.
- Existing `next_invoice_number` signature unchanged: `async def next_invoice_number(self, tenant_id: UUID) -> str`
- The concurrency test must use `asyncio.gather` to surface the race deterministically.
- No migrations. No schema changes.

**Pre-flight verification (run before starting Task 1):**
- Migration `0005_enable_rls_all_tables` is applied (RLS on the invoices table).
- The current `next_invoice_number` in `apps/backend/src/payments/infrastructure/repositories.py:124-136` matches the example in the spec.
- `tests/integration/test_payments_repositories.py` exists. If not, create it for this task.

---

## File Structure

| File | Type | Responsibility |
|---|---|---|
| `apps/backend/src/payments/infrastructure/repositories.py` | Modify | Add advisory lock; existing logic unchanged |
| `apps/backend/tests/integration/test_payments_repositories.py` | Create or Modify | Add concurrent `next_invoice_number` test |

---

### Task 1: Add concurrent test + advisory lock fix

**Files:**
- Modify: `apps/backend/src/payments/infrastructure/repositories.py:124-136` (add lock)
- Modify (or create): `apps/backend/tests/integration/test_payments_repositories.py` (add concurrent test)

**Interfaces:**
- Consumes: existing `next_invoice_number` signature
- Produces: a serialized, race-free `next_invoice_number`

- [ ] **Step 1: Locate the existing test file and verify the current implementation**

```bash
ls apps/backend/tests/integration/test_payments_repositories.py 2>&1
grep -n "next_invoice_number" apps/backend/src/payments/infrastructure/repositories.py
```

Expected: the file exists (or you create it); the function is at line ~124.

- [ ] **Step 2: Read the existing `next_invoice_number` to confirm the pre-condition**

```bash
sed -n '120,140p' apps/backend/src/payments/infrastructure/repositories.py
```

Expected: matches the spec's quoted code (read last invoice for tenant, increment, return `INV-{:06d}`).

- [ ] **Step 3: Add the failing concurrent test**

Add this test to `apps/backend/tests/integration/test_payments_repositories.py` (create the file if it doesn't exist). The test exercises `next_invoice_number` for the same tenant concurrently and asserts all numbers are unique.

```python
import asyncio
import pytest
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from common.infrastructure.db import AsyncSessionLocal
from payments.infrastructure.models import InvoiceModel, TenantModel
from payments.infrastructure.repositories import InvoiceRepository


@pytest.mark.asyncio
async def test_next_invoice_number_concurrent_calls_produce_unique_numbers():
    """F-22: 10 concurrent calls for the same tenant must produce 10 unique numbers.

    Without pg_advisory_xact_lock, two concurrent reads of the same
    last invoice can compute the same next number, and the UNIQUE
    constraint will reject the second persist with a 500.
    """
    tenant_id = uuid4()

    # Seed: one tenant and zero invoices
    async with AsyncSessionLocal() as session:
        session.add(TenantModel(id=tenant_id, name=f"t-{tenant_id}"))
        await session.commit()

        repo = InvoiceRepository(session)

        # 10 concurrent calls for the same tenant
        numbers = await asyncio.gather(
            *[repo.next_invoice_number(tenant_id) for _ in range(10)]
        )

    # All 10 numbers must be unique
    assert len(set(numbers)) == 10, f"duplicate numbers produced: {numbers}"

    # All must follow the INV-NNNNNN format
    for n in numbers:
        assert n.startswith("INV-")
        assert n[4:].isdigit()
```

- [ ] **Step 4: Run the test to verify it fails (no lock yet)**

Run:
```bash
cd apps/backend && PYTHONPATH=src pytest tests/integration/test_payments_repositories.py::test_next_invoice_number_concurrent_calls_produce_unique_numbers -v --tb=short 2>&1 | tail -30
```

Expected: FAIL — duplicates appear in the output (e.g., `duplicate numbers produced: ['INV-000001', 'INV-000001', ...]`).

If the test PASSES on the first run, the existing code may already have a lock. Stop and report to the controller — do not proceed.

- [ ] **Step 5: Add the advisory lock to `next_invoice_number`**

Modify `apps/backend/src/payments/infrastructure/repositories.py` at the top of the file (in the imports section) to add `text` to the SQLAlchemy import:

```python
from sqlalchemy import text  # add to existing sqlalchemy imports
```

Then modify the `next_invoice_number` method (around line 124) to add the advisory lock at the start:

```python
async def next_invoice_number(self, tenant_id: UUID) -> str:
    # F-22: serialize concurrent calls per tenant via a transaction-scoped
    # advisory lock. Lock auto-released on commit/rollback.
    lock_key = int.from_bytes(tenant_id.bytes[:8], "big", signed=False)
    await self._s.execute(
        text("SELECT pg_advisory_xact_lock(:key)").bindparams(key=lock_key)
    )
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

- [ ] **Step 6: Run the test to verify it passes**

Run:
```bash
cd apps/backend && PYTHONPATH=src pytest tests/integration/test_payments_repositories.py::test_next_invoice_number_concurrent_calls_produce_unique_numbers -v --tb=short 2>&1 | tail -15
```

Expected: PASS — 10 unique numbers produced.

- [ ] **Step 7: Run the existing invoice tests to confirm no regression**

Run:
```bash
cd apps/backend && PYTHONPATH=src pytest tests/integration/test_payments_repositories.py tests/payments/ -q --tb=short 2>&1 | tail -10
```

Expected: all existing tests pass.

- [ ] **Step 8: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/src/payments/infrastructure/repositories.py apps/backend/tests/integration/test_payments_repositories.py
git commit -m "fix(payments): serialize next_invoice_number per tenant via pg_advisory_xact_lock (F-22)"
```

---

## Verification (after all tasks land)

- [ ] F-22: 10 concurrent `next_invoice_number` calls for the same tenant produce 10 unique consecutive numbers
- [ ] F-22: Existing payment tests still pass (no regression)
- [ ] F-22: The advisory lock is auto-released on transaction end (no leak)
- [ ] F-22: Different tenants do NOT block each other (verified by inspecting pg_locks during the test if needed)

## Out of scope for this plan

- Replacing the `INV-` prefix scheme (e.g., ULIDs)
- Migration to a DB-generated sequence
- Multi-tenant serialization at a higher layer (e.g., in the service)
- F-24 (idempotency), F-25 (availability rules) — separate plans
