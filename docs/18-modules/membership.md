# Membership Module

> Plans, subscriptions, renewals, and freezes.

The membership module manages **subscription lifecycle** — plans, subscriptions, renewals, cancellations, and freezes.

> **Status — Not yet implemented.** The backend module folder,
> alembic migration, FastAPI router, and PWA pages do not exist in
> `apps/backend/src/` or `apps/web-pwa/src/`. Implementation is in
> progress on `feature/membership-v1`. For the current intent, see
> [Membership Flow](../../02-architecture/flow-membership.md) and the
> membership design doc.

---

## Purpose

The membership module:
- Defines membership plans (pricing tiers)
- Manages active subscriptions
- Handles renewals and expirations
- Manages membership freezes (pausing)

---

## Aggregates

### MembershipPlan

```python
class MembershipPlan(AggregateRoot):
    id: UUID
    tenant_id: UUID
    name: str  # e.g., "Gold", "Silver"
    description: str
    monthly_price: Decimal
    yearly_price: Decimal
    included_hours: int | None  # Pay-per-hour if None
    max_members_per_booking: int
    booking_window_days: int
    cancellation_window_days: int
    is_active: bool
```

### Subscription

```python
class Subscription(AggregateRoot):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    plan_id: UUID
    status: SubscriptionStatus  # ACTIVE, FROZEN, CANCELLED, EXPIRED
    current_period_start: date
    current_period_end: date
    hours_used: int
    hours_included: int
    frozen_at: date | None
    freeze_end_date: date | None
    cancelled_at: date | None
    cancellation_reason: str | None
```

---

## Public APIs

### Plans

| Endpoint | Method | Description |
|---|---|---|
| `/membership/plans` | GET | List available plans |
| `/membership/plans/{id}` | GET | Get plan details |
| `/membership/plans` | POST | Create plan (tenant admin) |
| `/membership/plans/{id}` | PATCH | Update plan |

### Subscriptions

| Endpoint | Method | Description |
|---|---|---|
| `/membership/subscriptions` | GET | List subscriptions |
| `/membership/subscriptions/{id}` | GET | Get subscription |
| `/membership/subscriptions` | POST | Create subscription |
| `/membership/subscriptions/{id}/freeze` | POST | Freeze subscription |
| `/membership/subscriptions/{id}/unfreeze` | POST | Unfreeze subscription |
| `/membership/subscriptions/{id}/cancel` | POST | Cancel subscription |

---

## Events

| Event | Produced By | Consumed By |
|---|---|---|
| `MembershipStarted` | Subscription creation | booking, notifications, analytics |
| `MembershipRenewed` | Automatic renewal | notifications, analytics |
| `MembershipCancelled` | Cancellation | booking (block), notifications |
| `MembershipExpired` | Expiration | booking (block), notifications |
| `MembershipFrozen` | Freeze | booking (block), notifications |
| `MembershipUnfrozen` | Unfreeze | booking (allow), notifications |

---

## Dependencies

**Upstream:**
- customer (customer lookup)
- auth (tenant context)

**Downstream:**
- booking (verify membership status)
- payments (create invoices)
- notifications (membership events)

---

## Invariants

1. **Pro-rating** — Mid-period changes are prorated
2. **Freeze limits** — Max freeze duration configurable per plan
3. **Cancellation policy** — Cancellation takes effect at period end
4. **No double-billing** — Ensure one active subscription per customer

---

## Open Questions

- How to handle plan downgrades? — Need proration rules
- Should we support gift memberships? — Future feature

---

## Related Documents

- [Payments Module](./payments.md)
- [Booking Module](./booking.md)
