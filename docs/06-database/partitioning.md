# Partitioning

> This document covers PostgreSQL table partitioning for large tables, partitioning strategies, and maintenance.

## Overview

**Partitioning** splits a large table into smaller, more manageable pieces called partitions. It's used when tables exceed ~100M rows or when index size exceeds ~50GB.

## When to Partition

| Indicator | Threshold | Action |
|-----------|-----------|--------|
| Table size | > 100M rows | Consider partitioning |
| Index size | > 50GB | Consider partitioning |
| Query performance | Slow on recent data | Partition by date |
| Hot data | Recent 30 days | Keep in fast storage |

## Partitioning Strategy

### Range Partitioning by Date

Best for time-series data like bookings, logs:

```sql
-- Create partitioned table
CREATE TABLE bookings (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    facility_id UUID NOT NULL,
    slot_date DATE NOT NULL,
    slot_start_time TIME NOT NULL,
    slot_end_time TIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
) PARTITION BY RANGE (slot_date);

-- Create partitions by month
CREATE TABLE bookings_2024_01 PARTITION OF bookings
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE bookings_2024_02 PARTITION OF bookings
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Default partition for overflow
CREATE TABLE bookings_default PARTITION OF bookings
    DEFAULT;
```

### Hash Partitioning

For even distribution of large tenants:

```sql
-- Hash partition by tenant
CREATE TABLE bookings (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    -- ... columns ...
) PARTITION BY HASH (tenant_id);

-- Create 16 partitions
CREATE TABLE bookings_00 PARTITION OF bookings
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
-- ... more partitions
```

## Partition Management

### Create New Partition

```sql
-- Create partition for next month
CREATE TABLE bookings_2024_02 PARTITION OF bookings
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

### Detach Partition

```sql
-- Move old partition to archive
ALTER TABLE bookings DETACH PARTITION bookings_2023_01;

-- Make it standalone table
ALTER TABLE bookings_2023_01 RENAME TO bookings_archive_2023_01;
```

### Attach Partition

```sql
-- Re-attach archived partition if needed
ALTER TABLE bookings ATTACH PARTITION bookings_archive_2023_01
    FOR VALUES FROM ('2023-01-01') TO ('2023-02-01');
```

## Partition-Specific Indexes

```sql
-- Indexes are local to each partition
CREATE INDEX ON bookings_2024_01 (customer_id, tenant_id);
CREATE INDEX ON bookings_2024_02 (customer_id, tenant_id);

-- Or use a single index on parent (propagates)
CREATE INDEX ON bookings (customer_id, tenant_id);
```

## Query Routing

PostgreSQL automatically routes queries to relevant partitions:

```sql
-- Query only hits January partition
SELECT * FROM bookings
WHERE slot_date = '2024-01-15';

-- Query hits all partitions (no partition key)
SELECT * FROM bookings WHERE customer_id = 'cust-123';
```

## Partition Maintenance

### Move Old Data to Cold Storage

```sql
-- Detach old partition
ALTER TABLE bookings DETACH PARTITION bookings_2023_01;

-- Rename for archive
ALTER TABLE bookings_2023_01 RENAME TO bookings_archive_2023_01;

-- Move to archive schema
ALTER TABLE bookings_archive_2023_01 SET SCHEMA archive;
```

### Automatic Partition Creation

```sql
-- Function to create next partition
CREATE OR REPLACE FUNCTION create_booking_partition()
RETURNS VOID AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
BEGIN
    partition_date := DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month');
    partition_name := 'bookings_' || TO_CHAR(partition_date, 'YYYY_MM');

    EXECUTE format(
        'CREATE TABLE %I PARTITION OF bookings FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        partition_date,
        partition_date + INTERVAL '1 month'
    );
END;
$$ LANGUAGE plpgsql;

-- Run monthly via cron
-- SELECT create_booking_partition();
```

## Trade-offs

| Aspect | Benefit | Drawback |
|--------|---------|----------|
| Query performance | Faster for date-range queries | Complexity in setup |
| Maintenance | Easier to drop old partitions | More tables to manage |
| Index size | Smaller per-partition indexes | Global queries hit all |
| Backup/restore | Can restore specific partitions | More complex ops |

## When NOT to Partition

- Tables < 10M rows (overhead not worth it)
- Queries don't filter by partition key
- Need to query across all partitions frequently

## Monitoring Partition Usage

```sql
-- Check partition sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Related Documents

- [Schema Design](schema-design.md)
- [Archival](archival.md)
- [Backups](backups.md)
- [Performance Optimization](performance-optimization.md)
