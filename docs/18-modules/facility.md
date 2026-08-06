# Facility Module

> Facilities, resources, and availability.

The facility module manages **physical resources** — sports facilities (courts, pools, gyms), their schedules, and availability rules.

---

## Purpose

The facility module:
- Manages facility inventory (courts, fields, lanes)
- Defines resource types and configurations
- Manages availability rules (opening hours, blackouts)
- Provides availability lookup for bookings

---

## Aggregates

### Facility

```python
class Facility(AggregateRoot):
    id: UUID
    tenant_id: UUID
    name: str  # "Tennis Court 1"
    facility_type: FacilityType  # TENNIS_COURT, POOL_LANE, GYM
    location: str | None
    capacity: int
    description: str | None
    is_active: bool
    images: list[str]
```

### Resource

```python
class Resource(AggregateRoot):
    id: UUID
    facility_id: UUID
    name: str  # "Lane 1"
    resource_type: ResourceType  # COURT, LANE, EQUIPMENT
    capacity: int
    attributes: dict  # { "surface": "hard", "lighting": "led" }
```

### AvailabilityRule

```python
class AvailabilityRule(AggregateRoot):
    id: UUID
    facility_id: UUID
    rule_type: RuleType  # RECURRING, ONE_TIME
    day_of_week: int | None  # 0-6 for recurring
    start_date: date
    end_date: date | None
    start_time: time
    end_time: time
    is_available: bool
    reason: str | None  # If not available
```

---

## Public APIs

### Facilities

| Endpoint | Method | Description |
|---|---|---|
| `/facilities` | GET | List facilities |
| `/facilities/{id}` | GET | Get facility |
| `/facilities` | POST | Create facility |
| `/facilities/{id}` | PATCH | Update facility |
| `/facilities/{id}` | DELETE | Deactivate facility |

### Availability

| Endpoint | Method | Description |
|---|---|---|
| `/facilities/{id}/availability` | GET | Get availability for date range |
| `/facilities/{id}/availability` | POST | Create availability rule |
| `/facilities/{id}/availability/{rule_id}` | DELETE | Remove rule |

---

## Events

| Event | Produced By | Consumed By |
|---|---|---|
| `FacilityCreated` | Facility creation | booking |
| `FacilityUpdated` | Facility update | booking |
| `FacilityDeactivated` | Facility deactivation | booking |
| `AvailabilityRuleCreated` | Rule creation | booking |
| `AvailabilityRuleDeleted` | Rule deletion | booking |

---

## Dependencies

**Upstream:** None (independent module)

**Downstream:**
- booking (resource availability)
- analytics (facility utilization)

---

## Invariants

1. **Resource uniqueness** — Each resource belongs to one facility
2. **No overlapping rules** — Availability rules must not overlap
3. **Facility activation** — Cannot book inactive facilities

---

## Open Questions

- How to handle facility maintenance windows? — Need blackout rules
- Should we support equipment booking? — Future feature

---

## Related Documents

- [Booking Module](./booking.md)
