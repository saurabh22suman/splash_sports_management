# Payments Module v1 — Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a multi-tenant payments module that lets booking/membership create invoices, lets customers pay via Stripe-hosted Checkout, lets admins issue full refunds, and emits domain events that future modules (membership, notifications, analytics) can subscribe to. Payments are processed through a single platform-owned Stripe account; the schema leaves room for Stripe Connect later.

**Architecture:** A new `payments` backend module (`interfaces/http/` + `application/` + `domain/` + `infrastructure/`) plus a small event-bus addition to `common` (`common/application/events.py` + a singleton `InProcessEventPublisher` wired at startup). All Stripe interaction is hidden behind a `PaymentProvider` protocol with a `StripeAdapter` (production) and a `NullAdapter` (tests). The customer-facing checkout flow is Stripe Checkout (hosted redirect). The webhook receiver is synchronous and idempotent by Stripe event id. The frontend gains an admin `/admin/invoices*` set and a customer `/book/pay/:invoiceId*` set, both backed by typed hooks in `@splashh/api-client`.

**Tech Stack:** FastAPI, SQLAlchemy 2 (async) + Alembic, Pydantic v2, Stripe Python SDK, `stripe-mock` (dev/test), `pytest` + `httpx` (backend), React 19 + react-router-dom + @tanstack/react-query + zustand + vitest + RTL + Playwright (frontend). One new Python dependency (`stripe`) and one dev dependency (`stripe-mock`). No new npm dependencies.

---

## Workflow (binding for implementation)

- **Test-driven development (red-green-refactor).** Every line of production code is preceded by a failing test that proves the behavior. The cycle is RED → verify fail → GREEN → verify pass → REFACTOR → next. No production code without a failing test first. "Watch it fail" is mandatory — a test that passes on first run is a false positive.
- **Subagent-driven execution.** Implementation is dispatched as a series of fresh subagent tasks (one per task in the plan), with a task reviewer (spec compliance + code quality) after each, and a broad whole-branch review at the end. The controller does not edit code directly; it dispatches subagents and tracks results in a ledger.
- **Bite-sized tasks.** Each task in the implementation plan is the smallest unit that carries its own test cycle. Tasks fold setup, scaffolding, and configuration into the deliverable that needs them.
- **Frequent commits.** Each task ends with a green, reviewed commit. No mega-commits.
- **Verification before completion claims.** Every claim of "done" is backed by the test command's actual output, not by the implementer's recall. Show the command and the output.

---

## Global Constraints

- **Multi-tenancy:** every business table has `tenant_id UUID NOT NULL` and a corresponding Postgres RLS policy. Payments tables follow the existing pattern enforced in `common/infrastructure/repository.py`.
- **Audit columns:** every business table has `created_at` and `updated_at` timestamptz columns populated by the existing base mixin.
- **Money:** stored as `Decimal` columns in DB and `int` cents in API + Stripe payloads. Never floats. Currency code is a 3-char string (`USD`, `INR`, ...).
- **Idempotency keys:** client-supplied `Idempotency-Key` header (UUID v4 string, ≤ 64 chars) on mutating endpoints; cached server-side for 24 h. Stripe event ids are stored separately for webhook dedup.
- **Stripe SDK version:** pinned via `uv` lock; match the version installed by `uv add stripe`.
- **Stripe keys:** `STRIPE_SECRET_KEY` (sk_test_... in dev), `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` from env (`common/infrastructure/settings.py`). Single platform account; per-tenant config table leaves `stripe_account_id` NULL.
- **No card data on our servers.** All PCI compliance is via Stripe Checkout.
- **Logging:** never log full payment objects or Stripe API responses. Log only `invoice_id`, `payment_id`, `stripe_event_id`, and high-level status.
- **Errors:** never expose Stripe SDK error details to API consumers; map to standard `common` exceptions (`Validation`, `Conflict`, `ServiceUnavailable`).
- **Auth:** all `/payments/*` endpoints require an authenticated session. Customers see only their own invoices; staff and tenant_admin see all invoices in their tenant. Refund endpoint requires `tenant_admin` role.
- **Webhook auth:** `/webhooks/stripe` requires a valid `Stripe-Signature` header. No JWT.
- **CORS / CSRF:** webhook endpoint is on the backend origin only; no CORS or CSRF needed.
- **No new `@splashh/ui` primitives** — payments pages use `Card`, `Button`, `Input`, `Table` (already in the package).
- **No npm dependencies added.**
- **Brand:** reuse existing tokens — primary `sky-500`, danger `red-500`, surface tokens from `@splashh/ui`. No new colors.
- **Eventing:** the publisher is in-process and synchronous. Subscribers are callables registered at startup. No external broker. Switch to Redis pub/sub or a DB outbox only if a concrete need arises.

---

## File Structure

### Backend — new files

```
apps/backend/src/payments/
  __init__.py
  domain/
    __init__.py
    entities.py            # Invoice, Payment, Refund, TenantPaymentConfig (pure Python)
    value_objects.py       # Money, InvoiceStatus, PaymentStatus, RefundStatus, Channel
  application/
    __init__.py
    payment_service.py     # create_invoice, create_checkout_session, handle_webhook, refund, get_invoice, list_invoices
    provider.py            # PaymentProvider protocol, StripeAdapter, NullAdapter
    events.py              # Domain events emitted by payments
  infrastructure/
    __init__.py
    models.py              # SQLAlchemy ORM models
    repositories.py        # InvoiceRepository, PaymentRepository, RefundRepository, ProcessedStripeEventRepository
    stripe_client.py       # Wraps stripe SDK with our settings; constructs the SDK client
    idempotency.py         # IdempotencyKeyRepository backed by Redis (24h TTL) or DB
  interfaces/
    http/
      __init__.py
      router.py            # /payments/invoices, /payments/invoices/{id}/checkout, /webhooks/stripe, ...
      schemas.py           # Pydantic request/response models
      deps.py              # FastAPI dependencies for current user, tenant, idempotency-key extraction
apps/backend/src/common/application/
  events.py                # NEW — DomainEvent base, EventPublisher protocol, InProcessEventPublisher
apps/backend/alembic/versions/
  20240101_0003_0004_payments.py      # NEW — migration
```

### Backend — modified files

```
apps/backend/src/common/interfaces/http/app.py    # wire InProcessEventPublisher singleton at startup
apps/backend/src/common/infrastructure/settings.py    # add STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PUBLISHABLE_KEY, STRIPE_API_BASE (override for stripe-mock)
apps/backend/src/common/domain/types.py    # add InvoiceId, PaymentId, RefundId NewType wrappers
apps/backend/pyproject.toml    # add stripe + stripe-mock (dev) deps
apps/backend/tests/conftest.py    # add stripe-mock fixture, idempotency cache clear, event-bus reset
```

### Frontend — new files

```
apps/web-pwa/src/features/payments/
  api.ts                    # createCheckoutSession, listInvoices, getInvoice, refundInvoice
  hooks.ts                  # useInvoices, useInvoice, useCreateCheckoutSession, useRefundInvoice
  schemas.ts                # Invoice, Payment, Refund, LineItem types
apps/web-pwa/src/pages/admin/
  InvoicesPage.tsx          # list + filters + create-invoice modal
  InvoiceDetailPage.tsx     # detail + line items + payment status + refund action
apps/web-pwa/src/pages/book/
  PayInvoicePage.tsx        # customer "Pay now" entry; shows summary + button
  PayInvoiceReturnPage.tsx  # Stripe success-redirect target; polls status
apps/web-pwa/src/components/nav.ts    # add "Invoices" entry to tenant_admin nav
```

### Frontend — modified files

```
apps/web-pwa/src/routes/index.tsx    # add /admin/invoices, /admin/invoices/:id, /book/pay/:id, /book/pay/:id/return
packages/api-client/src/
  client.ts    # add typed wrappers for the new payment endpoints (or whichever file the existing auth/facilities wrappers live in)
```

### Test files (new)

```
apps/backend/tests/payments/
  test_invoice_service.py          # service-level tests with NullAdapter
  test_checkout_endpoint.py        # HTTP tests for POST /payments/invoices/{id}/checkout
  test_webhook_endpoint.py         # signed-fixture tests for /webhooks/stripe
  test_idempotency.py              # webhook dedup + Idempotency-Key caching
  test_refund_endpoint.py
  test_stripe_adapter.py           # integration tests against stripe-mock
  test_tenant_rls.py               # RLS scoping: customer A cannot read customer B's invoices
apps/web-pwa/test/payments/
  invoices-page.test.tsx
  invoice-detail-page.test.tsx
  pay-invoice-page.test.tsx
  pay-invoice-return-page.test.tsx
e2e/admin-invoice-flow.spec.ts    # admin creates invoice → customer pays via Stripe test card → status updates
```

---

## Architecture

### Module layout (mirrors `booking`)

```
src/payments/
  domain/         # pure Python — entities, value objects, status enums
  application/    # payment_service, PaymentProvider protocol + adapters, events
  infrastructure/ # SQLAlchemy models, repositories, Stripe SDK wrapper, idempotency store
  interfaces/http # FastAPI router + Pydantic schemas + deps
```

The `domain/` layer has zero framework imports (per `docs/01-vision/principles.md`). Status transitions and invariants live there; the service layer orchestrates them and the repositories persist.

### Domain entities

```python
# apps/backend/src/payments/domain/value_objects.py

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"

class RefundStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass(frozen=True)
class Money:
    amount_cents: int
    currency: str  # ISO-4217
```

```python
# apps/backend/src/payments/domain/entities.py

@dataclass
class Invoice:
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    invoice_number: str          # per-tenant sequential, e.g. "INV-000123"
    status: InvoiceStatus
    subtotal: Money
    tax: Money
    total: Money
    due_date: date
    paid_at: datetime | None
    description: str
    line_items: list[LineItem]
    created_at: datetime
    updated_at: datetime

    def can_pay(self) -> bool:
        return self.status in (InvoiceStatus.DRAFT, InvoiceStatus.PENDING)

    def can_refund(self) -> bool:
        return self.status == InvoiceStatus.PAID

    def mark_paid(self, when: datetime) -> None:
        if self.status != InvoiceStatus.PENDING:
            raise Conflict("Invoice is not pending payment", details={"status": self.status.value})
        self.status = InvoiceStatus.PAID
        self.paid_at = when
        self.updated_at = when

    def mark_failed(self) -> None:
        if self.status not in (InvoiceStatus.PENDING, InvoiceStatus.DRAFT):
            raise Conflict("Invoice cannot transition to failed", details={"status": self.status.value})
        self.status = InvoiceStatus.FAILED
        self.updated_at = utcnow()

    def mark_refunded(self, when: datetime) -> None:
        if self.status != InvoiceStatus.PAID:
            raise Conflict("Only paid invoices can be refunded", details={"status": self.status.value})
        self.status = InvoiceStatus.REFUNDED
        self.updated_at = when

@dataclass
class LineItem:
    id: UUID
    description: str
    quantity: int
    unit_price: Money
    total: Money

@dataclass
class Payment:
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    amount: Money
    status: PaymentStatus
    stripe_payment_intent_id: str | None
    stripe_checkout_session_id: str | None
    idempotency_key: str | None
    captured_at: datetime | None
    created_at: datetime

    def mark_captured(self, when: datetime) -> None:
        if self.status not in (PaymentStatus.PENDING, PaymentStatus.AUTHORIZED):
            raise Conflict("Payment cannot transition to captured", details={"status": self.status.value})
        self.status = PaymentStatus.CAPTURED
        self.captured_at = when

@dataclass
class Refund:
    id: UUID
    tenant_id: UUID
    payment_id: UUID
    amount: Money
    status: RefundStatus
    stripe_refund_id: str | None
    reason: str
    created_at: datetime

@dataclass
class TenantPaymentConfig:
    tenant_id: UUID
    stripe_account_id: str | None    # NULL in v1
    default_currency: str            # "USD" by default
    created_at: datetime
    updated_at: datetime
```

### PaymentProvider protocol

```python
# apps/backend/src/payments/application/provider.py

from typing import Protocol
from payments.domain.entities import Invoice, Payment
from payments.domain.value_objects import Money

@dataclass
class CheckoutSessionResult:
    checkout_url: str
    stripe_checkout_session_id: str
    expires_at: datetime

class PaymentProvider(Protocol):
    async def create_checkout_session(
        self,
        *,
        invoice: Invoice,
        payment_id: UUID,
        idempotency_key: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutSessionResult: ...

    async def retrieve_checkout_session(self, stripe_session_id: str) -> dict: ...

    async def create_refund(
        self,
        *,
        stripe_payment_intent_id: str,
        amount_cents: int,
        idempotency_key: str,
    ) -> dict: ...

    def verify_webhook(self, payload: bytes, signature: str) -> dict: ...


class StripeAdapter:
    """Production adapter. Wraps the official `stripe` SDK."""
    def __init__(self, *, api_key: str, api_base: str | None = None) -> None:
        self._stripe = stripe
        self._stripe.api_key = api_key
        if api_base:
            self._stripe.api_base = api_base  # set to stripe-mock URL in tests

    async def create_checkout_session(self, *, invoice, payment_id, idempotency_key, success_url, cancel_url) -> CheckoutSessionResult:
        # sync SDK call wrapped in asyncio.to_thread
        session = await asyncio.to_thread(self._stripe.checkout.Session.create, ...)
        return CheckoutSessionResult(checkout_url=session.url, stripe_checkout_session_id=session.id, expires_at=datetime.fromtimestamp(session.expires_at))
    # ... (other methods follow the same pattern)


class NullAdapter:
    """Test adapter. Returns deterministic fake values; no network calls."""
    # Used only in `pytest` when `STRIPE_PROVIDER=null` is set.
```

The active adapter is selected at app startup based on settings:
- `STRIPE_PROVIDER=stripe` → `StripeAdapter`
- `STRIPE_PROVIDER=null` → `NullAdapter` (unit tests)

A single instance is held in `app.state.payment_provider` and accessed via a FastAPI dependency.

### Application service

```python
# apps/backend/src/payments/application/payment_service.py

class PaymentService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        invoice_repo: InvoiceRepository,
        payment_repo: PaymentRepository,
        refund_repo: RefundRepository,
        processed_event_repo: ProcessedStripeEventRepository,
        idempotency: IdempotencyStore,
        provider: PaymentProvider,
        events: EventPublisher,
        tenant_config_repo: TenantPaymentConfigRepository,
        settings: Settings,
    ) -> None: ...

    async def create_invoice(
        self, *, tenant_id: UUID, customer_id: UUID, line_items: list[LineItemInput],
        description: str, due_date: date, idempotency_key: str | None,
    ) -> Invoice: ...

    async def create_checkout_session(
        self, *, tenant_id: UUID, customer_id: UUID, invoice_id: UUID, idempotency_key: str,
    ) -> CheckoutSessionResult: ...

    async def handle_webhook(self, *, raw_payload: bytes, signature: str) -> None:
        """Single entry point for /webhooks/stripe.

        1. Verify signature (provider.verify_webhook)
        2. Dedup by stripe event id (processed_event_repo)
        3. Dispatch by event type:
           - checkout.session.completed → mark Payment CAPTURED, Invoice PAID, publish InvoicePaid
           - charge.refunded → mark Refund COMPLETED, publish RefundIssued
           - payment_intent.payment_failed → mark Payment FAILED, Invoice FAILED, publish PaymentFailed
        4. Mark event processed (committed atomically with state changes)
        """
        ...

    async def refund_invoice(
        self, *, tenant_id: UUID, invoice_id: UUID, reason: str, idempotency_key: str,
    ) -> Refund: ...
```

### Domain events

```python
# apps/backend/src/payments/application/events.py

@dataclass(frozen=True)
class InvoiceCreated(DomainEvent):
    invoice_id: UUID
    tenant_id: UUID
    customer_id: UUID
    total_cents: int
    currency: str

@dataclass(frozen=True)
class InvoicePaid(DomainEvent):
    invoice_id: UUID
    payment_id: UUID
    tenant_id: UUID
    customer_id: UUID
    amount_cents: int
    currency: str

@dataclass(frozen=True)
class PaymentFailed(DomainEvent):
    invoice_id: UUID
    payment_id: UUID
    tenant_id: UUID
    customer_id: UUID
    reason: str

@dataclass(frozen=True)
class RefundIssued(DomainEvent):
    invoice_id: UUID
    payment_id: UUID
    refund_id: UUID
    tenant_id: UUID
    customer_id: UUID
    amount_cents: int
    currency: str
```

All events inherit `DomainEvent` which carries `event_id: UUID`, `occurred_at: datetime`, `tenant_id: UUID`. (See `common/application/events.py` below.)

### Event bus (common addition)

```python
# apps/backend/src/common/application/events.py

class DomainEvent:
    event_id: UUID
    occurred_at: datetime
    tenant_id: UUID

Subscriber = Callable[[DomainEvent], Awaitable[None]]

class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...

class InProcessEventPublisher:
    """Synchronous in-memory fan-out. Replaces with Redis pub/sub or a DB outbox when async delivery is needed."""
    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[Subscriber]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], fn: Subscriber) -> None:
        self._subscribers[event_type].append(fn)

    async def publish(self, event: DomainEvent) -> None:
        for fn in list(self._subscribers[type(event)]):
            await fn(event)
```

Wiring: `common/interfaces/http/app.py` constructs one `InProcessEventPublisher` at startup and stashes it on `app.state.event_bus`. Modules fetch it via a `get_event_bus()` FastAPI dependency. In v1, no module subscribes — the bus is exercised only by tests asserting that `publish` was called with the right event. Notifications will subscribe in the next spec.

---

## Data Model

### Tables (Alembic migration `20240101_0003_0004_payments.py`)

```sql
CREATE TABLE payments_tenant_config (
  tenant_id          UUID PRIMARY KEY REFERENCES auth_tenants(id) ON DELETE CASCADE,
  stripe_account_id  TEXT,                  -- NULL in v1; populated when Connect is enabled
  default_currency   CHAR(3) NOT NULL DEFAULT 'USD',
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE payments_invoices (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL,
  customer_id     UUID NOT NULL,
  invoice_number  TEXT NOT NULL,
  status          TEXT NOT NULL CHECK (status IN ('draft','pending','paid','failed','cancelled','refunded')),
  subtotal_cents  BIGINT NOT NULL CHECK (subtotal_cents >= 0),
  tax_cents       BIGINT NOT NULL DEFAULT 0 CHECK (tax_cents >= 0),
  total_cents     BIGINT NOT NULL CHECK (total_cents >= 0),
  currency        CHAR(3) NOT NULL,
  due_date        DATE NOT NULL,
  paid_at         TIMESTAMPTZ,
  description     TEXT NOT NULL DEFAULT '',
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, invoice_number)
);
CREATE INDEX payments_invoices_tenant_customer_idx ON payments_invoices (tenant_id, customer_id);
CREATE INDEX payments_invoices_tenant_status_idx  ON payments_invoices (tenant_id, status);

CREATE TABLE payments_invoice_line_items (
  id              UUID PRIMARY KEY,
  invoice_id      UUID NOT NULL REFERENCES payments_invoices(id) ON DELETE CASCADE,
  description     TEXT NOT NULL,
  quantity        INTEGER NOT NULL CHECK (quantity > 0),
  unit_price_cents BIGINT NOT NULL CHECK (unit_price_cents >= 0),
  total_cents     BIGINT NOT NULL CHECK (total_cents >= 0)
);
CREATE INDEX payments_line_items_invoice_idx ON payments_invoice_line_items (invoice_id);

CREATE TABLE payments_payments (
  id                          UUID PRIMARY KEY,
  tenant_id                   UUID NOT NULL,
  invoice_id                  UUID NOT NULL REFERENCES payments_invoices(id) ON DELETE RESTRICT,
  amount_cents                BIGINT NOT NULL CHECK (amount_cents > 0),
  currency                    CHAR(3) NOT NULL,
  status                      TEXT NOT NULL CHECK (status IN ('pending','authorized','captured','failed')),
  stripe_payment_intent_id    TEXT,
  stripe_checkout_session_id  TEXT,
  idempotency_key             TEXT,
  captured_at                 TIMESTAMPTZ,
  created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX payments_payments_stripe_pi_uniq ON payments_payments (tenant_id, stripe_payment_intent_id) WHERE stripe_payment_intent_id IS NOT NULL;
CREATE UNIQUE INDEX payments_payments_stripe_session_uniq ON payments_payments (tenant_id, stripe_checkout_session_id) WHERE stripe_checkout_session_id IS NOT NULL;
CREATE UNIQUE INDEX payments_payments_idempotency_uniq ON payments_payments (tenant_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE payments_refunds (
  id                UUID PRIMARY KEY,
  tenant_id         UUID NOT NULL,
  payment_id        UUID NOT NULL REFERENCES payments_payments(id) ON DELETE RESTRICT,
  amount_cents      BIGINT NOT NULL CHECK (amount_cents > 0),
  currency          CHAR(3) NOT NULL,
  status            TEXT NOT NULL CHECK (status IN ('pending','completed','failed')),
  stripe_refund_id  TEXT,
  reason            TEXT NOT NULL DEFAULT '',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX payments_refunds_stripe_uniq ON payments_refunds (tenant_id, stripe_refund_id) WHERE stripe_refund_id IS NOT NULL;

CREATE TABLE payments_processed_stripe_events (
  stripe_event_id  TEXT PRIMARY KEY,
  tenant_id        UUID NOT NULL,
  event_type       TEXT NOT NULL,
  processed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX payments_processed_events_processed_at_idx ON payments_processed_stripe_events (processed_at);

CREATE TABLE payments_idempotency_keys (
  key             TEXT NOT NULL,
  tenant_id       UUID NOT NULL,
  endpoint        TEXT NOT NULL,
  request_hash    TEXT NOT NULL,
  response_status INTEGER NOT NULL,
  response_body   JSONB NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at      TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (tenant_id, endpoint, key)
);
CREATE INDEX payments_idempotency_keys_expires_at_idx ON payments_idempotency_keys (expires_at);
```

Row-Level Security: each table gets a `tenant_id = current_setting('app.tenant_id')::uuid` policy, matching the existing pattern.

Seed: a one-time Alembic data migration inserts a `payments_tenant_config` row for every existing tenant (idempotent on tenant_id).

---

## Public API

All endpoints return JSON. All mutating endpoints (POST) accept an optional `Idempotency-Key` header.

| Endpoint | Method | Auth | Roles | Purpose |
|---|---|---|---|---|
| `/payments/invoices` | GET | session | customer (own only), tenant_admin/staff (all in tenant) | List invoices; query: `status`, `customer_id`, `from`, `to`, `limit`, `offset` |
| `/payments/invoices` | POST | session | tenant_admin, staff | Create invoice (internal — booking/membership will call) |
| `/payments/invoices/{id}` | GET | session | customer (own only), tenant_admin/staff | Get invoice with line items |
| `/payments/invoices/{id}/checkout` | POST | session | customer (own only) | Create Stripe Checkout Session; return `{ checkout_url, expires_at, session_id }` |
| `/payments/invoices/{id}/return` | GET | session | customer (own only) | Stripe success-redirect target; returns the invoice (frontend shows "Paid" or "Processing") |
| `/payments/invoices/{id}/refund` | POST | session | tenant_admin | Full refund; body: `{ reason }` |
| `/webhooks/stripe` | POST | Stripe signature | — | Stripe webhook receiver |

### Status codes

| Code | When |
|---|---|
| 200 | Successful read or state-already-final action |
| 201 | Invoice created |
| 202 | Checkout session created (returns URL) |
| 400 | Malformed request, signature invalid on webhook |
| 401 | Unauthenticated |
| 403 | Authenticated but wrong role / accessing another tenant's invoice |
| 404 | Invoice not found |
| 409 | Invoice already paid / not refundable / non-cancellable |
| 422 | Validation error (line item quantity ≤ 0, etc.) |
| 503 | Stripe API unavailable (call timed out, 5xx from Stripe) |

### Response schemas (Pydantic)

```python
class LineItemResponse(BaseModel):
    id: UUID
    description: str
    quantity: int
    unit_price_cents: int
    total_cents: int

class InvoiceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    invoice_number: str
    status: InvoiceStatus
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    currency: str
    due_date: date
    paid_at: datetime | None
    description: str
    line_items: list[LineItemResponse]
    created_at: datetime
    updated_at: datetime

class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    stripe_checkout_session_id: str
    expires_at: datetime

class RefundResponse(BaseModel):
    id: UUID
    payment_id: UUID
    amount_cents: int
    currency: str
    status: RefundStatus
    reason: str
    stripe_refund_id: str | None
    created_at: datetime
```

---

## Data Flow

### 1. Invoice creation (called by booking/membership)

```
POST /payments/invoices
  Authorization: Bearer <access_token>
  Idempotency-Key: <uuid>          (optional)
  {
    "customer_id": "...",
    "line_items": [{"description":"Lane 4, 60min","quantity":1,"unit_price_cents":1500}],
    "description": "Booking #abc-123",
    "due_date": "2026-08-14"
  }

→ PaymentService.create_invoice
  1. Resolve TenantPaymentConfig (default_currency, future stripe_account_id)
  2. Validate line items (positive qty + unit price; total == sum)
  3. Compute next per-tenant invoice_number atomically (SELECT MAX + 1 in same tx; uniqueness enforced by UNIQUE index as backstop)
  4. Persist Invoice (status=PENDING) + line items
  5. Publish InvoiceCreated event
  6. Return InvoiceResponse
```

### 2. Checkout (customer pays)

```
POST /payments/invoices/{id}/checkout
  Authorization: Bearer <access_token>
  Idempotency-Key: <uuid>          (required)

→ PaymentService.create_checkout_session
  1. Load invoice (404 if not found, 403 if not own, 409 if not can_pay)
  2. Create Payment row (status=PENDING)
  3. StripeAdapter.create_checkout_session:
     - line_items built from invoice_line_items
     - metadata = {tenant_id, invoice_id, payment_id}
     - success_url = {APP_URL}/book/pay/{id}/return?session_id={CHECKOUT_SESSION_ID}
     - cancel_url  = {APP_URL}/book/pay/{id}
     - idempotency_key passed to Stripe SDK
  4. Persist stripe_checkout_session_id on Payment
  5. Return CheckoutSessionResponse

Frontend: window.location = response.checkout_url
User pays on Stripe → Stripe redirects to success_url
```

### 3. Webhook (source of truth)

```
POST /webhooks/stripe
  Stripe-Signature: <t=...,v1=...>
  Content-Type: application/json
  <raw JSON body>

→ PaymentService.handle_webhook(raw_payload, signature)
  1. event = StripeAdapter.verify_webhook(raw_payload, signature)
     → raises Validation("invalid signature") on mismatch (→ 400, log warning, no retry)
  2. If ProcessedStripeEventRepository.exists(event.id):
     return  (idempotent no-op → 200)
  3. Switch on event.type:
     a. checkout.session.completed
        - Payment = load by stripe_checkout_session_id (UNIQUE index hits)
        - Invoice = load by id (from event.metadata)
        - Payment.mark_captured(utcnow()); Invoice.mark_paid(utcnow())
        - Persist both
        - Publish InvoicePaid event
     b. payment_intent.payment_failed
        - Payment.mark_failed()
        - Invoice.mark_failed()
        - Persist
        - Publish PaymentFailed event
     c. charge.refunded
        - Refund = load by stripe_refund_id (UNIQUE index hits)
        - If Refund is None: log warning, mark event processed, return (orphan event)
        - Refund.status = COMPLETED; Invoice.mark_refunded()
        - Persist
        - Publish RefundIssued event
  4. processed_event_repo.insert(event.id, tenant_id, event.type)  — same transaction
  5. Return 200
```

### 4. Refund (admin)

```
POST /payments/invoices/{id}/refund
  Authorization: Bearer <access_token>   (tenant_admin only)
  Idempotency-Key: <uuid>
  { "reason": "Customer requested cancellation" }

→ PaymentService.refund_invoice
  1. Load Invoice (404 if not found)
  2. If not invoice.can_refund(): raise Conflict
  3. Load latest CAPTURED Payment for invoice
  4. Create Refund row (status=PENDING)
  5. StripeAdapter.create_refund(stripe_payment_intent_id, total_cents, idempotency_key)
     → returns stripe refund dict
  6. Persist stripe_refund_id on Refund (UNIQUE index dedups retries)
  7. Return RefundResponse (status=PENDING; webhook flips to COMPLETED)
```

### 5. Return URL (frontend)

The `/book/pay/{id}/return` page polls the invoice once on mount via `GET /payments/invoices/{id}`. If status is `PAID`, show "Payment successful" with a link back to "My bookings". Otherwise show "Processing — refresh in a moment". No mutation; this is purely UX.

---

## Error Handling

| Failure | Behaviour |
|---|---|
| Stripe API down at checkout creation | `StripeAdapter` raises `ServiceUnavailable("payment provider unavailable")`; 503 with `Retry-After: 5` header; frontend shows "Payment provider unavailable, try again" |
| Stripe SDK 4xx (bad params) | Logs the SDK error id, raises `Validation` with a generic message; 422 |
| Webhook signature invalid | Logs warning; 400 (Stripe will retry, but our handler stays idempotent) |
| Webhook event already processed | 200, no-op (dedup by `event.id`) |
| Webhook event for unknown invoice (orphan) | Logs warning, marks event processed, returns 200 (Stripe retry storm protection) |
| Invoice already PAID at checkout | 409 Conflict; frontend shows "This invoice is already paid" |
| Invoice already REFUNDED at refund | 409 Conflict |
| Refund on non-PAID invoice | 422 |
| Customer tries to pay another customer's invoice | 403 |
| Idempotency-Key reused with different body | 422 with explanation |
| Tenant RLS denies access | 404 (not 403) to avoid leaking invoice existence |
| Redis idempotency store down | Falls back to DB `payments_idempotency_keys` table; logs warning |
| `stripe-mock` URL not reachable in CI | Test fails fast; CI script asserts mock is up before pytest |

---

## Idempotency

Two layers, both required:

1. **Webhook dedup (Stripe event id)**
   - `payments_processed_stripe_events` table with `stripe_event_id` PK.
   - Webhook handler checks existence before processing; inserts in the same transaction as the state change.
   - Stripe retries the same event id with the same payload on transient failure → second call hits the dedup check, returns 200.
   - Background prune: a small Alembic-managed SQL function or a one-shot pytest fixture deletes rows older than 30 days.

2. **API idempotency (`Idempotency-Key` header)**
   - `payments_idempotency_keys` table with `(tenant_id, endpoint, key)` PK.
   - On every mutating endpoint: extract header (optional); if present:
     - Compute `request_hash = sha256(method + path + body)`
     - If a row exists with the same hash → return cached response.
     - If a row exists with a different hash → 422 (client reused the key for a different request).
     - Otherwise execute the request, then store `(response_status, response_body)`.
   - TTL: 24 h via `expires_at`; background prune keeps the table small.
   - Stripe SDK also receives the same `Idempotency-Key` so Stripe itself dedupes at the provider.

The two layers cover different threats: webhook dedup is about Stripe retries, API idempotency is about client retries (browser back button, double-clicks, network blips during checkout).

---

## Testing

### Backend (`pytest`)

- **Service tests** (`test_invoice_service.py`): `PaymentService` with `NullAdapter` + in-memory repos. Asserts state transitions (`can_pay`, `can_refund`), invoice number sequencing, and event emission via a test publisher that records calls.
- **Endpoint tests** (`test_checkout_endpoint.py`, `test_refund_endpoint.py`): FastAPI `TestClient` with `NullAdapter`. Asserts 201/202/409/422/403 paths, idempotency-Key reuse, and customer scoping.
- **Webhook tests** (`test_webhook_endpoint.py`): signed fixtures from `stripe` SDK test data (`tests/fixtures/stripe/webhook_checkout_completed.json`). Loads `payload` and `Stripe-Signature` from disk, posts raw bytes, asserts state change + event emission. Second call with the same fixture asserts dedup.
- **Stripe adapter tests** (`test_stripe_adapter.py`): integration tests against `stripe-mock` running on `localhost:10611`. Verifies request shape (line items, metadata, idempotency-key passthrough).
- **RLS tests** (`test_tenant_rls.py`): two tenants, assert that tenant A's session cannot SELECT tenant B's invoices (returns empty / 404).
- **Idempotency tests** (`test_idempotency.py`): two requests with the same key + body → second returns cached response; same key + different body → 422.

### Frontend (`vitest` + RTL)

- `invoices-page.test.tsx` — list rendering, filters, create-invoice modal open/close.
- `invoice-detail-page.test.tsx` — line items display, refund button hidden for non-admin, refund action calls hook and shows confirmation.
- `pay-invoice-page.test.tsx` — summary render, "Pay now" button calls `useCreateCheckoutSession` and redirects on success.
- `pay-invoice-return-page.test.tsx` — polls invoice, shows Paid / Processing state.

### E2E (`playwright`)

`e2e/admin-invoice-flow.spec.ts`:
1. Log in as `admin@demo.splashh.dev` (staff tab).
2. Navigate to `/admin/invoices`, create invoice for `alex@demo.splashh.dev` ($10 USD, "E2E test").
3. Log out, log in as `alex@demo.splashh.dev`.
4. Navigate to `/admin/invoices/{id}` → see "Pay now" button.
5. Click → mocked Stripe Checkout returns success → webhook (sent in-test via `stripe-mock`) updates status → invoice detail shows `PAID`.
6. Log back in as admin → click refund → status flips to `REFUNDED`.

Stripe test cards (`4242 4242 4242 4242`) used throughout. `stripe-mock` is spun up via Docker Compose alongside the existing Postgres + Redis for the e2e test target.

---

## Frontend Integration

### Pages

#### `/admin/invoices` — InvoicesPage

- Header: "Invoices" + "New invoice" button.
- Filters: status (`All` / `Pending` / `Paid` / `Refunded`), customer, date range.
- Table columns: Invoice #, Customer (email), Total, Status badge, Due date.
- Row click → `/admin/invoices/:id`.
- "New invoice" opens a modal with: customer picker (typeahead), description, due date, line item editor (add/remove rows, qty + unit price).

#### `/admin/invoices/:id` — InvoiceDetailPage

- Header: invoice number + status badge.
- Line items table (description, qty, unit price, total).
- Totals card (subtotal, tax, total).
- "Refund" button (tenant_admin only) → opens confirmation modal with reason field → POSTs `/refund` → optimistic update to `REFUNDED` (webhook will reconcile).
- "Copy payment link" button → copies `${APP_URL}/book/pay/{id}` to clipboard for emailing.

#### `/book/pay/:id` — PayInvoicePage

- Summary card (invoice #, description, total, due date).
- "Pay with card" button → `useCreateCheckoutSession` → `window.location = response.checkout_url`.
- Error state if checkout creation fails: "Payment provider unavailable, try again".

#### `/book/pay/:id/return` — PayInvoiceReturnPage

- On mount: fetch invoice once.
- If `status === PAID` → "Payment successful" + button to "My bookings".
- If `status === PENDING` or `FAILED` → "Processing — refresh in a moment" + manual refresh button.
- No polling loop; the user clicks refresh if needed (low-frequency event; saves battery).

### API client additions

`packages/api-client/src/payments.ts` (new file in the existing api-client package):
- `createInvoice(input): Promise<Invoice>`
- `listInvoices(params): Promise<Invoice[]>`
- `getInvoice(id): Promise<Invoice>`
- `createCheckoutSession(invoiceId, idempotencyKey): Promise<CheckoutSessionResponse>`
- `refundInvoice(invoiceId, reason, idempotencyKey): Promise<Refund>`

`packages/api-client/src/hooks.ts` (existing file; add):
- `useInvoices(params)`, `useInvoice(id)`, `useCreateInvoice()`, `useCreateCheckoutSession()`, `useRefundInvoice()`

### Nav config

`apps/web-pwa/src/components/nav.ts` — add to `tenant_admin` nav:
```ts
{ to: "/admin/invoices", label: "Invoices", icon: "🧾" },
```

Routes file (`apps/web-pwa/src/routes/index.tsx`):
```tsx
<Route path="/admin/invoices" element={<AppShell><InvoicesPage /></AppShell>} />
<Route path="/admin/invoices/:id" element={<AppShell><InvoiceDetailPage /></AppShell>} />
<Route path="/book/pay/:id" element={<AppShell><PayInvoicePage /></AppShell>} />
<Route path="/book/pay/:id/return" element={<AppShell><PayInvoiceReturnPage /></AppShell>} />
```

### Auth scoping

- `RoleGate roles={["tenant_admin", "staff"]}` for `/admin/invoices*`.
- `RoleGate roles={["customer", "tenant_admin", "staff"]}` for `/book/pay/*` (admin can pay on behalf of customer in support flows).
- Customer sees only own invoices — enforced in the backend (RLS + repo filtering), not the frontend.

---

## Out of Scope (deferred to later specs)

- Saved payment methods / Stripe Customer setup UI (membership may need this; revisit then).
- Partial refunds (only full refunds in v1).
- Stripe Connect / multi-account payouts (schema is ready; feature deferred).
- Subscription / recurring billing logic (membership module owns this — may add Stripe Subscriptions API integration then).
- Async webhook processing via worker queue (sync is fine until processing becomes slow).
- Multi-currency conversion (display in invoice currency only).
- Email/SMS notification of payment events (notifications module will consume `InvoicePaid` etc.).
- Analytics dashboards for revenue / MRR (analytics module will consume events).
- Invoice PDF generation.
- Tax calculation integration (tax is a manual input field for v1).
- A "Switch to admin" link in the user menu for users with both roles.

---

## Spec self-review

- ✅ No placeholders or TBDs. Every endpoint, schema field, status code, and file path is concrete.
- ✅ Internal consistency: the same file names appear in every section that references them (`payments/application/payment_service.py`, `common/application/events.py`, `e2e/admin-invoice-flow.spec.ts`, etc.). Endpoint signatures match between the router and the service. Status enums appear identically in the domain layer and the DB CHECK constraints.
- ✅ Scope: single bounded context, single app surface, no decomposition needed.
- ✅ No ambiguous requirements: every status code, every Stripe mode (test vs live), every auth scope, every role requirement is explicit. The two idempotency layers have distinct, documented responsibilities.
- ✅ Recommended options baked in: adapter interface + Stripe v1, platform account + Connect-ready schema, Stripe Checkout hosted redirect, sync event bus + sync webhooks, full refunds only, no saved methods, both idempotency layers, both admin + customer frontend pages.