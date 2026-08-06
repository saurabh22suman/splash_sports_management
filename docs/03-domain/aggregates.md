# Aggregates

> Key aggregates per bounded context: root entity, invariants, consistency boundary, repository, key events.

This document details the aggregate roots in each bounded context. Aggregates are the transactional boundaries of the domain — changes to an aggregate are atomic and consistent. This level answers: **what each aggregate contains**, **what rules it enforces**, and **what events it publishes**.

---

## Overview Table

| Context | Aggregate Root | Entities | Repository |
|---|---|---|---|
| auth | User, Tenant | Session, Role, Permission | UserRepository, TenantRepository |
| customer | Customer | Guardian, Waiver | CustomerRepository |
| membership | MembershipPlan, Subscription | MembershipBenefit | PlanRepository, SubscriptionRepository |
| facility | Facility, Resource | AvailabilityRule, Slot | FacilityRepository, ResourceRepository |
| booking | Booking | WaitlistEntry, CheckIn | BookingRepository |
| payments | Invoice | Payment, Refund | InvoiceRepository |

---

## auth Context

### User Aggregate

```python
class User(AggregateRoot):
    """Identity and authentication."""
    id: UUID
    tenant_id: UUID
    email: str
    password_hash: str
    role: Role
    mfa_enabled: bool
    mfa_secret: str | None  # Encrypted
    status: UserStatus  # ACTIVE, INACTIVE, SUSPENDED
    created_at: datetime
    updated_at: datetime
```

#### Invariants

- Email is unique per tenant
- Password must meet complexity requirements
- MFA secret is encrypted at rest

#### Consistency Boundary

User is the boundary — other entities reference user_id but are not part of the aggregate.

#### Repository

```python
class UserRepository:
    def get_by_id(self, user_id: UUID, tenant_id: UUID) -> User | None
    def get_by_email(self, email: str, tenant_id: UUID) -> User | None
    def save(self, user: User) -> User
    def delete(self, user_id: UUID, tenant_id: UUID) -> bool
```

#### Key Events

- `UserCreated` — Emitted when a user is created
- `UserUpdated` — Emitted on profile changes
- `PasswordChanged` — Emitted on password reset

### Tenant Aggregate

```python
class Tenant(AggregateRoot):
    """Organization (sports club)."""
    id: UUID
    name: str
    slug: str  # URL-friendly
    settings: dict  # Tenant-specific config
    status: TenantStatus  # ACTIVE, INACTIVE
    created_at: datetime
```

---

## customer Context

### Customer Aggregate

```python
class Customer(AggregateRoot):
    """Member with profile."""
    id: UUID
    tenant_id: UUID
    user_id: UUID  # Linked user account
    first_name: str
    last_name: str
    email: str
    phone: str
    date_of_birth: date | None
    address: Address | None
    status: CustomerStatus  # ACTIVE, INACTIVE, SUSPENDED
    created_at: datetime
    updated_at: datetime

    # Value objects
    guardians: list[Guardian]
    waivers: list[Waiver]
```

#### Invariants

- Must have valid user account
- Email unique per tenant
- Phone must be validated
- Waivers must be current for facility access

#### Consistency Boundary

Customer aggregate includes Guardians and Waivers. Changes to any are atomic.

```python
def add_guardian(self, guardian: Guardian) -> None:
    """Add guardian relationship."""
    if guardian.minor_age < 18:
        raise ValueError("Guardian only for minors")
    self.guardians.append(guardian)

def sign_waiver(self, waiver: Waiver) -> None:
    """Sign liability waiver."""
    # Check existing valid waiver
    existing = [w for w in self.waivers if w.is_valid]
    if existing:
        raise ValueError("Waiver already signed")
    self.waivers.append(waiver)
```

#### Repository

```python
class CustomerRepository:
    def get_by_id(self, customer_id: UUID, tenant_id: UUID) -> Customer | None
    def get_by_user_id(self, user_id: UUID, tenant_id: UUID) -> Customer | None
    def find_by_email(self, email: str, tenant_id: UUID) -> Customer | None
    def save(self, customer: Customer) -> Customer
    def list(self, tenant_id: UUID, filters: CustomerFilter) -> list[Customer]
```

#### Key Events

- `CustomerCreated` — Emitted when customer profile created
- `CustomerUpdated` — Emitted on profile changes
- `WaiverSigned` — Emitted when waiver signed

---

## membership Context

### MembershipPlan Aggregate

```python
class MembershipPlan(AggregateRoot):
    """Product offering."""
    id: UUID
    tenant_id: UUID
    name: str
    description: str
    billing_cycle: BillingCycle  # MONTHLY, ANNUAL
    price: Money
    included_bookings: int | None  # None = unlimited
    booking_discount_percent: float
    advance_booking_days: int
    guest_passes: int
    can_freeze: bool
    freeze_limit_days: int
    min_term_months: int
    is_active: bool
    created_at: datetime
```

### Subscription Aggregate

```python
class Subscription(AggregateRoot):
    """Active membership."""
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    plan_id: UUID
    status: SubscriptionStatus  # ACTIVE, FROZEN, PAST_DUE, CANCELLED
    current_period_start: date
    current_period_end: date
    auto_renew: bool
    frozen_until: date | None
    frozen_days_used: int
    created_at: datetime
    cancelled_at: datetime | None
```

#### Invariants

- Cannot freeze if plan doesn't allow it
- Cannot exceed freeze limit
- Cannot cancel if outstanding balance exists
- Must have active customer to have subscription

#### Consistency Boundary

Subscription references Plan but doesn't contain it. Changes to subscription are atomic.

```python
def freeze(self, days: int) -> None:
    """Freeze membership."""
    if self.status != SubscriptionStatus.ACTIVE:
        raise InvalidStateError("Can only freeze active subscription")

    if self.plan.frozen_days_used + days > self.plan.freeze_limit_days:
        raise ValueError("Freeze limit exceeded")

    self.status = SubscriptionStatus.FROZEN
    self.frozen_until = date.today() + timedelta(days=days)
    self.frozen_days_used += days
```

#### Repository

```python
class SubscriptionRepository:
    def get_by_id(self, subscription_id: UUID, tenant_id: UUID) -> Subscription | None
    def get_by_customer(self, customer_id: UUID, tenant_id: UUID) -> list[Subscription]
    def get_active(self, customer_id: UUID, tenant_id: UUID) -> Subscription | None
    def find_expiring(self, date: date) -> list[Subscription]
    def save(self, subscription: Subscription) -> Subscription
```

#### Key Events

- `SubscriptionActivated` — Emitted when subscription becomes active
- `SubscriptionRenewed` — Emitted on renewal
- `SubscriptionFrozen` — Emitted on freeze
- `SubscriptionCancelled` — Emitted on cancellation
- `SubscriptionExpired` — Emitted when subscription ends

---

## facility Context

### Facility Aggregate

```python
class Facility(AggregateRoot):
    """Physical location."""
    id: UUID
    tenant_id: UUID
    name: str
    address: Address
    timezone: str
    status: FacilityStatus  # OPEN, CLOSED, TEMPORARILY_CLOSED
    settings: dict

    # Entities
    resources: list[Resource]
```

### Resource Aggregate

```python
class Resource(AggregateRoot):
    """Bookable item."""
    id: UUID
    facility_id: UUID
    tenant_id: UUID
    name: str
    type: ResourceType  # COURT, LANE, GYM_EQUIPMENT
    sport: Sport
    capacity: int
    status: ResourceStatus  # AVAILABLE, MAINTENANCE, OUT_OF_SERVICE
    created_at: datetime

    # Entities
    availability_rules: list[AvailabilityRule]
```

### Slot Entity

```python
class Slot(Entity):
    """Time-bound availability."""
    id: UUID
    resource_id: UUID
    facility_id: UUID
    tenant_id: UUID
    start_time: datetime
    end_time: datetime
    status: SlotStatus  # AVAILABLE, BOOKED, BLOCKED
    price: Money
```

> **Note:** Slot is an entity, not an aggregate root. It belongs to Resource and is managed through Resource.

#### Invariants

- Slot times must not overlap for same resource
- Slot duration must match availability rule
- Price must be positive

#### Repository

```python
class SlotRepository:
    def get_by_id(self, slot_id: UUID, tenant_id: UUID) -> Slot | None
    def get_for_update(self, slot_id: UUID, tenant_id: UUID) -> Slot | None
    def find_available(self, resource_id: UUID, date: date) -> list[Slot]
    def mark_booked(self, slot_id: UUID, tenant_id: UUID) -> bool
    def mark_available(self, slot_id: UUID, tenant_id: UUID) -> bool
```

#### Key Events

- `SlotCreated` — Emitted when slot generated
- `SlotBooked` — Emitted when slot reserved
- `SlotReleased` — Emitted when booking cancelled

---

## booking Context

### Booking Aggregate

```python
class Booking(AggregateRoot):
    """Reservation."""
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    slot_id: UUID
    status: BookingStatus  # PENDING, CONFIRMED, CHECKED_IN, COMPLETED, CANCELLED, NO_SHOW
    price: Money
    payment_id: UUID | None
    notes: str | None
    created_at: datetime
    confirmed_at: datetime | None
    checked_in_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
```

#### Invariants

- Cannot check in before booking time
- Cannot cancel after check-in
- Cannot confirm without available slot
- Payment required for confirmed booking (unless membership covers it)

#### Consistency Boundary

Booking includes CheckIn. WaitlistEntry is separate.

```python
def confirm(self) -> None:
    """Confirm booking."""
    if self.status != BookingStatus.PENDING:
        raise InvalidStateError(f"Cannot confirm {self.status}")
    self.status = BookingStatus.CONFIRMED
    self.confirmed_at = datetime.utcnow()

def cancel(self, reason: str) -> None:
    """Cancel booking."""
    if self.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
        raise InvalidStateError(f"Cannot cancel {self.status}")
    self.status = BookingStatus.CANCELLED
    self.cancelled_at = datetime.utcnow()
    self.cancellation_reason = reason

def check_in(self) -> None:
    """Check in to booking."""
    if self.status != BookingStatus.CONFIRMED:
        raise InvalidStateError(f"Cannot check in {self.status}")
    # Allow check-in 15 min before to 30 min after
    self.status = BookingStatus.CHECKED_IN
    self.checked_in_at = datetime.utcnow()
```

#### Repository

```python
class BookingRepository:
    def get_by_id(self, booking_id: UUID, tenant_id: UUID) -> Booking | None
    def find_by_customer(self, customer_id: UUID, tenant_id: UUID) -> list[Booking]
    def find_by_slot(self, slot_id: UUID, tenant_id: UUID) -> Booking | None
    def find_conflicting(self, slot_id: UUID, tenant_id: UUID) -> Booking | None
    def save(self, booking: Booking) -> Booking
```

#### Key Events

- `BookingCreated` — Emitted when booking created
- `BookingConfirmed` — Emitted when payment succeeds
- `BookingCancelled` — Emitted when cancelled
- `BookingCheckedIn` — Emitted on check-in

---

## payments Context

### Invoice Aggregate

```python
class Invoice(AggregateRoot):
    """Bill to customer."""
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    invoice_number: str
    status: InvoiceStatus  # DRAFT, ISSUED, PAID, VOID
    line_items: list[LineItem]
    subtotal: Money
    tax_amount: Money
    total_amount: Money
    due_date: date
    paid_amount: Money
    created_at: datetime
    issued_at: datetime | None
    paid_at: datetime | None

class LineItem(Entity):
    description: str
    quantity: int
    unit_price: Money
    total: Money
```

### Payment Entity

```python
class Payment(Entity):
    """Transaction record."""
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    customer_id: UUID
    gateway_id: str
    amount: Money
    status: PaymentStatus  # PENDING, SUCCEEDED, FAILED, REFUNDED
    payment_method: str
    gateway_response: dict
    created_at: datetime
    succeeded_at: datetime | None
```

### Refund Entity

```python
class Refund(Entity):
    """Payment reversal."""
    id: UUID
    payment_id: UUID
    amount: Money
    reason: str
    status: RefundStatus  # PENDING, SUCCEEDED, FAILED
    gateway_refund_id: str | None
    created_at: datetime
    succeeded_at: datetime | None
```

#### Invariants

- Invoice total must equal sum of line items + tax
- Cannot pay more than invoice total
- Refund cannot exceed original payment amount

#### Repository

```python
class InvoiceRepository:
    def get_by_id(self, invoice_id: UUID, tenant_id: UUID) -> Invoice | None
    def find_by_customer(self, customer_id: UUID, tenant_id: UUID) -> list[Invoice]
    def find_pending(self, tenant_id: UUID) -> list[Invoice]
    def save(self, invoice: Invoice) -> Invoice
```

#### Key Events

- `InvoiceCreated` — Emitted when invoice created
- `InvoicePaid` — Emitted when payment succeeds
- `PaymentSucceeded` — Emitted for payment events
- `RefundProcessed` — Emitted when refund completes

---

## notifications Context

### NotificationTemplate Aggregate

```python
class NotificationTemplate(AggregateRoot):
    """Message template."""
    id: UUID
    tenant_id: UUID
    code: str  # Unique per tenant
    channel: Channel  # SMS, EMAIL, PUSH, IN_APP
    subject: str | None  # For email
    body: str
    short_body: str | None  # For SMS
    is_active: bool
    locale: str
    created_at: datetime
    updated_at: datetime
```

### NotificationDelivery Entity

```python
class NotificationDelivery(Entity):
    """Delivery attempt."""
    id: UUID
    notification_id: UUID
    channel: Channel
    status: DeliveryStatus  # PENDING, SENT, DELIVERED, FAILED, BOUNCED
    external_id: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    error: str | None
```

---

## What Makes a Good Aggregate

### Encapsulation

Aggregate internals are hidden. External code interacts only through the aggregate root.

### Invariants

Aggregates enforce business rules. The aggregate is the consistency boundary.

### Transactions

Changes to an aggregate are atomic. If any part fails, the entire aggregate rolls back.

### Events

Aggregates publish domain events when significant things happen. Events are the external interface.

---

## What's Next

- [Bounded Contexts](./bounded-contexts.md) — context definitions.
- [Ubiquitous Language](./ubiquitous-language.md) — term definitions.
- [Module Diagram](../02-architecture/module-diagram.md) — context relationships.
