# Payments Module

> Invoices, payment links, refunds, and Razorpay webhook handling.

The payments module manages **financial transactions** — creating invoices,
issuing Razorpay-hosted payment links, processing webhook events, and
issuing refunds. All amounts are denominated in INR (paise) and use a
`Money` value object. Card data is never stored; Razorpay is the only
payment surface.

---

## Purpose

The payments module:
- Creates invoices for one or more line items
- Issues Razorpay-hosted payment links for invoices
- Verifies and processes Razorpay webhook events (`payment.captured`, `payment.failed`, `refund.processed`)
- Issues refunds (full only at this stage) and emits refund events
- Enforces idempotency on all mutating endpoints via `Idempotency-Key`

---

## Aggregates

### Invoice

```python
class Invoice(AggregateRoot):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    invoice_number: str
    status: InvoiceStatus           # DRAFT, PENDING, PAID, FAILED, REFUNDED
    subtotal: Money
    tax: Money
    total: Money
    due_date: date
    paid_at: datetime | None
    description: str
    line_items: list[LineItem]
    created_at: datetime
    updated_at: datetime

    def can_pay(self) -> bool: ...
    def can_refund(self) -> bool: ...
    def mark_paid(self, when: datetime) -> None: ...
    def mark_failed(self) -> None: ...
    def mark_refunded(self, when: datetime) -> None: ...
```

### Payment

```python
class Payment(AggregateRoot):
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    amount: Money
    status: PaymentStatus           # PENDING, CAPTURED, FAILED
    razorpay_payment_id: str | None       # set on payment.captured
    razorpay_payment_link_id: str | None  # set on link creation
    idempotency_key: str | None
    captured_at: datetime | None
    created_at: datetime

    def mark_captured(self, when: datetime) -> None: ...
```

### Refund

```python
class Refund(AggregateRoot):
    id: UUID
    tenant_id: UUID
    payment_id: UUID
    amount: Money
    status: RefundStatus            # PENDING, COMPLETED, FAILED
    razorpay_refund_id: str | None
    reason: str
    created_at: datetime
```

### TenantPaymentConfig

```python
class TenantPaymentConfig(AggregateRoot):
    tenant_id: UUID
    razorpay_account_id: str | None
    default_currency: str           # always "INR" at this stage
    created_at: datetime
    updated_at: datetime
```

---

## Public APIs

All endpoints are mounted under the FastAPI app. The `Idempotency-Key`
header is required on every mutating endpoint that touches Razorpay
(`/payment-link`, `/refund`) and optional (but recommended) on
`POST /payments/invoices`.

### Invoices

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/payments/invoices` | tenant_admin | Optional `Idempotency-Key`; body = `{ customer_id, description, due_date, line_items[] }` |
| `GET`  | `/payments/invoices` | any authenticated | Filterable by `status` and `customer_id`; customers see only their own invoices |
| `GET`  | `/payments/invoices/{invoice_id}` | any authenticated | Returns 404 to avoid leaking existence of unauthorized invoices |

### Payment Links

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/payments/invoices/{invoice_id}/payment-link` | customer only | **Requires `Idempotency-Key`**. Returns `{ short_url, razorpay_payment_link_id, expires_at }` |

### Refunds

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/payments/invoices/{invoice_id}/refund` | tenant_admin only | **Requires `Idempotency-Key`**; body = `{ reason }` (full refund only) |

### Webhooks

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/webhooks/razorpay` | public (signature-verified) | HMAC-SHA256 via `X-Razorpay-Signature` header; handles `payment.captured`, `payment.failed`, `refund.processed` |

---

## Events

All events are frozen dataclasses extending `DomainEvent`. `invoice_id` and
`customer_id` are present on every event for downstream correlation. `currency`
defaults to `"INR"`.

| Event | When | Consumed by |
|---|---|---|
| `InvoiceCreated` | After invoice is persisted | notifications, analytics |
| `InvoicePaid` | After Razorpay `payment.captured` webhook | booking (confirm), membership (activate), notifications |
| `PaymentFailed` | After Razorpay `payment.failed` webhook | booking (cancel), notifications |
| `RefundIssued` | After `refund_invoice` completes | notifications, analytics |

---

## Idempotency

Mutating endpoints accept an `Idempotency-Key` header. The
`IdempotencyStore` (in `payments/infrastructure/idempotency.py`) deduplicates
requests across retries:

- Backed by Redis with a PostgreSQL fallback
- Keys are scoped to `(tenant_id, idempotency_key)` and TTL-bounded
- Same key + same body → returns the original response
- Same key + different body → `Conflict` (409)

---

## Dependencies

**Upstream:**
- `auth` (tenant context, role check)
- `customer` (customer lookup for invoice creation)

**Downstream:**
- `booking` (consumes `InvoicePaid` to confirm a booking; `PaymentFailed` to cancel)
- `membership` (consumes `InvoicePaid` to activate a subscription — future work)
- `notifications` (consumes all four events)
- `analytics` (consumes all four events)

---

## Invariants

1. **Idempotency** — Same request must not double-charge
2. **No double-capture** — Handled by Razorpay payment-link lifecycle
3. **Refund limit** — Full refund only at this stage (`RefundRequest` accepts `reason` only); partial refunds are an open question
4. **INR only** — `default_currency` is `"INR"`; the `Money` value object is paise-denominated
5. **No stored card data** — Razorpay-hosted page is the only payment surface; we never see PAN/CVV
6. **Tenant isolation** — Every query is scoped by `tenant_id`; customers can only read their own invoices

---

## Webhook Security

- The `/webhooks/razorpay` endpoint is the only public (unauthenticated) payment endpoint
- Requests are verified using `razorpay.Client.utility.verify_webhook_signature`
- Missing or invalid `X-Razorpay-Signature` header → `400`
- Successful processing is **idempotent on Razorpay event id** — duplicate webhook deliveries are silently dropped

---

## Open Questions

- Partial refunds (`RefundRequest.amount` optional) — Deferred; today, refunds are always full
- Multi-currency support — Deferred; INR is the only accepted currency
- Payment plans / installments — Out of scope

---

## Related Documents

- [Payment Flow](../../02-architecture/flow-payment.md)
- [Secrets Management](../../09-security/secrets-management.md)
- [Idempotency Pattern](../../02-architecture/caching-strategy.md#idempotency)
- [Booking Module](./booking.md)
