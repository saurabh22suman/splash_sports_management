# Schema Design

> This document covers database schema design principles, normalization, tenant isolation strategies, and key patterns.

## Overview

Our database design follows **third normal form (3NF)** for transactional data, with denormalization only for read models. We use a shared schema with `tenant_id` for multi-tenancy.

## Normalization Principles

### Third Normal Form (3NF)

```
1NF: Atomic values, no repeating groups
2NF: No partial dependencies (no composite keys with non-key dependencies)
3NF: No transitive dependencies (non-key columns depend only on primary key)
```

### Schema Example

```sql
-- Normalized booking schema
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    facility_id UUID NOT NULL,
    slot_date DATE NOT NULL,
    slot_start_time TIME NOT NULL,
    slot_end_time TIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_bookings_customer FOREIGN KEY (customer_id, tenant_id)
        REFERENCES customers(id, tenant_id),
    CONSTRAINT fk_bookings_facility FOREIGN KEY (facility_id, tenant_id)
        REFERENCES facilities(id, tenant_id)
);

CREATE INDEX idx_bookings_tenant ON bookings(tenant_id);
CREATE INDEX idx_bookings_customer ON bookings(customer_id, tenant_id);
CREATE INDEX idx_bookings_facility_date ON bookings(facility_id, tenant_id, slot_date);
```

## Multi-Tenant Strategy

> **Decision** — Shared schema with `tenant_id` column.

| Strategy | Pros | Cons |
|----------|------|------|
| **Shared schema + tenant_id** | Simple, easy operations | Row-level isolation critical |
| Schema per tenant | Strong isolation | Complex migrations, more connections |
| Database per tenant | Complete isolation | Overhead, complex ops |

### Tenant Isolation

Every table includes `tenant_id`:

```sql
-- Every query must filter by tenant_id
SELECT * FROM bookings WHERE tenant_id = 'tenant-123';

-- Foreign keys include tenant_id
ALTER TABLE bookings
ADD CONSTRAINT fk_bookings_customer
FOREIGN KEY (customer_id, tenant_id)
REFERENCES customers(id, tenant_id);
```

### Repository Filtering

```python
# All queries automatically include tenant_id
class SQLAlchemyBookingRepository:
    def get(self, booking_id: UUID, tenant_id: UUID) -> Optional[Booking]:
        return self._session.query(BookingModel).filter(
            BookingModel.id == booking_id,
            BookingModel.tenant_id == tenant_id,
            BookingModel.deleted_at.is_(None)
        ).first()
```

## Primary Keys

> **Rule** — Use UUIDs for all primary keys.

```sql
-- UUID primary key
id UUID PRIMARY KEY DEFAULT gen_random_uuid()

-- Why not auto-increment?
-- 1. Merging data across tenants/databases is easier
-- 2. No guessable IDs (security)
-- 3. Distributed ID generation without coordination
-- 4. URL-safe (no need for encoding)
```

## Soft Delete Pattern

```sql
-- Always include deleted_at
CREATE TABLE bookings (
    -- ... columns ...
    deleted_at TIMESTAMPTZ,  -- NULL = not deleted
    CONSTRAINT chk_deleted_at CHECK (
        (deleted_at IS NOT NULL AND status = 'cancelled')
        OR deleted_at IS NULL
    )
);

-- Queries filter by deleted_at
SELECT * FROM bookings WHERE deleted_at IS NULL;
```

## Value Objects as Columns

```sql
-- TimeSlot as separate columns (not JSON)
slot_date DATE NOT NULL,
slot_start_time TIME NOT NULL,
slot_end_time TIME NOT NULL,

-- This is better than:
-- slot_jsonb JSONB  -- Harder to query, no type safety

-- Contact info as separate columns
email VARCHAR(255),
phone VARCHAR(20),
-- vs:
-- contact_jsonb JSONB
```

## Denormalization for Read Models

For read-heavy views, denormalize:

```sql
-- Read model: facility with current stats
CREATE TABLE facility_stats (
    facility_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name VARCHAR(255),
    current_bookings INTEGER DEFAULT 0,
    todays_revenue DECIMAL(12,2) DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Materialized view or updated via triggers/events
-- Refresh periodically or on relevant changes
```

## Naming Conventions

See [Naming Standards](naming-standards.md).

| Element | Convention | Example |
|---------|------------|---------|
| Tables | `snake_case, plural` | `bookings` |
| Columns | `snake_case, singular` | `booking_id` |
| Primary key | `id` | `id UUID` |
| Foreign key | `<table>_id` | `customer_id` |
| Timestamps | `<action>_at` | `created_at`, `updated_at` |

## Anti-Patterns

1. **JSON columns for everything** — Use proper columns for queryable fields
2. **Missing tenant_id** — Every table must have tenant isolation
3. **No foreign keys** — Data integrity matters
4. **Over-normalization** — Don't create a table for every attribute
5. **Storing derived data** — Calculated columns that can be computed

## Schema Evolution

### Adding a Table

```sql
-- New table for membership
CREATE TABLE memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    plan_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    started_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_memberships_tenant ON memberships(tenant_id);
CREATE INDEX idx_memberships_customer ON memberships(customer_id, tenant_id);
```

### Adding a Column

```sql
-- Add nullable column
ALTER TABLE bookings
ADD COLUMN notes TEXT;

-- Add with default (backfill separately for large tables)
ALTER TABLE bookings
ADD COLUMN source VARCHAR(20) DEFAULT 'web';
```

## Related Documents

- [Naming Standards](naming-standards.md)
- [Indexes](indexes.md)
- [Constraints](constraints.md)
- [Soft Delete](soft-delete.md)
- [Multi-Tenant Strategy](../09-security/tenant-isolation.md)
