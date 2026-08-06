# Indexes

> This document covers PostgreSQL index types, when to create indexes, and index maintenance.

## Overview

Indexes are critical for query performance. We use the right index type for each access pattern.

## Index Types

| Type | Use Case | Example |
|------|----------|---------|
| B-tree | Equality, range, sorting | `WHERE status = 'pending'`, `ORDER BY created_at` |
| GIN | JSONB, arrays, full-text | `WHERE tags @> '{tennis}'` |
| GiST | Spatial, range types | `WHERE daterange && tstzrange(...)` |
| Hash | Simple equality (rare) | `WHERE email = 'x@y.com'` |
| BRIN | Time-series, append-only | `WHERE created_at > '2024-01-01'` |

## B-Tree Indexes (Default)

### Single Column

```sql
-- Index on customer_id for lookups
CREATE INDEX idx_bookings_customer ON bookings(customer_id);

-- Composite index for common query pattern
CREATE INDEX idx_bookings_facility_date
    ON bookings(facility_id, slot_date);
```

### When to Use B-Tree

- Column appears in WHERE, JOIN, ORDER BY
- High cardinality (many distinct values)
- Queries use =, <, >, <=, >=, BETWEEN

### Index Column Order

> **Rule** — Put high-cardinality columns first in composite indexes.

```sql
-- Query: WHERE facility_id = ? AND slot_date = ?
-- Best: (facility_id, slot_date)
-- Good: (slot_date, facility_id) -- works but less efficient
```

## Partial Indexes

For queries that filter by a condition:

```sql
-- Only query active bookings
CREATE INDEX idx_bookings_active
    ON bookings(customer_id, slot_date)
    WHERE status IN ('pending', 'confirmed');

-- Only non-deleted records
CREATE INDEX idx_bookings_not_deleted
    ON bookings(tenant_id, updated_at)
    WHERE deleted_at IS NULL;
```

## Covering Indexes (INCLUDE)

For queries that fetch additional columns:

```sql
-- Query: SELECT customer_id, status FROM bookings WHERE facility_id = ?
CREATE INDEX idx_bookings_facility_cover
    ON bookings(facility_id)
    INCLUDE (customer_id, status);

-- This allows index-only scans
```

## GIN Indexes

For JSONB and arrays:

```sql
-- Store metadata as JSONB
ALTER TABLE bookings ADD COLUMN metadata JSONB;

-- GIN index for containment queries
CREATE INDEX idx_bookings_metadata
    ON bookings USING GIN (metadata);

-- Query: WHERE metadata @> '{"source": "mobile"}'
CREATE INDEX idx_bookings_source
    ON bookings USING GIN ((metadata->'source'));

-- Array column
ALTER TABLE facilities ADD COLUMN tags TEXT[];

-- GIN index for array containment
CREATE INDEX idx_facilities_tags
    ON facilities USING GIN (tags);

-- Query: WHERE tags @> ARRAY['indoor', 'tennis']
```

## BRIN Indexes

For time-series or append-only data:

```sql
-- Large table with time-ordered data
CREATE INDEX idx_audit_logs_created
    ON audit_logs USING BRIN (created_at);

-- Very efficient for range queries on sequential data
-- Query: WHERE created_at > '2024-01-01'
```

## Concurrent Index Creation

For large tables, create indexes without locking:

```sql
-- Non-blocking index creation
CREATE INDEX CONCURRENTLY idx_bookings_customer_date
    ON bookings(customer_id, slot_date);

-- Non-blocking unique index
CREATE UNIQUE INDEX CONCURRENTLY uq_customers_email
    ON customers(email) WHERE deleted_at IS NULL;
```

> **Rule** — Use `CONCURRENTLY` for production tables.

## When NOT to Index

1. **Low cardinality columns** — Don't index status (only 5 values)
2. **Frequently updated columns** — Index overhead on writes
3. **Small tables** — Full scan is faster
4. **Uncommon queries** — Don't add indexes "just in case"

## Index Maintenance

### ANALYZE

```sql
-- Update statistics for query planner
ANALYZE bookings;
```

### Reindex

```sql
-- Rebuild bloated index
REINDEX INDEX idx_bookings_customer;

-- Concurrent reindex (PostgreSQL 13+)
REINDEX INDEX CONCURRENTLY idx_bookings_customer;
```

### Monitor Index Usage

```sql
-- Find unused indexes
SELECT
    schemaname,
    relname,
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelname NOT LIKE '%pkey%'
ORDER BY pg_relation_size(indexrelid) DESC;
```

## Indexing Foreign Keys

> **Rule** — Always index foreign key columns.

```sql
-- FK from bookings to customers
CREATE INDEX idx_bookings_customer ON bookings(customer_id);
CREATE INDEX idx_bookings_customer_tenant ON bookings(customer_id, tenant_id);
```

## Query Patterns and Indexes

| Query Pattern | Recommended Index |
|---------------|-------------------|
| `WHERE tenant_id = ?` | `(tenant_id)` |
| `WHERE customer_id = ?` | `(customer_id, tenant_id)` |
| `WHERE facility_id = ? AND date = ?` | `(facility_id, tenant_id, slot_date)` |
| `WHERE status = ? AND deleted_at IS NULL` | Partial index |
| `ORDER BY created_at DESC` | `(tenant_id, created_at)` |
| `WHERE tags @> ?` | GIN on array column |

## Examples

### Booking Queries

```sql
-- Query 1: List customer's bookings
CREATE INDEX idx_bookings_customer ON bookings(customer_id, tenant_id);

-- Query 2: Facility schedule for date
CREATE INDEX idx_bookings_facility_date
    ON bookings(facility_id, tenant_id, slot_date, slot_start_time);

-- Query 3: Find bookings by status
CREATE INDEX idx_bookings_status
    ON bookings(tenant_id, status) WHERE deleted_at IS NULL;

-- Query 4: Recent bookings
CREATE INDEX idx_bookings_recent
    ON bookings(tenant_id, created_at DESC);
```

## Anti-Patterns

1. **Over-indexing** — Each index slows writes
2. **Missing FK indexes** — Slow joins
3. **Wrong index type** — Using B-tree for arrays
4. **Ignoring partial indexes** — Wasted space for irrelevant rows

## Related Documents

- [Schema Design](schema-design.md)
- [Naming Standards](naming-standards.md)
- [Performance Optimization](performance-optimization.md)
