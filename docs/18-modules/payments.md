# Payments Module

> Invoices, payments, and refunds.

The payments module manages **financial transactions** — creating invoices, processing payments, and issuing refunds. It integrates with Stripe for payment processing.

---

## Purpose

The payments module:
- Creates invoices for bookings and memberships
- Processes payments via Stripe
- Handles refunds
- Manages payment methods

---

## Aggregates

### Invoice

```python
class Invoice(AggregateRoot):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    invoice_number: str
    status: InvoiceStatus  # DRAFT, PENDING, PAID, FAILED, CANCELLED
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    due_date: date
    paid_at: datetime | None
    line_items: list[InvoiceLineItem]
    created_at: datetime
```

### Payment

```python
class Payment(AggregateRoot):
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    amount: Decimal
    status: PaymentStatus  # AUTHORIZED, CAPTURED, FAILED, REFUNDED
    stripe_payment_intent_id: str
    payment_method: str  # CARD, BANK
    captured_at: datetime | None
    refund_id: str | None
```

### Refund

```python
class Refund(AggregateRoot):
    id: UUID
    tenant_id: UUID
    payment_id: UUID
    amount: Decimal
    reason: str
    status: RefundStatus  # PENDING, COMPLETED, FAILED
    stripe_refund_id: str
    created_at: datetime
```

---

## Public APIs

### Invoices

| Endpoint | Method | Description |
|---|---|---|
| `/payments/invoices` | GET | List invoices |
| `/payments/invoices/{id}` | GET | Get invoice |
| `/payments/invoices` | POST | Create invoice |
| `/payments/invoices/{id}/send` | POST | Send invoice |

### Payments

| Endpoint | Method | Description |
|---|---|---|
| `/payments/{id}` | GET | Get payment |
| `/payments` | POST | Process payment |
| `/payments/{id}/capture` | POST | Capture authorized payment |
| `/payments/{id}/refund` | POST | Issue refund |

### Payment Methods

| Endpoint | Method | Description |
|---|---|---|
| `/payments/methods` | GET | List saved methods |
| `/payments/methods` | POST | Add payment method |
| `/payments/methods/{id}` | DELETE | Remove method |

---

## Events

| Event | Produced By | Consumed By |
|---|---|---|
| `InvoiceGenerated` | Invoice creation | notifications |
| `InvoiceSent` | Invoice sent | notifications |
| `InvoicePaid` | Payment captured | booking, membership, notifications |
| `InvoiceFailed` | Payment failed | notifications |
| `PaymentAuthorized` | Payment authorized | booking (confirm) |
| `PaymentCaptured` | Payment captured | booking (confirm) |
| `PaymentFailed` | Payment failed | booking (cancel) |
| `RefundIssued` | Refund created | notifications, analytics |

---

## Dependencies

**Upstream:**
- booking (invoice from booking)
- membership (invoice from subscription)

**Downstream:**
- notifications (payment receipts)

---

## Invariants

1. **Idempotency** — Same request must not double-charge
2. **No double-capture** — Payment can only be captured once
3. **Refund limit** — Cannot refund more than original payment
4. **PII handling** — No card details stored (Stripe-only)

---

## Open Questions

- Support for partial refunds? — Need business rules
- Support for payment plans? — Future feature

---

## Related Documents

- [Stripe Integration](../09-security/secrets-management.md)
- [Booking Module](./booking.md)
