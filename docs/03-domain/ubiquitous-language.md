# Ubiquitous Language

> Glossary of 50+ domain terms used across the codebase. Each term: definition, scope, related terms.

This document defines the shared vocabulary of the platform. The ubiquitous language is the foundation of DDD — every term has a precise meaning that engineers and domain experts share. This level answers: **what each term means**, **its scope**, and **what it's related to**.

---

## Core Entities

### Tenant

The organization (sports club) that owns data and users. Each tenant is completely isolated from other tenants.

> **Scope:** Top-level isolation entity. All other entities belong to a tenant.
> **Related:** User, Customer, Facility, Subscription

```python
class Tenant:
    id: UUID
    name: str  # "Splashh Sports Club"
    slug: str  # "splashh" (URL-friendly)
    settings: dict  # Tenant-specific configuration
    created_at: datetime
```

### User

A person who can authenticate to the system. Users have roles (member, staff, coach, admin) and belong to a tenant.

> **Scope:** Authentication and identity
> **Related:** Tenant, Customer, Session, Role

### Customer (Member)

A member of a sports club who books facilities and pays for memberships. A customer is linked to a user account.

> **Scope:** Member management, bookings, payments
> **Related:** User, Guardian, Waiver, Subscription, Booking

```python
class Customer:
    id: UUID
    user_id: UUID  # Linked user account
    tenant_id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str
    date_of_birth: date | None
    status: CustomerStatus  # ACTIVE, INACTIVE, SUSPENDED
```

### Guardian

A parent or guardian for junior members (under 18). Guardians manage the account on behalf of minors.

> **Scope:** Family accounts, minor management
> **Related:** Customer (child), Waiver

---

## Facility & Resources

### Facility

A physical sports facility (club location). A tenant may have multiple facilities.

> **Scope:** Facility management, location
> **Related:** Tenant, Resource, Slot

```python
class Facility:
    id: UUID
    tenant_id: UUID
    name: str  # "Splashh Downtown"
    address: Address
    timezone: str
    status: FacilityStatus  # OPEN, CLOSED, TEMPORARILY_CLOSED
```

### Resource

A bookable item within a facility — a tennis court, swimming lane, badminton court, gym equipment, etc.

> **Scope:** Bookable items, scheduling
> **Related:** Facility, Slot, AvailabilityRule

```python
class Resource:
    id: UUID
    facility_id: UUID
    name: str  # "Court 1", "Lane 3"
    type: ResourceType  # COURT, LANE, GYM_EQUIPMENT
    sport: Sport  # TENNIS, SWIMMING, BADMINTON
    capacity: int  # Max users per slot
    status: ResourceStatus  # AVAILABLE, MAINTENANCE, OUT_OF_SERVICE
```

### Slot

A time-bound availability of a resource. Slots are generated based on availability rules.

> **Scope:** Booking, time-based availability
> **Related:** Resource, Booking, AvailabilityRule

```python
class Slot:
    id: UUID
    resource_id: UUID
    facility_id: UUID
    tenant_id: UUID
    start_time: datetime
    end_time: datetime
    status: SlotStatus  # AVAILABLE, BOOKED, BLOCKED
    price: Money
```

### AvailabilityRule

Defines when a resource is available for booking — operating hours, blackout dates, slot duration.

> **Scope:** Scheduling, resource configuration
> **Related:** Resource, Facility

```python
class AvailabilityRule:
    id: UUID
    resource_id: UUID
    day_of_week: int  # 0-6 (Monday-Sunday)
    start_time: time
    end_time: time
    slot_duration_minutes: int
    is_active: bool
```

---

## Booking

### Booking

A reservation linking a customer to a slot. The core domain concept.

> **Scope:** Reservations, check-in
> **Related:** Customer, Slot, Payment, CheckIn

```python
class Booking:
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    slot_id: UUID
    status: BookingStatus  # PENDING, CONFIRMED, CHECKED_IN, COMPLETED, CANCELLED, NO_SHOW
    price: Money
    payment_id: UUID | None
    created_at: datetime
    confirmed_at: datetime | None
```

### CheckIn

Record of a member's arrival at the facility for a booking.

> **Scope:** Attendance tracking
> **Related:** Booking, Customer

```python
class CheckIn:
    id: UUID
    booking_id: UUID
    customer_id: UUID
    checked_in_at: datetime
    check_in_method: CheckInMethod  # QR, OTP, MANUAL
```

### WaitlistEntry

A request to be notified when an unavailable slot becomes available.

> **Scope:** Demand management
> **Related:** Slot, Customer

---

## Membership

### MembershipPlan

A product offering defining what a subscription includes.

> **Scope:** Product definition
> **Related:** Subscription, Benefit

```python
class MembershipPlan:
    id: UUID
    tenant_id: UUID
    name: str  # "Gold Annual"
    description: str
    billing_cycle: BillingCycle  # MONTHLY, ANNUAL
    price: Money
    included_bookings: int | None  # None = unlimited
    booking_discount_percent: float
    advance_booking_days: int
```

### Subscription

An active membership linking a customer to a plan.

> **Scope:** Revenue, access control
> **Related:** Customer, MembershipPlan, Payment

```python
class Subscription:
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    plan_id: UUID
    status: SubscriptionStatus  # ACTIVE, FROZEN, PAST_DUE, CANCELLED
    current_period_start: date
    current_period_end: date
    auto_renew: bool
```

### Benefit

Something included in a membership plan — free bookings, guest passes, gym access, etc.

> **Scope:** Plan definition
> **Related:** MembershipPlan

---

## Payments

### Invoice

A bill to a customer for bookings, subscriptions, or other charges.

> **Scope:** Billing
> **Related:** Customer, Payment, LineItem

```python
class Invoice:
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    invoice_number: str
    status: InvoiceStatus  # DRAFT, ISSUED, PAID, VOID
    due_date: date
    total_amount: Money
    paid_amount: Money
```

### Payment

A successful transaction. Payments are processed by external gateways (Stripe, Razorpay).

> **Scope:** Financial transactions
> **Related:** Invoice, Refund, PaymentMethod

```python
class Payment:
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    invoice_id: UUID
    gateway_id: str  # Payment gateway's reference
    amount: Money
    status: PaymentStatus  # PENDING, SUCCEEDED, FAILED, REFUNDED
    payment_method: str  # Card, UPI, Wallet
```

### Refund

A reversal of a payment (full or partial).

> **Scope:** Financial returns
> **Related:** Payment

```python
class Refund:
    id: UUID
    payment_id: UUID
    amount: Money
    reason: str
    status: RefundStatus  # PENDING, SUCCEEDED, FAILED
```

### PaymentMethod

A stored payment method for recurring charges (tokenized card, etc.).

> **Scope:** Stored credentials
> **Related:** Customer, Payment

---

## People

### Coach

An instructor who teaches classes and manages schedules.

> **Scope:** Staff management, scheduling
> **Related:** User, Resource, Class

```python
class Coach:
    id: UUID
    user_id: UUID
    tenant_id: UUID
    name: str
    specialty: Sport
    bio: str | None
    status: CoachStatus  # ACTIVE, INACTIVE
```

### Staff

Club employees with operational roles (receptionist, manager, etc.).

> **Scope:** Employee management
> **Related:** User, Role

---

## Compliance

### Waiver

A signed liability release. Required for facility access in many jurisdictions.

> **Scope:** Legal compliance
> **Related:** Customer

```python
class Waiver:
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    waiver_type: str  # "GENERAL", "SWIMMING", "GYM"
    signed_at: datetime
    expires_at: date
    document_url: str
```

### KYC (Know Your Customer)

Identity verification for members. Required for compliance in some jurisdictions.

> **Scope:** Regulatory compliance
> **Related:** Customer

---

## Communication

### Notification

A message delivered to a customer via some channel.

> **Scope:** Communication
> **Related:** Customer, NotificationTemplate

```python
class Notification:
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    channel: Channel  # SMS, EMAIL, PUSH, IN_APP
    template_code: str
    status: NotificationStatus  # PENDING, SENT, DELIVERED, FAILED
```

### NotificationTemplate

A reusable message template with placeholders.

> **Scope:** Message templates
> **Related:** Notification

---

## Supporting Concepts

### Sport

The type of sport — Swimming, Tennis, Badminton, Cricket, etc.

> **Scope:** Classification
> **Related:** Resource, MembershipPlan

### Session

An active login session for a user.

> **Scope:** Authentication
> **Related:** User

### Role

A collection of permissions — Admin, Staff, Coach, Member.

> **Scope:** Authorization
> **Related:** User, Permission

### Class (Session)

A recurring coached session — a tennis lesson, swimming class, etc.

> **Scope:** Instruction
> **Related:** Coach, Resource, Booking

---

## Aggregates

### Aggregate Root

An aggregate is a cluster of related entities that are treated as a unit for data changes. The aggregate root is the entity that external references point to.

| Aggregate | Root Entity | Contains |
|---|---|---|
| Customer | Customer | Guardian, Waiver |
| Booking | Booking | CheckIn, WaitlistEntry |
| Subscription | Subscription | (references Plan) |
| Invoice | Invoice | LineItem |
| Payment | Payment | (references Invoice) |
| Facility | Facility | Resource, AvailabilityRule |
| Slot | Slot | (references Resource) |

---

## Why This Language

We defined this language because:

1. **Shared understanding** — Engineers and domain experts use the same terms
2. **Ubiquitous** — Used in code, tests, documentation, conversations
3. **Precise** — Each term has a single, unambiguous meaning
4. **Evolving** — New terms are added as the domain grows

---

## What's Next

- [Bounded Contexts](./bounded-contexts.md) — context boundaries.
- [Aggregates](./aggregates.md) — aggregate roots and boundaries.
- [Module Diagram](../02-architecture/module-diagram.md) — context relationships.
