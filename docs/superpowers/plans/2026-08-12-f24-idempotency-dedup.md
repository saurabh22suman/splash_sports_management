# F-24 Idempotency-Key Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `X-Idempotency-Key` actually deduplicate: two requests with the same key return the same response, two requests with different keys produce independent operations.

**Architecture:** Inline pre-check + post-cache in the payment link creation endpoint. The `IdempotencyKeyRepository` (already injected but unused) is wired to query before processing and to cache the response after success. No middleware — overkill for one endpoint.

**Tech Stack:** FastAPI, SQLAlchemy 2 (async), PostgreSQL 16, Alembic, pytest.

## Global Constraints

- The `X-Idempotency-Key` header is **already required** (returns 422 if missing). Do not change that.
- The `IdempotencyKeyRepository` is already injected into `PaymentService` at `payments/interfaces/http/deps.py:93-97` but never used.
- The cache write happens AFTER successful payment service call; on failure, no cache entry is written.
- The cached response is `(status_code, response_body)`; replays return the same body.
- The cache lookup is `(tenant_id, idempotency_key)` — both required for tenant isolation.
- No expiry/TTL on cache entries (matches the documented spec; can be added later).
- Only the payment link creation endpoint is in scope. No generic middleware.

**Pre-flight verification (run before starting Task 1):**
- Run `find apps/backend/alembic/versions -name "*idempot*" 2>&1 | head -5` to check if the idempotency table already exists.
- Run `grep -rn "idempotency_keys\|IdempotencyKey" apps/backend/src/common/ apps/backend/alembic/ 2>&1 | head -10` to find existing model/repo.
- Run `cat apps/backend/src/payments/interfaces/http/router.py | head -200` to find the payment link endpoint.
- Run `cat apps/backend/src/payments/interfaces/http/deps.py | head -120` to confirm the `IdempotencyKeyRepository` injection.

---

## File Structure

| File | Type | Responsibility |
|---|---|---|
| `apps/backend/alembic/versions/20260812_0008_idempotency_keys.py` | Create (if missing) | Alembic migration creating `idempotency_keys` table |
| `apps/backend/src/payments/interfaces/http/router.py` | Modify | Add idempotency pre-check + post-cache in payment link endpoint |
| `apps/backend/src/payments/application/payment_service.py` | Modify (if needed) | Wire idempotency cache write through the service |
| `apps/backend/tests/api/test_payment_link_endpoint.py` | Modify | Add idempotency dedup tests |

---

### Task 1: Add idempotency cache lookup + test

**Files:**
- Modify: `apps/backend/src/payments/interfaces/http/router.py` (pre-check before service call)
- Modify: `apps/backend/tests/api/test_payment_link_endpoint.py` (add dedup test)

**Interfaces:**
- Consumes: `X-Idempotency-Key` header (already extracted by existing dependency)
- Consumes: `IdempotencyKeyRepository` (needs to be injected into the endpoint as a dependency)
- Produces: same response on duplicate key, fresh response on new key

- [ ] **Step 1: Locate the payment link endpoint and the existing dependency**

```bash
grep -n "payment_link\|create_payment_link\|X-Idempotency-Key" apps/backend/src/payments/interfaces/http/router.py
grep -n "required_idempotency_key\|idempotency" apps/backend/src/payments/interfaces/http/deps.py
```

Expected: the endpoint and the dependency are found. Record the line numbers.

- [ ] **Step 2: Write the failing test**

Add this test to `apps/backend/tests/api/test_payment_link_endpoint.py` (or create the file if it doesn't exist). The test fires two requests with the same `X-Idempotency-Key` and asserts the second returns the same response.

```python
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_payment_link_endpoint_dedupes_on_idempotency_key(
    client: AsyncClient,
    auth_headers: dict,
    sample_invoice_data: dict,
):
    """F-24: two requests with the same X-Idempotency-Key return the same response.

    The first request hits the payment service. The second request
    (same key) must return the cached response WITHOUT calling the
    payment service again.
    """
    headers = {
        **auth_headers,
        "X-Idempotency-Key": "test-dedup-key-12345",
    }

    # First request: should call the service
    with patch(
        "payments.application.payment_service.PaymentService.create_payment_link",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = {"id": "inv_abc", "amount": 1000, "status": "created"}
        resp1 = await client.post(
            "/api/v1/payments/payment-link",
            json=sample_invoice_data,
            headers=headers,
        )
    assert resp1.status_code == 201
    assert mock_create.call_count == 1

    # Second request with same key: must NOT call the service
    with patch(
        "payments.application.payment_service.PaymentService.create_payment_link",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = {"id": "inv_xyz", "amount": 9999, "status": "DIFFERENT"}
        resp2 = await client.post(
            "/api/v1/payments/payment-link",
            json=sample_invoice_data,
            headers=headers,
        )
    assert resp2.status_code == 201
    # Same response body as the first request (cached)
    assert resp2.json() == resp1.json()
    # Service NOT called the second time
    assert mock_create.call_count == 0
```

**Note:** Adjust the test fixture names (`auth_headers`, `sample_invoice_data`) to match the existing test file's conventions. Read 30 lines of the existing test file to match the patterns.

- [ ] **Step 3: Run the test to verify it fails**

Run:
```bash
cd apps/backend && PYTHONPATH=src pytest tests/api/test_payment_link_endpoint.py::test_payment_link_endpoint_dedupes_on_idempotency_key -v --tb=short 2>&1 | tail -30
```

Expected: FAIL — second response does not match the first (likely 201 with a different mock return value, or the second call hits the service).

- [ ] **Step 4: Wire the IdempotencyKeyRepository into the payment link endpoint**

In `apps/backend/src/payments/interfaces/http/router.py`, modify the payment link endpoint to:

1. Take `IdempotencyKeyRepository` as a dependency (via `Depends`)
2. Read the `X-Idempotency-Key` header (already extracted by `required_idempotency_key`)
3. Before the service call: query the repo for an existing entry; if found, return cached response
4. After the service call: save the response in the repo

Concrete edits (replace the existing payment link endpoint's body):

```python
from fastapi import Depends
from fastapi.responses import JSONResponse

from payments.infrastructure.repositories import IdempotencyKeyRepository


@router.post("/payment-link", status_code=201)
async def create_payment_link(
    body: PaymentLinkCreate,
    request: Request,
    user: User = Depends(get_current_user),
    idempotency_key: str = Depends(required_idempotency_key),
    idem_repo: IdempotencyKeyRepository = Depends(get_idempotency_key_repository),
):
    # F-24: pre-check — return cached response on duplicate key
    cached = await idem_repo.get_by_key(
        tenant_id=user.tenant_id, key=idempotency_key
    )
    if cached is not None:
        return JSONResponse(
            status_code=cached.response_status,
            content=cached.response_body,
        )

    # Fresh request: process and cache the response
    response = await payments.create_payment_link(
        tenant_id=user.tenant_id,
        customer_id=user.id,
        body=body,
    )
    response_body = response.model_dump() if hasattr(response, "model_dump") else response

    await idem_repo.save(
        tenant_id=user.tenant_id,
        key=idempotency_key,
        response_status=201,
        response_body=response_body,
    )
    return response
```

**Note:** Adjust the existing variable names (`payments`, `user`, `body`) to match the codebase's conventions. Read the existing endpoint body first to align.

- [ ] **Step 5: Add the `get_idempotency_key_repository` dependency**

In `apps/backend/src/payments/interfaces/http/deps.py`, add a new dependency that yields an `IdempotencyKeyRepository`:

```python
async def get_idempotency_key_repository(
    session: AsyncSession = Depends(get_session),
) -> IdempotencyKeyRepository:
    return IdempotencyKeyRepository(session)
```

If a similar dependency already exists, align with its naming and pattern.

- [ ] **Step 6: Verify the IdempotencyKey table exists or add a migration**

Run:
```bash
find apps/backend/alembic/versions -name "*idempot*"
```

If no migration exists, create `apps/backend/alembic/versions/20260812_0008_idempotency_keys.py`:

```python
"""create idempotency_keys table

Revision ID: 20260812_0008
Revises: <previous-revision-id>
Create Date: 2026-08-12 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260812_0008"
down_revision = "<previous-revision-id>"  # fill from the latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "key"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_idempotency_keys_tenant_key"),
    )
    op.create_index(
        "ix_idempotency_keys_tenant_key",
        "idempotency_keys",
        ["tenant_id", "key"],
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_tenant_key", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
```

Replace `<previous-revision-id>` with the actual `down_revision` from the latest migration in `apps/backend/alembic/versions/`.

- [ ] **Step 7: Run the test to verify it passes**

Run:
```bash
cd apps/backend && PYTHONPATH=src pytest tests/api/test_payment_link_endpoint.py::test_payment_link_endpoint_dedupes_on_idempotency_key -v --tb=short 2>&1 | tail -15
```

Expected: PASS — second request returns the cached response, mock not called.

- [ ] **Step 8: Run the existing payment tests to confirm no regression**

Run:
```bash
cd apps/backend && PYTHONPATH=src pytest tests/api/test_payment_link_endpoint.py tests/payments/ -q --tb=short 2>&1 | tail -10
```

Expected: all existing tests pass.

- [ ] **Step 9: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/alembic/versions/20260812_0008_idempotency_keys.py \
    apps/backend/src/payments/interfaces/http/router.py \
    apps/backend/src/payments/interfaces/http/deps.py \
    apps/backend/tests/api/test_payment_link_endpoint.py
git commit -m "fix(payments): dedupe payment link endpoint via X-Idempotency-Key cache (F-24)"
```

---

## Verification (after all tasks land)

- [ ] F-24: Two requests with same `X-Idempotency-Key` return identical response
- [ ] F-24: Two requests with different keys produce independent operations
- [ ] F-24: Existing header-required test still passes
- [ ] F-24: All existing payment tests still pass
- [ ] F-24: Migration applies cleanly (if added)

## Out of scope for this plan

- Generic idempotency middleware (overkill for one endpoint)
- TTL / expiry on idempotency keys
- Applying idempotency to other endpoints
- Multi-tenant isolation hardening beyond the unique index
- F-22 (invoice race), F-25 (availability rules) — separate plans
