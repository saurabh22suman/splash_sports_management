# Database Optimization

> Index strategy. Query plan analysis. Avoiding N+1 queries. Vacuum & analyze schedules. Hot path query review. Table partitioning.

This document establishes database optimization strategies for the Splashh Sports Platform. We target sub-100ms queries for hot paths.

---

## Index Strategy

### When to Index

| Scenario | Index Type | Example |
|----------|-----------|---------|
| WHERE clause filter | B-tree | `CREATE INDEX ON bookings(tenant_id, date)` |
| Full text search | GIN | `CREATE INDEX ON bookings(notes) USING gin(to_tsvector('english', notes))` |
| Range queries | B-tree | `CREATE INDEX ON bookings(start_time)` |
| Unique constraints | B-tree (unique) | `CREATE UNIQUE INDEX ON facilities(name, tenant_id)` |
| JSON fields | GIN | `CREATE INDEX ON events(payload) USING gin(payload)` |

### Index Examples

```sql
-- Tenant isolation (most common filter)
CREATE INDEX idx_bookings_tenant_date
ON bookings(tenant_id, date DESC);

-- User-specific queries
CREATE INDEX idx_bookings_user_id
ON bookings(user_id, date DESC);

-- Facility lookups
CREATE INDEX idx_facilities_tenant_sport
ON facilities(tenant_id, sport_id);

-- Status filters
CREATE INDEX idx_bookings_status
ON bookings(status)
WHERE status IN ('pending', 'confirmed');

-- Composite for common query patterns
CREATE INDEX idx_bookings_tenant_user_status
ON bookings(tenant_id, user_id, status)
WHERE status = 'confirmed';
```

---

## Query Plan Analysis

Always analyze queries before deployment:

```sql
-- Explain query execution plan
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT b.*, f.name as facility_name
FROM bookings b
JOIN facilities f ON b.facility_id = f.id
WHERE b.tenant_id = 'tenant-abc'
  AND b.date >= '2024-01-01'
  AND b.date <= '2024-01-31';

-- Output shows:
-- - Execution time
-- - Rows scanned vs returned
-- - Indexes used
-- - Sequential vs index scans
```

### What to Look For

| Indicator | Good | Bad |
|-----------|------|-----|
| `Seq Scan` on large table | - | Should use index |
| `Rows` (actual) >> `Rows` (planned) | Statistics outdated | - |
| `Index Only Scan` | Efficient | - |
| `Bitmap Heap Scan` | Acceptable | - |
| `Nested Loop` | Small tables | Large tables |

---

## Avoiding N+1 Queries

### Problem

```python
# Anti-pattern: N+1 queries
bookings = await db.query(Booking).all()

for booking in bookings:
    # Each iteration hits the DB
    facility = await db.get(Facility, booking.facility_id)
    print(f"{booking.date} - {facility.name}")
```

### Solution: Eager Loading

```python
# Good: Eager load related data
from sqlalchemy.orm import selectinload

# Option 1: selectinload (2 queries total)
bookings = await db.execute(
    select(Booking)
    .options(selectinload(Booking.facility))
    .where(Booking.tenant_id == tenant_id)
)

# Option 2: joinedload (1 query with JOIN)
bookings = await db.execute(
    select(Booking)
    .options(joinedload(Booking.facility))
    .where(Booking.tenant_id == tenant_id)
)

# Option 3: Relationship loading
class Booking(Base):
    __tablename__ = 'bookings'

    facility = relationship("Facility", lazy="selectin")
```

---

## Vacuum & Analyze Schedules

```sql
-- Schedule: Daily vacuum at 2 AM
-- /etc/cron.d/postgresql-vacuum

-- Autovacuum is enabled by default, but tune for high-write tables
ALTER TABLE bookings SET (
    autovacuum_vacuum_threshold = 1000,
    autovacuum_vacuum_insert_threshold = 1000,
    autovacuum_analyze_threshold = 500,
    autovacuum_vacuum_scale_factor = 0.05,  -- Vac when 5% dead tuples
    autovacuum_analyze_scale_factor = 0.05
);

-- For high-write tables (bookings), increase frequency
ALTER TABLE bookings SET (
    autovacuum_vacuum_scale_factor = 0.02,
    autovacuum_analyze_scale_factor = 0.02
);
```

### Manual Operations

```sql
-- Analyze table for statistics
ANALYZE bookings;

-- Vacuum to reclaim space
VACUUM (VERBOSE, ANALYZE) bookings;

-- Full vacuum (blocks writes)
VACUUM FULL bookings;
```

---

## Hot Path Query Review

### Dashboard Queries

```python
# apps/backend/src/modules/dashboard/service.py
class DashboardService:
    async def get_tenant_summary(self, tenant_id: str) -> dict:
        """Optimized dashboard summary - target: < 50ms."""

        # Query 1: Today's bookings count
        today_bookings = await db.scalar(
            select(func.count(Booking.id))
            .where(
                Booking.tenant_id == tenant_id,
                Booking.date == date.today()
            )
        )  # Should use idx_bookings_tenant_date

        # Query 2: This week's revenue
        week_revenue = await db.scalar(
            select(func.sum(Booking.total_amount))
            .where(
                Booking.tenant_id == tenant_id,
                Booking.date >= date.today() - timedelta(days=7),
                Booking.status == 'confirmed'
            )
        )

        # Query 3: Active members (cached)
        active_members = await cache.get_or_set(
            f"stats:active_members:{tenant_id}",
            fetch_fn=lambda: self._count_active_members(tenant_id),
            ttl=300
        )

        return {
            "today_bookings": today_bookings or 0,
            "week_revenue": float(week_revenue or 0),
            "active_members": active_members,
        }
```

---

## Table Partitioning

For large tables (bookings, events):

```sql
-- Create partitioned bookings table
CREATE TABLE bookings (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    facility_id UUID NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (id, date)
) PARTITION BY RANGE (date);

-- Create monthly partitions
CREATE TABLE bookings_2024_01 PARTITION OF bookings
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE bookings_2024_02 PARTITION OF bookings
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Partition for future
CREATE TABLE bookings_2024_12 PARTITION OF bookings
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- Partition for old data (archive)
CREATE TABLE bookings_2023 PARTITION OF bookings
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
```

### Partition Benefits

- **Query pruning**: Only scans relevant partitions
- **Parallel queries**: Can scan partitions in parallel
- **Efficient maintenance**: Archive or drop old partitions
- **Index size**: Indexes are smaller per-partition

---

## Performance Monitoring

```sql
-- Slow query log (enabled in postgresql.conf)
-- log_min_duration_statement = 1000  -- Log queries > 1s

-- Find slowest queries
SELECT
    query,
    calls,
    mean_time,
    total_time,
    rows
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 20;

-- Index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY schemaname, tablename;
```

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| More indexes | Faster reads | Slower writes, more storage |
| Partitioning | Query performance, maintenance | Complexity, some query limitations |
| Denormalization | Fewer joins | Data consistency risk |
| Materialized views | Fast aggregations | Stale data risk |

---

## Related Documents

- [Caching](caching.md) — Database caching
- [Connection Pooling](connection-pooling.md) — Pool sizing
- [Query Patterns](database-query-patterns) — Common patterns
