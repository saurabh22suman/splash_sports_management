# Database Migrations

> This document covers safe migration strategies for PostgreSQL, including online migrations and handling large tables.

## Overview

Database migrations must be safe to run in production. We follow a pattern of **nullable-first, backfill, then constraint** for adding columns.

## Migration Safety Rules

> **Rule** — Never run destructive migrations without a rollback plan.

> **Rule** — Test migrations on production-like data volume before deploying.

## Adding a Column (Safe Pattern)

### Step 1: Add Nullable Column

```sql
-- Step 1: Add nullable column (instant, no table lock)
ALTER TABLE bookings
ADD COLUMN notes TEXT;
```

### Step 2: Backfill (if needed)

```sql
-- Step 2: Backfill data in batches
DO $$
DECLARE
    batch_size INTEGER := 1000;
    updated INTEGER := 0;
BEGIN
    LOOP
        UPDATE bookings
        SET notes = 'Migrated'
        WHERE notes IS NULL
        AND id IN (
            SELECT id FROM bookings
            WHERE notes IS NULL
            LIMIT batch_size
        );
        updated := SQL%ROWCOUNT;
        IF updated < batch_size THEN
            EXIT;
        END IF;
        PERFORM pg_sleep(0.1);  -- Brief pause
    END LOOP;
END $$;
```

### Step 3: Add NOT NULL Constraint

```sql
-- Step 3: Add NOT NULL (requires table scan)
ALTER TABLE bookings
ALTER COLUMN notes SET NOT NULL;
```

## Adding a Foreign Key (Safe Pattern)

```sql
-- Step 1: Add nullable FK column
ALTER TABLE bookings
ADD COLUMN facility_id UUID;

-- Step 2: Backfill
UPDATE bookings b
SET facility_id = f.id
FROM facilities f
WHERE b.facility_name = f.name
AND b.tenant_id = f.tenant_id;

-- Step 3: Add NOT NULL
ALTER TABLE bookings
ALTER COLUMN facility_id SET NOT NULL;

-- Step 4: Add FK constraint
ALTER TABLE bookings
ADD CONSTRAINT fk_bookings_facility
FOREIGN KEY (facility_id, tenant_id)
REFERENCES facilities(id, tenant_id);
```

## Adding an Index

### Non-Blocking

```sql
-- CREATE INDEX CONCURRENTLY doesn't lock writes
CREATE INDEX CONCURRENTLY idx_bookings_customer_date
ON bookings(customer_id, slot_date);
```

### Regular Index (Blocks writes)

```sql
-- Only for small tables or maintenance windows
CREATE INDEX idx_bookings_status
ON bookings(status);
```

## Renaming a Column

```sql
-- Step 1: Add new column
ALTER TABLE bookings
ADD COLUMN facility_ref UUID;

-- Step 2: Copy data
UPDATE bookings
SET facility_ref = old_facility_id;

-- Step 3: Switch references in code
-- (deploy code that writes to both columns)

-- Step 4: Migrate remaining data

-- Step 5: Drop old column
ALTER TABLE bookings
DROP COLUMN old_facility_id;
```

## Removing a Column

```sql
-- Step 1: Stop writing to column in code

-- Step 2: Verify no reads (monitor logs)

-- Step 3: Drop column
ALTER TABLE bookings
DROP COLUMN old_column;
```

## Large Table Migrations

For tables with millions of rows:

### 1. Use pg_repack

```bash
-- Non-blocking table changes
apt-get install pg_repack

pg_repack -t bookings -c concurrently
```

### 2. Use pg_stat_statements

```sql
-- Monitor query performance
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slow queries
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
WHERE query LIKE '%bookings%'
ORDER BY mean_time DESC;
```

### 3. Partition Migration

```sql
-- For very large tables, migrate partition by partition
-- See Partitioning document
```

## Migration Testing

### 1. Test on Staging

```bash
# Run migrations on staging
alembic upgrade head

# Verify data integrity
psql -c "SELECT COUNT(*) FROM bookings;"
```

### 2. Dry Run

```sql
-- Use EXPLAIN to estimate impact
EXPLAIN (ANALYZE, BUFFERS)
ALTER TABLE bookings ADD COLUMN notes TEXT;
```

### 3. Rollback Plan

```sql
-- Always have rollback
-- If migration is:
-- ALTER TABLE bookings ADD COLUMN notes TEXT;

-- Rollback is:
ALTER TABLE bookings DROP COLUMN notes;
```

## Migration Scripts

```python
# alembic/versions/2024_01_15_0001_add_notes_to_bookings.py
"""Add notes column to bookings

Revision ID: 2024_01_15_0001
Revises:
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '2024_01_15_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add nullable column
    op.add_column(
        'bookings',
        sa.Column('notes', sa.Text(), nullable=True)
    )

    # Step 2: Add index (concurrent for large tables)
    op.create_index(
        'idx_bookings_notes',
        'bookings',
        ['notes'],
        postgresql_where=sa.text('notes IS NOT NULL'),
        postgresql_concurrently=True
    )


def downgrade() -> None:
    op.drop_index('idx_bookings_notes', 'bookings')
    op.drop_column('bookings', 'notes')
```

## Common Migration Patterns

| Scenario | Pattern |
|----------|---------|
| Add column | Nullable -> Backfill -> NOT NULL |
| Add FK | Nullable -> Backfill -> NOT NULL -> FK |
| Add index | CONCURRENTLY for large tables |
| Rename column | Add new -> Copy -> Switch -> Drop |
| Remove column | Stop writes -> Verify -> Drop |
| Change type | Add new -> Copy -> Switch -> Drop |

## Anti-Patterns

1. **Direct NOT NULL without data** — Fails if table has rows
2. **Missing CONCURRENTLY** — Locks table for large tables
3. **No rollback plan** — Migration fails mid-way
4. **Not testing on volume** — Works on dev, fails on prod
5. **Long-running without monitoring** — No visibility into progress

## Related Documents

- [Backend Migrations](../04-backend/migrations.md)
- [Schema Design](schema-design.md)
- [Partitioning](partitioning.md)
