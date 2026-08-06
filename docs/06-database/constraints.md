# Constraints

> This document covers PostgreSQL constraints: primary keys, foreign keys, unique, check, and exclusion constraints.

## Overview

Constraints enforce data integrity at the database level. They are the last line of defense against invalid data.

## Primary Keys

```sql
-- UUID primary key (recommended)
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid()
);

-- Composite primary key (rare)
CREATE TABLE booking_lines (
    booking_id UUID NOT NULL,
    line_number INTEGER NOT NULL,
    equipment_id UUID NOT NULL,
    PRIMARY KEY (booking_id, line_number)
);
```

> **Rule** — Use UUID for all primary keys.

## Foreign Keys

### Basic FK

```sql
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL,
    facility_id UUID NOT NULL,
    -- Simple FK
    CONSTRAINT fk_bookings_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(id)
        ON DELETE RESTRICT
);
```

### Composite FK (with tenant_id)

```sql
-- Tenant-scoped FK
CREATE TABLE bookings (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    facility_id UUID NOT NULL,

    CONSTRAINT fk_bookings_customer
        FOREIGN KEY (customer_id, tenant_id)
        REFERENCES customers(id, tenant_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_bookings_facility
        FOREIGN KEY (facility_id, tenant_id)
        REFERENCES facilities(id, tenant_id)
        ON DELETE RESTRICT
);
```

### FK Actions

| Action | Behavior |
|--------|----------|
| `ON DELETE NO ACTION` | Error if child exists (default) |
| `ON DELETE RESTRICT` | Same as NO ACTION (immediate check) |
| `ON DELETE CASCADE` | Delete children automatically |
| `ON DELETE SET NULL` | Set FK to NULL |
| `ON DELETE SET DEFAULT` | Set FK to default value |

> **Rule** — Use `ON DELETE RESTRICT` for most FKs. Use `CASCADE` only when child should be deleted with parent.

```sql
-- Good: Prevent deletion of customer with bookings
CONSTRAINT fk_bookings_customer
    FOREIGN KEY (customer_id) REFERENCES customers(id)
    ON DELETE RESTRICT

-- Good: Delete lines with booking
CONSTRAINT fk_booking_lines_booking
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
    ON DELETE CASCADE
```

### Deferrable Constraints

For circular references:

```sql
-- Defer FK check until commit
CREATE TABLE employees (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    manager_id UUID,
    CONSTRAINT fk_employee_manager
        FOREIGN KEY (manager_id)
        REFERENCES employees(id)
        ON DELETE SET NULL
        DEFERRABLE INITIALLY DEFERRED
);
```

## Unique Constraints

### Single Column

```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    email VARCHAR(255) NOT NULL,

    CONSTRAINT uq_customers_email
        UNIQUE (tenant_id, email)
);
```

### Composite Unique

```sql
-- One active membership per customer
CREATE TABLE memberships (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    plan_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    started_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT uq_memberships_customer_active
        UNIQUE (customer_id, status)
        WHERE status = 'active'
);
```

## Check Constraints

### Basic Checks

```sql
CREATE TABLE bookings (
    id UUID PRIMARY KEY,
    slot_start_time TIME NOT NULL,
    slot_end_time TIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- End after start
    CONSTRAINT chk_booking_times
        CHECK (slot_end_time > slot_start_time),

    -- Valid status
    CONSTRAINT chk_booking_status
        CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')),

    -- Positive version
    CONSTRAINT chk_version_positive
        CHECK (version >= 1)
);
```

### Complex Checks

```sql
-- Booking must be cancelled if deleted
ALTER TABLE bookings
ADD CONSTRAINT chk_deleted_status
CHECK (
    (deleted_at IS NOT NULL AND status = 'cancelled')
    OR deleted_at IS NULL
);

-- Date range validity
CONSTRAINT chk_date_range
CHECK (end_date >= start_date)
```

## Exclusion Constraints

For overlapping ranges:

```sql
-- Prevent double-booking same facility/time
ALTER TABLE bookings
ADD CONSTRAINT ex_booking_no_overlap
EXCLUDE USING gist (
    facility_id WITH =,
    tsrange(slot_date + slot_start_time, slot_date + slot_end_time) WITH &&
);

-- Or with explicit time range
ALTER TABLE bookings
ADD CONSTRAINT ex_booking_slot
EXCLUDE USING gist (
    facility_id WITH =,
    tstzrange(
        slot_date + slot_start_time,
        slot_date + slot_end_time,
        '[)'
    ) WITH &&
);
```

> **Note** — Requires `btree_gist` extension:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

## Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Primary key | `pk_<table>` | `pk_bookings` |
| Foreign key | `fk_<table>_<ref>` | `fk_bookings_customer` |
| Unique | `uq_<table>_<cols>` | `uq_customers_email` |
| Check | `chk_<table>_<desc>` | `chk_booking_times` |
| Exclusion | `ex_<table>_<desc>` | `ex_booking_slot` |

## Constraint Validation

```sql
-- Check existing data against constraint before adding
ALTER TABLE bookings
ADD CONSTRAINT chk_booking_times
CHECK (slot_end_time > slot_start_time)
NOT VALID;  -- Don't lock table

-- Later validate
ALTER TABLE bookings
VALIDATE CONSTRAINT chk_booking_times;
```

## Anti-Patterns

1. **No FK constraints** — Data integrity risk
2. **Missing unique** — Duplicate data possible
3. **No checks** — Invalid business data
4. **Cascade everywhere** — Unintended deletions

## Examples

### Complete Table with Constraints

```sql
CREATE TABLE bookings (
    -- PK
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tenant isolation
    tenant_id UUID NOT NULL,

    -- FKs
    customer_id UUID NOT NULL,
    facility_id UUID NOT NULL,

    CONSTRAINT fk_bookings_customer
        FOREIGN KEY (customer_id, tenant_id)
        REFERENCES customers(id, tenant_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_bookings_facility
        FOREIGN KEY (facility_id, tenant_id)
        REFERENCES facilities(id, tenant_id)
        ON DELETE RESTRICT,

    -- Data
    slot_date DATE NOT NULL,
    slot_start_time TIME NOT NULL,
    slot_end_time TIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    notes TEXT,
    version INTEGER NOT NULL DEFAULT 1,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT chk_booking_times
        CHECK (slot_end_time > slot_start_time),

    CONSTRAINT chk_booking_status
        CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')),

    CONSTRAINT chk_version
        CHECK (version >= 1)
);
```

## Related Documents

- [Schema Design](schema-design.md)
- [Naming Standards](naming-standards.md)
- [Relationships](relationships.md)
