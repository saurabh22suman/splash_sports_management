# Customer Module

> Member profiles, guardians, and waivers.

The customer module manages **member data** — profiles, contact information, guardian relationships for minors, and liability waivers.

---

## Purpose

The customer module:
- Manages member profiles and contact information
- Handles guardian relationships for minor members
- Manages liability waivers and consent
- Provides customer lookup for other modules

---

## Aggregates

### Customer

```python
class Customer(AggregateRoot):
    id: UUID
    tenant_id: UUID
    user_id: UUID  # Link to auth.User
    first_name: str
    last_name: str
    email: str
    phone: str | None
    date_of_birth: date | None
    status: CustomerStatus  # ACTIVE, INACTIVE, PENDING_WAIVER
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    created_at: datetime
    updated_at: datetime
```

### Guardian

```python
class Guardian(AggregateRoot):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    customer_id: UUID  # Link to customer being guardian for
    relationship: str  # PARENT, LEGAL_GUARDIAN
    is_primary: bool
```

### Waiver

```python
class Waiver(AggregateRoot):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    waiver_type: WaiverType  # GENERAL, ACTIVITY_SPECIFIC
    signed_at: datetime
    signed_by: UUID
    ip_address: str
    document_version: str
```

---

## Public APIs

### Customer CRUD

| Endpoint | Method | Description |
|---|---|---|
| `/customers` | GET | List customers |
| `/customers/{id}` | GET | Get customer |
| `/customers` | POST | Create customer |
| `/customers/{id}` | PATCH | Update customer |
| `/customers/{id}` | DELETE | Soft-delete customer |

### Guardian Management

| Endpoint | Method | Description |
|---|---|---|
| `/customers/{id}/guardians` | GET | List guardians for customer |
| `/customers/{id}/guardians` | POST | Add guardian |
| `/customers/{id}/guardians/{guardian_id}` | DELETE | Remove guardian |

### Waiver Management

| Endpoint | Method | Description |
|---|---|---|
| `/customers/{id}/waivers` | GET | List waivers |
| `/customers/{id}/waivers` | POST | Sign waiver |
| `/customers/{id}/waivers/latest` | GET | Get latest waiver |

---

## Events

| Event | Produced By | Consumed By |
|---|---|---|
| `CustomerRegistered` | Customer creation | membership, analytics |
| `CustomerUpdated` | Customer update | analytics |
| `WaiverSigned` | Waiver signing | booking (enables bookings) |
| `WaiverExpired` | Waiver expiration | notifications |

---

## Dependencies

**Upstream:**
- auth (for user_id)

**Downstream:**
- membership (member lookup)
- booking (member verification)
- notifications (contact info)

---

## Invariants

1. **PII handling** — Customer data is PII; must comply with privacy policy
2. **Guardian authorization** — Minors require guardian consent for activities
3. **Waiver requirement** — Customer must have signed waiver before booking
4. **One profile per user** — One customer record per auth user

---

## Open Questions

- Should we support customer merging? — Deferred
- How to handle data export (GDPR)? — Need runbook

---

## Related Documents

- [PII Handling](../09-security/tenant-isolation.md)
- [Customer Profile UI](../05-frontend/component-design.md)
