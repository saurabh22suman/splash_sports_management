# Naming Standards

> This document defines naming conventions for database tables, columns, indexes, constraints, and sequences.

## Overview

Consistent naming makes the database self-documenting and easier to navigate. All names follow PostgreSQL conventions.

## Tables

> **Rule** — Use `snake_case` and **plural** form.

```sql
-- Good
CREATE TABLE bookings (...);
CREATE TABLE customers (...);
CREATE TABLE facilities (...);
CREATE TABLE membership_plans (...);

-- Bad
CREATE TABLE booking (...);      -- singular
CREATE TABLE Customer (...);     -- PascalCase
CREATE TABLE booking_data (...);  # generic
```

### Table Naming Patterns

| Pattern | Example |
|---------|---------|
| Main entity | `bookings`, `customers` |
| Junction table | `booking_equipment` (many-to-many) |
| Join table | `membership_subscriptions` |
| Audit log | `audit_logs` |
| Junction | `booking_custom_fields` |

## Columns

> **Rule** — Use `snake_case` and **singular** form for column names.

```sql
-- Good
customer_id
facility_id
created_at
is_active

-- Bad
customerId      -- camelCase
CustomerID      -- PascalCase
customer_ids    -- plural (confusing)
```

### Standard Columns

Every table should have these columns:

```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
tenant_id       UUID NOT NULL,
created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
deleted_at      TIMESTAMPTZ,  -- for soft delete
```

### Column Naming Patterns

| Type | Pattern | Example |
|------|---------|---------|
| Primary key | `id` | `id UUID` |
| Foreign key | `<table>_id` | `customer_id`, `facility_id` |
| Boolean | `is_<adjective>` | `is_active`, `is_verified` |
| Timestamp | `<verb>_at` | `created_at`, `updated_at`, `deleted_at` |
| Status | `<noun>_status` or just `status` | `booking_status` or `status` |
| Code | `<noun>_code` | `error_code`, `currency_code` |

### Reserved Words

Avoid these PostgreSQL reserved words:

```
user, table, index, select, insert, update, delete
order, group, having, from, where, join, limit
type, name, value, key, primary, foreign, references
```

Instead use:

| Reserved | Use Instead |
|----------|-------------|
| `user` | `customer`, `member`, `app_user` |
| `type` | `category`, `kind`, `entity_type` |
| `name` | `display_name`, `entity_name` |
| `order` | `sort_order`, `display_order` |
| `level` | `access_level`, `priority` |

## Indexes

> **Rule** — Use prefix `idx_` for regular indexes, `uq_` for unique indexes.

```sql
-- Regular index
CREATE INDEX idx_bookings_customer ON bookings(customer_id);
CREATE INDEX idx_bookings_facility_date ON bookings(facility_id, slot_date);

-- Unique index
CREATE UNIQUE INDEX uq_customers_email ON customers(email);

-- Partial index
CREATE INDEX idx_bookings_active ON bookings(customer_id)
    WHERE deleted_at IS NULL;

-- Covering index (include)
CREATE INDEX idx_bookings_tenant_status ON bookings(tenant_id, status)
    INCLUDE (customer_id, facility_id);
```

### Index Naming

| Type | Pattern | Example |
|------|---------|---------|
| Regular | `idx_<table>_<cols>` | `idx_bookings_customer_date` |
| Unique | `uq_<table>_<cols>` | `uq_customers_email` |
| Partial | `idx_<table>_<desc>` | `idx_bookings_active` |
| Primary | (auto) | Primary key constraint |
| FK | `fk_<table>_<ref>` | `fk_bookings_customer` |

## Constraints

> **Rule** — Name constraints explicitly.

```sql
-- Primary key
CONSTRAINT pk_bookings PRIMARY KEY (id);

-- Foreign key
CONSTRAINT fk_bookings_customer
    FOREIGN KEY (customer_id, tenant_id)
    REFERENCES customers(id, tenant_id);

-- Unique
CONSTRAINT uq_customers_email
    UNIQUE (tenant_id, email);

-- Check
CONSTRAINT chk_booking_dates
    CHECK (slot_end_time > slot_start_time);

-- Exclusion
CONSTRAINT ex_booking_slot
    EXCLUDE USING gist (
        facility_id WITH =,
        tstzrange(slot_start, slot_end) WITH &&
    );
```

### Constraint Naming

| Type | Pattern |
|------|---------|
| Primary key | `pk_<table>` |
| Foreign key | `fk_<table>_<ref_table>` |
| Unique | `uq_<table>_<cols>` |
| Check | `chk_<table>_<description>` |
| Exclusion | `ex_<table>_<description>` |

## Sequences

```sql
-- If using auto-increment (not recommended, use UUID)
CREATE SEQUENCE booking_number_seq;
booking_number INTEGER DEFAULT nextval('booking_number_seq');
```

## Schemas

> **Rule** — Use schemas for logical grouping.

```sql
-- Production
CREATE SCHEMA booking;
CREATE SCHEMA payment;
CREATE SCHEMA audit;

-- Usage
SELECT * FROM booking.bookings;
SELECT * FROM payment.invoices;
```

## Examples

### Complete Table Definition

```sql
CREATE TABLE bookings (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tenant isolation (mandatory)
    tenant_id UUID NOT NULL,

    -- Foreign keys
    customer_id UUID NOT NULL,
    facility_id UUID NOT NULL,

    -- Business columns
    slot_date DATE NOT NULL,
    slot_start_time TIME NOT NULL,
    slot_end_time TIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    notes TEXT,
    version INTEGER NOT NULL DEFAULT 1,

    -- Audit columns
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT fk_bookings_customer
        FOREIGN KEY (customer_id, tenant_id)
        REFERENCES customers(id, tenant_id),
    CONSTRAINT fk_bookings_facility
        FOREIGN KEY (facility_id, tenant_id)
        REFERENCES facilities(id, tenant_id),
    CONSTRAINT chk_booking_times
        CHECK (slot_end_time > slot_start_time)
);

-- Indexes
CREATE INDEX idx_bookings_tenant ON bookings(tenant_id);
CREATE INDEX idx_bookings_customer ON bookings(customer_id, tenant_id);
CREATE INDEX idx_bookings_facility_date ON bookings(facility_id, tenant_id, slot_date);
CREATE INDEX idx_bookings_status ON bookings(status)
    WHERE deleted_at IS NULL;
```

## Anti-Patterns

1. **CamelCase** — Always use snake_case
2. **Missing tenant_id** — Every table needs tenant isolation
3. **Unnamed constraints** — Let the DB name them
4. **Generic names** — `data`, `info`, `misc` tables
5. **Singular table names** — Use plural

## Related Documents

- [Schema Design](schema-design.md)
- [Indexes](indexes.md)
- [Constraints](constraints.md)
- [Relationships](relationships.md)
