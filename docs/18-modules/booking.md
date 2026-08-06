# Booking Module

> Reservations, slots, check-in, and waitlist.

The booking module manages **facility reservations** — creating, canceling, and checking in bookings. It coordinates with facility, customer, membership, and payment modules.

---

## Purpose

The booking module:
- Creates and manages facility bookings
- Handles booking cancellations
- Manages check-in and no-show tracking
- Maintains waitlist for full slots

---

## Aggregates

### Booking

```python
class Booking(AggregateRoot):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    facility_id: UUID
    slot_id: UUID
    status: BookingStatus  # CONFIRMED, CHECKED_IN, COMPLETED, CANCELLED, NO_SHOW
    start_time: datetime
    end_time: datetime
    guest_count: int
    total_price: Decimal
    checked_in_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
```

### Slot

```python
class Slot(AggregateRoot):
    id: UUID
    facility_id: UUID
    date: date
    start_time: time
    end_time: time
    is_available: bool
    max_capacity: int
    current_bookings: int
```

### WaitlistEntry

```python
class WaitlistEntry(AggregateRoot):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    facility_id: UUID
    requested_date: date
    requested_start_time: time
    position: int  # In queue
    notified_at: datetime | None
    expires_at: datetime
```

---

## Public APIs

### Bookings

| Endpoint | Method | Description |
|---|---|---|
| `/bookings` | GET | List bookings |
| `/bookings/{id}` | GET | Get booking |
| `/bookings` | POST | Create booking |
| `/bookings/{id}/cancel` | POST | Cancel booking |
| `/bookings/{id}/check-in` | POST | Check in |
| `/bookings/{id}/reschedule` | POST | Reschedule |

### Availability

| Endpoint | Method | Description |
|---|---|---|
| `/bookings/availability` | GET | Get available slots |

### Waitlist

| Endpoint | Method | Description |
|---|---|---|
| `/bookings/waitlist` | GET | List waitlist entries |
| `/bookings/waitlist` | POST | Join waitlist |
| `/bookings/waitlist/{id}` | DELETE | Leave waitlist |

---

## Events

| Event | Produced By | Consumed By |
|---|---|---|
| `BookingCreated` | Booking creation | payments, notifications, analytics |
| `BookingConfirmed` | Payment confirmed | notifications |
| `BookingCancelled` | Cancellation | payments (refund), notifications |
| `BookingRescheduled` | Rescheduling | payments, notifications |
| `BookingCompleted` | Check-in + time passed | analytics |
| `CustomerCheckedIn` | Check-in | analytics |
| `CustomerNoShow` | No-show | analytics |

---

## Dependencies

**Upstream:**
- customer (customer lookup)
- facility (facility/slot lookup)
- membership (verify active membership)
- payments (verify payment)

**Downstream:**
- payments (create invoice)
- notifications (booking reminders)

---

## Invariants

1. **No double-booking** — Slot cannot have overlapping bookings
2. **Cancellation policy** — Cancellations within X hours may be non-refundable
3. **Check-in window** — Must check in within X minutes of start
4. **Membership required** — Customer must have active membership
5. **Payment required** — Booking not confirmed until paid

---

## Open Questions

- How to handle partial refunds? — Need cancellation policy rules
- Should we support recurring bookings? — Future feature

---

## Related Documents

- [Payments Module](./payments.md)
- [Facility Module](./facility.md)
- [Membership Module](./membership.md)
