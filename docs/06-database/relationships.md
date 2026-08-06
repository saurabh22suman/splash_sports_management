# Relationships

> This document covers database relationship patterns: one-to-one, one-to-many, many-to-many, and tenant scoping.

## Overview

Relationships model how entities relate to each other. We use proper foreign keys with constraints to maintain referential integrity.

## One-to-Many (Parent-Child)

### Example: Facility -> Bookings

```sql
-- Parent: facilities
CREATE TABLE facilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Child: bookings (many per facility)
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    facility_id UUID NOT NULL,  -- FK
    customer_id UUID NOT NULL,
    slot_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT fk_bookings_facility
        FOREIGN KEY (facility_id, tenant_id)
        REFERENCES facilities(id, tenant_id)
        ON DELETE RESTRICT
);

-- Index for finding bookings per facility
CREATE INDEX idx_bookings_facility
    ON bookings(facility_id, tenant_id);
```

### ORM Mapping

```python
# Domain entity
class Facility:
    bookings: List[Booking]  # One-to-many


class Booking:
    facility: Facility  # Many-to-one
```

## One-to-One

Use when entities have a 1:1 relationship:

```sql
-- User profile info (sensitive, separated)
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY,  -- Same as users.id
    tenant_id UUID NOT NULL,
    date_of_birth DATE,
    address TEXT,
    emergency_contact TEXT,

    CONSTRAINT fk_profile_user
        FOREIGN KEY (user_id, tenant_id)
        REFERENCES users(id, tenant_id)
        ON DELETE CASCADE
);
```

> **Rule** — Use the same primary key in both tables, or add a unique constraint on the FK.

## Many-to-Many

### Junction Table Pattern

```sql
-- Booking can use multiple equipment items
CREATE TABLE equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    deleted_at TIMESTAMPTZ
);

-- Junction table
CREATE TABLE booking_equipment (
    booking_id UUID NOT NULL,
    equipment_id UUID NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (booking_id, equipment_id),

    CONSTRAINT fk_be_booking
        FOREIGN KEY (booking_id)
        REFERENCES bookings(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_be_equipment
        FOREIGN KEY (equipment_id)
        REFERENCES equipment(id)
        ON DELETE RESTRICT
);

-- Index for finding bookings by equipment
CREATE INDEX idx_booking_equipment_equipment
    ON booking_equipment(equipment_id);
```

### Querying Many-to-Many

```sql
-- Find all equipment for a booking
SELECT e.*
FROM equipment e
JOIN booking_equipment be ON e.id = be.equipment_id
WHERE be.booking_id = 'booking-uuid';

-- Find all bookings with specific equipment
SELECT b.*
FROM bookings b
JOIN booking_equipment be ON b.id = be.booking_id
WHERE be.equipment_id = 'equipment-uuid';
```

## Tenant Scoping on Relationships

> **Rule** — Every foreign key must include `tenant_id`.

### Why Composite FKs

```sql
-- Without tenant_id (BAD)
CONSTRAINT fk_bookings_customer
    FOREIGN KEY (customer_id)
    REFERENCES customers(id)

-- This allows: bookings.customer_id = other_tenant.customer_id

-- With tenant_id (GOOD)
CONSTRAINT fk_bookings_customer
    FOREIGN KEY (customer_id, tenant_id)
    REFERENCES customers(id, tenant_id)

-- PostgreSQL enforces: bookings.tenant_id = customers.tenant_id
```

### Implementation

```sql
CREATE TABLE bookings (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    -- ...
    CONSTRAINT fk_bookings_customer
        FOREIGN KEY (customer_id, tenant_id)
        REFERENCES customers(id, tenant_id)
        ON DELETE RESTRICT
);
```

## Polymorphic Associations (Avoid)

> **Anti-pattern** — Don't use polymorphic associations.

```sql
-- BAD: Polymorphic
CREATE TABLE comments (
    id UUID PRIMARY KEY,
    commentable_id UUID NOT NULL,
    commentable_type VARCHAR(50) NOT NULL,  -- 'booking', 'facility'
    content TEXT
);

-- GOOD: Explicit FKs
CREATE TABLE booking_comments (
    id UUID PRIMARY KEY,
    booking_id UUID NOT NULL,
    content TEXT,

    CONSTRAINT fk_bc_booking
        FOREIGN KEY (booking_id)
        REFERENCES bookings(id)
);

CREATE TABLE facility_comments (
    id UUID PRIMARY KEY,
    facility_id UUID NOT NULL,
    content TEXT,

    CONSTRAINT fk_fc_facility
        FOREIGN KEY (facility_id)
        REFERENCES facilities(id)
);
```

## Self-Referential Relationships

```sql
-- Employee hierarchy
CREATE TABLE employees (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    manager_id UUID,  -- References employees.id
    department_id UUID,

    CONSTRAINT fk_employee_manager
        FOREIGN KEY (manager_id, tenant_id)
        REFERENCES employees(id, tenant_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_employee_department
        FOREIGN KEY (department_id, tenant_id)
        REFERENCES departments(id, tenant_id)
);
```

## Relationship Cardinality Summary

| Cardinality | Pattern | Example |
|-------------|---------|---------|
| One-to-Many | FK in child table | Facility -> Bookings |
| One-to-One | Shared PK or unique FK | User -> Profile |
| Many-to-Many | Junction table | Bookings <-> Equipment |
| Self-ref | FK to same table | Employee -> Manager |

## Anti-Patterns

1. **No FK constraints** — Data drift
2. **Missing tenant in FK** — Cross-tenant data
3. **Polymorphic associations** — No referential integrity
4. **Missing indexes** — Slow joins
5. **Cascade deletes without thought** — Data loss

## Related Documents

- [Schema Design](schema-design.md)
- [Constraints](constraints.md)
- [Naming Standards](naming-standards.md)
- [Tenant Isolation](../09-security/tenant-isolation.md)
