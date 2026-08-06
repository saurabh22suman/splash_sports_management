# Performance Optimization

> This document covers PostgreSQL query optimization, connection pooling, and performance troubleshooting.

## Overview

Database performance is critical for API latency. We optimize through proper indexing, query analysis, and connection management.

## Query Analysis

### EXPLAIN ANALYZE

> **Rule** — Always run EXPLAIN ANALYZE on slow queries.

```sql
-- Analyze query plan
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM bookings
WHERE customer_id = 'cust-123'
AND tenant_id = 'tenant-1'
ORDER BY created_at DESC
LIMIT 20;
```

### Understanding Plans

| Operation | Good | Bad |
|-----------|------|-----|
| Index Scan | Yes | - |
| Seq Scan on large table | No | Rebuild index |
| Nested Loop | Small tables | Large tables |
| Hash Join | Medium tables | - |
| Sort (Memory) | Yes | - |
| Sort (Disk) | No | Add memory / index |

### Bad Query Patterns

```sql
-- BAD: Sequential scan on large table
SELECT * FROM bookings WHERE status = 'pending';

-- GOOD: Using index
SELECT * FROM bookings
WHERE status = 'pending'
AND deleted_at IS NULL;  -- partial index

-- BAD: Function on indexed column
SELECT * FROM bookings
WHERE DATE(created_at) = '2024-01-15';

-- GOOD: Range query on timestamp
SELECT * FROM bookings
WHERE created_at >= '2024-01-15 00:00:00'
AND created_at < '2024-01-16 00:00:00';
```

## N+1 Detection

### Problem

```python
# BAD: N+1 queries
for booking in bookings:
    customer = session.query(Customer).get(booking.customer_id)  # Query per booking
    print(customer.name)
```

### Solution: Eager Loading

```python
# GOOD: Load in single query
bookings = session.query(Booking).options(
    joinedload(Booking.customer)
).all()

# Or with selectinload for batch loading
bookings = session.query(Booking).options(
    selectinload(Booking.customer)
).all()
```

### SQL Output

```sql
-- N+1: 101 queries
SELECT * FROM bookings LIMIT 100;
SELECT * FROM customers WHERE id = 'c1';
SELECT * FROM customers WHERE id = 'c2';
-- ... 100 more

-- Fixed: 2 queries
SELECT * FROM bookings;
SELECT * FROM customers WHERE id IN ('c1', 'c2', ...);
```

## Vacuum & Analyze

### VACUUM

```sql
-- Reclaim space from deleted rows
VACUUM bookings;

-- Full vacuum (locks table)
VACUUM FULL bookings;

-- Analyze: update statistics
ANALYZE bookings;
```

### Autovacuum

PostgreSQL handles most automatically:

```sql
-- postgresql.conf
autovacuum = on
autovacuum_max_workers = 4
autovacuum_naptime = 1min

-- Per-table settings
ALTER TABLE bookings SET (
    autovacuum_vacuum_threshold = 1000,
    autvacuum_analyze_threshold = 500
);
```

### Monitoring Bloat

```sql
-- Check for bloated tables/indexes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    n_dead_tup,
    n_live_tup,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 1) as dead_tuple_percent
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

## Statistics

### Target Settings

```sql
-- postgresql.conf
default_statistics_target = 100  -- Range: 1-10000

-- Per-column statistics
ALTER TABLE bookings ALTER COLUMN customer_id SET STATISTICS 500;
```

### Query Stats

```sql
-- Find columns lacking statistics
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE n_distinct < 0  -- Estimates based on sample
AND schemaname = 'public';
```

## Connection Pooling

### PgBouncer

```ini
# pgbouncer.ini
[databases]
splashh = host=localhost dbname=splashh

[pgbouncer]
listen_port = 6432
listen_addr = 127.0.0.1
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

pool_mode = transaction  -- Release connection after transaction
max_client_conn = 1000
default_pool_size = 20
min_pool_size = 5
```

### Pool Sizing

| Metric | Formula |
|--------|---------|
| Max connections | `num_cpus * 2 + spindle_count` |
| Pool size | `max_connections / num_services` |
| PgBouncer clients | `pool_size * num_deployments * 2` |

### Application Configuration

```python
# connection.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:pass@localhost:6432/splashh",
    poolclass=QueuePool,
    pool_size=10,        # Regular connections
    max_overflow=20,     # Burst connections
    pool_timeout=30,     # Wait for connection
    pool_recycle=3600,   # Recycle after 1 hour
)
```

## Query Optimization Patterns

### Covering Index

```sql
-- Query: SELECT customer_id, status FROM bookings WHERE facility_id = ?
CREATE INDEX idx_bookings_facility_cover
    ON bookings(facility_id)
    INCLUDE (customer_id, status);
```

### Partial Index

```sql
-- Query: SELECT * FROM bookings WHERE status = 'confirmed'
CREATE INDEX idx_bookings_confirmed
    ON bookings(customer_id, facility_id)
    WHERE status = 'confirmed';
```

### Composite Index Order

```sql
-- Query: WHERE facility_id = ? AND slot_date = ?
-- Best: (facility_id, slot_date) not (slot_date, facility_id)
-- High cardinality first
```

## Performance Monitoring

### Slow Query Log

```sql
-- postgresql.conf
log_min_duration_statement = 1000  -- Log queries > 1 second
log_connections = on
log_disconnections = on
log_lock_waits = on
```

### Query Statistics

```sql
-- Enable extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slowest queries
SELECT
    query,
    calls,
    mean_time,
    total_time,
    rows,
    100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) as hit_percent
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;
```

## Anti-Patterns

1. **Missing indexes** — Slow lookups
2. **N+1 queries** — Excessive round-trips
3. **No connection pool** — Connection exhaustion
4. **Sequential scans** — Full table scans
5. **Unoptimized joins** — Cartesian products

## Related Documents

- [Schema Design](schema-design.md)
- [Indexes](indexes.md)
- [Connection Pooling](../11-performance/connection-pooling.md)
- [Observability](../11-performance/observability.md)
