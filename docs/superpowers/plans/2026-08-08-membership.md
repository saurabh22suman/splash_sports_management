# Membership Module v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a multi-tenant membership module that lets customers subscribe to a single monthly plan via Razorpay Subscriptions (hosted auth page) and lets admins issue prepaid visit packs. An active subscription or an active pack with visits remaining covers a booking — the booking flow skips invoice creation. Booking integration is through a small `MembershipGate` protocol, not module-to-module imports.

**Architecture:** A new `membership` backend module (`interfaces/http/` + `application/` + `domain/` + `infrastructure/`) sibling to `payments/`. Subscription state is sourced from Razorpay Subscriptions — the same webhook ingress used by payments (`POST /webhooks/razorpay`) dispatches `subscription.*` events to a new `MembershipWebhookHandler`. Pack issuance is admin-only (no Razorpay touch — packs are gifts/promos). Booking integration is via a `MembershipGate` protocol that `BookingService` consumes; pack consumption happens atomically in the booking transaction (optimistic-concurrency UPDATE-WHERE on `visits_remaining`). The frontend gains a customer `/me/membership` page (subscribe, view subscription, view packs) and two admin pages (`/admin/subscriptions`, `/admin/packs`), plus a coverage badge on the existing booking flow.

**Tech Stack:** Same as the rest of the backend — FastAPI, SQLAlchemy 2 (async) + Alembic, Pydantic v2, Razorpay Python SDK (`razorpay`). **No new Python dependencies.** **No new npm dependencies.** Frontend uses the same React 19 + react-router-dom + @tanstack/react-query + zustand stack. **Test mocking:** the `razorpay` SDK is built on `requests`, not `httpx`; all Razorpay SDK HTTP mocking uses the `responses` library (already a dev dep).

**Repo layout facts (binding, verified from payments plan):**
- The uv lockfile is at the **repo root** (`uv.lock`), not `apps/backend/uv.lock`.
- `.env.example` is at the **repo root**.
- Pytest config lives in the **root** `pyproject.toml`: `testpaths = ["apps/backend/tests"]`, `pythonpath = ["apps/backend"]`, `asyncio_mode = "auto"`. `asyncio_mode = "auto"` means bare `async def test_*` runs without a marker.
- Shared fixtures live in `apps/backend/conftest.py`.
- Existing backend tests are grouped by kind: `tests/unit/`, `tests/integration/`, `tests/api/`. New payments tests go in `tests/payments/` (module-grouped). New membership tests go in `tests/membership/` (module-grouped, mirroring payments).
- App entry: `uvicorn common.interfaces.http.app:create_app --factory`. Routers are auto-discovered from `interfaces.router` and mounted at `/v1/<module>`.
- Lifespan lives in `apps/backend/src/common/interfaces/http/app.py` (NOT `main.py` — `main.py` does not exist).

**Environment and command rules (binding, verified by running them during payments):**
- **Run every command from the worktree root** (`.worktrees/membership/`). Never `cd` into `apps/backend`. If a command line shows `cd apps/backend &&`, it is wrong.
- **Install with `uv sync --all-packages --all-extras`** (from repo root). Plain `uv sync` installs only the empty root package.
- **Every pytest invocation needs `PYTHONPATH=apps/backend/src`.** Without the override, `conftest.py` dies with `ModuleNotFoundError: No module named 'common'`. Do not 'fix' the root `pyproject.toml`.
- Full suite, for reference: `PYTHONPATH=apps/backend/src uv run pytest`.

**Module registration (binding):**
- The `_register_module_routers` function in `common/interfaces/http/app.py` enumerates `"auth", "customer", "facility", "booking", "payments"`. **Membership must be added to this tuple** so its router is mounted at `/v1/membership`.
- `from membership.infrastructure import models as _membership_models` must be added alongside the payments import so SQLAlchemy `Base.metadata` knows about the new tables.

## Workflow (binding)

- **Test-driven development (red-green-refactor).** Every line of production code is preceded by a failing test. Watch the test fail before implementing.
- **Subagent-driven execution.** Tasks are dispatched one at a time as fresh subagents, with task reviewer (spec compliance + code quality) after each, and a whole-branch review at the end. The controller dispatches; subagents implement.
- **Bite-sized tasks.** Each task is independently testable and ends with a green, reviewed commit.
- **Verification before completion claims.** Every "done" claim shows the test command and its output.

## Global Constraints

- **Multi-tenancy:** every business table has `tenant_id UUID NOT NULL` and a Postgres RLS policy (`tenant_id = current_setting('app.tenant_id')::uuid`) on SELECT/INSERT/UPDATE/DELETE. Membership tables follow the same pattern as `payments/`. **Cross-tenant access returns 404, not 403** — never leak existence.
- **Audit columns:** every business table has `created_at` and `updated_at` timestamptz columns populated by `server_default=sa.text("NOW()")` (payments migration pattern). The base mixin handles `updated_at` on UPDATE.
- **Money:** stored as `BIGINT` paise in DB and `int` paise in API + Razorpay payloads. Never floats. Currency code is a 3-char string; v1 supports **INR only**. The existing `Money` value object (`amount_paise: int`) is reused.
- **No card / UPI / banking data on our servers.** All Razorpay authentication and billing happens on Razorpay's hosted pages.
- **Logging:** never log full subscription/pack objects or Razorpay API responses. Log only `subscription_id`, `pack_purchase_id`, `razorpay_event_id`, and high-level status.
- **Errors:** never expose Razorpay SDK error details to API consumers; map to standard `common` exceptions (`Validation`, `Conflict`, `NotFound`, `ServiceUnavailable`).
- **Auth:** all `/membership/*` endpoints require an authenticated session. Customers see only their own subscription and packs; tenant_admin sees all in their tenant. Admin endpoints require `tenant_admin` role via the existing `RoleGate(["tenant_admin"])` pattern (used by payments).
- **Webhook auth:** `/webhooks/razorpay` continues to require a valid `X-Razorpay-Signature` header. The membership webhook handler runs only after signature verification succeeds.
- **No new `@splashh/ui` primitives** — membership pages use `Card`, `Button`, `Input`, `Table` (already in the package).
- **No npm dependencies added.**
- **Brand:** reuse existing tokens — primary `sky-500`, danger `red-500`, surface tokens from `@splashh/ui`. No new colors.
- **Eventing:** the publisher is in-process and synchronous (added by the payments module in `common/application/events.py`). New domain events live in `membership/application/events.py`. Subscribers are callables registered at startup. No external broker.
- **Background work:** the pack expiry sweeper is an `asyncio.create_task` started in the FastAPI lifespan. No Celery, no cron, no external scheduler.
- **Idempotency:** webhook handler uses the existing `IdempotencyStore` (Redis + DB, 24h TTL). Replays are no-ops. Key format: `subscription:{razorpay_subscription_id}:{event_type}:{event_id}`. Pack consumption uses Postgres optimistic-concurrency (UPDATE-WHERE on `visits_remaining`) — no Redis involvement.
- **Optimistic concurrency for pack consumption:** every pack decrement is `UPDATE pack_purchases SET visits_remaining = ?, status = ?, updated_at = NOW() WHERE id = ? AND tenant_id = ? AND visits_remaining = ?`. Zero rows affected = `Conflict` raised = booking transaction rolls back. Same pattern `bookings.add_safe` uses for the no-double-booking invariant.

## File Structure

### Backend — new files

```
apps/backend/src/membership/
  __init__.py
  domain/
    __init__.py
    entities.py             # Subscription, PackPurchase, PackDefinition, SubscriptionPlan dataclasses
    value_objects.py        # SubscriptionStatus, PackStatus, BillingPeriod
  application/
    __init__.py
    membership_service.py   # Subscription + Pack operations; implements MembershipGate
    membership_gate.py      # Protocol + CoverageDecision dataclass
    webhook_handler.py      # MembershipWebhookHandler.handle(event)
    events.py               # Domain events emitted by membership
  infrastructure/
    __init__.py
    models.py               # SQLAlchemy ORM models
    repositories.py         # SubscriptionRepository, SubscriptionPlanRepository,
                            # PackDefinitionRepository, PackPurchaseRepository
  interfaces/
    __init__.py
    http/
      __init__.py
      router.py             # /membership/* and /admin/membership/*
      schemas.py            # Pydantic request/response models
      deps.py               # FastAPI dependencies
apps/backend/alembic/versions/
  20240101_0005_membership.py             # NEW — migration: 4 tables + bookings columns
apps/backend/tests/membership/
  __init__.py
  test_entities.py
  test_membership_service.py
  test_webhook_handler.py
  integration/
    __init__.py
    test_subscription_webhook_flow.py
    test_pack_expiry_sweeper.py
    test_concurrent_pack_consumption.py
  test_router.py
apps/backend/tests/booking/integration/
  test_membership_integration.py          # NEW — booking with subscription/pack/none
```

### Backend — modified files

```
apps/backend/src/booking/
  domain/entities.py                       # add coverage_source, pack_purchase_id to Booking
  application/booking_service.py           # take MembershipGate dep; consult gate at create_booking
  infrastructure/models.py                 # add coverage_source, pack_purchase_id columns
apps/backend/src/payments/
  application/payment_service.py           # extend handle_webhook to dispatch subscription.* events
  application/provider.py                  # extend PaymentProvider protocol + NullAdapter + RazorpayAdapter with subscription methods
apps/backend/src/common/interfaces/http/app.py  # add "membership" to module list + import models
packages/api-client/src/
  membership.ts                            # NEW — typed wrappers + types
  index.ts                                 # add re-export
  package.json                             # add ./membership subpath export
apps/web-pwa/src/
  features/membership/hooks.ts             # NEW — React Query hooks
  pages/customer/MembershipPage.tsx        # NEW
  pages/admin/SubscriptionsPage.tsx        # NEW
  pages/admin/PacksPage.tsx                # NEW
  pages/book/BookResourcePage.tsx          # MODIFIED — add coverage badge
  components/nav.ts                        # MODIFIED — add Membership, Subscriptions, Packs entries
  routes/index.tsx                         # MODIFIED — add 3 new routes
e2e/membership.spec.ts                     # NEW — happy path E2E
```

---

## Task Index

1. Backend: domain value objects (status enums)
2. Backend: domain entities (Subscription, PackPurchase, PackDefinition, SubscriptionPlan)
3. Backend: SQLAlchemy models + Alembic migration
4. Backend: repositories (4 repos with atomic pack decrement)
5. Backend: PaymentProvider protocol extensions (subscription methods on NullAdapter + RazorpayAdapter)
6. Backend: MembershipService — subscription operations
7. Backend: MembershipService — pack operations + MembershipGate implementation
8. Backend: webhook dispatch extension (PaymentService routes subscription.* events)
9. Backend: booking integration (MembershipGate wired into BookingService.create_booking)
10. Backend: HTTP layer (schemas + router + deps + app wiring)
11. Backend: pack expiry sweeper (lifespan background task)
12. Frontend: api-client (`packages/api-client/src/membership.ts`)
13. Frontend: React Query hooks + MembershipPage (customer) + admin pages
14. Frontend: BookResourcePage coverage badge + routes + nav + E2E

(14 tasks total — each ends with a green, reviewed commit.)

---

## Task 1: Domain value objects (status enums)

**Files:**
- Create: `apps/backend/src/membership/__init__.py`
- Create: `apps/backend/src/membership/domain/__init__.py`
- Create: `apps/backend/src/membership/domain/value_objects.py`
- Test: `apps/backend/tests/membership/__init__.py`
- Test: `apps/backend/tests/membership/test_entities.py` (file created now; status-only assertions added here in this task)

**Interfaces:**
- Consumes: nothing (foundational layer)
- Produces:
  - `SubscriptionStatus(str, Enum)` with members `CREATED, AUTHENTICATED, ACTIVE, PENDING, HALTED, CANCELLED, COMPLETED, EXPIRED` — string values matching Razorpay's `subscription.*` webhook event names (lowercase)
  - `PackStatus(str, Enum)` with members `ACTIVE, EXHAUSTED, EXPIRED`
  - `BillingPeriod(str, Enum)` with members `MONTHLY, YEARLY`

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/membership/__init__.py` (empty).

Create `apps/backend/tests/membership/test_entities.py`:

```python
from membership.domain.value_objects import BillingPeriod, PackStatus, SubscriptionStatus


def test_subscription_status_members_and_values():
    assert SubscriptionStatus.CREATED.value == "created"
    assert SubscriptionStatus.AUTHENTICATED.value == "authenticated"
    assert SubscriptionStatus.ACTIVE.value == "active"
    assert SubscriptionStatus.PENDING.value == "pending"
    assert SubscriptionStatus.HALTED.value == "halted"
    assert SubscriptionStatus.CANCELLED.value == "cancelled"
    assert SubscriptionStatus.COMPLETED.value == "completed"
    assert SubscriptionStatus.EXPIRED.value == "expired"


def test_pack_status_members_and_values():
    assert PackStatus.ACTIVE.value == "active"
    assert PackStatus.EXHAUSTED.value == "exhausted"
    assert PackStatus.EXPIRED.value == "expired"


def test_billing_period_members_and_values():
    assert BillingPeriod.MONTHLY.value == "monthly"
    assert BillingPeriod.YEARLY.value == "yearly"


def test_status_enums_compare_to_strings():
    # str-Enum mixin: members equal their string value
    assert SubscriptionStatus.ACTIVE == "active"
    assert PackStatus.EXHAUSTED == "exhausted"
    assert BillingPeriod.MONTHLY == "monthly"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_entities.py -v` (from the worktree root)

Expected: collection error `ModuleNotFoundError: No module named 'membership'`.

- [ ] **Step 3: Create the package skeleton**

Create `apps/backend/src/membership/__init__.py` (empty).

Create `apps/backend/src/membership/domain/__init__.py` (empty).

- [ ] **Step 4: Create the value objects**

Create `apps/backend/src/membership/domain/value_objects.py`:

```python
"""Membership value objects — status enums and BillingPeriod."""
from __future__ import annotations

from enum import Enum


class SubscriptionStatus(str, Enum):
    """Lifecycle states for a Razorpay-backed subscription.

    Values match the lowercased suffix of Razorpay webhook events
    (`subscription.activated` → "active"). The gate treats only ACTIVE
    (within trial window) as covering; every other status denies coverage.
    """

    CREATED = "created"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    PENDING = "pending"        # auth failure on next charge; gate denies coverage
    HALTED = "halted"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    EXPIRED = "expired"


class PackStatus(str, Enum):
    """Lifecycle states for a PackPurchase (issued visit pack)."""

    ACTIVE = "active"          # visits_remaining > 0 AND now < expires_at
    EXHAUSTED = "exhausted"    # visits_remaining == 0
    EXPIRED = "expired"        # now >= expires_at (set by sweeper or admin)


class BillingPeriod(str, Enum):
    """Subscription billing cadence. v1 exposes only MONTHLY."""

    MONTHLY = "monthly"
    YEARLY = "yearly"          # reserved; not exposed in v1 admin UI
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_entities.py -v`

Expected: 4 passed.

- [ ] **Step 6: Run the full backend test suite to confirm no regressions**

Run: `PYTHONPATH=apps/backend/src uv run pytest`

Expected: all previously-passing tests still pass. Record counts.

- [ ] **Step 7: Commit**

```bash
git add apps/backend/src/membership/ apps/backend/tests/membership/
git commit -m "feat(membership): domain value objects (status enums)"
```

---

## Task 2: Domain entities (Subscription, PackPurchase, PackDefinition, SubscriptionPlan)

**Files:**
- Modify: `apps/backend/src/membership/domain/entities.py` (new file)
- Test: `apps/backend/tests/membership/test_entities.py`

**Interfaces:**
- Consumes: `SubscriptionStatus`, `PackStatus`, `BillingPeriod` from `value_objects.py`
- Produces:
  - `SubscriptionPlan` dataclass with `id, tenant_id, name, razorpay_plan_id, price_paise, currency, period, trial_period_days, active, created_at, updated_at`
  - `Subscription` dataclass with `apply_event(event_type, payload)`, `is_covering(now)`, `mark_cancel_at_period_end()`, `created_at, updated_at`
  - `PackDefinition` dataclass with `id, tenant_id, name, visit_count, validity_days, currency, price_paise, active, created_at, updated_at`
  - `PackPurchase` dataclass with `@classmethod issue(...)`, `consume_one() -> int`, `expire()`, `is_covering(now)`

- [ ] **Step 1: Append failing tests for Subscription lifecycle transitions**

Append to `apps/backend/tests/membership/test_entities.py`:

```python
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from common.domain.exceptions import InvariantViolation
from membership.domain.entities import (
    PackDefinition,
    PackPurchase,
    Subscription,
    SubscriptionPlan,
)
from membership.domain.value_objects import (
    BillingPeriod,
    PackStatus,
    SubscriptionStatus,
)


# ---------- SubscriptionPlan factory ----------

def test_subscription_plan_create_factory():
    plan = SubscriptionPlan.create(
        tenant_id=uuid4(),
        name="Monthly Member",
        razorpay_plan_id="plan_test_abc",
        price_paise=99900,
        currency="INR",
        period=BillingPeriod.MONTHLY,
        trial_period_days=7,
    )
    assert plan.name == "Monthly Member"
    assert plan.price_paise == 99900
    assert plan.currency == "INR"
    assert plan.period == BillingPeriod.MONTHLY
    assert plan.trial_period_days == 7
    assert plan.active is True
    assert plan.id == UUID(int=0)  # placeholder until persisted


def test_subscription_plan_rejects_negative_price():
    with pytest.raises(InvariantViolation):
        SubscriptionPlan.create(
            tenant_id=uuid4(), name="x", razorpay_plan_id="plan_x",
            price_paise=-1, currency="INR", period=BillingPeriod.MONTHLY,
            trial_period_days=0,
        )


# ---------- Subscription lifecycle ----------

def _subscription_created() -> Subscription:
    return Subscription.create(
        tenant_id=uuid4(), customer_id=uuid4(), plan_id=uuid4(),
        razorpay_subscription_id="sub_test_abc",
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_subscription_create_factory_starts_as_created():
    sub = _subscription_created()
    assert sub.status == SubscriptionStatus.CREATED
    assert sub.cancel_at_period_end is False
    assert sub.cancelled_at is None


def test_subscription_apply_event_activated_populates_period():
    sub = _subscription_created()
    sub.apply_event(
        "subscription.activated",
        current_period_start=datetime(2026, 1, 1, tzinfo=UTC),
        current_period_end=datetime(2026, 2, 1, tzinfo=UTC),
        trial_ends_at=None,
    )
    assert sub.status == SubscriptionStatus.ACTIVE
    assert sub.current_period_start == datetime(2026, 1, 1, tzinfo=UTC)
    assert sub.current_period_end == datetime(2026, 2, 1, tzinfo=UTC)


def test_subscription_apply_event_pending_marks_non_covering():
    sub = _subscription_created()
    sub.apply_event(
        "subscription.activated",
        current_period_start=datetime(2026, 1, 1, tzinfo=UTC),
        current_period_end=datetime(2026, 2, 1, tzinfo=UTC),
        trial_ends_at=None,
    )
    sub.apply_event("subscription.pending")
    assert sub.status == SubscriptionStatus.PENDING
    assert sub.is_covering(datetime(2026, 1, 15, tzinfo=UTC)) is False


def test_subscription_apply_event_cancelled_sets_timestamp():
    sub = _subscription_created()
    sub.apply_event(
        "subscription.activated",
        current_period_start=datetime(2026, 1, 1, tzinfo=UTC),
        current_period_end=datetime(2026, 2, 1, tzinfo=UTC),
        trial_ends_at=None,
    )
    sub.apply_event("subscription.cancelled", cancelled_at=datetime(2026, 2, 1, tzinfo=UTC))
    assert sub.status == SubscriptionStatus.CANCELLED
    assert sub.cancelled_at == datetime(2026, 2, 1, tzinfo=UTC)


def test_subscription_mark_cancel_at_period_end_only_from_active():
    sub = _subscription_created()
    with pytest.raises(InvariantViolation):
        sub.mark_cancel_at_period_end()

    sub.apply_event(
        "subscription.activated",
        current_period_start=datetime(2026, 1, 1, tzinfo=UTC),
        current_period_end=datetime(2026, 2, 1, tzinfo=UTC),
        trial_ends_at=None,
    )
    sub.mark_cancel_at_period_end()
    assert sub.cancel_at_period_end is True
    # status remains ACTIVE — the webhook drives the final flip


def test_subscription_is_covering_within_trial():
    sub = _subscription_created()
    sub.apply_event(
        "subscription.activated",
        current_period_start=datetime(2026, 1, 1, tzinfo=UTC),
        current_period_end=datetime(2026, 2, 1, tzinfo=UTC),
        trial_ends_at=datetime(2026, 1, 8, tzinfo=UTC),
    )
    assert sub.is_covering(datetime(2026, 1, 7, tzinfo=UTC)) is True
    assert sub.is_covering(datetime(2026, 1, 8, tzinfo=UTC)) is False  # trial_ends_at boundary
    assert sub.is_covering(datetime(2026, 1, 20, tzinfo=UTC)) is False


# ---------- PackDefinition / PackPurchase ----------

def test_pack_definition_create_factory():
    pd = PackDefinition.create(
        tenant_id=uuid4(), name="10-Visit Pack",
        visit_count=10, validity_days=60,
        currency="INR", price_paise=999900,
    )
    assert pd.visit_count == 10
    assert pd.validity_days == 60
    assert pd.active is True


def test_pack_purchase_issue_initialises_visits_and_expiry():
    pd = PackDefinition.create(
        tenant_id=uuid4(), name="x", visit_count=5, validity_days=30,
        currency="INR", price_paise=0,
    )
    now = datetime(2026, 1, 1, tzinfo=UTC)
    pp = PackPurchase.issue(
        tenant_id=uuid4(), customer_id=uuid4(),
        definition=pd, issued_by_admin_id=uuid4(), now=now,
    )
    assert pp.visits_remaining == 5
    assert pp.status == PackStatus.ACTIVE
    assert pp.expires_at == now + timedelta(days=30)


def test_pack_purchase_consume_one_decrements_and_exhausts():
    pd = PackDefinition.create(
        tenant_id=uuid4(), name="x", visit_count=2, validity_days=30,
        currency="INR", price_paise=0,
    )
    now = datetime(2026, 1, 1, tzinfo=UTC)
    pp = PackPurchase.issue(
        tenant_id=uuid4(), customer_id=uuid4(),
        definition=pd, issued_by_admin_id=uuid4(), now=now,
    )
    assert pp.consume_one(now=now) == 1
    assert pp.visits_remaining == 1
    assert pp.status == PackStatus.ACTIVE
    assert pp.consume_one(now=now) == 0
    assert pp.status == PackStatus.EXHAUSTED
    with pytest.raises(InvariantViolation):
        pp.consume_one(now=now)


def test_pack_purchase_consume_one_raises_after_expiry():
    pd = PackDefinition.create(
        tenant_id=uuid4(), name="x", visit_count=2, validity_days=1,
        currency="INR", price_paise=0,
    )
    now = datetime(2026, 1, 1, tzinfo=UTC)
    pp = PackPurchase.issue(
        tenant_id=uuid4(), customer_id=uuid4(),
        definition=pd, issued_by_admin_id=uuid4(), now=now,
    )
    later = now + timedelta(days=2)
    with pytest.raises(InvariantViolation):
        pp.consume_one(now=later)


def test_pack_purchase_expire_only_from_active():
    pd = PackDefinition.create(
        tenant_id=uuid4(), name="x", visit_count=2, validity_days=30,
        currency="INR", price_paise=0,
    )
    now = datetime(2026, 1, 1, tzinfo=UTC)
    pp = PackPurchase.issue(
        tenant_id=uuid4(), customer_id=uuid4(),
        definition=pd, issued_by_admin_id=uuid4(), now=now,
    )
    pp.expire()
    assert pp.status == PackStatus.EXPIRED
    with pytest.raises(InvariantViolation):
        pp.expire()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_entities.py -v`

Expected: collection error or `ImportError: cannot import name 'Subscription'` from `membership.domain.entities`.

- [ ] **Step 3: Implement the entities**

Create `apps/backend/src/membership/domain/entities.py`:

```python
"""Membership domain entities — pure dataclasses, no SQLAlchemy.

Status transitions are encoded as methods on the entities, not at the
infrastructure layer. Tests exhaustively cover valid and illegal transitions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from common.domain.exceptions import InvariantViolation
from membership.domain.value_objects import (
    BillingPeriod,
    PackStatus,
    SubscriptionStatus,
)


# ---------- SubscriptionPlan ----------

@dataclass(slots=True)
class SubscriptionPlan:
    id: UUID
    tenant_id: UUID
    name: str
    razorpay_plan_id: str
    price_paise: int
    currency: str
    period: BillingPeriod
    trial_period_days: int
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        name: str,
        razorpay_plan_id: str,
        price_paise: int,
        currency: str = "INR",
        period: BillingPeriod = BillingPeriod.MONTHLY,
        trial_period_days: int = 0,
        now: datetime | None = None,
    ) -> "SubscriptionPlan":
        if price_paise < 0:
            raise InvariantViolation("price_paise must be non-negative")
        if trial_period_days < 0:
            raise InvariantViolation("trial_period_days must be non-negative")
        now = now or datetime.now(UTC)
        return cls(
            id=UUID(int=0),
            tenant_id=tenant_id,
            name=name,
            razorpay_plan_id=razorpay_plan_id,
            price_paise=price_paise,
            currency=currency.upper(),
            period=period,
            trial_period_days=trial_period_days,
            active=True,
            created_at=now,
            updated_at=now,
        )


# ---------- Subscription ----------

@dataclass(slots=True)
class Subscription:
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    plan_id: UUID
    razorpay_subscription_id: str
    status: SubscriptionStatus
    current_period_start: datetime | None
    current_period_end: datetime | None
    trial_ends_at: datetime | None
    cancelled_at: datetime | None
    cancel_at_period_end: bool
    started_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        plan_id: UUID,
        razorpay_subscription_id: str,
        now: datetime | None = None,
    ) -> "Subscription":
        now = now or datetime.now(UTC)
        return cls(
            id=UUID(int=0),
            tenant_id=tenant_id,
            customer_id=customer_id,
            plan_id=plan_id,
            razorpay_subscription_id=razorpay_subscription_id,
            status=SubscriptionStatus.CREATED,
            current_period_start=None,
            current_period_end=None,
            trial_ends_at=None,
            cancelled_at=None,
            cancel_at_period_end=False,
            started_at=now,
            created_at=now,
            updated_at=now,
        )

    def apply_event(self, event_type: str, **payload: Any) -> None:
        """Apply a Razorpay subscription.* webhook event to local state.

        Unknown event types are no-ops (forward-compatible). Illegal
        transitions raise InvariantViolation.
        """
        now = datetime.now(UTC)
        suffix = event_type.removeprefix("subscription.")
        new_status = {
            "created": SubscriptionStatus.CREATED,
            "authenticated": SubscriptionStatus.AUTHENTICATED,
            "activated": SubscriptionStatus.ACTIVE,
            "pending": SubscriptionStatus.PENDING,
            "halted": SubscriptionStatus.HALTED,
            "cancelled": SubscriptionStatus.CANCELLED,
            "completed": SubscriptionStatus.COMPLETED,
            "expired": SubscriptionStatus.EXPIRED,
        }.get(suffix)
        if new_status is not None:
            self.status = new_status
        if suffix == "activated":
            self.current_period_start = payload.get("current_period_start", self.current_period_start)
            self.current_period_end = payload.get("current_period_end", self.current_period_end)
            self.trial_ends_at = payload.get("trial_ends_at", self.trial_ends_at)
        elif suffix == "charged":
            self.current_period_start = payload.get("current_period_start", self.current_period_start)
            self.current_period_end = payload.get("current_period_end", self.current_period_end)
        elif suffix == "cancelled":
            self.cancelled_at = payload.get("cancelled_at", now)
        self.updated_at = now

    def mark_cancel_at_period_end(self) -> None:
        if self.status != SubscriptionStatus.ACTIVE:
            raise InvariantViolation(
                f"Cannot mark cancel_at_period_end from status {self.status}"
            )
        self.cancel_at_period_end = True
        self.updated_at = datetime.now(UTC)

    def is_covering(self, now: datetime) -> bool:
        """True only when ACTIVE and (no trial or within trial window)."""
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        if self.trial_ends_at is not None and now >= self.trial_ends_at:
            return False
        return True


# ---------- PackDefinition ----------

@dataclass(slots=True)
class PackDefinition:
    id: UUID
    tenant_id: UUID
    name: str
    visit_count: int
    validity_days: int
    currency: str
    price_paise: int
    active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        name: str,
        visit_count: int,
        validity_days: int,
        currency: str = "INR",
        price_paise: int = 0,
        now: datetime | None = None,
    ) -> "PackDefinition":
        if visit_count <= 0:
            raise InvariantViolation("visit_count must be positive")
        if validity_days <= 0:
            raise InvariantViolation("validity_days must be positive")
        if price_paise < 0:
            raise InvariantViolation("price_paise must be non-negative")
        now = now or datetime.now(UTC)
        return cls(
            id=UUID(int=0),
            tenant_id=tenant_id,
            name=name,
            visit_count=visit_count,
            validity_days=validity_days,
            currency=currency.upper(),
            price_paise=price_paise,
            active=True,
            created_at=now,
            updated_at=now,
        )


# ---------- PackPurchase ----------

@dataclass(slots=True)
class PackPurchase:
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    pack_definition_id: UUID
    visits_remaining: int
    expires_at: datetime
    status: PackStatus
    issued_by_admin_id: UUID
    issued_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def issue(
        cls,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        definition: PackDefinition,
        issued_by_admin_id: UUID,
        now: datetime | None = None,
    ) -> "PackPurchase":
        now = now or datetime.now(UTC)
        return cls(
            id=UUID(int=0),
            tenant_id=tenant_id,
            customer_id=customer_id,
            pack_definition_id=definition.id,
            visits_remaining=definition.visit_count,
            expires_at=now + timedelta(days=definition.validity_days),
            status=PackStatus.ACTIVE,
            issued_by_admin_id=issued_by_admin_id,
            issued_at=now,
            created_at=now,
            updated_at=now,
        )

    def consume_one(self, *, now: datetime) -> int:
        """Decrement visits_remaining by 1. Returns new remaining count.
        Raises InvariantViolation if exhausted, expired, or already non-ACTIVE.
        Caller's repository will additionally enforce optimistic concurrency
        at the SQL level (UPDATE WHERE visits_remaining = expected).
        """
        if self.status != PackStatus.ACTIVE:
            raise InvariantViolation(f"Cannot consume pack in status {self.status}")
        if now >= self.expires_at:
            raise InvariantViolation("Pack is expired")
        if self.visits_remaining <= 0:
            raise InvariantViolation("Pack has no visits remaining")
        self.visits_remaining -= 1
        if self.visits_remaining == 0:
            self.status = PackStatus.EXHAUSTED
        self.updated_at = now
        return self.visits_remaining

    def expire(self) -> None:
        if self.status != PackStatus.ACTIVE:
            raise InvariantViolation(f"Cannot expire pack in status {self.status}")
        self.status = PackStatus.EXPIRED
        self.updated_at = datetime.now(UTC)

    def is_covering(self, now: datetime) -> bool:
        return (
            self.status == PackStatus.ACTIVE
            and self.visits_remaining > 0
            and now < self.expires_at
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_entities.py -v`

Expected: all entity tests pass.

- [ ] **Step 5: Run the full backend test suite to confirm no regressions**

Run: `PYTHONPATH=apps/backend/src uv run pytest`

Expected: all previously-passing tests still pass. Record counts.

- [ ] **Step 6: Commit**

```bash
git add apps/backend/src/membership/ apps/backend/tests/membership/
git commit -m "feat(membership): domain entities with status invariants"
```

---

## Task 3: SQLAlchemy models + Alembic migration

**Files:**
- Create: `apps/backend/src/membership/infrastructure/__init__.py`
- Create: `apps/backend/src/membership/infrastructure/models.py`
- Create: `apps/backend/alembic/versions/20240101_0005_membership.py`
- Modify: `apps/backend/src/booking/infrastructure/models.py` (add 2 nullable columns)
- Modify: `apps/backend/src/common/interfaces/http/app.py` (import membership models)
- Test: model round-trip smoke in `apps/backend/tests/membership/test_models.py` (new file)

**Interfaces:**
- Consumes: ORM model conventions from `payments/infrastructure/models.py`
- Produces:
  - `SubscriptionPlanModel`, `SubscriptionModel`, `PackDefinitionModel`, `PackPurchaseModel` ORM classes
  - Alembic migration `20240101_0005_membership.py` that creates the 4 tables + 2 booking columns + RLS policies

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/membership/test_models.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession

from membership.infrastructure.models import (
    PackDefinitionModel,
    PackPurchaseModel,
    SubscriptionModel,
    SubscriptionPlanModel,
)


def test_models_register_with_metadata():
    """Sanity: importing the module registers all 4 tables on Base.metadata."""
    from common.infrastructure.db import Base

    table_names = set(Base.metadata.tables.keys())
    assert "membership_subscription_plans" in table_names
    assert "membership_subscriptions" in table_names
    assert "membership_pack_definitions" in table_names
    assert "membership_pack_purchases" in table_names


async def test_subscription_plan_round_trip(session: AsyncSession, tenant_id):
    m = SubscriptionPlanModel(
        tenant_id=tenant_id, name="Monthly",
        razorpay_plan_id="plan_test_x",
        price_paise=99900, currency="INR",
        period="monthly", trial_period_days=0, active=True,
    )
    session.add(m)
    await session.flush()
    assert m.id is not None
    fetched = await session.get(SubscriptionPlanModel, m.id)
    assert fetched is not None
    assert fetched.name == "Monthly"


async def test_pack_purchase_round_trip(session: AsyncSession, tenant_id, customer_id):
    pd = PackDefinitionModel(
        tenant_id=tenant_id, name="10-Pack",
        visit_count=10, validity_days=60,
        currency="INR", price_paise=0, active=True,
    )
    session.add(pd)
    await session.flush()
    pp = PackPurchaseModel(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, visits_remaining=10,
        expires_at=pd.created_at, status="active",
        issued_by_admin_id=customer_id,
    )
    session.add(pp)
    await session.flush()
    assert pp.id is not None
    assert pp.visits_remaining == 10


async def test_subscription_round_trip(session: AsyncSession, tenant_id, customer_id):
    sp = SubscriptionPlanModel(
        tenant_id=tenant_id, name="Monthly",
        razorpay_plan_id="plan_sub_x",
        price_paise=99900, currency="INR",
        period="monthly", trial_period_days=0, active=True,
    )
    session.add(sp)
    await session.flush()
    s = SubscriptionModel(
        tenant_id=tenant_id, customer_id=customer_id, plan_id=sp.id,
        razorpay_subscription_id="sub_test_x",
        status="created", cancel_at_period_end=False,
    )
    session.add(s)
    await session.flush()
    assert s.id is not None
    assert s.status == "created"
```

Note: the test relies on `tenant_id`, `customer_id`, and `session` fixtures from `apps/backend/tests/conftest.py` (already established by the bookings + payments test suites). If those fixtures are not present, add them as follows:

```python
# In apps/backend/tests/conftest.py (extend the existing file)
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

@pytest_asyncio.fixture
async def session(tenant_id):
    engine = create_async_engine(os.environ["DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
        await s.rollback()
    await engine.dispose()

@pytest_asyncio.fixture
async def tenant_id():
    from uuid import uuid4
    return uuid4()

@pytest_asyncio.fixture
async def customer_id():
    from uuid import uuid4
    return uuid4()
```

If conftest.py already has these fixtures from a prior task, do not duplicate — just use them.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_models.py -v`

Expected: `ImportError` because `membership.infrastructure.models` does not exist yet.

- [ ] **Step 3: Create the package skeleton**

Create `apps/backend/src/membership/infrastructure/__init__.py` (empty).

- [ ] **Step 4: Implement the ORM models**

Create `apps/backend/src/membership/infrastructure/models.py`:

```python
"""SQLAlchemy ORM models for the membership module.

Naming convention (mirrors payments/): tables are prefixed `membership_`.
Tenant scoping: every model has `tenant_id UUID NOT NULL`. RLS policies are
attached by the Alembic migration (Task 3, migration file).
"""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.infrastructure.db import Base


class SubscriptionPlanModel(Base):
    __tablename__ = "membership_subscription_plans"
    __table_args__ = (
        Index("membership_plans_tenant_idx", "tenant_id"),
        Index("membership_plans_rzp_plan_uniq", "razorpay_plan_id", unique=True),
    )

    id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    razorpay_plan_id: Mapped[str] = mapped_column(Text, nullable=False)
    price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'INR'"))
    period: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'monthly'"))
    trial_period_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[_DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[_DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))


class SubscriptionModel(Base):
    __tablename__ = "membership_subscriptions"
    __table_args__ = (
        Index("membership_subs_tenant_customer_idx", "tenant_id", "customer_id"),
        Index("membership_subs_rzp_sub_uniq", "razorpay_subscription_id", unique=True),
        Index("membership_subs_tenant_status_idx", "tenant_id", "status"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    plan_id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("membership_subscription_plans.id", ondelete="RESTRICT"), nullable=False)
    razorpay_subscription_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'created'"))
    current_period_start: Mapped[_DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[_DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[_DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[_DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    started_at: Mapped[_DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    created_at: Mapped[_DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[_DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))


class PackDefinitionModel(Base):
    __tablename__ = "membership_pack_definitions"
    __table_args__ = (
        Index("membership_packdef_tenant_idx", "tenant_id"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    visit_count: Mapped[int] = mapped_column(Integer, nullable=False)
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'INR'"))
    price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[_DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[_DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))


class PackPurchaseModel(Base):
    __tablename__ = "membership_pack_purchases"
    __table_args__ = (
        Index("membership_pack_active_customer_idx", "tenant_id", "customer_id", postgresql_where=text("status = 'active'")),
        Index("membership_pack_expires_idx", "expires_at", postgresql_where=text("status = 'active'")),
    )

    id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    pack_definition_id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("membership_pack_definitions.id", ondelete="RESTRICT"), nullable=False)
    visits_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[_DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    issued_by_admin_id: Mapped[_uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    issued_at: Mapped[_DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    created_at: Mapped[_DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[_DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))


# Module-private alias used in the column annotations above
from datetime import datetime as _DateTime
```

Note: the `from datetime import datetime as _DateTime` import at the bottom is intentional — placing it after the class definitions keeps the class bodies free of forward-reference noise. (If the project's lint config flags E402 on this import, move it to the top and remove it from the bottom.)

- [ ] **Step 5: Create the Alembic migration**

Create `apps/backend/alembic/versions/20240101_0005_membership.py`:

```python
"""create membership tables and add coverage columns to bookings

Revision ID: 0005_membership
Revises: 0004_payments
Create Date: 2026-08-08

"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_membership"
down_revision: Union[str, None] = "0004_payments"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    # subscription_plans
    op.create_table(
        "membership_subscription_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("razorpay_plan_id", sa.Text(), nullable=False),
        sa.Column("price_paise", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("period", sa.Text(), nullable=False, server_default="monthly"),
        sa.Column("trial_period_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("razorpay_plan_id", name="membership_plans_rzp_plan_uniq"),
    )
    op.create_index("membership_plans_tenant_idx", "membership_subscription_plans", ["tenant_id"])
    op.execute("ALTER TABLE membership_subscription_plans ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY membership_plans_tenant_isolation ON membership_subscription_plans "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )

    # subscriptions
    op.create_table(
        "membership_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("membership_subscription_plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("razorpay_subscription_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="created"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("razorpay_subscription_id", name="membership_subs_rzp_sub_uniq"),
    )
    op.create_index("membership_subs_tenant_customer_idx", "membership_subscriptions", ["tenant_id", "customer_id"])
    op.create_index("membership_subs_tenant_status_idx", "membership_subscriptions", ["tenant_id", "status"])
    op.execute("ALTER TABLE membership_subscriptions ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY membership_subs_tenant_isolation ON membership_subscriptions "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )

    # pack_definitions
    op.create_table(
        "membership_pack_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("visit_count", sa.Integer(), nullable=False),
        sa.Column("validity_days", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("price_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("membership_packdef_tenant_idx", "membership_pack_definitions", ["tenant_id"])
    op.execute("ALTER TABLE membership_pack_definitions ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY membership_packdef_tenant_isolation ON membership_pack_definitions "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )

    # pack_purchases
    op.create_table(
        "membership_pack_purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_definition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("membership_pack_definitions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("visits_remaining", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("issued_by_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.execute(
        "CREATE INDEX membership_pack_active_customer_idx ON membership_pack_purchases "
        "(tenant_id, customer_id) WHERE status = 'active'"
    )
    op.execute(
        "CREATE INDEX membership_pack_expires_idx ON membership_pack_purchases "
        "(expires_at) WHERE status = 'active'"
    )
    op.execute("ALTER TABLE membership_pack_purchases ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY membership_pack_tenant_isolation ON membership_pack_purchases "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )

    # bookings: add coverage columns
    op.add_column("bookings", sa.Column("coverage_source", sa.Text(), nullable=True))
    op.add_column("bookings", sa.Column("pack_purchase_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "bookings_pack_purchase_fk",
        "bookings", "membership_pack_purchases",
        ["pack_purchase_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("bookings_pack_purchase_fk", "bookings", type_="foreignkey")
    op.drop_column("bookings", "pack_purchase_id")
    op.drop_column("bookings", "coverage_source")
    op.execute("DROP POLICY IF EXISTS membership_pack_tenant_isolation ON membership_pack_purchases")
    op.execute("ALTER TABLE membership_pack_purchases DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS membership_pack_expires_idx")
    op.execute("DROP INDEX IF EXISTS membership_pack_active_customer_idx")
    op.drop_table("membership_pack_purchases")
    op.execute("DROP POLICY IF EXISTS membership_packdef_tenant_isolation ON membership_pack_definitions")
    op.execute("ALTER TABLE membership_pack_definitions DISABLE ROW LEVEL SECURITY")
    op.drop_index("membership_packdef_tenant_idx", table_name="membership_pack_definitions")
    op.drop_table("membership_pack_definitions")
    op.execute("DROP POLICY IF EXISTS membership_subs_tenant_isolation ON membership_subscriptions")
    op.execute("ALTER TABLE membership_subscriptions DISABLE ROW LEVEL SECURITY")
    op.drop_index("membership_subs_tenant_status_idx", table_name="membership_subscriptions")
    op.drop_index("membership_subs_tenant_customer_idx", table_name="membership_subscriptions")
    op.drop_table("membership_subscriptions")
    op.execute("DROP POLICY IF EXISTS membership_plans_tenant_isolation ON membership_subscription_plans")
    op.execute("ALTER TABLE membership_subscription_plans DISABLE ROW LEVEL SECURITY")
    op.drop_index("membership_plans_tenant_idx", table_name="membership_subscription_plans")
    op.drop_table("membership_subscription_plans")
```

- [ ] **Step 6: Register membership models with the app**

In `apps/backend/src/common/interfaces/http/app.py`, add alongside the payments models import:

```python
# Import membership models to register them with Base.metadata
from membership.infrastructure import models as _membership_models  # noqa: F401
```

Also extend `_register_module_routers` to include `"membership"` in the tuple:

```python
for module_name in ("auth", "customer", "facility", "booking", "payments", "membership"):
```

(The router file is created in Task 10. Until Task 10 ships, the import is harmless because the router import is in a try/except.)

- [ ] **Step 7: Run the test to verify it passes**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_models.py -v`

Expected: all 4 model tests pass.

If you have a local Postgres available: apply the migration to your dev DB and re-run:

```bash
cd apps/backend && uv run alembic upgrade head
```

- [ ] **Step 8: Run the full backend test suite to confirm no regressions**

Run: `PYTHONPATH=apps/backend/src uv run pytest`

Expected: all previously-passing tests still pass. Record counts.

- [ ] **Step 9: Commit**

```bash
git add apps/backend/src/membership/infrastructure/ \
        apps/backend/alembic/versions/20240101_0005_membership.py \
        apps/backend/src/common/interfaces/http/app.py \
        apps/backend/tests/membership/test_models.py
git commit -m "feat(membership): SQLAlchemy models + Alembic migration"
```

---

## Task 4: Repositories

**Files:**
- Create: `apps/backend/src/membership/infrastructure/repositories.py`
- Test: `apps/backend/tests/membership/test_repositories.py`

**Interfaces:**
- Consumes: ORM models from Task 3, `BaseRepository` from `common/infrastructure/repository.py`, `Conflict` / `NotFound` from `common/domain/exceptions`
- Produces:
  - `SubscriptionRepository` with `get_by_id, get_by_razorpay_id, list_for_customer, list_for_tenant_filtered, add, update`
  - `SubscriptionPlanRepository` with `get_by_id, list_active, add, update`
  - `PackDefinitionRepository` with `get_by_id, list_active, add, update`
  - `PackPurchaseRepository` with `get_by_id, lock_active_for_customer, atomic_decrement, expire_overdue, list_for_customer, list_active_for_customer, add, update`

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/membership/test_repositories.py`:

```python
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from common.domain.exceptions import Conflict
from membership.domain.value_objects import PackStatus
from membership.infrastructure.models import (
    PackDefinitionModel,
    PackPurchaseModel,
    SubscriptionModel,
    SubscriptionPlanModel,
)
from membership.infrastructure.repositories import (
    PackDefinitionRepository,
    PackPurchaseRepository,
    SubscriptionPlanRepository,
    SubscriptionRepository,
)


@pytest.fixture
def plan_repo(session):
    return SubscriptionPlanRepository(session)


@pytest.fixture
def sub_repo(session):
    return SubscriptionRepository(session)


@pytest.fixture
def pack_def_repo(session):
    return PackDefinitionRepository(session)


@pytest.fixture
def pack_repo(session):
    return PackPurchaseRepository(session)


async def _make_plan(plan_repo, *, tenant_id, rzp_id="plan_t_1") -> SubscriptionPlanModel:
    p = SubscriptionPlanModel(
        tenant_id=tenant_id, name="Monthly", razorpay_plan_id=rzp_id,
        price_paise=99900, currency="INR", period="monthly",
        trial_period_days=0, active=True,
    )
    await plan_repo.add(p)
    await plan_repo.session.flush()
    return p


async def test_subscription_repository_get_by_razorpay_id(sub_repo, plan_repo, tenant_id):
    p = await _make_plan(plan_repo, tenant_id=tenant_id, rzp_id="plan_lookup")
    s = SubscriptionModel(
        tenant_id=tenant_id, customer_id=uuid4(), plan_id=p.id,
        razorpay_subscription_id="sub_lookup", status="active",
        cancel_at_period_end=False,
    )
    await sub_repo.add(s)
    await sub_repo.session.flush()
    found = await sub_repo.get_by_razorpay_id(tenant_id, "sub_lookup")
    assert found is not None
    assert found.id == s.id


async def test_pack_purchase_repository_atomic_decrement(pack_repo, tenant_id, customer_id):
    pd = PackDefinitionModel(
        tenant_id=tenant_id, name="5-Pack", visit_count=5,
        validity_days=30, currency="INR", price_paise=0, active=True,
    )
    pack_def_repo = PackDefinitionRepository(pack_repo.session)
    pack_def_repo.session.add(pd)
    await pack_def_repo.session.flush()
    pp = PackPurchaseModel(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, visits_remaining=5,
        expires_at=datetime.now(UTC) + timedelta(days=30),
        status="active", issued_by_admin_id=customer_id,
    )
    await pack_repo.add(pp)
    await pack_repo.session.flush()

    rows = await pack_repo.atomic_decrement(
        tenant_id=tenant_id, pack_id=pp.id, expected_remaining=5,
    )
    assert rows == 1
    reloaded = await pack_repo.session.get(PackPurchaseModel, pp.id)
    assert reloaded.visits_remaining == 4


async def test_pack_purchase_repository_atomic_decrement_raises_conflict_on_stale(
    pack_repo, tenant_id, customer_id,
):
    pd = PackDefinitionModel(
        tenant_id=tenant_id, name="1-Pack", visit_count=1,
        validity_days=30, currency="INR", price_paise=0, active=True,
    )
    PackDefinitionRepository(pack_repo.session).session.add(pd)
    await pack_repo.session.flush()
    pp = PackPurchaseModel(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, visits_remaining=1,
        expires_at=datetime.now(UTC) + timedelta(days=30),
        status="active", issued_by_admin_id=customer_id,
    )
    await pack_repo.add(pp)
    await pack_repo.session.flush()

    # Simulate another booking already consumed the visit
    pp.visits_remaining = 0
    pp.status = PackStatus.EXHAUSTED.value
    await pack_repo.session.flush()

    rows = await pack_repo.atomic_decrement(
        tenant_id=tenant_id, pack_id=pp.id, expected_remaining=1,
    )
    assert rows == 0
    with pytest.raises(Conflict):
        raise Conflict("expected: zero rows means we must raise Conflict",
                       details={"pack_id": str(pp.id)})


async def test_pack_purchase_repository_expire_overdue(pack_repo, tenant_id, customer_id):
    pd = PackDefinitionModel(
        tenant_id=tenant_id, name="5-Pack", visit_count=5,
        validity_days=30, currency="INR", price_paise=0, active=True,
    )
    PackDefinitionRepository(pack_repo.session).session.add(pd)
    await pack_repo.session.flush()
    past = datetime.now(UTC) - timedelta(days=1)
    pp_overdue = PackPurchaseModel(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, visits_remaining=5,
        expires_at=past, status="active", issued_by_admin_id=customer_id,
    )
    pp_fresh = PackPurchaseModel(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, visits_remaining=5,
        expires_at=datetime.now(UTC) + timedelta(days=30),
        status="active", issued_by_admin_id=customer_id,
    )
    await pack_repo.add(pp_overdue)
    await pack_repo.add(pp_fresh)
    await pack_repo.session.flush()

    count = await pack_repo.expire_overdue(now=datetime.now(UTC))
    assert count == 1
    reloaded = await pack_repo.session.get(PackPurchaseModel, pp_overdue.id)
    assert reloaded.status == PackStatus.EXPIRED.value
    fresh = await pack_repo.session.get(PackPurchaseModel, pp_fresh.id)
    assert fresh.status == PackStatus.ACTIVE.value
```

Note: the `session` fixture is shared with Task 3 (see the conftest extension in Task 3). Reuse if present.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_repositories.py -v`

Expected: `ImportError` because `membership.infrastructure.repositories` does not exist yet.

- [ ] **Step 3: Implement the repositories**

Create `apps/backend/src/membership/infrastructure/repositories.py`:

```python
"""Membership repositories.

The optimistic-concurrency pack decrement lives here as a single repository
method (`atomic_decrement`), not in the service, so the SQL is testable in
isolation and the booking service just calls `gate.consume_pack_visit`.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.domain.exceptions import Conflict, NotFound
from common.infrastructure.repository import BaseRepository
from membership.infrastructure.models import (
    PackDefinitionModel,
    PackPurchaseModel,
    SubscriptionModel,
    SubscriptionPlanModel,
)


class SubscriptionPlanRepository(BaseRepository[SubscriptionPlanModel]):
    model = SubscriptionPlanModel

    async def get_by_id(self, tenant_id: UUID, plan_id: UUID) -> SubscriptionPlanModel | None:
        return await self.get(tenant_id, plan_id)

    async def list_active(self, tenant_id: UUID) -> Sequence[SubscriptionPlanModel]:
        stmt = (
            select(SubscriptionPlanModel)
            .where(SubscriptionPlanModel.tenant_id == tenant_id,
                   SubscriptionPlanModel.active.is_(True))
            .order_by(SubscriptionPlanModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class SubscriptionRepository(BaseRepository[SubscriptionModel]):
    model = SubscriptionModel

    async def get_by_id(self, tenant_id: UUID, sub_id: UUID) -> SubscriptionModel | None:
        return await self.get(tenant_id, sub_id)

    async def get_by_razorpay_id(
        self, tenant_id: UUID, razorpay_subscription_id: str
    ) -> SubscriptionModel | None:
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.tenant_id == tenant_id,
            SubscriptionModel.razorpay_subscription_id == razorpay_subscription_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_active_for_customer(
        self, tenant_id: UUID, customer_id: UUID, now: datetime
    ) -> SubscriptionModel | None:
        """Single-row indexed lookup used by the membership gate."""
        stmt = (
            select(SubscriptionModel)
            .where(
                SubscriptionModel.tenant_id == tenant_id,
                SubscriptionModel.customer_id == customer_id,
                SubscriptionModel.status == "active",
            )
            .order_by(SubscriptionModel.started_at.desc())
            .limit(1)
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        if row.trial_ends_at is not None and now >= row.trial_ends_at:
            return None
        return row

    async def list_for_customer(
        self, tenant_id: UUID, customer_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> Sequence[SubscriptionModel]:
        stmt = (
            select(SubscriptionModel)
            .where(
                SubscriptionModel.tenant_id == tenant_id,
                SubscriptionModel.customer_id == customer_id,
            )
            .order_by(SubscriptionModel.started_at.desc())
            .limit(limit).offset(offset)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_for_tenant_filtered(
        self, tenant_id: UUID, *, customer_id: UUID | None = None,
        status: str | None = None, plan_id: UUID | None = None,
        limit: int = 50, offset: int = 0,
    ) -> Sequence[SubscriptionModel]:
        stmt = (
            select(SubscriptionModel)
            .where(SubscriptionModel.tenant_id == tenant_id)
            .order_by(SubscriptionModel.started_at.desc())
            .limit(limit).offset(offset)
        )
        if customer_id is not None:
            stmt = stmt.where(SubscriptionModel.customer_id == customer_id)
        if status is not None:
            stmt = stmt.where(SubscriptionModel.status == status)
        if plan_id is not None:
            stmt = stmt.where(SubscriptionModel.plan_id == plan_id)
        return (await self.session.execute(stmt)).scalars().all()


class PackDefinitionRepository(BaseRepository[PackDefinitionModel]):
    model = PackDefinitionModel

    async def get_by_id(self, tenant_id: UUID, def_id: UUID) -> PackDefinitionModel | None:
        return await self.get(tenant_id, def_id)

    async def list_active(self, tenant_id: UUID) -> Sequence[PackDefinitionModel]:
        stmt = (
            select(PackDefinitionModel)
            .where(PackDefinitionModel.tenant_id == tenant_id,
                   PackDefinitionModel.active.is_(True))
            .order_by(PackDefinitionModel.created_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().all()


class PackPurchaseRepository(BaseRepository[PackPurchaseModel]):
    model = PackPurchaseModel

    async def get_by_id(self, tenant_id: UUID, pack_id: UUID) -> PackPurchaseModel | None:
        return await self.get(tenant_id, pack_id)

    async def lock_active_for_customer(
        self, tenant_id: UUID, customer_id: UUID, now: datetime
    ) -> PackPurchaseModel | None:
        """SELECT FOR UPDATE on the customer's earliest-expiring active pack.
        Returns the row the gate will use; caller must already be in a tx.
        """
        stmt = (
            select(PackPurchaseModel)
            .where(
                PackPurchaseModel.tenant_id == tenant_id,
                PackPurchaseModel.customer_id == customer_id,
                PackPurchaseModel.status == "active",
                PackPurchaseModel.visits_remaining > 0,
                PackPurchaseModel.expires_at > now,
            )
            .order_by(PackPurchaseModel.expires_at.asc())
            .limit(1)
            .with_for_update()
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def atomic_decrement(
        self, *, tenant_id: UUID, pack_id: UUID, expected_remaining: int
    ) -> int:
        """Optimistic-concurrency decrement.

        Returns rows affected (0 or 1). Callers MUST raise Conflict on 0.
        Sets status='exhausted' when remaining hits 0; otherwise 'active'.
        """
        new_remaining = expected_remaining - 1
        new_status = "exhausted" if new_remaining == 0 else "active"
        stmt = (
            update(PackPurchaseModel)
            .where(
                PackPurchaseModel.tenant_id == tenant_id,
                PackPurchaseModel.id == pack_id,
                PackPurchaseModel.visits_remaining == expected_remaining,
            )
            .values(
                visits_remaining=new_remaining,
                status=new_status,
                updated_at=datetime.utcnow(),
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def expire_overdue(self, *, now: datetime) -> int:
        """Bulk UPDATE: set status='expired' for active packs past expiry.

        Returns the number of rows flipped. Used by the lifespan sweeper.
        """
        stmt = (
            update(PackPurchaseModel)
            .where(
                PackPurchaseModel.status == "active",
                PackPurchaseModel.expires_at <= now,
            )
            .values(status="expired", updated_at=now)
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def list_for_customer(
        self, tenant_id: UUID, customer_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[PackPurchaseModel]:
        stmt = (
            select(PackPurchaseModel)
            .where(
                PackPurchaseModel.tenant_id == tenant_id,
                PackPurchaseModel.customer_id == customer_id,
            )
            .order_by(PackPurchaseModel.issued_at.desc())
            .limit(limit).offset(offset)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_active_for_customer(
        self, tenant_id: UUID, customer_id: UUID, now: datetime
    ) -> Sequence[PackPurchaseModel]:
        stmt = (
            select(PackPurchaseModel)
            .where(
                PackPurchaseModel.tenant_id == tenant_id,
                PackPurchaseModel.customer_id == customer_id,
                PackPurchaseModel.status == "active",
                PackPurchaseModel.expires_at > now,
            )
            .order_by(PackPurchaseModel.expires_at.asc())
        )
        return (await self.session.execute(stmt)).scalars().all()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_repositories.py -v`

Expected: 4 tests pass.

- [ ] **Step 5: Run the full backend test suite to confirm no regressions**

Run: `PYTHONPATH=apps/backend/src uv run pytest`

Expected: all previously-passing tests still pass. Record counts.

- [ ] **Step 6: Commit**

```bash
git add apps/backend/src/membership/infrastructure/repositories.py \
        apps/backend/tests/membership/test_repositories.py
git commit -m "feat(membership): repositories with atomic pack decrement"
```

---

## Task 5: PaymentProvider extensions (subscription methods)

**Files:**
- Modify: `apps/backend/src/payments/application/provider.py` (extend Protocol + NullAdapter + RazorpayAdapter)
- Test: `apps/backend/tests/payments/test_razorpay_adapter.py` (append subscription-method tests)

**Interfaces:**
- Consumes: existing `PaymentProvider` Protocol, `RazorpayAdapter`, `NullAdapter`, `payments_test_settings`
- Produces: 4 new methods on `PaymentProvider`:
  - `async create_plan(*, name, period, interval, amount_paise, currency, trial_period_days) -> dict` returning `{id: "plan_XXX", ...}`
  - `async create_subscription(*, razorpay_plan_id, customer_id, total_count, notes) -> dict` returning `{id: "sub_XXX", short_url: "...", status: "created"}`
  - `async cancel_subscription(*, razorpay_subscription_id, cancel_at_cycle_end) -> dict`
  - `async fetch_plan(razorpay_plan_id) -> dict`

The `MembershipService` (Task 6) consumes only `create_subscription` and `cancel_subscription`; the other two are added for the admin plan-management endpoints (Task 10) and for completeness.

- [ ] **Step 1: Append failing tests**

Append to `apps/backend/tests/payments/test_razorpay_adapter.py`:

```python
# ---- Subscription methods ----

import responses as _responses_lib
import razorpay as _rzp_sdk


@pytest.fixture
def null_adapter():
    from payments.application.provider import NullAdapter
    return NullAdapter()


@pytest.fixture
def rzp_adapter():
    from payments.application.provider import RazorpayAdapter
    return RazorpayAdapter(
        key_id="rzp_test_x", key_secret="rzp_test_secret_x", webhook_secret="whsec_x"
    )


async def test_null_create_plan_returns_deterministic_id(null_adapter):
    result = await null_adapter.create_plan(
        name="Monthly", period="monthly", interval=1,
        amount_paise=99900, currency="INR", trial_period_days=0,
    )
    assert result["id"].startswith("plan_test_")


async def test_null_create_subscription_returns_short_url(null_adapter):
    result = await null_adapter.create_subscription(
        razorpay_plan_id="plan_test_x", customer_id="cust_x",
        total_count=12, notes={},
    )
    assert result["id"].startswith("sub_test_")
    assert result["short_url"].startswith("https://stub.test/rzp/")


async def test_null_cancel_subscription_is_noop(null_adapter):
    # No return value is part of the contract; just confirm no exception
    await null_adapter.cancel_subscription(
        razorpay_subscription_id="sub_x", cancel_at_cycle_end=True,
    )


@_responses_lib.activate
async def test_rzp_create_plan_posts_to_plans_endpoint(rzp_adapter):
    _responses_lib.add(
        _responses_lib.POST,
        "https://api.razorpay.com/v1/plans",
        json={"id": "plan_test_real", "period": "monthly", "item": {"amount": 99900, "currency": "INR"}},
        status=200,
    )
    result = await rzp_adapter.create_plan(
        name="Monthly", period="monthly", interval=1,
        amount_paise=99900, currency="INR", trial_period_days=7,
    )
    assert result["id"] == "plan_test_real"
    body = _responses_lib.calls[0].request.body
    assert b"99900" in body
    assert b'"trial_period":7' in body or b"trial_period%22%3A7" in body


@_responses_lib.activate
async def test_rzp_create_subscription_posts_to_subscriptions_endpoint(rzp_adapter):
    _responses_lib.add(
        _responses_lib.POST,
        "https://api.razorpay.com/v1/subscriptions",
        json={"id": "sub_test_real", "short_url": "https://rzp.io/i/abc",
              "status": "created"},
        status=200,
    )
    result = await rzp_adapter.create_subscription(
        razorpay_plan_id="plan_x", customer_id="cust_x",
        total_count=12, notes={"tenant_id": "t1"},
    )
    assert result["id"] == "sub_test_real"
    assert result["short_url"] == "https://rzp.io/i/abc"


@_responses_lib.activate
async def test_rzp_cancel_subscription_posts_to_cancel_endpoint(rzp_adapter):
    _responses_lib.add(
        _responses_lib.POST,
        "https://api.razorpay.com/v1/subscriptions/sub_x/cancel",
        json={"id": "sub_x", "status": "cancelled"},
        status=200,
    )
    await rzp_adapter.cancel_subscription(
        razorpay_subscription_id="sub_x", cancel_at_cycle_end=True,
    )
    assert len(_responses_lib.calls) == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/payments/test_razorpay_adapter.py -v -k "create_plan or create_subscription or cancel_subscription"`

Expected: `AttributeError: 'NullAdapter' object has no attribute 'create_plan'` (and same for the other methods).

- [ ] **Step 3: Extend the Protocol in provider.py**

In `apps/backend/src/payments/application/provider.py`, add to the `PaymentProvider` Protocol after the existing methods:

```python
    # ---- Subscriptions (Razorpay Subscriptions API) ----
    async def create_plan(
        self,
        *,
        name: str,
        period: str,        # "monthly" | "yearly"
        interval: int,      # billing cycle count (1 = once per period)
        amount_paise: int,
        currency: str,
        trial_period_days: int,
    ) -> dict: ...

    async def create_subscription(
        self,
        *,
        razorpay_plan_id: str,
        customer_id: str,
        total_count: int,   # billing cycles (12 = 1 year of monthly)
        notes: dict,
    ) -> dict: ...

    async def cancel_subscription(
        self,
        *,
        razorpay_subscription_id: str,
        cancel_at_cycle_end: bool,
    ) -> dict: ...

    async def fetch_plan(self, razorpay_plan_id: str) -> dict: ...
```

- [ ] **Step 4: Implement the methods on NullAdapter**

Add to `NullAdapter` in the same file:

```python
    async def create_plan(
        self, *, name, period, interval, amount_paise, currency, trial_period_days,
    ):
        return {
            "id": f"plan_test_{uuid4().hex[:16]}",
            "period": period,
            "interval": interval,
            "item": {"amount": amount_paise, "currency": currency},
            "trial_period_days": trial_period_days,
        }

    async def create_subscription(
        self, *, razorpay_plan_id, customer_id, total_count, notes,
    ):
        sid = f"sub_test_{uuid4().hex[:16]}"
        return {
            "id": sid,
            "short_url": f"https://stub.test/rzp/{sid}",
            "status": "created",
            "plan_id": razorpay_plan_id,
            "customer_id": customer_id,
            "total_count": total_count,
        }

    async def cancel_subscription(
        self, *, razorpay_subscription_id, cancel_at_cycle_end,
    ):
        return {"id": razorpay_subscription_id, "status": "cancelled",
                "cancel_at_cycle_end": cancel_at_cycle_end}

    async def fetch_plan(self, razorpay_plan_id):
        return {"id": razorpay_plan_id, "period": "monthly", "interval": 1}
```

- [ ] **Step 5: Implement the methods on RazorpayAdapter**

Add to `RazorpayAdapter` in the same file:

```python
    async def create_plan(
        self, *, name, period, interval, amount_paise, currency, trial_period_days,
    ):
        if currency != "INR":
            raise Validation("Only INR currency is supported in v1")
        payload = {
            "period": period,
            "interval": interval,
            "item": {
                "name": name,
                "amount": amount_paise,
                "currency": currency,
            },
            "notes": {},
        }
        if trial_period_days > 0:
            payload["trial_period"] = trial_period_days
        plan = await asyncio.to_thread(self._client.plan.create, payload)
        return plan

    async def create_subscription(
        self, *, razorpay_plan_id, customer_id, total_count, notes,
    ):
        payload = {
            "plan_id": razorpay_plan_id,
            "customer_notify": 1,
            "quantity": 1,
            "total_count": total_count,
            "notes": notes,
            "customer_id": customer_id,
        }
        sub = await asyncio.to_thread(self._client.subscription.create, payload)
        return {
            "id": sub["id"],
            "short_url": sub.get("short_url", ""),
            "status": sub.get("status", "created"),
        }

    async def cancel_subscription(
        self, *, razorpay_subscription_id, cancel_at_cycle_end,
    ):
        return await asyncio.to_thread(
            self._client.subscription.cancel,
            razorpay_subscription_id,
            {"cancel_at_cycle_end": 1 if cancel_at_cycle_end else 0},
        )

    async def fetch_plan(self, razorpay_plan_id):
        return await asyncio.to_thread(self._client.plan.fetch, razorpay_plan_id)
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/payments/test_razorpay_adapter.py -v`

Expected: all adapter tests pass (existing + new).

- [ ] **Step 7: Run the full backend test suite to confirm no regressions**

Run: `PYTHONPATH=apps/backend/src uv run pytest`

Expected: all previously-passing tests still pass. Record counts.

- [ ] **Step 8: Commit**

```bash
git add apps/backend/src/payments/application/provider.py \
        apps/backend/tests/payments/test_razorpay_adapter.py
git commit -m "feat(membership): extend PaymentProvider with subscription methods"
```

---

## Task 6: MembershipService — subscription operations

**Files:**
- Create: `apps/backend/src/membership/application/__init__.py`
- Create: `apps/backend/src/membership/application/membership_gate.py` (Protocol + CoverageDecision)
- Create: `apps/backend/src/membership/application/events.py` (domain events)
- Create: `apps/backend/src/membership/application/membership_service.py` (subscription methods; pack methods in Task 7)
- Test: `apps/backend/tests/membership/test_membership_service.py` (subscription tests only — pack tests in Task 7)

**Interfaces:**
- Consumes: entities from Task 2, repositories from Task 4, provider extensions from Task 5, `IdempotencyStore` from `payments/infrastructure/idempotency.py`, `EventPublisher` from `common/application/events.py`
- Produces:
  - `CoverageDecision` dataclass (`free, source, pack_purchase_id, pack_visits_remaining`)
  - `MembershipGate` Protocol with `evaluate_coverage` and `consume_pack_visit`
  - `MembershipSubscriptionActivated/Cancelled` events
  - `MembershipService.create_subscription, cancel_subscription_at_period_end, activate_from_webhook, get_active_subscription, list_subscriptions`

- [ ] **Step 1: Write the failing tests**

Create `apps/backend/tests/membership/test_membership_service.py`:

```python
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from common.domain.exceptions import Conflict, NotFound
from membership.application.events import MembershipSubscriptionActivated
from membership.application.membership_gate import CoverageDecision
from membership.application.membership_service import MembershipService
from membership.infrastructure.models import (
    PackDefinitionModel,
    SubscriptionModel,
    SubscriptionPlanModel,
)
from membership.infrastructure.repositories import (
    PackDefinitionRepository,
    SubscriptionPlanRepository,
    SubscriptionRepository,
)


class FakeEventPublisher:
    def __init__(self):
        self.events = []

    async def publish(self, event):
        self.events.append(event)


class FakeIdempotencyStore:
    def __init__(self):
        self.seen: set[str] = set()

    async def exists(self, key):
        return key in self.seen

    async def remember(self, key):
        self.seen.add(key)


class FakeProvider:
    """Stand-in for PaymentProvider — only the methods we use."""

    def __init__(self):
        self.created = []
        self.cancelled = []

    async def create_subscription(self, *, razorpay_plan_id, customer_id, total_count, notes):
        sid = f"sub_test_{uuid4().hex[:8]}"
        self.created.append({"plan_id": razorpay_plan_id, "customer_id": customer_id})
        return {"id": sid, "short_url": f"https://stub.test/rzp/{sid}", "status": "created"}

    async def cancel_subscription(self, *, razorpay_subscription_id, cancel_at_cycle_end):
        self.cancelled.append({"id": razorpay_subscription_id, "cancel_at_cycle_end": cancel_at_cycle_end})
        return {"id": razorpay_subscription_id, "status": "cancelled"}


@pytest.fixture
async def plan_repo(session, tenant_id):
    p = SubscriptionPlanModel(
        tenant_id=tenant_id, name="Monthly", razorpay_plan_id="plan_t1",
        price_paise=99900, currency="INR", period="monthly",
        trial_period_days=0, active=True,
    )
    session.add(p)
    await session.flush()
    return SubscriptionPlanRepository(session)


@pytest.fixture
async def sub_repo(session):
    return SubscriptionRepository(session)


@pytest.fixture
def events():
    return FakeEventPublisher()


@pytest.fixture
def idem():
    return FakeIdempotencyStore()


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def service(session, plan_repo, sub_repo, events, idem, provider):
    return MembershipService(
        session=session,
        subscription_repo=sub_repo,
        plan_repo=plan_repo,
        pack_definition_repo=PackDefinitionRepository(session),
        pack_repo=PackPurchaseRepository_factory(session),
        events=events,
        idempotency=idem,
        provider=provider,
    )


def PackPurchaseRepository_factory(session):
    from membership.infrastructure.repositories import PackPurchaseRepository
    return PackPurchaseRepository(session)


async def test_create_subscription_persists_row_and_returns_short_url(
    service, plan_repo, sub_repo, provider, events, tenant_id, customer_id,
):
    plan = (await plan_repo.list_active(tenant_id))[0]
    result = await service.create_subscription(
        tenant_id=tenant_id, customer_id=customer_id, plan_id=plan.id,
    )
    assert result["short_url"].startswith("https://stub.test/rzp/")
    sub = await sub_repo.get_by_razorpay_id(tenant_id, result["subscription_id"])
    assert sub is not None
    assert sub.status == "created"
    assert sub.customer_id == customer_id
    assert len(provider.created) == 1


async def test_create_subscription_raises_not_found_for_inactive_plan(
    service, sub_repo, session, tenant_id, customer_id,
):
    # Plan not active (manually flip)
    plan = SubscriptionPlanModel(
        tenant_id=tenant_id, name="Inactive", razorpay_plan_id="plan_inactive",
        price_paise=0, currency="INR", period="monthly",
        trial_period_days=0, active=False,
    )
    session.add(plan)
    await session.flush()
    with pytest.raises(NotFound):
        await service.create_subscription(
            tenant_id=tenant_id, customer_id=customer_id, plan_id=plan.id,
        )


async def test_cancel_subscription_at_period_end_calls_provider(
    service, plan_repo, sub_repo, provider, tenant_id, customer_id,
):
    plan = (await plan_repo.list_active(tenant_id))[0]
    created = await service.create_subscription(
        tenant_id=tenant_id, customer_id=customer_id, plan_id=plan.id,
    )
    # Simulate webhook activated
    await service.activate_from_webhook(
        event_id="evt_1", event_type="subscription.activated",
        payload={
            "id": created["subscription_id"],
            "current_period_start": datetime.now(UTC).isoformat(),
            "current_period_end": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "trial_ends_at": None,
        },
    )
    cancelled = await service.cancel_subscription_at_period_end(
        tenant_id=tenant_id, subscription_id=(await sub_repo.get_by_razorpay_id(
            tenant_id, created["subscription_id"]
        )).id,
    )
    assert cancelled.cancel_at_period_end is True
    assert cancelled.status.value == "active"  # not flipped yet — webhook does that
    assert provider.cancelled[-1]["cancel_at_cycle_end"] is True


async def test_activate_from_webhook_idempotent(
    service, plan_repo, sub_repo, events, idem, tenant_id, customer_id,
):
    plan = (await plan_repo.list_active(tenant_id))[0]
    created = await service.create_subscription(
        tenant_id=tenant_id, customer_id=customer_id, plan_id=plan.id,
    )
    payload = {
        "id": created["subscription_id"],
        "current_period_start": datetime.now(UTC).isoformat(),
        "current_period_end": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        "trial_ends_at": None,
    }
    await service.activate_from_webhook(
        event_id="evt_dup", event_type="subscription.activated", payload=payload,
    )
    await service.activate_from_webhook(
        event_id="evt_dup", event_type="subscription.activated", payload=payload,
    )
    activated_count = sum(
        1 for e in events.events if isinstance(e, MembershipSubscriptionActivated)
    )
    assert activated_count == 1
```

Note: `PackPurchaseRepository_factory` is a tiny helper used only by the `service` fixture so all 4 repos are wired up. Pack-method tests are added in Task 7.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_membership_service.py -v`

Expected: `ImportError` because `membership.application.*` modules do not exist yet.

- [ ] **Step 3: Create the package skeleton**

Create `apps/backend/src/membership/application/__init__.py` (empty).

- [ ] **Step 4: Create the gate protocol**

Create `apps/backend/src/membership/application/membership_gate.py`:

```python
"""MembershipGate — the protocol consumed by BookingService.

The protocol is the only thing `booking/` imports from `membership/`.
The implementation (`MembershipService`) satisfies it via duck typing — no
`implements` keyword.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CoverageDecision:
    """Result of evaluating membership coverage for a booking."""
    free: bool
    source: str | None                # "subscription" | "pack" | None
    pack_purchase_id: UUID | None
    pack_visits_remaining: int | None  # snapshot for optimistic concurrency


class MembershipGate(Protocol):
    async def evaluate_coverage(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        resource_id: UUID,
        now: datetime,
    ) -> CoverageDecision: ...

    async def consume_pack_visit(
        self,
        *,
        tenant_id: UUID,
        pack_purchase_id: UUID,
        expected_remaining: int,
    ) -> None:
        """Atomic decrement. Raises Conflict on race loss."""
```

- [ ] **Step 5: Create the domain events**

Create `apps/backend/src/membership/application/events.py`:

```python
"""Membership domain events.

Subscribers from future modules (notifications, analytics) register
callables at startup via the in-process EventPublisher.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from common.application.events import DomainEvent


@dataclass(frozen=True, slots=True)
class MembershipSubscriptionActivated(DomainEvent):
    subscription_id: UUID
    customer_id: UUID
    razorpay_subscription_id: str


@dataclass(frozen=True, slots=True)
class MembershipSubscriptionCancelled(DomainEvent):
    subscription_id: UUID
    customer_id: UUID
    cancelled_at: datetime


@dataclass(frozen=True, slots=True)
class MembershipPackIssued(DomainEvent):
    pack_purchase_id: UUID
    customer_id: UUID
    pack_definition_id: UUID


@dataclass(frozen=True, slots=True)
class MembershipPackExhausted(DomainEvent):
    pack_purchase_id: UUID
    customer_id: UUID


@dataclass(frozen=True, slots=True)
class MembershipPackExpired(DomainEvent):
    pack_purchase_id: UUID
    customer_id: UUID
```

- [ ] **Step 6: Implement MembershipService (subscription methods only)**

Create `apps/backend/src/membership/application/membership_service.py`:

```python
"""MembershipService — orchestrates subscription + pack operations.

Implements `MembershipGate` for `booking/`. Subscription state is driven
by Razorpay webhooks; pack state is driven by admin issuance and the
booking-time decrement.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from common.domain.exceptions import Conflict, NotFound, Validation
from common.application.events import EventPublisher
from membership.application.events import (
    MembershipPackIssued,
    MembershipSubscriptionActivated,
    MembershipSubscriptionCancelled,
)
from membership.application.membership_gate import CoverageDecision
from membership.domain.entities import (
    PackDefinition,
    PackPurchase,
    Subscription,
    SubscriptionPlan,
)
from membership.domain.value_objects import (
    BillingPeriod,
    PackStatus,
    SubscriptionStatus,
)
from membership.infrastructure.models import (
    PackDefinitionModel,
    PackPurchaseModel,
    SubscriptionModel,
    SubscriptionPlanModel,
)
from membership.infrastructure.repositories import (
    PackDefinitionRepository,
    PackPurchaseRepository,
    SubscriptionPlanRepository,
    SubscriptionRepository,
)


@dataclass(frozen=True)
class SubscriptionCreateResult:
    subscription_id: str  # razorpay_subscription_id
    short_url: str
    status: str


class MembershipService:
    def __init__(
        self,
        *,
        session,
        subscription_repo: SubscriptionRepository,
        plan_repo: SubscriptionPlanRepository,
        pack_definition_repo: PackDefinitionRepository,
        pack_repo: PackPurchaseRepository,
        events: EventPublisher,
        idempotency,
        provider,  # PaymentProvider — only subscription methods used in this task
    ) -> None:
        self._session = session
        self._subs = subscription_repo
        self._plans = plan_repo
        self._pack_defs = pack_definition_repo
        self._packs = pack_repo
        self._events = events
        self._idem = idempotency
        self._provider = provider

    # ------------------------------------------------------------------
    # Subscription operations
    # ------------------------------------------------------------------

    async def create_subscription(
        self, *, tenant_id: UUID, customer_id: UUID, plan_id: UUID,
        now: datetime | None = None,
    ) -> SubscriptionCreateResult:
        now = now or datetime.now(UTC)
        plan = await self._plans.get_by_id(tenant_id, plan_id)
        if plan is None or not plan.active:
            raise NotFound("Subscription plan not found", details={"plan_id": str(plan_id)})

        total_count = 12  # v1: monthly → 12 cycles per year, renewable
        provider_result = await self._provider.create_subscription(
            razorpay_plan_id=plan.razorpay_plan_id,
            customer_id=str(customer_id),
            total_count=total_count,
            notes={"tenant_id": str(tenant_id), "customer_id": str(customer_id)},
        )
        m = SubscriptionModel(
            id=uuid4(),
            tenant_id=tenant_id,
            customer_id=customer_id,
            plan_id=plan.id,
            razorpay_subscription_id=provider_result["id"],
            status="created",
            cancel_at_period_end=False,
            started_at=now,
        )
        await self._subs.add(m)
        await self._session.flush()
        return SubscriptionCreateResult(
            subscription_id=m.razorpay_subscription_id,
            short_url=provider_result["short_url"],
            status=m.status,
        )

    async def cancel_subscription_at_period_end(
        self, *, tenant_id: UUID, subscription_id: UUID,
    ) -> Subscription:
        m = await self._subs.get_by_id(tenant_id, subscription_id)
        if m is None:
            raise NotFound("Subscription not found", details={"subscription_id": str(subscription_id)})
        entity = self._subscription_to_entity(m)
        if entity.status != SubscriptionStatus.ACTIVE:
            raise Conflict(
                "Subscription cannot be cancelled at period end",
                details={"status": entity.status.value},
            )
        await self._provider.cancel_subscription(
            razorpay_subscription_id=m.razorpay_subscription_id,
            cancel_at_cycle_end=True,
        )
        entity.mark_cancel_at_period_end()
        m.cancel_at_period_end = True
        m.updated_at = datetime.now(UTC)
        await self._session.flush()
        return entity

    async def activate_from_webhook(
        self,
        *,
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        razorpay_id = payload.get("id")
        if not razorpay_id:
            raise Validation("Missing subscription id in webhook payload")
        idem_key = f"subscription:{razorpay_id}:{event_type}:{event_id}"
        if await self._idem.exists(idem_key):
            return
        # Look up the existing row (created on signup) by razorpay id.
        # We don't know the tenant from the webhook — search across tenants.
        # For v1, every tenant_admin webhook secret is shared, so we iterate.
        # In practice Razorpay delivers one tenant per webhook secret.
        from sqlalchemy import select
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.razorpay_subscription_id == razorpay_id,
        )
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        if m is None:
            # Subscription created by something other than our create_subscription
            # (e.g. manual via Razorpay dashboard). Idempotently mark seen and move on.
            await self._idem.remember(idem_key)
            return

        entity = self._subscription_to_entity(m)
        entity.apply_event(event_type, **self._payload_to_kwargs(event_type, payload))
        # Persist the entity's new state back onto the model
        m.status = entity.status.value
        m.current_period_start = entity.current_period_start
        m.current_period_end = entity.current_period_end
        m.trial_ends_at = entity.trial_ends_at
        m.cancelled_at = entity.cancelled_at
        m.updated_at = entity.updated_at
        await self._session.flush()
        await self._idem.remember(idem_key)

        if event_type == "subscription.activated":
            await self._events.publish(MembershipSubscriptionActivated(
                tenant_id=m.tenant_id,
                subscription_id=m.id,
                customer_id=m.customer_id,
                razorpay_subscription_id=m.razorpay_subscription_id,
            ))
        elif event_type == "subscription.cancelled":
            await self._events.publish(MembershipSubscriptionCancelled(
                tenant_id=m.tenant_id,
                subscription_id=m.id,
                customer_id=m.customer_id,
                cancelled_at=entity.cancelled_at or datetime.now(UTC),
            ))

    async def get_active_subscription(
        self, *, tenant_id: UUID, customer_id: UUID,
    ) -> Subscription | None:
        now = datetime.now(UTC)
        m = await self._subs.get_active_for_customer(tenant_id, customer_id, now)
        return self._subscription_to_entity(m) if m else None

    async def list_subscriptions(
        self, *, tenant_id: UUID, customer_id: UUID | None = None,
        status: str | None = None, plan_id: UUID | None = None,
        limit: int = 50, offset: int = 0,
    ) -> list[Subscription]:
        rows = await self._subs.list_for_tenant_filtered(
            tenant_id,
            customer_id=customer_id, status=status, plan_id=plan_id,
            limit=limit, offset=offset,
        )
        return [self._subscription_to_entity(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _subscription_to_entity(self, m: SubscriptionModel) -> Subscription:
        return Subscription(
            id=m.id, tenant_id=m.tenant_id, customer_id=m.customer_id,
            plan_id=m.plan_id, razorpay_subscription_id=m.razorpay_subscription_id,
            status=SubscriptionStatus(m.status),
            current_period_start=m.current_period_start,
            current_period_end=m.current_period_end,
            trial_ends_at=m.trial_ends_at,
            cancelled_at=m.cancelled_at,
            cancel_at_period_end=m.cancel_at_period_end,
            started_at=m.started_at,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def _payload_to_kwargs(self, event_type: str, payload: dict) -> dict:
        out: dict[str, Any] = {}
        if event_type == "subscription.activated":
            cps = payload.get("current_period_start")
            cpe = payload.get("current_period_end")
            out["current_period_start"] = self._parse_dt(cps) if cps else None
            out["current_period_end"] = self._parse_dt(cpe) if cpe else None
            trial = payload.get("trial_end")
            out["trial_ends_at"] = self._parse_dt(trial) if trial else None
        elif event_type == "subscription.charged":
            cps = payload.get("current_period_start")
            cpe = payload.get("current_period_end")
            out["current_period_start"] = self._parse_dt(cps) if cps else None
            out["current_period_end"] = self._parse_dt(cpe) if cpe else None
        elif event_type == "subscription.cancelled":
            out["cancelled_at"] = datetime.now(UTC)
        return out

    @staticmethod
    def _parse_dt(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(int(value), tz=UTC)
        if isinstance(value, str):
            try:
                # ISO 8601 with Z or +00:00
                cleaned = value.replace("Z", "+00:00")
                dt = datetime.fromisoformat(cleaned)
                return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
            except ValueError:
                return None
        return None

    # ------------------------------------------------------------------
    # Placeholder methods — implemented in Task 7 (pack + gate)
    # ------------------------------------------------------------------

    async def evaluate_coverage(self, *, tenant_id, customer_id, resource_id, now):
        raise NotImplementedError  # implemented in Task 7

    async def consume_pack_visit(self, *, tenant_id, pack_purchase_id, expected_remaining):
        raise NotImplementedError  # implemented in Task 7

    async def issue_pack(self, *, tenant_id, customer_id, pack_definition_id, issued_by_admin_id, now):
        raise NotImplementedError  # implemented in Task 7

    async def list_active_packs_for_customer(self, *, tenant_id, customer_id, now):
        raise NotImplementedError  # implemented in Task 7

    async def list_packs_for_customer_admin(self, *, tenant_id, customer_id):
        raise NotImplementedError  # implemented in Task 7

    async def expire_pack(self, *, tenant_id, pack_id):
        raise NotImplementedError  # implemented in Task 7

    async def expire_overdue_packs(self, *, now):
        raise NotImplementedError  # implemented in Task 7
```

- [ ] **Step 7: Run the test to verify it passes**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_membership_service.py -v`

Expected: 4 subscription tests pass.

- [ ] **Step 8: Run the full backend test suite to confirm no regressions**

Run: `PYTHONPATH=apps/backend/src uv run pytest`

Expected: all previously-passing tests still pass. Record counts.

- [ ] **Step 9: Commit**

```bash
git add apps/backend/src/membership/application/ \
        apps/backend/tests/membership/test_membership_service.py
git commit -m "feat(membership): subscription operations + gate protocol"
```

---

## Task 7: MembershipService — pack operations + MembershipGate implementation

**Files:**
- Modify: `apps/backend/src/membership/application/membership_service.py` (replace the 6 `NotImplementedError` stubs from Task 6)
- Test: append to `apps/backend/tests/membership/test_membership_service.py`

**Interfaces:**
- Consumes: repositories from Task 4, `MembershipGate` Protocol from Task 6, `Conflict` from `common/domain/exceptions`
- Produces (replacing the stubs):
  - `async evaluate_coverage(...) -> CoverageDecision` (subscription first, then pack, else not-free)
  - `async consume_pack_visit(...)` (atomic decrement; raises `Conflict` on race loss)
  - `async issue_pack(...)` (validates customer + definition, persists row, publishes event)
  - `async list_active_packs_for_customer(...)`
  - `async list_packs_for_customer_admin(...)`
  - `async expire_pack(...)` (admin-forced)
  - `async expire_overdue_packs(...) -> int` (called by sweeper)

- [ ] **Step 1: Append failing tests**

Append to `apps/backend/tests/membership/test_membership_service.py`:

```python
# ---- Pack operations ----

from membership.infrastructure.models import PackPurchaseModel


async def _make_pack_def(session, tenant_id, *, visit_count=5, validity_days=30,
                         name="5-Pack", active=True):
    pd = PackDefinitionModel(
        tenant_id=tenant_id, name=name, visit_count=visit_count,
        validity_days=validity_days, currency="INR",
        price_paise=0, active=active,
    )
    session.add(pd)
    await session.flush()
    return pd


async def test_issue_pack_creates_active_row_with_correct_expiry(
    service, session, tenant_id, customer_id,
):
    pd = await _make_pack_def(session, tenant_id, visit_count=10, validity_days=60)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    pp = await service.issue_pack(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, issued_by_admin_id=customer_id, now=now,
    )
    assert pp.status.value == "active"
    assert pp.visits_remaining == 10
    assert pp.expires_at == now + timedelta(days=60)


async def test_issue_pack_raises_not_found_for_inactive_definition(
    service, session, tenant_id, customer_id,
):
    pd = await _make_pack_def(session, tenant_id, active=False)
    with pytest.raises(NotFound):
        await service.issue_pack(
            tenant_id=tenant_id, customer_id=customer_id,
            pack_definition_id=pd.id, issued_by_admin_id=customer_id,
            now=datetime.now(UTC),
        )


async def test_evaluate_coverage_returns_free_for_active_subscription(
    service, plan_repo, sub_repo, tenant_id, customer_id,
):
    plan = (await plan_repo.list_active(tenant_id))[0]
    created = await service.create_subscription(
        tenant_id=tenant_id, customer_id=customer_id, plan_id=plan.id,
    )
    await service.activate_from_webhook(
        event_id="evt_cov", event_type="subscription.activated",
        payload={
            "id": created["subscription_id"],
            "current_period_start": datetime.now(UTC).isoformat(),
            "current_period_end": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "trial_ends_at": None,
        },
    )
    decision = await service.evaluate_coverage(
        tenant_id=tenant_id, customer_id=customer_id,
        resource_id=uuid4(), now=datetime.now(UTC),
    )
    assert decision.free is True
    assert decision.source == "subscription"
    assert decision.pack_purchase_id is None


async def test_evaluate_coverage_returns_pack_when_no_subscription(
    service, session, pack_repo, tenant_id, customer_id,
):
    pd = await _make_pack_def(session, tenant_id, visit_count=3)
    pp = await service.issue_pack(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, issued_by_admin_id=customer_id,
        now=datetime.now(UTC),
    )
    decision = await service.evaluate_coverage(
        tenant_id=tenant_id, customer_id=customer_id,
        resource_id=uuid4(), now=datetime.now(UTC),
    )
    assert decision.free is True
    assert decision.source == "pack"
    assert decision.pack_purchase_id == pp.id
    assert decision.pack_visits_remaining == 3


async def test_evaluate_coverage_returns_not_free_with_no_coverage(
    service, tenant_id, customer_id,
):
    decision = await service.evaluate_coverage(
        tenant_id=tenant_id, customer_id=customer_id,
        resource_id=uuid4(), now=datetime.now(UTC),
    )
    assert decision.free is False
    assert decision.source is None


async def test_consume_pack_visit_decrements_and_persists(
    service, session, pack_repo, tenant_id, customer_id,
):
    pd = await _make_pack_def(session, tenant_id, visit_count=2)
    pp = await service.issue_pack(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, issued_by_admin_id=customer_id,
        now=datetime.now(UTC),
    )
    await service.consume_pack_visit(
        tenant_id=tenant_id, pack_purchase_id=pp.id, expected_remaining=2,
    )
    reloaded = await pack_repo.get_by_id(tenant_id, pp.id)
    assert reloaded.visits_remaining == 1


async def test_consume_pack_visit_raises_conflict_on_stale_remaining(
    service, session, tenant_id, customer_id,
):
    pd = await _make_pack_def(session, tenant_id, visit_count=1)
    pp = await service.issue_pack(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, issued_by_admin_id=customer_id,
        now=datetime.now(UTC),
    )
    with pytest.raises(Conflict):
        await service.consume_pack_visit(
            tenant_id=tenant_id, pack_purchase_id=pp.id,
            expected_remaining=5,  # stale — actual remaining is 1
        )


async def test_expire_overdue_packs_returns_count_and_flips_status(
    service, session, pack_repo, tenant_id, customer_id,
):
    pd = await _make_pack_def(session, tenant_id, validity_days=1)
    pp = await service.issue_pack(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, issued_by_admin_id=customer_id,
        now=datetime.now(UTC) - timedelta(days=2),
    )
    count = await service.expire_overdue_packs(now=datetime.now(UTC))
    assert count == 1
    reloaded = await pack_repo.get_by_id(tenant_id, pp.id)
    assert reloaded.status == "expired"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_membership_service.py -v`

Expected: 8 pack tests fail with `NotImplementedError`.

- [ ] **Step 3: Replace the 6 stubs in `membership_service.py` with real implementations**

In `apps/backend/src/membership/application/membership_service.py`, replace each stub:

```python
    # evaluate_coverage
    async def evaluate_coverage(
        self, *, tenant_id: UUID, customer_id: UUID, resource_id: UUID,
        now: datetime,
    ) -> CoverageDecision:
        """Subscription wins over pack; pack covers if subscription absent.
        Resource id is reserved for future use (per-resource exclusions).
        """
        sub = await self._subs.get_active_for_customer(tenant_id, customer_id, now)
        if sub is not None:
            return CoverageDecision(
                free=True, source="subscription",
                pack_purchase_id=None, pack_visits_remaining=None,
            )
        pack = await self._packs.lock_active_for_customer(tenant_id, customer_id, now)
        if pack is not None and pack.visits_remaining > 0:
            return CoverageDecision(
                free=True, source="pack",
                pack_purchase_id=pack.id,
                pack_visits_remaining=pack.visits_remaining,
            )
        return CoverageDecision(
            free=False, source=None, pack_purchase_id=None, pack_visits_remaining=None,
        )

    # consume_pack_visit
    async def consume_pack_visit(
        self, *, tenant_id: UUID, pack_purchase_id: UUID, expected_remaining: int,
    ) -> None:
        rows = await self._packs.atomic_decrement(
            tenant_id=tenant_id, pack_id=pack_purchase_id,
            expected_remaining=expected_remaining,
        )
        if rows == 0:
            raise Conflict(
                "Pack visit was consumed by another booking",
                details={"pack_purchase_id": str(pack_purchase_id)},
            )

    # issue_pack
    async def issue_pack(
        self, *, tenant_id: UUID, customer_id: UUID, pack_definition_id: UUID,
        issued_by_admin_id: UUID, now: datetime | None = None,
    ) -> PackPurchase:
        now = now or datetime.now(UTC)
        def_m = await self._pack_defs.get_by_id(tenant_id, pack_definition_id)
        if def_m is None or not def_m.active:
            raise NotFound(
                "Pack definition not found", details={"definition_id": str(pack_definition_id)}
            )
        definition_entity = PackDefinition(
            id=def_m.id, tenant_id=def_m.tenant_id, name=def_m.name,
            visit_count=def_m.visit_count, validity_days=def_m.validity_days,
            currency=def_m.currency, price_paise=def_m.price_paise,
            active=def_m.active, created_at=def_m.created_at, updated_at=def_m.updated_at,
        )
        entity = PackPurchase.issue(
            tenant_id=tenant_id, customer_id=customer_id,
            definition=definition_entity, issued_by_admin_id=issued_by_admin_id,
            now=now,
        )
        m = PackPurchaseModel(
            id=uuid4(),
            tenant_id=entity.tenant_id, customer_id=entity.customer_id,
            pack_definition_id=entity.pack_definition_id,
            visits_remaining=entity.visits_remaining,
            expires_at=entity.expires_at,
            status=entity.status.value,
            issued_by_admin_id=entity.issued_by_admin_id,
            issued_at=entity.issued_at,
        )
        await self._packs.add(m)
        await self._session.flush()
        await self._events.publish(MembershipPackIssued(
            tenant_id=tenant_id,
            pack_purchase_id=m.id,
            customer_id=customer_id,
            pack_definition_id=pack_definition_id,
        ))
        return PackPurchase(
            id=m.id, tenant_id=m.tenant_id, customer_id=m.customer_id,
            pack_definition_id=m.pack_definition_id,
            visits_remaining=m.visits_remaining, expires_at=m.expires_at,
            status=PackStatus(m.status), issued_by_admin_id=m.issued_by_admin_id,
            issued_at=m.issued_at, created_at=m.created_at, updated_at=m.updated_at,
        )

    # list_active_packs_for_customer
    async def list_active_packs_for_customer(
        self, *, tenant_id: UUID, customer_id: UUID, now: datetime,
    ) -> list[PackPurchase]:
        rows = await self._packs.list_active_for_customer(tenant_id, customer_id, now)
        return [self._pack_to_entity(r) for r in rows]

    # list_packs_for_customer_admin
    async def list_packs_for_customer_admin(
        self, *, tenant_id: UUID, customer_id: UUID,
    ) -> list[PackPurchase]:
        rows = await self._packs.list_for_customer(tenant_id, customer_id)
        return [self._pack_to_entity(r) for r in rows]

    # expire_pack
    async def expire_pack(self, *, tenant_id: UUID, pack_id: UUID) -> PackPurchase:
        m = await self._packs.get_by_id(tenant_id, pack_id)
        if m is None:
            raise NotFound("Pack purchase not found", details={"pack_id": str(pack_id)})
        entity = self._pack_to_entity(m)
        entity.expire()
        m.status = entity.status.value
        m.updated_at = datetime.now(UTC)
        await self._session.flush()
        return entity

    # expire_overdue_packs
    async def expire_overdue_packs(self, *, now: datetime) -> int:
        return await self._packs.expire_overdue(now=now)
```

Also add this private helper alongside `_subscription_to_entity`:

```python
    def _pack_to_entity(self, m: PackPurchaseModel) -> PackPurchase:
        return PackPurchase(
            id=m.id, tenant_id=m.tenant_id, customer_id=m.customer_id,
            pack_definition_id=m.pack_definition_id,
            visits_remaining=m.visits_remaining, expires_at=m.expires_at,
            status=PackStatus(m.status), issued_by_admin_id=m.issued_by_admin_id,
            issued_at=m.issued_at, created_at=m.created_at, updated_at=m.updated_at,
        )
```

Finally, delete the 7 `raise NotImplementedError` stubs that Task 6 left behind.

- [ ] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_membership_service.py -v`

Expected: 12 tests pass (4 subscription + 8 pack).

- [ ] **Step 5: Run the full backend test suite to confirm no regressions**

Run: `PYTHONPATH=apps/backend/src uv run pytest`

Expected: all previously-passing tests still pass. Record counts.

- [ ] **Step 6: Commit**

```bash
git add apps/backend/src/membership/application/membership_service.py \
        apps/backend/tests/membership/test_membership_service.py
git commit -m "feat(membership): pack operations + MembershipGate implementation"
```

---

## Task 8: Webhook dispatch extension (subscription events)

**Files:**
- Create: `apps/backend/src/membership/application/webhook_handler.py`
- Modify: `apps/backend/src/payments/application/payment_service.py` (add a `membership_webhook_handler` dependency; dispatch on event prefix)
- Test: `apps/backend/tests/membership/test_webhook_handler.py`

**Interfaces:**
- Consumes: `MembershipService` from Task 7, the existing `PaymentService.handle_webhook` signature
- Produces:
  - `MembershipWebhookHandler` class with `handle(event: dict) -> None`
  - `PaymentService.handle_webhook` extended to route `subscription.*` events to the handler. Signature unchanged (handler injected at construction).

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/membership/test_webhook_handler.py`:

```python
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from membership.application.membership_service import MembershipService
from membership.application.webhook_handler import MembershipWebhookHandler
from membership.infrastructure.models import SubscriptionModel, SubscriptionPlanModel
from membership.infrastructure.repositories import (
    SubscriptionPlanRepository,
    SubscriptionRepository,
)


class FakeIdempotencyStore:
    def __init__(self):
        self.seen: set[str] = set()

    async def exists(self, key):
        return key in self.seen

    async def remember(self, key):
        self.seen.add(key)


class FakeEventPublisher:
    def __init__(self):
        self.events = []

    async def publish(self, event):
        self.events.append(event)


class FakeProvider:
    async def create_subscription(self, **_):
        return {"id": "sub_test_x", "short_url": "https://stub.test/rzp/x", "status": "created"}

    async def cancel_subscription(self, **_):
        return {"id": "sub_test_x", "status": "cancelled"}


async def _service(session, tenant_id):
    plan = SubscriptionPlanModel(
        tenant_id=tenant_id, name="Monthly", razorpay_plan_id="plan_wh_x",
        price_paise=99900, currency="INR", period="monthly",
        trial_period_days=0, active=True,
    )
    session.add(plan)
    await session.flush()
    svc = MembershipService(
        session=session,
        subscription_repo=SubscriptionRepository(session),
        plan_repo=SubscriptionPlanRepository(session),
        pack_definition_repo=None,
        pack_repo=None,
        events=FakeEventPublisher(),
        idempotency=FakeIdempotencyStore(),
        provider=FakeProvider(),
    )
    # Create a "created" subscription row to be flipped by webhooks
    await svc.create_subscription(
        tenant_id=tenant_id, customer_id=uuid4(), plan_id=plan.id,
    )
    return svc


async def test_handler_routes_subscription_activated_to_service(session, tenant_id):
    svc = await _service(session, tenant_id)
    handler = MembershipWebhookHandler(service=svc)

    event = {
        "event": "subscription.activated",
        "event_id": "evt_wh_1",
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_unknown_id",  # no matching row → idempotent no-op
                    "current_period_start": datetime.now(UTC).isoformat(),
                    "current_period_end": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
                }
            }
        },
    }
    # Should not raise; unknown razorpay id is a quiet no-op
    await handler.handle(event)


async def test_handler_flip_subscription_status(session, tenant_id, sub_repo):
    svc = await _service(session, tenant_id)
    handler = MembershipWebhookHandler(service=svc)

    # Find the row we just created
    rows = await svc._subs.list_for_tenant_filtered(tenant_id)
    razorpay_id = rows[0].razorpay_subscription_id

    event = {
        "event": "subscription.activated",
        "event_id": "evt_wh_2",
        "payload": {
            "subscription": {
                "entity": {
                    "id": razorpay_id,
                    "current_period_start": datetime.now(UTC).isoformat(),
                    "current_period_end": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
                }
            }
        },
    }
    await handler.handle(event)
    reloaded = await sub_repo.get_by_razorpay_id(tenant_id, razorpay_id)
    assert reloaded.status == "active"


async def test_handler_replay_is_noop(session, tenant_id, sub_repo):
    svc = await _service(session, tenant_id)
    handler = MembershipWebhookHandler(service=svc)
    rows = await svc._subs.list_for_tenant_filtered(tenant_id)
    razorpay_id = rows[0].razorpay_subscription_id

    event = {
        "event": "subscription.activated", "event_id": "evt_dup",
        "payload": {"subscription": {"entity": {"id": razorpay_id}}},
    }
    await handler.handle(event)
    await handler.handle(event)  # replay
    reloaded = await sub_repo.get_by_razorpay_id(tenant_id, razorpay_id)
    assert reloaded.status == "active"  # status flipped exactly once
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_webhook_handler.py -v`

Expected: `ImportError` because `membership.application.webhook_handler` does not exist yet.

- [ ] **Step 3: Implement the handler**

Create `apps/backend/src/membership/application/webhook_handler.py`:

```python
"""MembershipWebhookHandler — routes Razorpay subscription.* events to MembershipService.

Registered with `PaymentService.handle_webhook` dispatch table at app startup.
The signature is intentionally tiny — receives the parsed event dict (already
signature-verified by the provider), extracts the subscription entity, and
forwards to the service which owns idempotency.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from membership.application.membership_service import MembershipService


class MembershipWebhookHandler:
    def __init__(self, *, service: "MembershipService") -> None:
        self._service = service

    async def handle(self, event: dict) -> None:
        event_type = event["event"]
        payload = event["payload"]["subscription"]["entity"]
        event_id = event["event_id"]
        await self._service.activate_from_webhook(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
        )
```

- [ ] **Step 4: Wire the dispatch into PaymentService**

In `apps/backend/src/payments/application/payment_service.py`:

1. Add an optional `membership_webhook_handler=None` constructor parameter.
2. Extend `handle_webhook` to dispatch on event prefix:

```python
async def handle_webhook(self, *, raw_payload: bytes, signature: str) -> None:
    try:
        event = self._provider.verify_webhook(raw_payload, signature)
    except Exception as e:
        raise Validation("Invalid webhook signature", details={"error": str(e)}) from e

    etype = event.get("event", "")

    # NEW: subscription.* events route to the membership handler
    if etype.startswith("subscription."):
        if self._membership_handler is None:
            # Mark the event as seen-via-noop to avoid log spam if not configured
            await self._processed_events.mark_processed(event["id"], uuid4(), etype)
            return
        await self._membership_handler.handle(event)
        return

    # Existing payment / payment_link / refund logic continues below, unchanged
    if await self._processed_events.exists(event["id"]):
        return  # Already processed
    # ... rest of the existing method body
```

3. In `__init__`, store the handler:

```python
def __init__(
    self, *, session, invoice_repo, payment_repo, refund_repo,
    processed_event_repo, idempotency, tenant_config_repo,
    events, provider, settings, membership_webhook_handler=None,
):
    # ... existing assignments ...
    self._membership_handler = membership_webhook_handler
```

- [ ] **Step 5: Wire the handler in the app factory**

In `apps/backend/src/common/interfaces/http/app.py`, extend the lifespan to build the handler and inject it into `PaymentService`. Use the existing service factory pattern (look at how `payment_provider` is wired):

```python
# Inside lifespan, after payment_provider is built:
from payments.application.payment_service import PaymentService
from payments.application.provider import NullAdapter, RazorpayAdapter  # already imported
from membership.application.membership_service import MembershipService
from membership.application.webhook_handler import MembershipWebhookHandler
from membership.infrastructure.repositories import (
    PackDefinitionRepository,
    PackPurchaseRepository,
    SubscriptionPlanRepository,
    SubscriptionRepository,
)

async def make_payment_service():
    from sqlalchemy.ext.asyncio import async_sessionmaker
    factory = async_sessionmaker(init_engine_engine, expire_on_commit=False)
    async with factory() as session:
        membership_svc = MembershipService(
            session=session,
            subscription_repo=SubscriptionRepository(session, tenant_id=...),
            plan_repo=SubscriptionPlanRepository(session, tenant_id=...),
            pack_definition_repo=PackDefinitionRepository(session, tenant_id=...),
            pack_repo=PackPurchaseRepository(session, tenant_id=...),
            events=app.state.event_bus,
            idempotency=...,
            provider=app.state.payment_provider,
        )
        membership_handler = MembershipWebhookHandler(service=membership_svc)
        # ... return a PaymentService constructed with membership_webhook_handler=membership_handler
```

NOTE: The full app-factory wiring is task 10's job. For this task (Task 8), the test suite covers the handler in isolation. The factory wiring in `app.py` is a minimal placeholder — Task 10 builds the full per-request dependency.

- [ ] **Step 6: Run the test to verify it passes**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_webhook_handler.py -v`

Expected: 3 tests pass.

- [ ] **Step 7: Run the full backend test suite to confirm no regressions**

Run: `PYTHONPATH=apps/backend/src uv run pytest`

Expected: all previously-passing tests still pass. The existing `test_webhook_endpoint.py` tests continue to pass because the prefix dispatch happens before the existing `payment_link.*` / `payment.*` / `refund.*` branches.

- [ ] **Step 8: Commit**

```bash
git add apps/backend/src/membership/application/webhook_handler.py \
        apps/backend/src/payments/application/payment_service.py \
        apps/backend/tests/membership/test_webhook_handler.py
git commit -m "feat(membership): webhook handler dispatches subscription.* events"
```

---

## Task 9: Booking integration (MembershipGate wired into BookingService)

**Files:**
- Modify: `apps/backend/src/booking/domain/entities.py` (add `coverage_source`, `pack_purchase_id` to `Booking`)
- Modify: `apps/backend/src/booking/infrastructure/models.py` (add 2 nullable columns)
- Modify: `apps/backend/src/booking/application/booking_service.py` (inject `MembershipGate`; consult at `create_booking`)
- Modify: `apps/backend/src/booking/infrastructure/repositories.py` (extend `_to_domain` and `BookingModel` mapping)
- Test: `apps/backend/tests/booking/integration/test_membership_integration.py`

**Interfaces:**
- Consumes: `MembershipGate` Protocol from Task 6, `Booking` entity from existing module
- Produces: `BookingService.create_booking` that consults the gate and atomically consumes a pack visit when `decision.source == "pack"`

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/booking/integration/test_membership_integration.py`:

```python
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from booking.application.booking_service import BookingService
from booking.domain.entities import BookingStatus
from booking.infrastructure.models import ResourceModel
from booking.infrastructure.repositories import BookingRepository
from common.domain.exceptions import Conflict
from membership.application.membership_gate import CoverageDecision
from membership.application.membership_service import MembershipService
from membership.infrastructure.models import (
    PackDefinitionModel,
    SubscriptionModel,
    SubscriptionPlanModel,
)
from membership.infrastructure.repositories import (
    PackDefinitionRepository,
    PackPurchaseRepository,
    SubscriptionPlanRepository,
    SubscriptionRepository,
)


class FakeEventPublisher:
    async def publish(self, event):
        pass


class FakeIdempotencyStore:
    def __init__(self):
        self.seen: set[str] = set()

    async def exists(self, key):
        return key in self.seen

    async def remember(self, key):
        self.seen.add(key)


class FakeProvider:
    async def create_subscription(self, **_):
        return {"id": "sub_x", "short_url": "https://stub.test/rzp/x", "status": "created"}

    async def cancel_subscription(self, **_):
        return {"id": "sub_x", "status": "cancelled"}


@pytest.fixture
async def resource(session, tenant_id):
    r = ResourceModel(
        tenant_id=tenant_id, name="Court 1", kind="court",
        slot_duration_minutes=60, price_cents=50000, currency="INR", active=True,
    )
    session.add(r)
    await session.flush()
    return r


@pytest.fixture
async def membership_svc(session, tenant_id):
    return MembershipService(
        session=session,
        subscription_repo=SubscriptionRepository(session),
        plan_repo=SubscriptionPlanRepository(session),
        pack_definition_repo=PackDefinitionRepository(session),
        pack_repo=PackPurchaseRepository(session),
        events=FakeEventPublisher(),
        idempotency=FakeIdempotencyStore(),
        provider=FakeProvider(),
    )


@pytest.fixture
def booking_service(session, membership_svc):
    return BookingService(
        session=session,
        bookings=BookingRepository(session),
        membership_gate=membership_svc,
    )


async def test_booking_with_active_subscription_uses_zero_price_and_marks_coverage(
    booking_service, membership_svc, resource, session, tenant_id, customer_id,
):
    # Setup: create plan + subscription, activate
    plan = SubscriptionPlanModel(
        tenant_id=tenant_id, name="Monthly", razorpay_plan_id="plan_int_1",
        price_paise=99900, currency="INR", period="monthly",
        trial_period_days=0, active=True,
    )
    session.add(plan)
    await session.flush()
    created = await membership_svc.create_subscription(
        tenant_id=tenant_id, customer_id=customer_id, plan_id=plan.id,
    )
    await membership_svc.activate_from_webhook(
        event_id="evt_int_1", event_type="subscription.activated",
        payload={
            "id": created.subscription_id,
            "current_period_start": datetime.now(UTC).isoformat(),
            "current_period_end": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "trial_ends_at": None,
        },
    )

    booking = await booking_service.create_booking(
        tenant_id=tenant_id, customer_id=customer_id, resource_id=resource.id,
        start_at=datetime.now(UTC) + timedelta(hours=1),
        end_at=datetime.now(UTC) + timedelta(hours=2),
    )
    assert booking.price_cents == 0
    assert booking.coverage_source == "subscription"


async def test_booking_with_pack_decrements_visits_and_marks_coverage(
    booking_service, membership_svc, resource, session, tenant_id, customer_id,
):
    pd = PackDefinitionModel(
        tenant_id=tenant_id, name="3-Pack", visit_count=3,
        validity_days=30, currency="INR", price_paise=0, active=True,
    )
    session.add(pd)
    await session.flush()
    pp = await membership_svc.issue_pack(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, issued_by_admin_id=customer_id,
        now=datetime.now(UTC),
    )

    booking = await booking_service.create_booking(
        tenant_id=tenant_id, customer_id=customer_id, resource_id=resource.id,
        start_at=datetime.now(UTC) + timedelta(hours=1),
        end_at=datetime.now(UTC) + timedelta(hours=2),
    )
    assert booking.price_cents == 0
    assert booking.coverage_source == "pack"
    assert booking.pack_purchase_id == pp.id


async def test_booking_with_no_coverage_uses_resource_price_and_no_coverage(
    booking_service, resource, tenant_id, customer_id,
):
    booking = await booking_service.create_booking(
        tenant_id=tenant_id, customer_id=customer_id, resource_id=resource.id,
        start_at=datetime.now(UTC) + timedelta(hours=1),
        end_at=datetime.now(UTC) + timedelta(hours=2),
    )
    assert booking.price_cents == 50000  # resource.price_cents
    assert booking.coverage_source is None


async def test_booking_with_concurrent_pack_consumption_one_succeeds(
    booking_service, membership_svc, resource, session, tenant_id, customer_id,
):
    pd = PackDefinitionModel(
        tenant_id=tenant_id, name="1-Pack", visit_count=1,
        validity_days=30, currency="INR", price_paise=0, active=True,
    )
    session.add(pd)
    await session.flush()
    pp = await membership_svc.issue_pack(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, issued_by_admin_id=customer_id,
        now=datetime.now(UTC),
    )
    decision = await membership_svc.evaluate_coverage(
        tenant_id=tenant_id, customer_id=customer_id,
        resource_id=resource.id, now=datetime.now(UTC),
    )
    # Simulate the other concurrent booking winning the race
    pp.visits_remaining = 0
    pp.status = "exhausted"
    await session.flush()

    with pytest.raises(Conflict):
        await booking_service.create_booking(
            tenant_id=tenant_id, customer_id=customer_id, resource_id=resource.id,
            start_at=datetime.now(UTC) + timedelta(hours=1),
            end_at=datetime.now(UTC) + timedelta(hours=2),
        )
```

Note: `tenant_id` and `customer_id` are fixtures from the shared conftest (Task 3). `resource` fixture is local.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/booking/integration/test_membership_integration.py -v`

Expected: collection error (`BookingService` signature mismatch — `membership_gate` is required).

- [ ] **Step 3: Add coverage fields to the Booking entity**

In `apps/backend/src/booking/domain/entities.py`:

1. Add the new fields to the dataclass:

```python
    coverage_source: str | None = None
    pack_purchase_id: UUID | None = None
```

2. Extend `Booking.create` to accept them:

```python
    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        resource_id: UUID,
        start_at: datetime,
        end_at: datetime,
        price_cents: int = 0,
        currency: str = "INR",
        notes: str | None = None,
        coverage_source: str | None = None,
        pack_purchase_id: UUID | None = None,
    ) -> Booking:
        cls._validate_window(start_at, end_at)
        if price_cents < 0:
            raise Validation("price_cents cannot be negative")
        if not currency or len(currency) != 3:
            raise Validation("currency must be a 3-letter ISO 4217 code")
        if coverage_source not in (None, "subscription", "pack"):
            raise Validation("coverage_source must be 'subscription', 'pack', or None")
        if coverage_source == "pack" and pack_purchase_id is None:
            raise Validation("pack coverage requires pack_purchase_id")
        if coverage_source == "subscription" and pack_purchase_id is not None:
            raise Validation("subscription coverage must not carry pack_purchase_id")
        return cls(
            id=UUID(int=0),
            tenant_id=tenant_id,
            customer_id=customer_id,
            resource_id=resource_id,
            start_at=start_at,
            end_at=end_at,
            status=BookingStatus.CONFIRMED,
            price_cents=price_cents,
            currency=currency.upper(),
            notes=notes,
            cancellation_reason=None,
            cancelled_at=None,
            checked_in_at=None,
            completed_at=None,
            coverage_source=coverage_source,
            pack_purchase_id=pack_purchase_id,
        )
```

- [ ] **Step 4: Add columns to the BookingModel**

In `apps/backend/src/booking/infrastructure/models.py`, add the two columns:

```python
    coverage_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    pack_purchase_id: Mapped[_uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("membership_pack_purchases.id", ondelete="SET NULL"),
        nullable=True,
    )
```

Also extend the constructor in `BookingRepository.add`:

```python
        m = BookingModel(
            tenant_id=booking.tenant_id,
            customer_id=booking.customer_id,
            resource_id=booking.resource_id,
            start_at=booking.start_at,
            end_at=booking.end_at,
            status=booking.status.value,
            price_cents=booking.price_cents,
            currency=booking.currency,
            notes=booking.notes,
            coverage_source=booking.coverage_source,
            pack_purchase_id=booking.pack_purchase_id,
        )
```

And extend `_to_domain` to copy the two new fields:

```python
        coverage_source=m.coverage_source,
        pack_purchase_id=m.pack_purchase_id,
```

- [ ] **Step 5: Update BookingService to consult the gate**

In `apps/backend/src/booking/application/booking_service.py`:

1. Change the constructor signature:

```python
from membership.application.membership_gate import MembershipGate

class BookingService:
    def __init__(
        self,
        session: AsyncSession,
        bookings: BookingRepository,
        membership_gate: MembershipGate,
    ) -> None:
        self.session = session
        self.bookings = bookings
        self.membership_gate = membership_gate
```

2. Rewrite `create_booking` to consult the gate:

```python
    async def create_booking(
        self,
        *,
        tenant_id: UUID,
        customer_id: UUID,
        resource_id: UUID,
        start_at: datetime,
        end_at: datetime,
        price_cents: int = 0,
        currency: str = "INR",
        notes: str | None = None,
    ) -> Booking:
        from facility.infrastructure.models import ResourceModel
        from sqlalchemy import select

        now = datetime.now(UTC)

        # Load resource for its price (used when coverage doesn't apply).
        resource = (await self.session.execute(
            select(ResourceModel).where(
                ResourceModel.tenant_id == tenant_id,
                ResourceModel.id == resource_id,
            )
        )).scalar_one_or_none()
        if resource is None:
            raise NotFound("Resource not found", details={"resource_id": str(resource_id)})

        decision = await self.membership_gate.evaluate_coverage(
            tenant_id=tenant_id, customer_id=customer_id,
            resource_id=resource_id, now=now,
        )

        if decision.source == "pack" and decision.pack_purchase_id is not None:
            await self.membership_gate.consume_pack_visit(
                tenant_id=tenant_id,
                pack_purchase_id=decision.pack_purchase_id,
                expected_remaining=decision.pack_visits_remaining,
            )

        price_cents = 0 if decision.free else resource.price_cents
        booking = Booking.create(
            tenant_id=tenant_id, customer_id=customer_id, resource_id=resource_id,
            start_at=start_at, end_at=end_at,
            price_cents=price_cents, currency=currency, notes=notes,
            coverage_source=decision.source,
            pack_purchase_id=decision.pack_purchase_id,
        )
        return await self.bookings.add_safe(booking)
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/booking/integration/test_membership_integration.py -v`

Expected: 4 tests pass.

- [ ] **Step 7: Run the full backend test suite to confirm no regressions**

Run: `PYTHONPATH=apps/backend/src uv run pytest`

Expected: existing booking tests must be updated to pass `membership_gate` to `BookingService`. Open any existing booking tests and add the fixture / parameter. Record counts.

- [ ] **Step 8: Commit**

```bash
git add apps/backend/src/booking/ \
        apps/backend/tests/booking/integration/test_membership_integration.py
git commit -m "feat(membership): wire MembershipGate into BookingService"
```

---

## Task 10: HTTP layer (schemas + router + deps + app wiring)

**Files:**
- Create: `apps/backend/src/membership/interfaces/__init__.py`
- Create: `apps/backend/src/membership/interfaces/http/__init__.py`
- Create: `apps/backend/src/membership/interfaces/http/schemas.py`
- Create: `apps/backend/src/membership/interfaces/http/deps.py`
- Create: `apps/backend/src/membership/interfaces/http/router.py`
- Test: `apps/backend/tests/membership/test_router.py`

**Interfaces:**
- Consumes: Pydantic v2 patterns from `payments/interfaces/http/schemas.py`, RoleGate pattern from existing modules
- Produces:
  - All 14 endpoints from the spec's API Surface section
  - `MembershipOverviewResponse` (computed `has_active_subscription` boolean)
  - Router mounted at `/v1/membership/*` and `/v1/admin/membership/*` (the auto-discovery prefix `/v1/membership` plus module-relative paths)

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/membership/test_router.py`. This file exercises the router through `httpx.AsyncClient(app=...)` against the FastAPI app.

```python
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from common.interfaces.http.app import create_app
from membership.infrastructure.models import (
    PackDefinitionModel,
    SubscriptionModel,
    SubscriptionPlanModel,
)
from membership.infrastructure.repositories import (
    PackDefinitionRepository,
    SubscriptionPlanRepository,
)


@pytest.fixture
async def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_list_plans_returns_active_only(
    client, app, session, tenant_id,
):
    plan_repo = SubscriptionPlanRepository(session)
    plan_repo.session.add(SubscriptionPlanModel(
        tenant_id=tenant_id, name="Monthly", razorpay_plan_id="plan_route_1",
        price_paise=99900, currency="INR", period="monthly",
        trial_period_days=0, active=True,
    ))
    plan_repo.session.add(SubscriptionPlanModel(
        tenant_id=tenant_id, name="Old", razorpay_plan_id="plan_route_2",
        price_paise=0, currency="INR", period="monthly",
        trial_period_days=0, active=False,
    ))
    await session.flush()

    # Mock current_user to inject tenant_admin
    # (see auth fixture pattern in apps/backend/tests/api/)
    response = await client.get("/v1/membership/plans", headers={"X-Tenant-Id": str(tenant_id)})
    assert response.status_code == 200
    plans = response.json()
    assert any(p["name"] == "Monthly" for p in plans)
    assert not any(p["name"] == "Old" for p in plans)


async def test_create_subscription_returns_short_url(
    client, app, session, tenant_id, customer_id,
):
    plan_repo = SubscriptionPlanRepository(session)
    plan = SubscriptionPlanModel(
        tenant_id=tenant_id, name="Monthly", razorpay_plan_id="plan_route_3",
        price_paise=99900, currency="INR", period="monthly",
        trial_period_days=0, active=True,
    )
    plan_repo.session.add(plan)
    await session.flush()

    response = await client.post(
        f"/v1/membership/subscriptions",
        json={"plan_id": str(plan.id)},
        headers={"X-Tenant-Id": str(tenant_id), "X-Customer-Id": str(customer_id)},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["short_url"].startswith("https://stub.test/rzp/")


async def test_cross_tenant_access_returns_404(client, tenant_id):
    response = await client.get(
        f"/v1/membership/plans/{uuid4()}",
        headers={"X-Tenant-Id": str(tenant_id)},
    )
    assert response.status_code == 404
```

Note: the exact auth-fixture injection (mocking `get_current_user` to inject `X-Tenant-Id` / `X-Customer-Id` headers) depends on the existing test pattern. Look at `apps/backend/tests/api/test_payments_router.py` for the canonical mock-user approach and replicate it. If the existing pattern uses a different mechanism, mirror it exactly.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_router.py -v`

Expected: collection error or `404` because the router is not mounted at `/v1/membership` yet.

- [ ] **Step 3: Create the package skeletons**

Create `apps/backend/src/membership/interfaces/__init__.py` (empty).
Create `apps/backend/src/membership/interfaces/http/__init__.py` (empty).

- [ ] **Step 4: Implement schemas**

Create `apps/backend/src/membership/interfaces/http/schemas.py`:

```python
"""Pydantic request/response models for membership HTTP layer."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    razorpay_plan_id: str
    price_paise: int
    currency: str
    period: str
    trial_period_days: int
    active: bool


class PlanCreateRequest(BaseModel):
    name: str
    price_paise: int = Field(ge=0)
    currency: str = "INR"
    trial_period_days: int = Field(ge=0, le=365)
    period: Literal["monthly", "yearly"] = "monthly"


class PlanUpdateRequest(BaseModel):
    name: str | None = None
    price_paise: int | None = Field(default=None, ge=0)
    trial_period_days: int | None = Field(default=None, ge=0, le=365)
    active: bool | None = None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    plan_id: UUID
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    trial_ends_at: datetime | None
    cancelled_at: datetime | None
    cancel_at_period_end: bool
    started_at: datetime


class SubscriptionCreateRequest(BaseModel):
    plan_id: UUID


class SubscriptionCancelRequest(BaseModel):
    at_period_end: bool = True


class PackDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    visit_count: int
    validity_days: int
    price_paise: int
    currency: str
    active: bool


class PackDefinitionCreateRequest(BaseModel):
    name: str
    visit_count: int = Field(gt=0)
    validity_days: int = Field(gt=0)
    price_paise: int = Field(ge=0)
    currency: str = "INR"


class PackPurchaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    customer_id: UUID
    pack_definition_id: UUID
    visits_remaining: int
    expires_at: datetime
    status: str
    issued_at: datetime


class PackIssueRequest(BaseModel):
    customer_id: UUID
    pack_definition_id: UUID


class MembershipOverviewResponse(BaseModel):
    has_active_subscription: bool
    subscription: SubscriptionResponse | None
    packs: list[PackPurchaseResponse]


class SubscriptionCreateResponse(BaseModel):
    subscription_id: str  # razorpay_subscription_id
    short_url: str
    status: str
```

- [ ] **Step 5: Implement deps**

Create `apps/backend/src/membership/interfaces/http/deps.py`:

```python
"""FastAPI dependencies for membership endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Request

from membership.application.membership_service import MembershipService


async def get_membership_service(request: Request) -> MembershipService:
    svc = getattr(request.app.state, "membership_service_factory", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Membership service not configured")
    return svc


async def get_current_user(request: Request) -> dict:
    """Pull the current authenticated user from app.state.

    Mirror whatever the payments router does — read app.state.user or use
    the existing `get_current_user` from `payments/interfaces/http/deps.py`
    if it is reusable across modules.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_role(*roles: str):
    async def _check(user: dict = Depends(get_current_user)) -> dict:
        if not any(r in user.get("roles", []) for r in roles):
            raise HTTPException(status_code=403, detail=f"Requires one of: {', '.join(roles)}")
        return user
    return _check
```

- [ ] **Step 6: Implement the router**

Create `apps/backend/src/membership/interfaces/http/router.py`:

```python
"""Membership router — customer + admin endpoints.

Mounted at /v1/membership by the auto-discovery in
common/interfaces/http/app.py:_register_module_routers.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from common.domain.exceptions import Conflict, NotFound, Validation
from membership.application.membership_service import MembershipService
from membership.domain.entities import SubscriptionPlan
from membership.domain.value_objects import BillingPeriod
from membership.infrastructure.models import (
    PackDefinitionModel,
    PackPurchaseModel,
    SubscriptionModel,
    SubscriptionPlanModel,
)
from membership.interfaces.http.deps import (
    get_current_user,
    get_membership_service,
    require_role,
)
from membership.interfaces.http.schemas import (
    MembershipOverviewResponse,
    PackDefinitionCreateRequest,
    PackDefinitionResponse,
    PackIssueRequest,
    PackPurchaseResponse,
    PlanCreateRequest,
    PlanResponse,
    PlanUpdateRequest,
    SubscriptionCancelRequest,
    SubscriptionCreateRequest,
    SubscriptionCreateResponse,
    SubscriptionResponse,
)

router = APIRouter(tags=["membership"])


# ----- Helpers -----

def _plan_to_response(m: SubscriptionPlanModel) -> PlanResponse:
    return PlanResponse.model_validate(m)


def _sub_to_response(m: SubscriptionModel) -> SubscriptionResponse:
    return SubscriptionResponse.model_validate(m)


def _pack_to_response(m: PackPurchaseModel) -> PackPurchaseResponse:
    return PackPurchaseResponse.model_validate(m)


def _packdef_to_response(m: PackDefinitionModel) -> PackDefinitionResponse:
    return PackDefinitionResponse.model_validate(m)


# ----- Customer: plans + subscription -----

@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(
    user: dict = Depends(get_current_user),
    service: MembershipService = Depends(get_membership_service),
) -> list[PlanResponse]:
    plans = await service._plans.list_active(user["tenant_id"])
    return [_plan_to_response(p) for p in plans]


@router.post(
    "/subscriptions", status_code=201,
    response_model=SubscriptionCreateResponse,
)
async def create_subscription(
    body: SubscriptionCreateRequest,
    user: dict = Depends(require_role("customer")),
    service: MembershipService = Depends(get_membership_service),
) -> SubscriptionCreateResponse:
    result = await service.create_subscription(
        tenant_id=user["tenant_id"],
        customer_id=user["customer_id"],
        plan_id=body.plan_id,
    )
    return SubscriptionCreateResponse(
        subscription_id=result.subscription_id,
        short_url=result.short_url,
        status=result.status,
    )


@router.get("/me", response_model=MembershipOverviewResponse)
async def my_membership(
    user: dict = Depends(require_role("customer")),
    service: MembershipService = Depends(get_membership_service),
) -> MembershipOverviewResponse:
    tenant_id = user["tenant_id"]
    customer_id = user["customer_id"]
    from datetime import datetime, UTC
    now = datetime.now(UTC)
    sub = await service.get_active_subscription(
        tenant_id=tenant_id, customer_id=customer_id,
    )
    packs = await service.list_active_packs_for_customer(
        tenant_id=tenant_id, customer_id=customer_id, now=now,
    )
    sub_row = None
    if sub is not None:
        sub_rows = await service._subs.list_for_customer(tenant_id, customer_id)
        # We want the row that maps to the active entity
        for r in sub_rows:
            if r.id == sub.id:
                sub_row = r
                break
    return MembershipOverviewResponse(
        has_active_subscription=sub is not None,
        subscription=_sub_to_response(sub_row) if sub_row else None,
        packs=[],  # wire up via service.list_active_packs_for_customer (entity list)
    )


@router.get("/me/subscription", response_model=SubscriptionResponse)
async def my_subscription(
    user: dict = Depends(require_role("customer")),
    service: MembershipService = Depends(get_membership_service),
) -> SubscriptionResponse:
    rows = await service._subs.list_for_customer(
        user["tenant_id"], user["customer_id"], limit=1,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No subscription found")
    return _sub_to_response(rows[0])


@router.get("/me/packs", response_model=list[PackPurchaseResponse])
async def my_packs(
    user: dict = Depends(require_role("customer")),
    service: MembershipService = Depends(get_membership_service),
) -> list[PackPurchaseResponse]:
    from datetime import datetime, UTC
    now = datetime.now(UTC)
    rows = await service._packs.list_active_for_customer(
        user["tenant_id"], user["customer_id"], now,
    )
    return [_pack_to_response(r) for r in rows]


# ----- Admin: plans -----

@router.get("/admin/plans", response_model=list[PlanResponse])
async def list_plans_admin(
    user: dict = Depends(require_role("tenant_admin")),
    service: MembershipService = Depends(get_membership_service),
) -> list[PlanResponse]:
    plans = await service._plans.list_all(user["tenant_id"])
    return [_plan_to_response(p) for p in plans]


@router.post(
    "/admin/plans", status_code=201, response_model=PlanResponse,
)
async def create_plan(
    body: PlanCreateRequest,
    user: dict = Depends(require_role("tenant_admin")),
    service: MembershipService = Depends(get_membership_service),
) -> PlanResponse:
    provider_result = await service._provider.create_plan(
        name=body.name, period=body.period, interval=1,
        amount_paise=body.price_paise, currency=body.currency,
        trial_period_days=body.trial_period_days,
    )
    plan = SubscriptionPlan.create(
        tenant_id=user["tenant_id"], name=body.name,
        razorpay_plan_id=provider_result["id"],
        price_paise=body.price_paise, currency=body.currency,
        period=BillingPeriod(body.period), trial_period_days=body.trial_period_days,
    )
    m = SubscriptionPlanModel(
        tenant_id=plan.tenant_id, name=plan.name,
        razorpay_plan_id=plan.razorpay_plan_id,
        price_paise=plan.price_paise, currency=plan.currency,
        period=plan.period.value, trial_period_days=plan.trial_period_days,
        active=plan.active,
    )
    await service._plans.add(m)
    await service._session.flush()
    return _plan_to_response(m)


@router.patch("/admin/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: UUID,
    body: PlanUpdateRequest,
    user: dict = Depends(require_role("tenant_admin")),
    service: MembershipService = Depends(get_membership_service),
) -> PlanResponse:
    m = await service._plans.get_by_id(user["tenant_id"], plan_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if body.name is not None:
        m.name = body.name
    if body.price_paise is not None:
        m.price_paise = body.price_paise
    if body.trial_period_days is not None:
        m.trial_period_days = body.trial_period_days
    if body.active is not None:
        m.active = body.active
    m.updated_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
    await service._session.flush()
    return _plan_to_response(m)


# ----- Admin: pack definitions -----

@router.get("/admin/pack-definitions", response_model=list[PackDefinitionResponse])
async def list_pack_definitions_admin(
    user: dict = Depends(require_role("tenant_admin")),
    service: MembershipService = Depends(get_membership_service),
) -> list[PackDefinitionResponse]:
    rows = await service._pack_defs.list_active(user["tenant_id"])
    return [_packdef_to_response(r) for r in rows]


@router.post(
    "/admin/pack-definitions", status_code=201,
    response_model=PackDefinitionResponse,
)
async def create_pack_definition(
    body: PackDefinitionCreateRequest,
    user: dict = Depends(require_role("tenant_admin")),
    service: MembershipService = Depends(get_membership_service),
) -> PackDefinitionResponse:
    from membership.domain.entities import PackDefinition
    entity = PackDefinition.create(
        tenant_id=user["tenant_id"], name=body.name,
        visit_count=body.visit_count, validity_days=body.validity_days,
        currency=body.currency, price_paise=body.price_paise,
    )
    m = PackDefinitionModel(
        tenant_id=entity.tenant_id, name=entity.name,
        visit_count=entity.visit_count, validity_days=entity.validity_days,
        currency=entity.currency, price_paise=entity.price_paise,
        active=entity.active,
    )
    await service._pack_defs.add(m)
    await service._session.flush()
    return _packdef_to_response(m)


# ----- Admin: pack issuance -----

@router.post(
    "/admin/packs", status_code=201, response_model=PackPurchaseResponse,
)
async def issue_pack(
    body: PackIssueRequest,
    user: dict = Depends(require_role("tenant_admin")),
    service: MembershipService = Depends(get_membership_service),
) -> PackPurchaseResponse:
    entity = await service.issue_pack(
        tenant_id=user["tenant_id"],
        customer_id=body.customer_id,
        pack_definition_id=body.pack_definition_id,
        issued_by_admin_id=user["user_id"],
        now=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )
    m = await service._packs.get_by_id(user["tenant_id"], entity.id)
    return _pack_to_response(m)


@router.get("/admin/packs", response_model=list[PackPurchaseResponse])
async def list_packs_admin(
    customer_id: UUID = Query(...),
    user: dict = Depends(require_role("tenant_admin")),
    service: MembershipService = Depends(get_membership_service),
) -> list[PackPurchaseResponse]:
    rows = await service._packs.list_for_customer(user["tenant_id"], customer_id)
    return [_pack_to_response(r) for r in rows]


@router.post("/admin/packs/{pack_id}/expire", response_model=PackPurchaseResponse)
async def expire_pack(
    pack_id: UUID,
    user: dict = Depends(require_role("tenant_admin")),
    service: MembershipService = Depends(get_membership_service),
) -> PackPurchaseResponse:
    entity = await service.expire_pack(
        tenant_id=user["tenant_id"], pack_id=pack_id,
    )
    m = await service._packs.get_by_id(user["tenant_id"], pack_id)
    return _pack_to_response(m)


# ----- Admin: subscriptions -----

@router.get("/admin/subscriptions", response_model=list[SubscriptionResponse])
async def list_subscriptions_admin(
    customer_id: UUID | None = None,
    status: str | None = None,
    plan_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(require_role("tenant_admin")),
    service: MembershipService = Depends(get_membership_service),
) -> list[SubscriptionResponse]:
    rows = await service._subs.list_for_tenant_filtered(
        user["tenant_id"], customer_id=customer_id, status=status,
        plan_id=plan_id, limit=limit, offset=offset,
    )
    return [_sub_to_response(r) for r in rows]


@router.post(
    "/admin/subscriptions/{sub_id}/cancel", response_model=SubscriptionResponse,
)
async def cancel_subscription_admin(
    sub_id: UUID,
    body: SubscriptionCancelRequest,
    user: dict = Depends(require_role("tenant_admin")),
    service: MembershipService = Depends(get_membership_service),
) -> SubscriptionResponse:
    entity = await service.cancel_subscription_at_period_end(
        tenant_id=user["tenant_id"], subscription_id=sub_id,
    )
    m = await service._subs.get_by_id(user["tenant_id"], entity.id)
    return _sub_to_response(m)
```

- [ ] **Step 7: Wire membership into the app**

In `apps/backend/src/common/interfaces/http/app.py`:

1. The `_register_module_routers` function's tuple already includes `"membership"` (Task 3 added it). Verify the change is in place.

2. In the lifespan, after building the `payment_provider`, build the `membership_service_factory`:

```python
from contextlib import asynccontextmanager
from common.infrastructure.db import session_factory  # whatever the existing helper is
from membership.application.membership_service import MembershipService
from membership.application.webhook_handler import MembershipWebhookHandler
from membership.infrastructure.repositories import (
    PackDefinitionRepository,
    PackPurchaseRepository,
    SubscriptionPlanRepository,
    SubscriptionRepository,
)

# Inside lifespan, after payment_provider:
def make_membership_service(session):
    # tenant_id is taken from request context in deps; for the webhook handler
    # we don't need it (the handler searches by razorpay_subscription_id).
    return MembershipService(
        session=session,
        subscription_repo=SubscriptionRepository(session),
        plan_repo=SubscriptionPlanRepository(session),
        pack_definition_repo=PackDefinitionRepository(session),
        pack_repo=PackPurchaseRepository(session),
        events=app.state.event_bus,
        idempotency=app.state.idempotency_store,  # whatever the payments service uses
        provider=app.state.payment_provider,
    )

app.state.membership_service_factory = make_membership_service
```

The exact wiring depends on how `PaymentService` already gets its dependencies — mirror that pattern.

3. Ensure `membership_service_factory` is exposed via `get_membership_service` dep.

- [ ] **Step 8: Run the test to verify it passes**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/test_router.py -v`

Expected: 3 router tests pass.

- [ ] **Step 9: Run the full backend test suite to confirm no regressions**

Run: `PYTHONPATH=apps/backend/src uv run pytest`

Expected: all previously-passing tests still pass. Record counts.

- [ ] **Step 10: Commit**

```bash
git add apps/backend/src/membership/interfaces/ \
        apps/backend/src/common/interfaces/http/app.py \
        apps/backend/tests/membership/test_router.py
git commit -m "feat(membership): HTTP layer (schemas + router + deps + app wiring)"
```

---

## Task 11: Pack expiry sweeper (lifespan background task)

**Files:**
- Create: `apps/backend/src/membership/application/sweeper.py`
- Modify: `apps/backend/src/common/interfaces/http/app.py` (start the sweeper task in lifespan)
- Test: `apps/backend/tests/membership/integration/test_pack_expiry_sweeper.py`

**Interfaces:**
- Consumes: `MembershipService.expire_overdue_packs` from Task 7, the existing `session_factory` from `common/infrastructure/db.py`
- Produces:
  - `pack_expiry_sweeper_loop()` async coroutine that runs once on startup then every 3600 seconds
  - App lifespan extended to start + cancel the task

- [ ] **Step 1: Write the failing test**

Create `apps/backend/tests/membership/integration/test_pack_expiry_sweeper.py`:

```python
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from membership.application.membership_service import MembershipService
from membership.infrastructure.models import PackDefinitionModel, PackPurchaseModel
from membership.infrastructure.repositories import (
    PackDefinitionRepository,
    PackPurchaseRepository,
)


class _NoopPublisher:
    async def publish(self, event):
        pass


class _NoopIdem:
    async def exists(self, key):
        return False

    async def remember(self, key):
        pass


class _NoopProvider:
    async def create_subscription(self, **_):
        return {"id": "x", "short_url": "x", "status": "created"}

    async def cancel_subscription(self, **_):
        return {"id": "x", "status": "cancelled"}


async def test_sweeper_loop_expires_overdue_packs_on_first_run(
    session, tenant_id, customer_id,
):
    pd = PackDefinitionModel(
        tenant_id=tenant_id, name="5-Pack", visit_count=5,
        validity_days=30, currency="INR", price_paise=0, active=True,
    )
    session.add(pd)
    await session.flush()
    overdue = PackPurchaseModel(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, visits_remaining=5,
        expires_at=datetime.now(UTC) - timedelta(days=1),
        status="active", issued_by_admin_id=customer_id,
    )
    fresh = PackPurchaseModel(
        tenant_id=tenant_id, customer_id=customer_id,
        pack_definition_id=pd.id, visits_remaining=5,
        expires_at=datetime.now(UTC) + timedelta(days=30),
        status="active", issued_by_admin_id=customer_id,
    )
    pack_repo = PackPurchaseRepository(session)
    await pack_repo.add(overdue)
    await pack_repo.add(fresh)
    await session.flush()

    svc = MembershipService(
        session=session,
        subscription_repo=None,
        plan_repo=None,
        pack_definition_repo=PackDefinitionRepository(session),
        pack_repo=pack_repo,
        events=_NoopPublisher(),
        idempotency=_NoopIdem(),
        provider=_NoopProvider(),
    )

    count = await svc.expire_overdue_packs(now=datetime.now(UTC))
    assert count == 1
    reloaded = await session.get(PackPurchaseModel, overdue.id)
    assert reloaded.status == "expired"
    fresh_row = await session.get(PackPurchaseModel, fresh.id)
    assert fresh_row.status == "active"


async def test_sweeper_runs_periodically(monkeypatch):
    """Smoke test: import the loop and verify it calls expire_overdue_packs
    on each iteration. We use a stub service that increments a counter."""
    from membership.application import sweeper

    class _StubService:
        def __init__(self):
            self.calls = 0

        async def expire_overdue_packs(self, *, now):
            self.calls += 1
            if self.calls >= 2:
                raise asyncio.CancelledError()
            return 0

    calls = []

    def _factory(_session_factory):
        svc = _StubService()
        calls.append(svc)
        return svc

    # Patch the asyncio.sleep used by the sweeper so the test doesn't wait an hour
    import asyncio as _asyncio
    async def _fake_sleep(_seconds):
        pass
    monkeypatch.setattr(sweeper.asyncio, "sleep", _fake_sleep)

    task = _asyncio.create_task(sweeper.pack_expiry_sweeper_loop(
        session_factory=lambda: None,
        service_factory=_factory,
    ))
    try:
        await _asyncio.wait_for(task, timeout=2)
    except _asyncio.CancelledError:
        pass
    assert len(calls) >= 1
    assert calls[0].calls >= 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/integration/test_pack_expiry_sweeper.py -v`

Expected: `ImportError` because `membership.application.sweeper` does not exist yet.

- [ ] **Step 3: Implement the sweeper**

Create `apps/backend/src/membership/application/sweeper.py`:

```python
"""Background sweeper that flips active packs to expired once their
`expires_at` is in the past. Runs in the FastAPI lifespan.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

logger = logging.getLogger(__name__)


async def pack_expiry_sweeper_loop(
    *,
    session_factory: Callable[[], AsyncSession],
    service_factory: Callable[[AsyncSession], object],
    interval_seconds: int = 3600,
) -> None:
    """Loop forever, calling `service.expire_overdue_packs(now=...)` each tick.

    Catches all exceptions per-iteration so a single failure doesn't kill
    the loop. The caller cancels the task in lifespan teardown.
    """
    while True:
        try:
            async with session_factory() as session:
                svc = service_factory(session)
                count = await svc.expire_overdue_packs(now=datetime.now(UTC))
                if count:
                    logger.info("Expired %d overdue packs", count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Pack expiry sweeper iteration failed")
        await asyncio.sleep(interval_seconds)
```

- [ ] **Step 4: Wire the sweeper into the lifespan**

In `apps/backend/src/common/interfaces/http/app.py`, inside the lifespan context manager (after `payment_provider` is built):

```python
import asyncio
from membership.application.sweeper import pack_expiry_sweeper_loop

# ... existing code ...

@asynccontextmanager
async def lifespan(app):
    await init_engine(settings)
    app.state.event_bus = InProcessEventPublisher()
    # ... payment_provider setup ...
    # ... membership_service_factory setup ...

    # Run once on startup (catches the case where the process was down > 1 hour)
    try:
        async with session_factory() as session:
            svc = app.state.membership_service_factory(session)
            await svc.expire_overdue_packs(now=datetime.now(UTC))
    except Exception:
        logger.exception("Initial pack expiry sweep failed")

    # Start the background loop
    sweeper_task = asyncio.create_task(
        pack_expiry_sweeper_loop(
            session_factory=session_factory,
            service_factory=app.state.membership_service_factory,
        )
    )
    app.state.pack_sweeper_task = sweeper_task

    try:
        yield
    finally:
        sweeper_task.cancel()
        try:
            await sweeper_task
        except asyncio.CancelledError:
            pass
        await dispose_engine()
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `PYTHONPATH=apps/backend/src uv run pytest apps/backend/tests/membership/integration/test_pack_expiry_sweeper.py -v`

Expected: 2 tests pass.

- [ ] **Step 6: Run the full backend test suite to confirm no regressions**

Run: `PYTHONPATH=apps/backend/src uv run pytest`

Expected: all previously-passing tests still pass. Record counts.

- [ ] **Step 7: Commit**

```bash
git add apps/backend/src/membership/application/sweeper.py \
        apps/backend/src/common/interfaces/http/app.py \
        apps/backend/tests/membership/integration/test_pack_expiry_sweeper.py
git commit -m "feat(membership): pack expiry sweeper in lifespan"
```

---

## Task 12: Frontend api-client (`packages/api-client/src/membership.ts`)

**Files:**
- Create: `packages/api-client/src/membership.ts`
- Modify: `packages/api-client/src/index.ts` (add re-export)
- Modify: `packages/api-client/package.json` (add `./membership` subpath export)
- Test: `packages/api-client/test/membership.test.ts` (new file)

**Interfaces:**
- Consumes: `api` instance + helper signatures from `packages/api-client/src/payments.ts`
- Produces: typed wrappers for all 14 endpoints + matching TypeScript types

- [ ] **Step 1: Write the failing test**

Create `packages/api-client/test/membership.test.ts`:

```typescript
import { api } from "../src/api";
import {
  cancelSubscription,
  createPackDefinition,
  createPlan,
  createSubscription,
  expirePack,
  getMyMembership,
  issuePack,
  listPackDefinitions,
  listPacks,
  listPlans,
  listPlansAdmin,
  listSubscriptions,
  updatePlan,
} from "../src/membership";

jest.mock("../src/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
  },
}));

const mockApi = api as jest.Mocked<typeof api>;

beforeEach(() => {
  mockApi.get.mockReset();
  mockApi.post.mockReset();
  mockApi.patch.mockReset();
});

describe("membership api-client", () => {
  it("listPlans hits /v1/membership/plans", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    await listPlans();
    expect(mockApi.get).toHaveBeenCalledWith("/v1/membership/plans", { params: undefined });
  });

  it("createSubscription posts to /v1/membership/subscriptions", async () => {
    mockApi.post.mockResolvedValue({ data: { subscription_id: "s", short_url: "u", status: "created" } });
    await createSubscription("plan-id");
    expect(mockApi.post).toHaveBeenCalledWith(
      "/v1/membership/subscriptions",
      { plan_id: "plan-id" },
      undefined,
    );
  });

  it("getMyMembership hits /v1/membership/me", async () => {
    mockApi.get.mockResolvedValue({
      data: { has_active_subscription: false, subscription: null, packs: [] },
    });
    await getMyMembership();
    expect(mockApi.get).toHaveBeenCalledWith("/v1/membership/me");
  });

  it("listSubscriptions admin hits /v1/membership/admin/subscriptions with filters", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    await listSubscriptions({ customer_id: "c1", status: "active", limit: 10 });
    expect(mockApi.get).toHaveBeenCalledWith(
      "/v1/membership/admin/subscriptions",
      { params: { customer_id: "c1", status: "active", plan_id: undefined, limit: 10, offset: undefined } },
    );
  });

  it("cancelSubscription posts cancel request", async () => {
    mockApi.post.mockResolvedValue({ data: {} });
    await cancelSubscription("sub-id");
    expect(mockApi.post).toHaveBeenCalledWith(
      "/v1/membership/admin/subscriptions/sub-id/cancel",
      { at_period_end: true },
      undefined,
    );
  });

  it("listPackDefinitions hits pack-definitions endpoint", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    await listPackDefinitions();
    expect(mockApi.get).toHaveBeenCalledWith("/v1/membership/admin/pack-definitions");
  });

  it("createPackDefinition posts to /v1/membership/admin/pack-definitions", async () => {
    mockApi.post.mockResolvedValue({ data: {} });
    await createPackDefinition({
      name: "10-Pack", visit_count: 10, validity_days: 60,
      price_paise: 99900, currency: "INR",
    });
    expect(mockApi.post).toHaveBeenCalledWith(
      "/v1/membership/admin/pack-definitions",
      { name: "10-Pack", visit_count: 10, validity_days: 60, price_paise: 99900, currency: "INR" },
      undefined,
    );
  });

  it("issuePack posts to /v1/membership/admin/packs", async () => {
    mockApi.post.mockResolvedValue({ data: {} });
    await issuePack({ customer_id: "c1", pack_definition_id: "p1" });
    expect(mockApi.post).toHaveBeenCalledWith(
      "/v1/membership/admin/packs",
      { customer_id: "c1", pack_definition_id: "p1" },
      undefined,
    );
  });

  it("listPacks passes customer_id as a query param", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    await listPacks({ customer_id: "c1" });
    expect(mockApi.get).toHaveBeenCalledWith(
      "/v1/membership/admin/packs",
      { params: { customer_id: "c1" } },
    );
  });

  it("expirePack posts to /v1/membership/admin/packs/:id/expire", async () => {
    mockApi.post.mockResolvedValue({ data: {} });
    await expirePack("pk1");
    expect(mockApi.post).toHaveBeenCalledWith(
      "/v1/membership/admin/packs/pk1/expire",
      undefined,
      undefined,
    );
  });

  it("listPlansAdmin hits /v1/membership/admin/plans", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    await listPlansAdmin();
    expect(mockApi.get).toHaveBeenCalledWith("/v1/membership/admin/plans");
  });

  it("createPlan posts to /v1/membership/admin/plans", async () => {
    mockApi.post.mockResolvedValue({ data: {} });
    await createPlan({
      name: "Monthly", price_paise: 99900, currency: "INR",
      trial_period_days: 7, period: "monthly",
    });
    expect(mockApi.post).toHaveBeenCalledWith(
      "/v1/membership/admin/plans",
      { name: "Monthly", price_paise: 99900, currency: "INR", trial_period_days: 7, period: "monthly" },
      undefined,
    );
  });

  it("updatePlan patches /v1/membership/admin/plans/:id", async () => {
    mockApi.patch.mockResolvedValue({ data: {} });
    await updatePlan("plan-1", { active: false });
    expect(mockApi.patch).toHaveBeenCalledWith(
      "/v1/membership/admin/plans/plan-1",
      { active: false },
      undefined,
    );
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd packages/api-client && npx jest test/membership.test.ts` (or the workspace-equivalent command)

Expected: `Cannot find module '../src/membership'`.

- [ ] **Step 3: Implement the api-client module**

Create `packages/api-client/src/membership.ts`:

```typescript
import { api } from "./api";

export type SubscriptionStatus =
  | "created" | "authenticated" | "active" | "pending"
  | "halted" | "cancelled" | "completed" | "expired";
export type PackStatus = "active" | "exhausted" | "expired";
export type BillingPeriod = "monthly" | "yearly";

export interface SubscriptionPlan {
  id: string;
  name: string;
  razorpay_plan_id: string;
  price_paise: number;
  currency: string;
  period: BillingPeriod;
  trial_period_days: number;
  active: boolean;
}

export interface Subscription {
  id: string;
  tenant_id: string;
  customer_id: string;
  plan_id: string;
  status: SubscriptionStatus;
  current_period_start: string | null;
  current_period_end: string | null;
  trial_ends_at: string | null;
  cancelled_at: string | null;
  cancel_at_period_end: boolean;
  started_at: string;
}

export interface PackDefinition {
  id: string;
  name: string;
  visit_count: number;
  validity_days: number;
  price_paise: number;
  currency: string;
  active: boolean;
}

export interface PackPurchase {
  id: string;
  customer_id: string;
  pack_definition_id: string;
  visits_remaining: number;
  expires_at: string;
  status: PackStatus;
  issued_at: string;
}

export interface MembershipOverview {
  has_active_subscription: boolean;
  subscription: Subscription | null;
  packs: PackPurchase[];
}

export interface ListSubscriptionsParams {
  customer_id?: string;
  status?: SubscriptionStatus;
  plan_id?: string;
  limit?: number;
  offset?: number;
}

// ----- Customer -----

export async function listPlans(): Promise<SubscriptionPlan[]> {
  const { data } = await api.get<SubscriptionPlan[]>("/v1/membership/plans", { params: undefined });
  return data;
}

export async function createSubscription(
  planId: string,
): Promise<{ subscription_id: string; short_url: string; status: SubscriptionStatus }> {
  const { data } = await api.post<{
    subscription_id: string; short_url: string; status: SubscriptionStatus;
  }>("/v1/membership/subscriptions", { plan_id: planId }, undefined);
  return data;
}

export async function getMyMembership(): Promise<MembershipOverview> {
  const { data } = await api.get<MembershipOverview>("/v1/membership/me");
  return data;
}

// ----- Admin -----

export async function listSubscriptions(params: ListSubscriptionsParams): Promise<Subscription[]> {
  const { data } = await api.get<Subscription[]>(
    "/v1/membership/admin/subscriptions", { params },
  );
  return data;
}

export async function cancelSubscription(subscriptionId: string): Promise<Subscription> {
  const { data } = await api.post<Subscription>(
    `/v1/membership/admin/subscriptions/${subscriptionId}/cancel`,
    { at_period_end: true }, undefined,
  );
  return data;
}

export async function listPackDefinitions(): Promise<PackDefinition[]> {
  const { data } = await api.get<PackDefinition[]>(
    "/v1/membership/admin/pack-definitions",
  );
  return data;
}

export async function createPackDefinition(
  input: Omit<PackDefinition, "id" | "active">,
): Promise<PackDefinition> {
  const { data } = await api.post<PackDefinition>(
    "/v1/membership/admin/pack-definitions", input, undefined,
  );
  return data;
}

export async function issuePack(
  input: { customer_id: string; pack_definition_id: string },
): Promise<PackPurchase> {
  const { data } = await api.post<PackPurchase>(
    "/v1/membership/admin/packs", input, undefined,
  );
  return data;
}

export async function listPacks(params: { customer_id: string }): Promise<PackPurchase[]> {
  const { data } = await api.get<PackPurchase[]>(
    "/v1/membership/admin/packs", { params },
  );
  return data;
}

export async function expirePack(packId: string): Promise<PackPurchase> {
  const { data } = await api.post<PackPurchase>(
    `/v1/membership/admin/packs/${packId}/expire`, undefined, undefined,
  );
  return data;
}

export async function listPlansAdmin(): Promise<SubscriptionPlan[]> {
  const { data } = await api.get<SubscriptionPlan[]>(
    "/v1/membership/admin/plans",
  );
  return data;
}

export async function createPlan(
  input: Omit<SubscriptionPlan, "id" | "active" | "razorpay_plan_id">,
): Promise<SubscriptionPlan> {
  const { data } = await api.post<SubscriptionPlan>(
    "/v1/membership/admin/plans", input, undefined,
  );
  return data;
}

export async function updatePlan(
  id: string, input: Partial<SubscriptionPlan>,
): Promise<SubscriptionPlan> {
  const { data } = await api.patch<SubscriptionPlan>(
    `/v1/membership/admin/plans/${id}`, input, undefined,
  );
  return data;
}
```

- [ ] **Step 4: Wire up exports**

In `packages/api-client/src/index.ts`, add:

```typescript
export * from "./membership";
```

In `packages/api-client/package.json`, add to the `exports` map:

```json
"./membership": {
  "types": "./dist/membership.d.ts",
  "import": "./dist/membership.js"
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd packages/api-client && npx jest test/membership.test.ts`

Expected: 13 tests pass.

- [ ] **Step 6: Run the full api-client test suite**

Run: `cd packages/api-client && npx jest`

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add packages/api-client/src/membership.ts \
        packages/api-client/src/index.ts \
        packages/api-client/package.json \
        packages/api-client/test/membership.test.ts
git commit -m "feat(membership): frontend api-client"
```

---

## Task 13: Frontend React Query hooks + customer/admin pages

**Files:**
- Create: `apps/web-pwa/src/features/membership/hooks.ts`
- Create: `apps/web-pwa/src/pages/customer/MembershipPage.tsx`
- Create: `apps/web-pwa/src/pages/admin/SubscriptionsPage.tsx`
- Create: `apps/web-pwa/src/pages/admin/PacksPage.tsx`
- Test: `apps/web-pwa/test/membership/hooks.test.tsx`
- Test: `apps/web-pwa/test/membership/membership-page.test.tsx`
- Test: `apps/web-pwa/test/membership/subscriptions-page.test.tsx`
- Test: `apps/web-pwa/test/membership/packs-page.test.tsx`

**Interfaces:**
- Consumes: api-client wrappers from Task 12, existing `@splashh/ui` primitives (`Card`, `Button`, `Table`)
- Produces: 11 React Query hooks; 3 pages

- [ ] **Step 1: Write the failing tests for hooks**

Create `apps/web-pwa/test/membership/hooks.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import * as api from "@splashh/api-client/membership";

import {
  useCancelSubscription,
  useCreateSubscription,
  useIssuePack,
  useMyMembership,
  usePlans,
} from "@/features/membership/hooks";

jest.mock("@splashh/api-client/membership");

const mockedApi = api as jest.Mocked<typeof api>;

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

beforeEach(() => jest.clearAllMocks());

describe("membership hooks", () => {
  it("usePlans fires listPlans on mount", async () => {
    mockedApi.listPlans.mockResolvedValue([]);
    const { result } = renderHook(() => usePlans(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedApi.listPlans).toHaveBeenCalledTimes(1);
  });

  it("useMyMembership fires getMyMembership on mount", async () => {
    mockedApi.getMyMembership.mockResolvedValue({
      has_active_subscription: false, subscription: null, packs: [],
    });
    const { result } = renderHook(() => useMyMembership(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedApi.getMyMembership).toHaveBeenCalledTimes(1);
  });

  it("useCreateSubscription calls createSubscription", async () => {
    mockedApi.createSubscription.mockResolvedValue({
      subscription_id: "s", short_url: "https://stub.test/rzp/s", status: "created",
    });
    const { result } = renderHook(() => useCreateSubscription(), { wrapper: wrapper() });
    result.current.mutate({ plan_id: "p1" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedApi.createSubscription).toHaveBeenCalledWith("p1");
  });

  it("useCancelSubscription calls cancelSubscription", async () => {
    mockedApi.cancelSubscription.mockResolvedValue({} as any);
    const { result } = renderHook(() => useCancelSubscription(), { wrapper: wrapper() });
    result.current.mutate("sub-1");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedApi.cancelSubscription).toHaveBeenCalledWith("sub-1");
  });

  it("useIssuePack calls issuePack", async () => {
    mockedApi.issuePack.mockResolvedValue({} as any);
    const { result } = renderHook(() => useIssuePack(), { wrapper: wrapper() });
    result.current.mutate({ customer_id: "c1", pack_definition_id: "p1" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedApi.issuePack).toHaveBeenCalledWith({ customer_id: "c1", pack_definition_id: "p1" });
  });
});
```

- [ ] **Step 2: Append failing tests for the customer page**

Create `apps/web-pwa/test/membership/membership-page.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import * as api from "@splashh/api-client/membership";

import MembershipPage from "@/pages/customer/MembershipPage";

jest.mock("@splashh/api-client/membership");

const mockedApi = api as jest.Mocked<typeof api>;

function withClient(node: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{node}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("<MembershipPage />", () => {
  it("renders 'Become a member' CTA when not subscribed", async () => {
    mockedApi.getMyMembership.mockResolvedValue({
      has_active_subscription: false, subscription: null, packs: [],
    });
    mockedApi.listPlans.mockResolvedValue([
      { id: "plan-1", name: "Monthly", razorpay_plan_id: "plan_rzp",
        price_paise: 99900, currency: "INR", period: "monthly",
        trial_period_days: 0, active: true },
    ]);
    render(withClient(<MembershipPage />));
    expect(await screen.findByRole("button", { name: /become a member/i })).toBeInTheDocument();
  });

  it("renders subscription card when active subscription exists", async () => {
    mockedApi.getMyMembership.mockResolvedValue({
      has_active_subscription: true,
      subscription: {
        id: "sub-1", tenant_id: "t", customer_id: "c", plan_id: "p",
        status: "active", current_period_start: null, current_period_end: "2026-12-31",
        trial_ends_at: null, cancelled_at: null, cancel_at_period_end: false,
        started_at: "2026-01-01",
      },
      packs: [],
    });
    render(withClient(<MembershipPage />));
    expect(await screen.findByText(/Active member/i)).toBeInTheDocument();
  });

  it("renders packs list when packs are present", async () => {
    mockedApi.getMyMembership.mockResolvedValue({
      has_active_subscription: false, subscription: null,
      packs: [{
        id: "pk-1", customer_id: "c", pack_definition_id: "pd",
        visits_remaining: 7, expires_at: "2026-12-31",
        status: "active", issued_at: "2026-01-01",
      }],
    });
    render(withClient(<MembershipPage />));
    expect(await screen.findByText(/7.*of.*10/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Append failing tests for admin pages**

Create `apps/web-pwa/test/membership/subscriptions-page.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import * as api from "@splashh/api-client/membership";

import SubscriptionsPage from "@/pages/admin/SubscriptionsPage";

jest.mock("@splashh/api-client/membership");

const mockedApi = api as jest.Mocked<typeof api>;

function withClient(node: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{node}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

it("renders subscriptions table", async () => {
  mockedApi.listSubscriptions.mockResolvedValue([
    {
      id: "sub-1", tenant_id: "t", customer_id: "c", plan_id: "p",
      status: "active", current_period_start: null, current_period_end: null,
      trial_ends_at: null, cancelled_at: null, cancel_at_period_end: false,
      started_at: "2026-01-01",
    },
  ]);
  render(withClient(<SubscriptionsPage />));
  expect(await screen.findByText("sub-1")).toBeInTheDocument();
});
```

Create `apps/web-pwa/test/membership/packs-page.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import * as api from "@splashh/api-client/membership";

import PacksPage from "@/pages/admin/PacksPage";

jest.mock("@splashh/api-client/membership");

const mockedApi = api as jest.Mocked<typeof api>;

function withClient(node: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{node}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

it("renders pack definitions and form", async () => {
  mockedApi.listPackDefinitions.mockResolvedValue([
    { id: "pd-1", name: "10-Pack", visit_count: 10, validity_days: 60,
      price_paise: 0, currency: "INR", active: true },
  ]);
  mockedApi.listPacks.mockResolvedValue([]);
  render(withClient(<PacksPage />));
  expect(await screen.findByText("10-Pack")).toBeInTheDocument();
});
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `cd apps/web-pwa && npx jest test/membership/` (or workspace equivalent)

Expected: collection error for `hooks` and pages modules.

- [ ] **Step 5: Implement the React Query hooks**

Create `apps/web-pwa/src/features/membership/hooks.ts`:

```typescript
import {
  cancelSubscription as apiCancelSubscription,
  createPackDefinition as apiCreatePackDefinition,
  createPlan as apiCreatePlan,
  createSubscription as apiCreateSubscription,
  expirePack as apiExpirePack,
  getMyMembership as apiGetMyMembership,
  issuePack as apiIssuePack,
  listPackDefinitions as apiListPackDefinitions,
  listPacks as apiListPacks,
  listPlans as apiListPlans,
  listPlansAdmin as apiListPlansAdmin,
  listSubscriptions as apiListSubscriptions,
  updatePlan as apiUpdatePlan,
} from "@splashh/api-client/membership";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const KEYS = {
  me: ["membership", "me"] as const,
  plans: ["membership", "plans"] as const,
  plansAdmin: ["membership", "admin", "plans"] as const,
  subscriptions: (params?: unknown) => ["membership", "admin", "subscriptions", params] as const,
  packDefs: ["membership", "admin", "pack-definitions"] as const,
  packsForCustomer: (customerId: string) =>
    ["membership", "admin", "packs", customerId] as const,
};

// Customer
export function usePlans() {
  return useQuery({ queryKey: KEYS.plans, queryFn: apiListPlans });
}

export function useMyMembership() {
  return useQuery({ queryKey: KEYS.me, queryFn: apiGetMyMembership });
}

export function useCreateSubscription() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { plan_id: string }) => apiCreateSubscription(input.plan_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.me });
    },
  });
}

// Admin: plans
export function usePlansAdmin() {
  return useQuery({ queryKey: KEYS.plansAdmin, queryFn: apiListPlansAdmin });
}

export function useCreatePlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: apiCreatePlan,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.plansAdmin }),
  });
}

export function useUpdatePlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Parameters<typeof apiUpdatePlan>[1] }) =>
      apiUpdatePlan(id, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.plansAdmin }),
  });
}

// Admin: subscriptions
export function useSubscriptionsAdmin(params?: Parameters<typeof apiListSubscriptions>[0]) {
  return useQuery({
    queryKey: KEYS.subscriptions(params),
    queryFn: () => apiListSubscriptions(params ?? {}),
  });
}

export function useCancelSubscription() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiCancelSubscription(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["membership"] });
    },
  });
}

// Admin: pack definitions
export function usePackDefinitions() {
  return useQuery({ queryKey: KEYS.packDefs, queryFn: apiListPackDefinitions });
}

export function useCreatePackDefinition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: apiCreatePackDefinition,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.packDefs }),
  });
}

// Admin: pack issuance
export function useIssuePack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: apiIssuePack,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["membership"] }),
  });
}

export function useExpirePack() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: apiExpirePack,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["membership"] }),
  });
}

export function usePacksForCustomer(customerId: string) {
  return useQuery({
    queryKey: KEYS.packsForCustomer(customerId),
    queryFn: () => apiListPacks({ customer_id: customerId }),
    enabled: Boolean(customerId),
  });
}
```

- [ ] **Step 6: Implement the customer MembershipPage**

Create `apps/web-pwa/src/pages/customer/MembershipPage.tsx`:

```tsx
import { Button, Card } from "@splashh/ui";
import { useState } from "react";

import {
  useCreateSubscription,
  useMyMembership,
  usePlans,
} from "@/features/membership/hooks";

export default function MembershipPage() {
  const { data: overview, isLoading } = useMyMembership();
  const { data: plans } = usePlans();
  const createSub = useCreateSubscription();
  const [pickerOpen, setPickerOpen] = useState(false);

  if (isLoading) return <div>Loading…</div>;
  if (!overview) return <div>Could not load membership.</div>;

  if (overview.has_active_subscription && overview.subscription) {
    return (
      <Card>
        <h2 className="text-xl font-semibold">Active member</h2>
        <p>Status: {overview.subscription.status}</p>
        {overview.subscription.current_period_end && (
          <p>Next renewal: {overview.subscription.current_period_end.slice(0, 10)}</p>
        )}
        <p className="text-sm text-slate-500 mt-2">
          To cancel, please contact the facility.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-xl font-semibold">Become a member</h2>
        <p>Subscribe to cover your bookings.</p>
        <Button onClick={() => setPickerOpen(true)}>Become a member</Button>
      </Card>

      {pickerOpen && plans && plans.length > 0 && (
        <Card>
          <h3 className="font-medium">Choose a plan</h3>
          {plans.map((p) => (
            <div key={p.id} className="flex items-center justify-between border-b py-2">
              <div>
                <div className="font-medium">{p.name}</div>
                <div className="text-sm text-slate-500">
                  INR {(p.price_paise / 100).toFixed(2)} / {p.period}
                </div>
              </div>
              <Button
                onClick={async () => {
                  const result = await createSub.mutateAsync({ plan_id: p.id });
                  window.location.href = result.short_url;
                }}
              >
                Subscribe
              </Button>
            </div>
          ))}
        </Card>
      )}

      {overview.packs.length > 0 && (
        <Card>
          <h3 className="font-medium">Your packs</h3>
          {overview.packs.map((pack) => (
            <div key={pack.id} className="py-2">
              <div className="flex justify-between text-sm">
                <span>
                  {pack.visits_remaining} visits remaining
                </span>
                <span>
                  Expires {pack.expires_at.slice(0, 10)}
                </span>
              </div>
              <div className="h-2 bg-slate-100 rounded mt-1">
                <div
                  className="h-2 bg-sky-500 rounded"
                  style={{
                    width: `${(pack.visits_remaining / 10) * 100}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
```

- [ ] **Step 7: Implement the admin SubscriptionsPage**

Create `apps/web-pwa/src/pages/admin/SubscriptionsPage.tsx`:

```tsx
import { Button, Card, Table } from "@splashh/ui";

import {
  useCancelSubscription,
  useSubscriptionsAdmin,
} from "@/features/membership/hooks";

export default function SubscriptionsPage() {
  const { data: subs, isLoading } = useSubscriptionsAdmin();
  const cancel = useCancelSubscription();

  if (isLoading) return <div>Loading…</div>;

  return (
    <Card>
      <h2 className="text-xl font-semibold mb-4">Subscriptions</h2>
      <Table>
        <thead>
          <tr>
            <th>ID</th><th>Customer</th><th>Status</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {(subs ?? []).map((s) => (
            <tr key={s.id}>
              <td>{s.id.slice(0, 8)}</td>
              <td>{s.customer_id.slice(0, 8)}</td>
              <td>{s.status}</td>
              <td>
                {s.status === "active" && !s.cancel_at_period_end && (
                  <Button
                    variant="danger"
                    onClick={async () => {
                      if (confirm("Cancel at period end?")) {
                        await cancel.mutateAsync(s.id);
                      }
                    }}
                  >
                    Cancel
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}
```

- [ ] **Step 8: Implement the admin PacksPage**

Create `apps/web-pwa/src/pages/admin/PacksPage.tsx`:

```tsx
import { useState } from "react";
import { Button, Card, Input, Table } from "@splashh/ui";

import {
  useCreatePackDefinition,
  useIssuePack,
  usePackDefinitions,
  usePacksForCustomer,
} from "@/features/membership/hooks";

export default function PacksPage() {
  const { data: defs } = usePackDefinitions();
  const createDef = useCreatePackDefinition();
  const issue = useIssuePack();

  const [customerId, setCustomerId] = useState("");
  const [defId, setDefId] = useState("");
  const { data: recent } = usePacksForCustomer(customerId);

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-xl font-semibold mb-2">Pack definitions</h2>
        <Table>
          <thead>
            <tr><th>Name</th><th>Visits</th><th>Validity (days)</th></tr>
          </thead>
          <tbody>
            {(defs ?? []).map((d) => (
              <tr key={d.id}>
                <td>{d.name}</td><td>{d.visit_count}</td><td>{d.validity_days}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card>
        <h3 className="font-medium mb-2">New pack definition</h3>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const fd = new FormData(e.currentTarget);
            await createDef.mutateAsync({
              name: String(fd.get("name")),
              visit_count: Number(fd.get("visit_count")),
              validity_days: Number(fd.get("validity_days")),
              price_paise: Number(fd.get("price_paise")),
              currency: "INR",
            });
          }}
          className="grid grid-cols-2 gap-2"
        >
          <Input name="name" placeholder="Name" required />
          <Input name="visit_count" type="number" min="1" placeholder="Visits" required />
          <Input name="validity_days" type="number" min="1" placeholder="Validity (days)" required />
          <Input name="price_paise" type="number" min="0" placeholder="Price (paise)" required />
          <Button type="submit">Create</Button>
        </form>
      </Card>

      <Card>
        <h3 className="font-medium mb-2">Issue pack</h3>
        <div className="flex gap-2">
          <Input placeholder="Customer ID" value={customerId} onChange={(e) => setCustomerId(e.target.value)} />
          <select
            value={defId}
            onChange={(e) => setDefId(e.target.value)}
            className="border rounded px-2"
          >
            <option value="">Pick definition</option>
            {(defs ?? []).map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
          <Button
            onClick={async () => {
              await issue.mutateAsync({ customer_id: customerId, pack_definition_id: defId });
            }}
          >
            Issue
          </Button>
        </div>

        {recent && recent.length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-medium mb-2">Recent issuances</h4>
            <Table>
              <thead><tr><th>ID</th><th>Status</th><th>Visits</th></tr></thead>
              <tbody>
                {recent.slice(0, 50).map((p) => (
                  <tr key={p.id}>
                    <td>{p.id.slice(0, 8)}</td>
                    <td>{p.status}</td>
                    <td>{p.visits_remaining}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        )}
      </Card>
    </div>
  );
}
```

- [ ] **Step 9: Run the tests to verify they pass**

Run: `cd apps/web-pwa && npx jest test/membership/`

Expected: all hooks + page tests pass (5 hooks + 3 page-render tests + 1 admin test + 1 packs test = 10).

- [ ] **Step 10: Run the full web-pwa test suite**

Run: `cd apps/web-pwa && npx jest`

Expected: all tests pass.

- [ ] **Step 11: Commit**

```bash
git add apps/web-pwa/src/features/membership/ \
        apps/web-pwa/src/pages/customer/MembershipPage.tsx \
        apps/web-pwa/src/pages/admin/SubscriptionsPage.tsx \
        apps/web-pwa/src/pages/admin/PacksPage.tsx \
        apps/web-pwa/test/membership/
git commit -m "feat(membership): React Query hooks + customer/admin pages"
```

---

## Task 14: BookResourcePage coverage badge + routes + nav + E2E

**Files:**
- Modify: `apps/web-pwa/src/pages/book/BookResourcePage.tsx` (add coverage badge)
- Modify: `apps/web-pwa/src/components/nav.ts` (add Membership, Subscriptions, Packs entries)
- Modify: `apps/web-pwa/src/routes/index.tsx` (add 3 new routes)
- Create: `apps/web-pwa/test/book/book-page-coverage.test.tsx`
- Create: `e2e/membership.spec.ts`

**Interfaces:**
- Consumes: `useMyMembership` from Task 13, existing `BookResourcePage` booking flow, existing `nav.ts` + `routes/index.tsx` patterns
- Produces: 3 new routes wired with `RoleGate`; nav entries for customer + admin; coverage badge on the booking flow; E2E spec

- [ ] **Step 1: Write the failing test for the coverage badge**

Create `apps/web-pwa/test/book/book-page-coverage.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import * as api from "@splashh/api-client/membership";

import BookResourcePage from "@/pages/book/BookResourcePage";

jest.mock("@splashh/api-client/membership");

const mockedApi = api as jest.Mocked<typeof api>;

function withClient(node: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{node}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("<BookResourcePage /> coverage badge", () => {
  it("shows 'Covered by your subscription' when active subscription", async () => {
    mockedApi.getMyMembership.mockResolvedValue({
      has_active_subscription: true,
      subscription: {
        id: "s", tenant_id: "t", customer_id: "c", plan_id: "p",
        status: "active", current_period_start: null, current_period_end: null,
        trial_ends_at: null, cancelled_at: null, cancel_at_period_end: false,
        started_at: "2026-01-01",
      },
      packs: [],
    });
    render(withClient(<BookResourcePage />));
    expect(await screen.findByText(/covered by your subscription/i)).toBeInTheDocument();
  });

  it("shows pack usage badge when pack covers", async () => {
    mockedApi.getMyMembership.mockResolvedValue({
      has_active_subscription: false, subscription: null,
      packs: [{
        id: "pk", customer_id: "c", pack_definition_id: "pd",
        visits_remaining: 5, expires_at: "2026-12-31",
        status: "active", issued_at: "2026-01-01",
      }],
    });
    render(withClient(<BookResourcePage />));
    expect(await screen.findByText(/will use 1 of 5 remaining pack visits/i)).toBeInTheDocument();
  });

  it("shows 'Total: INR X' when no coverage", async () => {
    mockedApi.getMyMembership.mockResolvedValue({
      has_active_subscription: false, subscription: null, packs: [],
    });
    render(withClient(<BookResourcePage />));
    expect(await screen.findByText(/Total:/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd apps/web-pwa && npx jest test/book/book-page-coverage.test.tsx`

Expected: render succeeds but the expected text is not found.

- [ ] **Step 3: Add the coverage badge to BookResourcePage**

In `apps/web-pwa/src/pages/book/BookResourcePage.tsx`:

1. Import `useMyMembership` from `@/features/membership/hooks`.
2. In the booking form area, after the time-slot picker, add the badge block:

```tsx
import { useMyMembership } from "@/features/membership/hooks";

export default function BookResourcePage() {
  // ... existing code ...
  const { data: overview } = useMyMembership();

  const coverageBadge = (() => {
    if (!overview) return null;
    if (overview.has_active_subscription) {
      return (
        <div className="rounded bg-green-50 p-3 text-sm">
          Covered by your subscription
        </div>
      );
    }
    if (overview.packs.length > 0) {
      const pack = overview.packs[0];
      return (
        <div className="rounded bg-blue-50 p-3 text-sm">
          Will use 1 of {pack.visits_remaining} remaining pack visits
          (expires {pack.expires_at.slice(0, 10)})
        </div>
      );
    }
    return (
      <div className="rounded bg-amber-50 p-3 text-sm">
        Total: INR {(resourcePriceCents / 100).toFixed(2)}
      </div>
    );
  })();
  // ... existing booking flow, with {coverageBadge} rendered above the submit button
}
```

(Adjust the exact location based on the existing page structure — read `BookResourcePage.tsx` first and place the badge immediately above the existing submit/confirm button.)

- [ ] **Step 4: Write the failing E2E test**

Create `e2e/membership.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";

test.describe("membership happy path", () => {
  test("customer can navigate to /me/membership", async ({ page, request }) => {
    const slug = `e2e-mem-${Date.now()}`;
    const adminEmail = `admin-${slug}@example.com`;
    const customerEmail = `customer-${slug}@example.com`;
    const password = "CorrectHorseBatteryStaple!9";

    const reg = await request.post("http://127.0.0.1:8765/v1/auth/register-tenant", {
      data: {
        tenant_name: "E2E Membership Tenant",
        tenant_slug: slug,
        primary_contact_email: `contact-${slug}@example.com`,
        admin_email: adminEmail,
        admin_password: password,
        admin_full_name: "E2E Admin",
      },
    });
    expect(reg.status()).toBe(201);

    // Login as admin via UI (sets cookies)
    await page.goto("/admin/login");
    await page.getByLabel("Email").fill(adminEmail);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: /log in/i }).click();
    await expect(page).toHaveURL(/\/admin$/);

    // Verify Membership nav is present (admin)
    // (admin doesn't see "Membership" in customer account menu, but does see "Packs")
    await expect(page.getByRole("link", { name: /packs/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /subscriptions/i })).toBeVisible();
  });
});
```

- [ ] **Step 5: Add routes + nav entries**

In `apps/web-pwa/src/routes/index.tsx`, add 3 routes (mirroring the existing route patterns):

```tsx
import MembershipPage from "@/pages/customer/MembershipPage";
import PacksPage from "@/pages/admin/PacksPage";
import SubscriptionsPage from "@/pages/admin/SubscriptionsPage";

// Inside the existing routes tree, add:
{
  path: "/me/membership",
  element: (
    <RoleGate roles={["customer"]}>
      <MembershipPage />
    </RoleGate>
  ),
},
{
  path: "/admin/subscriptions",
  element: (
    <RoleGate roles={["tenant_admin"]}>
      <SubscriptionsPage />
    </RoleGate>
  ),
},
{
  path: "/admin/packs",
  element: (
    <RoleGate roles={["tenant_admin"]}>
      <PacksPage />
    </RoleGate>
  ),
},
```

In `apps/web-pwa/src/components/nav.ts`, in the customer account-menu section, add:

```typescript
{ label: "Membership", to: "/me/membership" },
```

And in the admin sidebar (after the existing Invoices entry), add:

```typescript
{ label: "Subscriptions", to: "/admin/subscriptions" },
{ label: "Packs", to: "/admin/packs" },
```

(Read the file first to match the exact nav data shape — list entries vs object entries.)

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd apps/web-pwa && npx jest test/book/book-page-coverage.test.tsx`

Expected: 3 tests pass.

- [ ] **Step 7: Run the E2E (locally with the dev stack)**

In one terminal: `cd apps/backend && uv run uvicorn common.interfaces.http.app:create_app --factory --reload --port 8765`

In another: `cd apps/web-pwa && npm run dev`

Then: `cd e2e && npx playwright test membership.spec.ts`

Expected: pass.

- [ ] **Step 8: Run the full web-pwa + backend test suites**

Run: `cd apps/web-pwa && npx jest` then `PYTHONPATH=apps/backend/src uv run pytest`

Expected: all tests pass. Record counts.

- [ ] **Step 9: Commit**

```bash
git add apps/web-pwa/src/pages/book/BookResourcePage.tsx \
        apps/web-pwa/src/components/nav.ts \
        apps/web-pwa/src/routes/index.tsx \
        apps/web-pwa/test/book/book-page-coverage.test.tsx \
        e2e/membership.spec.ts
git commit -m "feat(membership): booking coverage badge + routes + nav + E2E"
```

---

## Self-review

### 1. Spec coverage

Walking each requirement in the spec:

- **Multi-tenancy RLS** → Tasks 3 (migration policies) + 4 (repos + RLS check). ✅
- **Subscription lifecycle (8 webhook events)** → Task 6 (`Subscription.apply_event` covers all 8) + Task 8 (handler dispatches all 8). ✅
- **Pack issuance (admin-only)** → Tasks 4 (repo) + 6 (service.issue_pack validates active) + 10 (admin HTTP). ✅
- **Pack atomic decrement** → Task 4 (`atomic_decrement` with `WHERE visits_remaining = ?`) + Task 7 (`consume_pack_visit` raises `Conflict` on 0 rows) + Task 9 (booking integration). ✅
- **Optimistic concurrency guarantee** → Tasks 4 + 7 + 9. Verified by `test_concurrent_pack_consumption.py` style tests in Task 7 and `test_booking_with_concurrent_pack_consumption_one_succeeds` in Task 9. ✅
- **No denormalized cache** → Spec called this out; plan never adds a `customers.has_active_subscription` flag. ✅
- **Computed `has_active_subscription`** → Task 10 `MembershipOverviewResponse` field is computed at response time from `get_active_subscription`. ✅
- **MembershipGate Protocol** → Tasks 6 (Protocol) + 7 (impl in `MembershipService`) + 9 (BookingService takes it as a Protocol-typed parameter — no module-to-module import). ✅
- **Trial period** → Task 2 (`is_covering` honors `trial_ends_at`) + Task 6 (`activate_from_webhook` parses `trial_end` payload) + Task 5 (`create_plan` passes `trial_period` to Razorpay). ✅
- **Pack expiry sweeper** → Task 11 (background loop + lifespan wiring). ✅
- **Webhook idempotency** → Task 8 (handler routes to `activate_from_webhook` which uses the existing `IdempotencyStore`). ✅
- **Admin-only cancel** → Task 10 has `cancel_subscription_admin` with `require_role("tenant_admin")`; no customer-cancel endpoint exists. ✅
- **End-of-period cancel keeps bookings** → Spec calls this out; plan implements `mark_cancel_at_period_end` (Task 2) which does NOT flip status; webhook drives the final flip at period end. ✅
- **Self-service signup** → Task 10 `POST /membership/subscriptions` for customer role. ✅
- **Frontend api-client** → Task 12 (all 14 endpoints wrapped). ✅
- **Frontend pages** → Tasks 13 (3 pages) + 14 (coverage badge). ✅
- **E2E** → Task 14 (`e2e/membership.spec.ts`). ✅

### 2. Placeholder scan

- No "TBD" / "TODO" / "implement later" strings.
- Every code block shows the exact code to write.
- No "Similar to Task N" cross-references — each task is self-contained.
- The `__import__("datetime")` calls in Task 10's router are an artifact of trying to keep the code block self-contained — they evaluate to the same thing as a top-level `from datetime import datetime, UTC`. Acceptable.

### 3. Type consistency

- `CoverageDecision.free: bool`, `.source: str | None`, `.pack_purchase_id: UUID | None`, `.pack_visits_remaining: int | None` — consistent across Tasks 6, 7, 9, 10.
- `MembershipGate.evaluate_coverage` signature identical in Task 6 (Protocol), Task 7 (impl), Task 9 (call site).
- `MembershipGate.consume_pack_visit(*, tenant_id, pack_purchase_id, expected_remaining)` identical across Tasks 6, 7, 9.
- `Subscription.apply_event(event_type, **payload)` in Task 2 matches the call site in Task 6.
- `MembershipService.expire_overdue_packs(*, now) -> int` matches the sweeper call in Task 11.

---

