# Membership Module v1 — Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a multi-tenant membership module that lets customers subscribe to a single monthly plan via Razorpay Subscriptions (hosted auth page) and lets admins issue prepaid visit packs. An active subscription or an active pack with visits remaining covers a booking — the booking flow skips invoice creation. The integration with `booking/` is through a small `MembershipGate` protocol, not module-to-module imports.

**Architecture:** A new `membership` backend module (`interfaces/http/` + `application/` + `domain/` + `infrastructure/`) sibling to `payments/`. Subscription state is sourced from Razorpay Subscriptions — the same webhook ingress used by payments (`POST /webhooks/razorpay`) dispatches `subscription.*` events to a new `MembershipWebhookHandler`. Pack issuance is admin-only (no Razorpay touch — packs are gifts/promos). Booking integration is via a `MembershipGate` protocol that `BookingService` consumes; pack consumption happens atomically in the booking transaction (optimistic-concurrency UPDATE-WHERE on `visits_remaining`). The frontend gains a customer `/me/membership` page (subscribe, view subscription, view packs) and two admin pages (`/admin/subscriptions`, `/admin/packs`), plus a coverage badge on the existing booking flow.

**Tech Stack:** Same as the rest of the backend — FastAPI, SQLAlchemy 2 (async) + Alembic, Pydantic v2, Razorpay Python SDK (`razorpay`). No new Python dependencies. No new npm dependencies. Frontend uses the same React 19 + react-router-dom + @tanstack/react-query + zustand stack.

---

## Workflow (binding for implementation)

- **Test-driven development (red-green-refactor).** Every line of production code is preceded by a failing test that proves the behavior. The cycle is RED → verify fail → GREEN → verify pass → REFACTOR → next. No production code without a failing test first. "Watch it fail" is mandatory — a test that passes on first run is a false positive.
- **Subagent-driven execution.** Implementation is dispatched as a series of fresh subagent tasks (one per task in the plan), with a task reviewer (spec compliance + code quality) after each, and a broad whole-branch review at the end. The controller does not edit code directly; it dispatches subagents and tracks results in a ledger.
- **Bite-sized tasks.** Each task in the implementation plan is the smallest unit that carries its own test cycle. Tasks fold setup, scaffolding, and configuration into the deliverable that needs them.
- **Frequent commits.** Each task ends with a green, reviewed commit. No mega-commits.
- **Verification before completion claims.** Every claim of "done" is backed by the test command's actual output, not by the implementer's recall. Show the command and the output.

---

## Global Constraints

- **Multi-tenancy:** every business table has `tenant_id UUID NOT NULL` and a corresponding Postgres RLS policy (`tenant_id = current_setting('app.tenant_id')::uuid`) on SELECT/INSERT/UPDATE/DELETE. The membership tables follow the same pattern as `payments/`. **Cross-tenant access returns 404, not 403** — never leak existence.
- **Audit columns:** every business table has `created_at` and `updated_at` timestamptz columns populated by the existing base mixin.
- **Money:** stored as `BIGINT` paise in DB (1 INR = 100 paise) and `int` paise in API + Razorpay payloads. Never floats. Currency code is a 3-char string; v1 supports **INR only**. The existing `Money` value object (`amount_paise: int`) is reused.
- **No card / UPI / banking data on our servers.** All Razorpay authentication and billing happens on Razorpay's hosted pages.
- **Logging:** never log full subscription/pack objects or Razorpay API responses. Log only `subscription_id`, `pack_purchase_id`, `razorpay_event_id`, and high-level status.
- **Errors:** never expose Razorpay SDK error details to API consumers; map to standard `common` exceptions (`Validation`, `Conflict`, `NotFound`, `ServiceUnavailable`).
- **Auth:** all `/membership/*` endpoints require an authenticated session. Customers see only their own subscription and packs; tenant_admin sees all in their tenant. Admin endpoints require `tenant_admin` role via `RoleGate(["tenant_admin"])`.
- **Webhook auth:** `/webhooks/razorpay` continues to require a valid `X-Razorpay-Signature` header (HMAC SHA256 of the raw body with the webhook secret). The new membership webhook handler runs only after signature verification succeeds.
- **No new `@splashh/ui` primitives** — membership pages use `Card`, `Button`, `Input`, `Table` (already in the package).
- **No npm dependencies added.**
- **Brand:** reuse existing tokens — primary `sky-500`, danger `red-500`, surface tokens from `@splashh/ui`. No new colors.
- **Eventing:** the publisher is in-process and synchronous (already added by the payments module). New domain events live in `membership/application/events.py`. Subscribers are callables registered at startup. No external broker.
- **Background work:** the pack expiry sweeper is an `asyncio.create_task` started in the FastAPI lifespan. No Celery, no cron, no external scheduler.
- **Idempotency:** webhook handler uses the existing `IdempotencyStore` (Redis + DB, 24h TTL). Replays are no-ops. Key format: `subscription:{razorpay_subscription_id}:{event_type}:{event_id}`. Pack consumption uses Postgres optimistic-concurrency (UPDATE-WHERE on `visits_remaining`) — no Redis involvement.
- **Optimistic concurrency for pack consumption:** every pack decrement is an `UPDATE pack_purchases SET visits_remaining = ?, status = ? WHERE id = ? AND visits_remaining = ?`. Zero rows affected = `Conflict` raised = booking transaction rolls back. This is the same pattern `bookings.add_safe` uses for the no-double-booking invariant.

---

## File Structure

### Backend — new files

```
apps/backend/src/membership/
  __init__.py
  domain/
    __init__.py
    entities.py             # Subscription, PackPurchase, value objects
    value_objects.py        # SubscriptionStatus, PackStatus, BillingPeriod
  application/
    __init__.py
    membership_service.py   # Subscription + Pack operations; implements MembershipGate
    membership_gate.py      # Protocol consumed by BookingService
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
      deps.py               # FastAPI dependencies (current_user, tenant, membership_service)
apps/backend/alembic/versions/
  20240101_0005_membership.py             # NEW — 2 migrations in one file (customers column + 4 tables)
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
apps/backend/src/customer/
  infrastructure/models.py                 # add has_active_subscription column
apps/backend/src/payments/
  application/payment_service.py           # extend handle_webhook to dispatch subscription.* events
  interfaces/http/router.py                # (no change — webhook endpoint already exists)
apps/backend/src/app.py                    # wire MembershipService into BookingService factory
apps/backend/src/main.py                   # start pack expiry sweeper in lifespan
packages/api-client/src/
  membership.ts                            # NEW — typed wrappers + types
  index.ts                                 # add re-export
packages/api-client/package.json           # add ./membership subpath export
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

## Data Model

### `customers` (modified)

Add one column:

| Column | Type | Notes |
|---|---|---|
| `has_active_subscription` | BOOL NOT NULL DEFAULT false | Fast pre-check for the gate; avoids subscription-table join on every booking. Flipped by webhook handler on `subscription.activated` and `subscription.cancelled`. |

### `subscription_plans` (new — tenant config)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID NOT NULL | FK, indexed, RLS |
| `name` | TEXT NOT NULL | e.g. "Monthly Member" |
| `razorpay_plan_id` | TEXT UNIQUE NOT NULL | Created via Razorpay Plans API on first admin save |
| `price_paise` | BIGINT NOT NULL | |
| `currency` | CHAR(3) NOT NULL DEFAULT 'INR' | |
| `period` | TEXT NOT NULL DEFAULT 'monthly' | v1: `monthly` only |
| `trial_period_days` | INT NOT NULL DEFAULT 0 | Configurable per tenant |
| `active` | BOOL NOT NULL DEFAULT true | |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

Single-row-per-tenant expectation in v1 (the "single tier" decision). Still a table so multi-tier is a config change later.

### `subscriptions` (new)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID NOT NULL | FK, indexed, RLS |
| `customer_id` | UUID NOT NULL | FK, indexed |
| `plan_id` | UUID NOT NULL | FK → `subscription_plans.id` |
| `razorpay_subscription_id` | TEXT UNIQUE NOT NULL | |
| `status` | TEXT NOT NULL | enum: `created`, `authenticated`, `active`, `pending`, `halted`, `cancelled`, `completed`, `expired` |
| `current_period_start` | TIMESTAMPTZ NULL | Populated on first `activated` event |
| `current_period_end` | TIMESTAMPTZ NULL | Populated on first `activated` event |
| `trial_ends_at` | TIMESTAMPTZ NULL | |
| `cancelled_at` | TIMESTAMPTZ NULL | |
| `cancel_at_period_end` | BOOL NOT NULL DEFAULT false | Set true by admin cancel; webhook-driven final cancel flips `status` |
| `started_at` | TIMESTAMPTZ NOT NULL | |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

Indexes: `(tenant_id, customer_id)`, `(razorpay_subscription_id)`, `(tenant_id, status)`.

### `pack_definitions` (new — tenant config)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID NOT NULL | FK, RLS |
| `name` | TEXT NOT NULL | e.g. "10-Visit Pack" |
| `visit_count` | INT NOT NULL | |
| `validity_days` | INT NOT NULL | Fixed window from issuance |
| `currency` | CHAR(3) NOT NULL DEFAULT 'INR' | |
| `price_paise` | BIGINT NOT NULL DEFAULT 0 | Informational only — packs are admin-issued, not purchased |
| `active` | BOOL NOT NULL DEFAULT true | |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

### `pack_purchases` (new)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID NOT NULL | FK, indexed, RLS |
| `customer_id` | UUID NOT NULL | FK, indexed |
| `pack_definition_id` | UUID NOT NULL | FK |
| `visits_remaining` | INT NOT NULL | Starts at `pack_definitions.visit_count`, decremented atomically on consume |
| `expires_at` | TIMESTAMPTZ NOT NULL | `issued_at + pack_definitions.validity_days` |
| `status` | TEXT NOT NULL | enum: `active`, `exhausted`, `expired` |
| `issued_by_admin_id` | UUID NOT NULL | FK → users |
| `issued_at` | TIMESTAMPTZ NOT NULL | |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

Indexes:
- `(tenant_id, customer_id, status) WHERE status = 'active'` — partial index for fast active lookup
- `(expires_at) WHERE status = 'active'` — partial index for the expiry sweeper

### `bookings` (modified)

Add two nullable columns:

| Column | Type | Notes |
|---|---|---|
| `coverage_source` | TEXT NULL | enum: `subscription`, `pack`, NULL |
| `pack_purchase_id` | UUID NULL | FK → `pack_purchases.id`, nullable |

These enable reporting (`GROUP BY coverage_source`) without reconstructing from events.

### Migrations

Two Alembic migrations:

1. `20240101_0005a_customers_has_active_subscription.py` — add `customers.has_active_subscription` column (default false, backfill safe).
2. `20240101_0005b_membership_tables.py` — create `subscription_plans`, `subscriptions`, `pack_definitions`, `pack_purchases`; add `bookings.coverage_source`, `bookings.pack_purchase_id`.

Both migrations are RLS-aware: tables created with RLS enabled, policies attached immediately. Backfills (none needed — no existing rows).

---

## Domain Layer (`apps/backend/src/membership/domain/`)

### `value_objects.py`

```python
class SubscriptionStatus(str, Enum):
    CREATED = "created"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    PENDING = "pending"
    HALTED = "halted"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    EXPIRED = "expired"

class PackStatus(str, Enum):
    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    EXPIRED = "expired"

class BillingPeriod(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"   # not exposed in v1, but defined for forward compat
```

### `entities.py`

`Subscription` (pure Python dataclass, no SQLAlchemy):

- `id`, `tenant_id`, `customer_id`, `plan_id`, `razorpay_subscription_id`, `status`, `current_period_start`, `current_period_end`, `trial_ends_at`, `cancelled_at`, `cancel_at_period_end`, `started_at`, `created_at`, `updated_at`
- `@classmethod create(...)` — factory that returns `Subscription` with `status=CREATED`, validates all inputs.
- `apply_event(event_type: SubscriptionEventType, **payload) -> None` — single dispatch on event type, transitions state, updates timestamps. Raises `InvariantViolation` for illegal transitions.
- `is_covering(now: datetime) -> bool` — True if `status == ACTIVE AND (trial_ends_at IS NULL OR now < trial_ends_at)`. Used by `MembershipGate.evaluate_coverage`.
- `mark_cancel_at_period_end() -> None` — only from `ACTIVE`; sets `cancel_at_period_end = true`. No state change.

`PackPurchase` (pure Python):

- `id`, `tenant_id`, `customer_id`, `pack_definition_id`, `visits_remaining`, `expires_at`, `status`, `issued_by_admin_id`, `issued_at`, `created_at`, `updated_at`
- `@classmethod issue(*, tenant_id, customer_id, definition: PackDefinition, issued_by_admin_id, now) -> PackPurchase` — factory with `visits_remaining = definition.visit_count`, `expires_at = now + definition.validity_days`, `status = ACTIVE`.
- `consume_one() -> int` — only valid if `status == ACTIVE AND visits_remaining > 0 AND now < expires_at`. Decrements; if zero → `status = EXHAUSTED`. Returns new remaining count. Raises `InvariantViolation` on illegal state.
- `expire() -> None` — only from `ACTIVE`; sets `status = EXPIRED`.
- `is_covering(now: datetime) -> bool` — True if `status == ACTIVE AND visits_remaining > 0 AND now < expires_at`.

Status invariants match the state tables in the Subscription Lifecycle and Pack Lifecycle sections below. They are unit-tested exhaustively in `tests/membership/test_entities.py`.

---

## Application Layer (`apps/backend/src/membership/application/`)

### `membership_gate.py`

```python
from typing import Protocol
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(frozen=True)
class CoverageDecision:
    free: bool
    source: str | None              # "subscription" | "pack" | None
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

The protocol is the only thing `booking/` imports from `membership/`. The implementation (`MembershipService`) satisfies it via duck typing — no `implements` keyword.

### `membership_service.py`

Implements `MembershipGate` and exposes the public API.

**Subscription methods:**

- `async create_subscription(*, tenant_id, customer_id, plan_id) -> SubscriptionResult`
  - Loads plan (validates `active=true`)
  - Calls `RazorpayAdapter.create_subscription(plan_id=plan.razorpay_plan_id, customer_id=str(customer_id), ...)`. Returns dict with `id`, `short_url`.
  - Inserts `Subscription` row with `status=CREATED`, `started_at=now`.
  - Returns `{subscription, short_url}`.
- `async cancel_subscription_at_period_end(*, tenant_id, subscription_id) -> Subscription`
  - Loads subscription (404 if missing, 409 if not `ACTIVE`).
  - Calls `RazorpayAdapter.cancel_subscription(razorpay_id, cancel_at_cycle_end=true)`.
  - Marks `cancel_at_period_end = true` locally.
  - Returns updated row. Does NOT flip status — that happens when the `subscription.cancelled` webhook fires at period end.
- `async activate_from_webhook(*, event_id, event_type, payload) -> None`
  - Idempotency: checks `IdempotencyStore` for `subscription:{razorpay_subscription_id}:{event_type}:{event_id}`; returns silently if seen.
  - Dispatches by `event_type` to `Subscription.apply_event`.
  - On `subscription.activated`: flips `customers.has_active_subscription = true` (single UPDATE).
  - On `subscription.cancelled` and `subscription.expired` and `subscription.halted`: flips `customers.has_active_subscription = false`.
  - Records event in `IdempotencyStore` (24h TTL).
- `async get_active_subscription(*, tenant_id, customer_id) -> Subscription | None`
- `async list_subscriptions(*, tenant_id, customer_id=None, plan_id=None, status=None, limit, offset) -> list[Subscription]`

**Pack methods:**

- `async issue_pack(*, tenant_id, customer_id, pack_definition_id, issued_by_admin_id, now) -> PackPurchase`
  - Loads customer (404 if missing)
  - Loads definition (validates `active=true`)
  - Calls `PackPurchase.issue(...)` factory.
  - Persists. Returns row.
- `async list_active_packs_for_customer(*, tenant_id, customer_id, now) -> list[PackPurchase]`
- `async list_packs_for_customer_admin(*, tenant_id, customer_id) -> list[PackPurchase]`
- `async expire_pack(*, tenant_id, pack_id) -> PackPurchase` (admin-forced)
- `async expire_overdue_packs(*, now) -> int` (called by sweeper; returns count expired)

**Gate implementation:**

- `async evaluate_coverage(*, tenant_id, customer_id, resource_id, now) -> CoverageDecision`
  - Reads `customers.has_active_subscription`. If true → return `CoverageDecision(free=True, source="subscription", pack_purchase_id=None, pack_visits_remaining=None)`.
  - Otherwise: locks and reads the customer's most-recent active pack (single SQL: `SELECT ... FROM pack_purchases WHERE tenant_id=? AND customer_id=? AND status='active' AND expires_at > ? ORDER BY expires_at ASC LIMIT 1 FOR UPDATE`).
  - If found with `visits_remaining > 0` → return `CoverageDecision(free=True, source="pack", pack_purchase_id=..., pack_visits_remaining=N)`.
  - Otherwise → return `CoverageDecision(free=False, source=None, ...)`.

  Resource ID is in the signature for future use (e.g. excluding certain resources from membership coverage). v1 ignores it.
- `async consume_pack_visit(*, tenant_id, pack_purchase_id, expected_remaining) -> None`
  - Executes: `UPDATE pack_purchases SET visits_remaining = ?, status = ?, updated_at = ? WHERE id = ? AND tenant_id = ? AND visits_remaining = ?`
  - New `visits_remaining = expected_remaining - 1`. New `status = 'exhausted'` if 0 else `'active'`.
  - If 0 rows affected → raise `Conflict("Pack visit was consumed by another booking")`.
  - Caller's transaction rolls back; safe to retry.

### `webhook_handler.py`

```python
class MembershipWebhookHandler:
    def __init__(self, *, session, membership_service: MembershipService):
        self.session = session
        self.membership_service = membership_service

    async def handle(self, event: dict) -> None:
        event_type = event["event"]            # e.g. "subscription.activated"
        payload = event["payload"]["subscription"]["entity"]
        event_id = event["event_id"]
        await self.membership_service.activate_from_webhook(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
        )
```

Registered with `PaymentService.handle_webhook` dispatch table:

```python
# In payments/application/payment_service.py
async def handle_webhook(self, *, raw_payload, signature):
    event = self.razorpay.verify_and_parse_webhook(raw_payload, signature)
    if event["event"].startswith("subscription."):
        await self.membership_webhook_handler.handle(event)
        return
    if event["event"].startswith("payment_link.") or event["event"].startswith("payment."):
        await self._handle_invoice_webhook(event)
```

The webhook endpoint URL stays the same (`POST /webhooks/razorpay`); the dispatch table fans out by event prefix.

### `events.py`

`MembershipSubscriptionActivated`, `MembershipSubscriptionCancelled`, `MembershipPackIssued`, `MembershipPackExhausted`, `MembershipPackExpired` — extend `common.application.events.DomainEvent`. Future modules (notifications, analytics) subscribe to these.

---

## Infrastructure Layer (`apps/backend/src/membership/infrastructure/`)

### `models.py`

SQLAlchemy ORM models for all 4 tables, plus a small mapping for `customers.has_active_subscription` on the existing customer model. Uses the existing `TenantScopedBase` mixin so RLS policies attach automatically.

### `repositories.py`

- `SubscriptionRepository(tenant_id)` — `get_by_id`, `get_by_razorpay_id`, `list_for_customer`, `list_for_tenant_filtered`, `add`, `update`
- `SubscriptionPlanRepository(tenant_id)` — `get_by_id`, `list_active`, `add`, `update`
- `PackDefinitionRepository(tenant_id)` — `get_by_id`, `list_active`, `add`, `update`
- `PackPurchaseRepository(tenant_id)` — `get_by_id`, `lock_active_for_customer` (single SELECT FOR UPDATE), `atomic_decrement` (the UPDATE-WHERE), `expire_overdue` (single UPDATE bulk), `list_for_customer`, `list_active_for_customer`, `add`, `update`

The optimistic-concurrency decrement lives here as a single repository method, not in the service, so the SQL is testable in isolation.

---

## HTTP Interface (`apps/backend/src/membership/interfaces/http/`)

### `router.py`

Mounts at two prefixes:

- `/membership/*` — customer-facing (authenticated `customer` role)
- `/admin/membership/*` — admin-facing (`tenant_admin` role)

Endpoints listed in the API Surface section below. All use `RoleGate` for auth, return standard error shapes from `common`.

### `schemas.py`

Pydantic v2 models with `ConfigDict(from_attributes=True)`:

- `SubscriptionResponse`, `SubscriptionCreateRequest`, `SubscriptionCancelRequest`
- `PlanResponse`, `PlanCreateRequest`, `PlanUpdateRequest`
- `PackDefinitionResponse`, `PackDefinitionCreateRequest`
- `PackPurchaseResponse`, `PackIssueRequest`
- `MembershipOverviewResponse` (the `/membership/me` payload: subscription + packs + `has_active_subscription`)

### `deps.py`

FastAPI dependencies: `get_membership_service(session, ...)`, `get_subscription_plan_repo(session)`, etc. Mirror the structure in `payments/interfaces/http/deps.py`.

---

## Booking Integration

### Booking entity changes

Add two nullable fields:

```python
coverage_source: Literal["subscription", "pack", None] = None
pack_purchase_id: UUID | None = None
```

Validation: `coverage_source == "pack"` iff `pack_purchase_id is not None`. `coverage_source == "subscription"` implies `pack_purchase_id is None`. `coverage_source is None` implies both fields are None.

### BookingService changes

```python
class BookingService:
    def __init__(
        self,
        session: AsyncSession,
        bookings: BookingRepository,
        membership_gate: MembershipGate,    # NEW — Protocol type, no module import
    ) -> None: ...

    async def create_booking(
        self, *, tenant_id, customer_id, resource_id, start_at, end_at,
        price_cents=0, currency="INR", notes=None,
    ) -> Booking:
        now = datetime.now(UTC)

        # Resource must exist — load to get its price for uncovered bookings
        resource = await self.resources.get_by_id(tenant_id, resource_id)
        if resource is None:
            raise NotFound("Resource not found")

        decision = await self.membership_gate.evaluate_coverage(
            tenant_id=tenant_id, customer_id=customer_id,
            resource_id=resource_id, now=now,
        )

        if decision.source == "pack" and decision.pack_purchase_id is not None:
            # Atomic decrement — raises Conflict on race loss, rolls back booking
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

One `await session.commit()` at the route handler commits booking + pack decrement atomically.

### Race condition guarantee

The pack decrement uses `WHERE visits_remaining = expected_remaining`. If another concurrent booking already decremented, 0 rows affected → `Conflict` raised → booking transaction rolls back → caller retries. Pack visits can never go negative; no double-spend is possible. Same correctness property as the existing no-double-booking invariant in `bookings.add_safe`.

---

## Subscription Lifecycle

### Razorpay event → state transition

| Razorpay event | DB action |
|---|---|
| `subscription.created` | Insert row (status `created`) if not present; idempotent. |
| `subscription.authenticated` | Status `authenticated`. |
| `subscription.activated` | Status `active`; populate `current_period_start`/`end`; if trial > 0, `trial_ends_at = current_period_start - 1 day`; flip `customers.has_active_subscription = true`. |
| `subscription.charged` | Refresh `current_period_start`/`end` to the new billing period. Idempotent. |
| `subscription.pending` | Status `pending`. |
| `subscription.halted` | Status `halted`; flip `customers.has_active_subscription = false`. |
| `subscription.cancelled` | Status `cancelled`; set `cancelled_at`; flip `customers.has_active_subscription = false`. (Final cancel — fires after period end if admin cancelled at period end.) |
| `subscription.completed` | Status `completed`. |
| `subscription.expired` | Status `expired`; flip `customers.has_active_subscription = false`. |

### Customer signup flow

1. Customer clicks "Become a member" on `/me/membership`.
2. Frontend calls `POST /membership/subscriptions` with `{plan_id}`. Backend creates Razorpay subscription via `RazorpayAdapter.create_subscription(plan_id, customer_id)` and returns `{id, short_url, status: "created"}`.
3. Frontend redirects to `short_url`.
4. Customer completes auth on Razorpay's hosted page.
5. Razorpay fires `subscription.created` → `subscription.authenticated` → `subscription.activated` webhooks.
6. Webhook handler routes to `MembershipService.activate_from_webhook`.
7. On `subscription.activated`, `customers.has_active_subscription` flips to `true`; the gate opens.

### Admin cancel flow

1. Admin opens `/admin/subscriptions`, clicks "Cancel subscription".
2. Frontend calls `POST /admin/membership/subscriptions/:id/cancel` with `{at_period_end: true}` (v1 only supports true).
3. Backend calls `RazorpayAdapter.cancel_subscription(razorpay_id, cancel_at_cycle_end=true)`.
4. Subscription remains `ACTIVE` until period end; `cancel_at_period_end = true` locally.
5. At period end, Razorpay fires `subscription.cancelled`. Handler flips `status` and `customers.has_active_subscription`.

### Trial period

- Configured per `subscription_plans.trial_period_days`.
- Passed to Razorpay on plan creation: `period: monthly, trial_period: <days>`.
- `subscription.activated` webhook populates `trial_ends_at`.
- Gate: `is_covering` returns True if `trial_ends_at IS NULL OR now < trial_ends_at`.

### Idempotency

Webhook handler uses the existing `IdempotencyStore` (Redis + DB, 24h TTL) with key `subscription:{razorpay_subscription_id}:{event_type}:{event_id}`. Replays are no-ops.

---

## Pack Lifecycle

### States

| State | Meaning |
|---|---|
| `active` | `visits_remaining > 0` AND `now < expires_at` |
| `exhausted` | `visits_remaining == 0` |
| `expired` | `now >= expires_at` |

### Admin issuance flow

1. Admin opens `/admin/packs/new`, picks customer + pack definition.
2. Frontend calls `POST /admin/membership/packs` with `{customer_id, pack_definition_id}`.
3. Backend loads definition (validates active), creates `PackPurchase` with `visits_remaining = visit_count`, `expires_at = now + validity_days`, `status = active`, `issued_by_admin_id = current_admin.id`.
4. Pack appears in customer's `/me/membership` view.

No payment, no Razorpay touch (admin-only issuance). Audit trail: `issued_by_admin_id`, `issued_at`.

### Consumption (in booking transaction)

Already detailed in "Booking Integration" above. Summary: `evaluate_coverage` decides; `consume_pack_visit` atomically decrements with optimistic concurrency.

### Expiry sweeper

Background task started in FastAPI lifespan:

```python
async def pack_expiry_sweeper_loop():
    while True:
        try:
            async with session_factory() as session:
                svc = MembershipService(session, ...)
                count = await svc.expire_overdue_packs(now=datetime.now(UTC))
                if count:
                    log.info("Expired %d packs", count)
        except Exception:
            log.exception("Pack expiry sweeper failed")
        await asyncio.sleep(3600)  # 1 hour
```

Also called once on app startup (catches the case where the process was down > 1 hour). No new infrastructure — matches the existing patterns.

### Refund policy

Packs are non-refundable (admin issued). Admin can force `expired` early via `POST /admin/membership/packs/:id/expire` (support tool). No automatic refund flow.

---

## API Surface

### Customer-facing (`/membership/*`, role: `customer`)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/membership/plans` | List active subscription plans for current tenant. |
| `POST` | `/membership/subscriptions` | Body `{plan_id}`. Creates Razorpay sub, returns `{subscription_id, short_url}`. Customer redirected to `short_url`. |
| `GET` | `/membership/me` | Current subscription + active packs + `has_active_subscription`. |
| `GET` | `/membership/me/subscription` | Just the subscription row (404 if none). |
| `GET` | `/membership/me/packs` | Active packs only. |

No customer cancel endpoint (self-service rule: signup yes, cancel no).

### Admin-facing (`/admin/membership/*`, role: `tenant_admin`)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/membership/plans` | List all plans (incl. inactive). |
| `POST` | `/admin/membership/plans` | Body `{name, price_paise, currency, trial_period_days, period: "monthly"}`. Creates Razorpay plan, stores `razorpay_plan_id`. |
| `PATCH` | `/admin/membership/plans/:id` | Update name/price/trial/active. Existing subscriptions unaffected. |
| `GET` | `/admin/membership/pack-definitions` | List pack definitions. |
| `POST` | `/admin/membership/pack-definitions` | Body `{name, visit_count, validity_days, price_paise}`. |
| `PATCH` | `/admin/membership/pack-definitions/:id` | Update name/count/validity/active. |
| `POST` | `/admin/membership/packs` | Body `{customer_id, pack_definition_id}`. Issue pack. |
| `GET` | `/admin/membership/packs?customer_id=` | List packs for a customer (all statuses). |
| `POST` | `/admin/membership/packs/:id/expire` | Admin-forced expiry. |
| `GET` | `/admin/membership/subscriptions?customer_id=&status=&plan_id=` | List subscriptions (filterable). |
| `POST` | `/admin/membership/subscriptions/:id/cancel` | Body `{at_period_end: true}`. Calls RazorpayAdapter. |

All return 404 (not 403) on cross-tenant access. All customer-facing return 404 if the resource belongs to another tenant.

### Webhook

No new endpoint. `POST /webhooks/razorpay` (existing) is extended via `PaymentService.handle_webhook` dispatch table to route `subscription.*` events to `MembershipWebhookHandler.handle`.

---

## Frontend

### `packages/api-client/src/membership.ts`

Typed wrappers + types:

```typescript
export type SubscriptionStatus = "created" | "authenticated" | "active" | "pending" | "halted" | "cancelled" | "completed" | "expired";
export type PackStatus = "active" | "exhausted" | "expired";
export type BillingPeriod = "monthly" | "yearly";

export interface SubscriptionPlan { id: string; name: string; price_paise: number; currency: string; period: BillingPeriod; trial_period_days: number; active: boolean; }
export interface Subscription { id: string; tenant_id: string; customer_id: string; plan_id: string; status: SubscriptionStatus; current_period_start: string | null; current_period_end: string | null; trial_ends_at: string | null; cancelled_at: string | null; cancel_at_period_end: boolean; started_at: string; }
export interface PackDefinition { id: string; name: string; visit_count: number; validity_days: number; price_paise: number; currency: string; active: boolean; }
export interface PackPurchase { id: string; customer_id: string; pack_definition_id: string; visits_remaining: number; expires_at: string; status: PackStatus; issued_at: string; }
export interface MembershipOverview { has_active_subscription: boolean; subscription: Subscription | null; packs: PackPurchase[]; }

export async function listPlans(): Promise<SubscriptionPlan[]>;
export async function createSubscription(planId: string): Promise<{ subscription_id: string; short_url: string; status: SubscriptionStatus }>;
export async function getMyMembership(): Promise<MembershipOverview>;

export async function listSubscriptions(params: { customer_id?: string; status?: SubscriptionStatus; plan_id?: string; limit?: number; offset?: number }): Promise<Subscription[]>;
export async function cancelSubscription(subscriptionId: string): Promise<Subscription>;

export async function listPackDefinitions(): Promise<PackDefinition[]>;
export async function createPackDefinition(input: Omit<PackDefinition, "id" | "active">): Promise<PackDefinition>;
export async function issuePack(input: { customer_id: string; pack_definition_id: string }): Promise<PackPurchase>;
export async function listPacks(params: { customer_id: string }): Promise<PackPurchase[]>;
export async function expirePack(packId: string): Promise<PackPurchase>;

export async function listPlansAdmin(): Promise<SubscriptionPlan[]>;
export async function createPlan(input: Omit<SubscriptionPlan, "id" | "active">): Promise<SubscriptionPlan>;
export async function updatePlan(id: string, input: Partial<SubscriptionPlan>): Promise<SubscriptionPlan>;
```

### `apps/web-pwa/src/features/membership/hooks.ts`

```typescript
usePlans() / useMyMembership() / useCreateSubscription() / useSubscriptionsAdmin(...) / useCancelSubscription() / usePackDefinitions() / usePackDefinitionsAdmin() / useCreatePackDefinition() / useIssuePack() / useExpirePack() / usePacksForCustomer(customerId)
```

Mutations invalidate `["membership", "me"]` (and admin variants) on success.

### Pages

**`/me/membership`** (customer):
- Hero card: "Become a member" CTA if `has_active_subscription === false` → opens plan picker modal → triggers `useCreateSubscription` → redirects to returned `short_url`.
- Current subscription card (if any): plan name, price (`INR X`), current period end, trial countdown if applicable. "Contact us to cancel" stub text (no button).
- Active packs list: each with `visits_remaining`, `expires_at`, progress bar (`visits_remaining / definition.visit_count`).

**`/admin/subscriptions`** (admin):
- Filterable table (customer / plan / status).
- "Cancel at period end" action per row, with confirmation modal.

**`/admin/packs`** (admin):
- Pack definitions list + "New pack definition" form.
- "Issue pack" form: customer picker + definition picker.
- Recent issuances table (most recent 50).

### Modified pages

**`/book/:resource_id`** (customer):
- After time slot selection, show one of:
  - "Covered by your subscription" → confirm books with `price_cents=0`, no pay button.
  - "Will use 1 of N remaining pack visits (expires DATE)" → confirm books with `price_cents=0`, no pay button.
  - "Total: INR X" → existing "Pay & book" flow.

**`/admin/customers/:id`** (admin):
- New "Membership" tab showing subscription + packs summary.

### Routes & nav

- 3 new routes in `apps/web-pwa/src/routes/index.tsx`:
  - `/me/membership` (RoleGate: `customer`)
  - `/admin/subscriptions` (RoleGate: `tenant_admin`)
  - `/admin/packs` (RoleGate: `tenant_admin`)
- `apps/web-pwa/src/components/nav.ts`:
  - Customer nav: add "Membership" entry (account menu).
  - Admin nav: add "Subscriptions" and "Packs" entries (after "Invoices").

---

## App Wiring (`apps/backend/src/app.py`)

```python
def make_booking_service(session: AsyncSession) -> BookingService:
    booking_repo = BookingRepository(session)
    sub_repo = SubscriptionRepository(session, tenant_id=current_tenant)
    plan_repo = SubscriptionPlanRepository(session, tenant_id=current_tenant)
    pack_def_repo = PackDefinitionRepository(session, tenant_id=current_tenant)
    pack_repo = PackPurchaseRepository(session, tenant_id=current_tenant)
    razorpay = get_razorpay_adapter()
    membership_svc = MembershipService(
        session=session,
        subscription_repo=sub_repo,
        plan_repo=plan_repo,
        pack_definition_repo=pack_def_repo,
        pack_repo=pack_repo,
        razorpay=razorpay,
    )
    return BookingService(
        session=session,
        bookings=booking_repo,
        resources=resource_repo,
        membership_gate=membership_svc,
    )
```

`MembershipService` is registered as the `membership_webhook_handler` dependency in `payments/application/payment_service.py` at app startup.

### Lifespan (`apps/backend/src/main.py`)

Add the pack expiry sweeper to the existing lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # existing startup
    sweeper_task = asyncio.create_task(pack_expiry_sweeper_loop())
    yield
    sweeper_task.cancel()
    # existing shutdown
```

---

## Testing Strategy

Following the red-green-refactor TDD pattern used by the payments module.

### Unit (`tests/membership/`)

**`test_entities.py`** — pure domain logic:
- `Subscription.activate` populates period fields
- `Subscription.mark_cancelled` only from `ACTIVE`/`PENDING`; raises from `CREATED`/`COMPLETED`/`EXPIRED`
- `Subscription.handle_*_event` correct for each event type
- `PackPurchase.consume_one` decrements; raises when `visits_remaining == 0`, `status != ACTIVE`, or expired
- `PackPurchase.expire` only from `ACTIVE`
- `is_covering` returns True/False correctly for all boundary cases (trial ends_at == now, expires_at == now)

**`test_membership_service.py`** — with FakeRepo + FakeRazorpayAdapter:
- `create_subscription` calls adapter, persists row, returns short URL
- `activate_from_webhook` is idempotent — second call with same event_id is no-op
- `cancel_subscription(at_period_end=True)` calls adapter with right flag
- `issue_pack` validates customer exists, definition active, returns row with correct `expires_at = now + validity_days`
- `evaluate_coverage` — 5 cases (subscription, pack with visits, neither, pack expired, pack exhausted)
- `consume_pack_visit` with stale `expected_remaining` raises `Conflict`

**`test_webhook_handler.py`**:
- Each Razorpay event type → correct state transition + correct `customers.has_active_subscription` flip
- Replay (same event_id) is no-op

### Integration (`tests/membership/integration/`)

- `test_subscription_webhook_flow.py`: full round-trip — stub Razorpay → POST synthetic `subscription.activated` to `/webhooks/razorpay` → assert DB updated + `customers.has_active_subscription=true` + gate returns `free=True`.
- `test_pack_expiry_sweeper.py`: insert pack with `expires_at` in past → run `expire_overdue_packs` → assert status flipped to `expired`.
- `test_concurrent_pack_consumption.py`: two simultaneous `consume_pack_visit` calls with `expected_remaining=5` — exactly one succeeds, one raises `Conflict`. Use `asyncio.gather` against real DB.

### Booking integration (`tests/booking/integration/test_membership_integration.py`)

- Booking with active subscription → `price_cents == 0`, `coverage_source == "subscription"`
- Booking with active pack → `price_cents == 0`, `coverage_source == "pack"`, pack `visits_remaining` decremented by 1
- Booking with neither → `price_cents == resource.price_cents`, `coverage_source is None`
- Booking with pack expired between evaluate and consume → `Conflict` raised, no booking row inserted
- Booking with pack exhausted between evaluate and consume → `Conflict` raised, no booking row inserted
- Concurrent bookings with single pack visit remaining → exactly one succeeds, one raises `Conflict`

### HTTP (`tests/membership/test_router.py`)

- All endpoints return correct status codes (200/201/400/403/404/409)
- `POST /membership/subscriptions` returns short URL on success
- `POST /admin/membership/subscriptions/:id/cancel` calls `RazorpayAdapter.cancel_subscription`
- Cross-tenant access → 404 (not 403)
- Customer hitting admin endpoint → 403
- Missing plan/customer/pack IDs → 400

### Frontend (`apps/web-pwa/test/membership/`)

- `hooks.test.tsx`: mocks api-client; verifies queries fire on mount; mutations invalidate correct keys.
- `membership-page.test.tsx`: renders all 3 states (no sub, active sub with period end, active packs list).
- `packs-page.test.tsx`: admin can issue a pack; success toast on response; form validation.
- `subscriptions-page.test.tsx`: admin can cancel at period end; confirmation modal before action.
- `book-page-coverage.test.tsx`: 3 rendered states (subscription / pack / pay).

### E2E (`e2e/membership.spec.ts`)

Two specs following the simplified `admin-invoice-flow.spec.ts` pattern:

1. **Subscription happy path**: register tenant + admin via API → admin creates plan via API → admin creates customer via API → login as customer → navigate to `/me/membership` → click "Become a member" → redirected to Razorpay hosted page (test stops here).
2. **Pack issuance**: admin issues a pack via UI → login as that customer → navigate to `/me/membership` → assert pack visible with correct visits/expires.

The booking-with-coverage flow is covered by integration tests, not E2E (no Razorpay backend infra needed).

### Coverage targets

- Domain: 100%
- Application: >95% (only exclusions are defensive raises for impossible states)
- HTTP router: all status codes exercised
- Webhook handlers: every event type + every idempotency replay case
- Frontend pages: each renders all relevant states (covered / uncovered / error)

---

## Migrations

Two Alembic migrations, both RLS-aware:

1. `20240101_0005a_customers_has_active_subscription.py` — adds `customers.has_active_subscription BOOL NOT NULL DEFAULT false`.
2. `20240101_0005b_membership_tables.py` — creates `subscription_plans`, `subscriptions`, `pack_definitions`, `pack_purchases` with RLS enabled and policies attached; adds `bookings.coverage_source` and `bookings.pack_purchase_id`.

No data backfill needed (no existing rows to migrate).

---

## Out of Scope / YAGNI (deferred to v2)

- Multiple subscription tiers per tenant — schema supports it (table), but v1 admin UI only creates/uses one plan.
- Multiple pack types per pack purchase — v1 each `pack_purchase` references exactly one `pack_definition`.
- Customer-facing subscription cancellation — admin-only in v1.
- Refunds for subscriptions — Razorpay handles cancellations; no automatic refund flow.
- Refunds for packs — admin-issued, non-refundable.
- Customer-self-service pack purchase — admin-issued only.
- Per-resource membership exclusion (e.g. premium resources not covered) — the `resource_id` parameter on `evaluate_coverage` is reserved but ignored.
- Proration / mid-cycle plan changes — not supported by Razorpay Subscriptions v1 API; deferred.
- Subscription pause/resume — Razorpay supports it; deferred.
- Subscription upgrade/downgrade — single tier in v1.
- Email/SMS notifications on subscription/pack events — handled by the future notifications module which subscribes to the events emitted here.
- Analytics dashboards on coverage_source / pack consumption — handled by the future analytics module.
- Multi-currency — INR only in v1.
- Multi-provider abstraction (Stripe etc.) — same pattern as payments (`PaymentProvider` protocol); can be added later without schema changes.

---

## Success Criteria

- Customer can subscribe via Razorpay hosted page and see "Active member" status in their account within seconds.
- Admin can issue a pack and customer sees the pack + visit count + expiry on their membership page.
- Booking with active subscription or pack visit decrements (pack) and skips invoice creation — booking flow returns `price_cents=0, coverage_source="subscription"|"pack"`.
- Concurrent bookings on the same pack with one visit remaining: exactly one succeeds, one rolls back cleanly.
- Pack expiry sweeper marks overdue packs as `expired` within 1 hour of expiry.
- Admin can cancel a subscription at period end; customer keeps access until period end, then `subscription.cancelled` webhook fires and `customers.has_active_subscription` flips to false.
- All RLS policies prevent cross-tenant access (verified by integration test).
- No regression in existing payments / booking / customer test suites.
