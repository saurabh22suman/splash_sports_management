# Event Catalog

> This document is the complete catalog of all domain events in the system, including producers, consumers, payloads, and retry policies.

## Overview

Every domain event is documented here. Events drive eventual consistency across modules and enable async processing.

## Event Definition Pattern

```python
# src/booking/domain/events.py
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass
class BookingCreatedEvent:
    """Published when a new booking is created."""
    booking_id: UUID
    customer_id: UUID
    facility_id: UUID
    slot_date: str  # ISO date
    slot_start_time: str  # ISO time
    slot_end_time: str
    status: str
    occurred_at: datetime = None

    def __post_init__(self):
        if self.occurred_at is None:
            self.occurred_at = datetime.utcnow()
```

## Complete Event Catalog

### Booking Events

| Event | Producer | Consumers | Idempotency Key | Retry Policy |
|-------|----------|-----------|-----------------|---------------|
| `BookingCreated` | booking | payments, notifications, analytics | `booking:{id}` | 6 retries, exp backoff |
| `BookingConfirmed` | booking | notifications, analytics | `booking:{id}:confirmed` | 6 retries |
| `BookingCancelled` | booking | payments, notifications, analytics | `booking:{id}:cancelled` | 6 retries |
| `BookingRescheduled` | booking | notifications, analytics | `booking:{id}:rescheduled` | 6 retries |
| `BookingCompleted` | booking | analytics, membership | `booking:{id}:completed` | 6 retries |
| `BookingNoShow` | booking | notifications, analytics | `booking:{id}:noshow` | 6 retries |

### Booking Event Payloads

```python
@dataclass
class BookingCreatedEvent:
    booking_id: UUID
    tenant_id: UUID
    customer_id: UUID
    facility_id: UUID
    slot_date: str
    slot_start_time: str
    slot_end_time: str
    status: str
    created_at: datetime
    occurred_at: datetime = None


@dataclass
class BookingConfirmedEvent:
    booking_id: UUID
    tenant_id: UUID
    confirmed_at: datetime
    occurred_at: datetime = None


@dataclass
class BookingCancelledEvent:
    booking_id: UUID
    tenant_id: UUID
    customer_id: UUID
    reason: str
    cancelled_by: UUID
    occurred_at: datetime = None


@dataclass
class BookingRescheduledEvent:
    booking_id: UUID
    tenant_id: UUID
    old_date: str
    old_start_time: str
    new_date: str
    new_start_time: str
    rescheduled_by: UUID
    occurred_at: datetime = None


@dataclass
class BookingCompletedEvent:
    booking_id: UUID
    tenant_id: UUID
    customer_id: UUID
    completed_at: datetime
    occurred_at: datetime = None


@dataclass
class BookingNoShowEvent:
    booking_id: UUID
    tenant_id: UUID
    facility_id: UUID
    scheduled_date: str
    occurred_at: datetime = None
```

### Payment Events

| Event | Producer | Consumers | Idempotency Key | Retry Policy |
|-------|----------|-----------|-----------------|---------------|
| `PaymentAuthorized` | payments | booking | `payment:{id}:authorized` | 6 retries |
| `PaymentCaptured` | payments | booking, analytics | `payment:{id}:captured` | 6 retries |
| `PaymentFailed` | payments | notifications | `payment:{id}:failed` | 6 retries |
| `RefundIssued` | payments | booking, analytics | `refund:{id}` | 6 retries |

```python
@dataclass
class PaymentAuthorizedEvent:
    payment_id: UUID
    booking_id: UUID
    tenant_id: UUID
    amount: int  # cents
    currency: str
    authorized_at: datetime
    occurred_at: datetime = None


@dataclass
class PaymentCapturedEvent:
    payment_id: UUID
    booking_id: UUID
    tenant_id: UUID
    amount: int
    captured_at: datetime
    occurred_at: datetime = None


@dataclass
class PaymentFailedEvent:
    payment_id: UUID
    booking_id: UUID
    tenant_id: UUID
    reason: str
    failed_at: datetime
    occurred_at: datetime = None


@dataclass
class RefundIssuedEvent:
    refund_id: UUID
    payment_id: UUID
    booking_id: UUID
    tenant_id: UUID
    amount: int
    reason: str
    issued_at: datetime
    occurred_at: datetime = None
```

### Membership Events

| Event | Producer | Consumers | Idempotency Key | Retry Policy |
|-------|----------|-----------|-----------------|---------------|
| `MembershipStarted` | membership | booking, notifications | `membership:{id}:started` | 6 retries |
| `MembershipRenewed` | membership | booking, notifications | `membership:{id}:renewed` | 6 retries |
| `MembershipFrozen` | membership | booking | `membership:{id}:frozen` | 6 retries |
| `MembershipCancelled` | membership | booking, notifications | `membership:{id}:cancelled` | 6 retries |
| `MembershipExpired` | membership | notifications | `membership:{id}:expired` | 6 retries |

```python
@dataclass
class MembershipStartedEvent:
    membership_id: UUID
    customer_id: UUID
    tenant_id: UUID
    plan_id: UUID
    started_at: datetime
    expires_at: datetime
    occurred_at: datetime = None


@dataclass
class MembershipRenewedEvent:
    membership_id: UUID
    customer_id: UUID
    tenant_id: UUID
    previous_expires_at: datetime
    new_expires_at: datetime
    renewed_at: datetime
    occurred_at: datetime = None


@dataclass
class MembershipFrozenEvent:
    membership_id: UUID
    customer_id: UUID
    tenant_id: UUID
    frozen_at: datetime
    unfreezes_at: datetime
    occurred_at: datetime = None


@dataclass
class MembershipCancelledEvent:
    membership_id: UUID
    customer_id: UUID
    tenant_id: UUID
    cancelled_at: datetime
    reason: str = None
    occurred_at: datetime = None


@dataclass
class MembershipExpiredEvent:
    membership_id: UUID
    customer_id: UUID
    tenant_id: UUID
    expired_at: datetime
    occurred_at: datetime = None
```

### Customer Events

| Event | Producer | Consumers | Idempotency Key | Retry Policy |
|-------|----------|-----------|-----------------|---------------|
| `CustomerRegistered` | customer | membership, notifications | `customer:{id}:registered` | 6 retries |
| `CustomerCheckedIn` | booking | analytics | `customer:{id}:checkedin:{facility}:{date}` | 6 retries |

```python
@dataclass
class CustomerRegisteredEvent:
    customer_id: UUID
    tenant_id: UUID
    email: str
    name: str
    registered_at: datetime
    occurred_at: datetime = None


@dataclass
class CustomerCheckedInEvent:
    customer_id: UUID
    tenant_id: UUID
    facility_id: UUID
    check_in_time: datetime
    booking_id: UUID = None
    occurred_at: datetime = None
```

### Invoice Events

| Event | Producer | Consumers | Idempotency Key | Retry Policy |
|-------|----------|-----------|-----------------|---------------|
| `InvoiceGenerated` | payments | notifications | `invoice:{id}` | 6 retries |
| `InvoicePaid` | payments | analytics | `invoice:{id}:paid` | 6 retries |

```python
@dataclass
class InvoiceGeneratedEvent:
    invoice_id: UUID
    customer_id: UUID
    tenant_id: UUID
    amount: int
    due_date: datetime
    generated_at: datetime
    occurred_at: datetime = None


@dataclass
class InvoicePaidEvent:
    invoice_id: UUID
    customer_id: UUID
    tenant_id: UUID
    amount: int
    paid_at: datetime
    occurred_at: datetime = None
```

### Notification Events

| Event | Producer | Consumers | Idempotency Key | Retry Policy |
|-------|----------|-----------|-----------------|---------------|
| `NotificationRequested` | any | notifications | `notification:{id}` | 3 retries |
| `NotificationDelivered` | notifications | - | `notification:{id}:delivered` | N/A |
| `NotificationFailed` | notifications | - | `notification:{id}:failed` | N/A |

```python
@dataclass
class NotificationRequestedEvent:
    notification_id: UUID
    tenant_id: UUID
    customer_id: UUID
    channel: str  # email, sms, push
    template: str
    context: dict
    requested_at: datetime
    occurred_at: datetime = None
```

### Audit Events

| Event | Producer | Consumers | Idempotency Key | Retry Policy |
|-------|----------|-----------|-----------------|---------------|
| `AuditRecorded` | any | - | `audit:{id}` | 3 retries |

```python
@dataclass
class AuditRecordedEvent:
    audit_id: UUID
    tenant_id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    user_id: UUID
    changes: dict
    recorded_at: datetime
    occurred_at: datetime = None
```

## Event Naming Convention

> **Rule** — Events are named as `<Entity><PastTenseVerb>Event` or `<Entity><Action>Event`.

| Pattern | Example |
|---------|---------|
| Entity created | `BookingCreatedEvent` |
| Entity updated | `BookingConfirmedEvent` |
| Entity deleted | `BookingCancelledEvent` |
| Entity state change | `MembershipExpiredEvent` |
| Action performed | `CustomerCheckedInEvent` |

## Related Documents

- [Event Bus](event-bus.md)
- [Retry & Failure](retry-failure.md)
- [Event Idempotency](idempotency.md)
