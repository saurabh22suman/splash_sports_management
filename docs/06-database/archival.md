# Archival

> This document covers data lifecycle management, moving cold data to archive storage, and retention policies.

## Overview

**Archival** moves inactive data from production to cheaper storage while maintaining access. This reduces database size, improves performance, and satisfies retention requirements.

## Retention Policies

| Data Class | Active Period | Archive Period | Total Retention | Reason |
|------------|---------------|----------------|-----------------|--------|
| Bookings | 2 years | 5 years | 7 years | Financial/legal |
| Memberships | Active | 7 years | 7 years | Legal |
| Audit logs | 1 year | 6 years | 7 years | Compliance |
| Sessions | 30 days | N/A | 30 days | Security |
| Login logs | 90 days | N/A | 90 days | Security |
| API logs | 30 days | N/A | 30 days | Debugging |

## Archive Strategy

### 1. Identify Cold Data

```sql
-- Find bookings older than 2 years
SELECT COUNT(*) FROM bookings
WHERE created_at < NOW() - INTERVAL '2 years';

-- Find bookings with no recent activity
SELECT COUNT(*) FROM bookings
WHERE created_at < NOW() - INTERVAL '2 years'
AND updated_at < NOW() - INTERVAL '2 years';
```

### 2. Create Archive Schema

```sql
CREATE SCHEMA archive;
```

### 3. Move Data

```sql
-- Move old bookings to archive
ALTER TABLE bookings_2022 ATTACH PARTITION bookings_archive_2022
    FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');

-- Or use partition detach
ALTER TABLE bookings DETACH PARTITION bookings_2022;
ALTER TABLE bookings_2022 RENAME TO archive.bookings_2022;
```

### 4. Create Archive Views

```sql
-- Unified view across active and archived
CREATE VIEW all_bookings AS
SELECT * FROM bookings
UNION ALL
SELECT * FROM archive.bookings_2022
UNION ALL
SELECT * FROM archive.bookings_2021;
```

## Cold Storage (S3)

For very large archives, move to object storage:

```sql
-- Export to CSV
COPY (SELECT * FROM archive.bookings_2021)
TO '/tmp/bookings_2021.csv'
WITH (FORMAT CSV, HEADER);

-- Upload to S3 (via psql or external tool)
aws s3 cp /tmp/bookings_2021.csv s3://splashh-archive/bookings_2021.csv

-- Drop local archive after verified
DROP TABLE archive.bookings_2021;
```

## Automated Archival Job

```python
# src/jobs/archive_job.py
from datetime import datetime, timedelta


class ArchiveJob:
    def __init__(self, db_session):
        self._db = db_session

    async def archive_old_bookings(self) -> dict:
        """Archive bookings older than 2 years."""
        cutoff = datetime.utcnow() - timedelta(days=730)

        # Find partitions to archive
        partitions = self._db.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename LIKE 'bookings_%'
            AND tablename < 'bookings_' || TO_CHAR(CURRENT_DATE - INTERVAL '2 years', 'YYYY_MM')
        """).fetchall()

        archived = 0
        for (partition,) in partitions:
            # Detach partition
            self._db.execute(f"""
                ALTER TABLE bookings DETACH PARTITION {partition}
            """)

            # Rename to archive schema
            self._db.execute(f"""
                ALTER TABLE {partition} RENAME TO archive.{partition}
            """)

            archived += 1

        return {"partitions_archived": archived}
```

## Accessing Archived Data

### Application-Level

```python
class BookingRepository:
    async def get(self, booking_id: UUID, tenant_id: UUID) -> Optional[Booking]:
        # Try active first
        booking = await self._get_from_table(booking_id, "bookings")
        if booking:
            return booking

        # Try archive
        # Check which partition might have it
        # Or query unified view
        return await self._get_from_view(booking_id, tenant_id)

    async def _get_from_view(self, booking_id, tenant_id):
        """Query unified view."""
        result = await self._db.execute("""
            SELECT * FROM all_bookings
            WHERE id = :id AND tenant_id = :tenant_id
        """, {"id": booking_id, "tenant_id": tenant_id})
        return result.fetchone()
```

## Data Masking in Archive

Archive may contain less sensitive data:

```sql
-- Archive table with masked PII
CREATE TABLE archive.bookings_masked AS
SELECT
    id,
    tenant_id,
    -- Mask PII
    'REDACTED' AS customer_email,
    SUBSTRING(customer_phone, 1, 3) || '***' AS customer_phone,
    -- Keep business data
    facility_id,
    slot_date,
    slot_start_time,
    slot_end_time,
    status,
    created_at
FROM bookings_2021;
```

## Verification

After archival, verify data integrity:

```sql
-- Count check
SELECT 'active' as source, COUNT(*) FROM bookings
UNION ALL
SELECT 'archive_2022', COUNT(*) FROM archive.bookings_2022
UNION ALL
SELECT 'archive_2021', COUNT(*) FROM archive.bookings_2021;

-- Sum should equal original count before archival
```

## Anti-Patterns

1. **Not archiving** — Database grows indefinitely
2. **No access pattern** — Archived data becomes inaccessible
3. **No retention policy** — Don't know what to keep
4. **PII in archives** — Compliance risk

## Related Documents

- [Schema Design](schema-design.md)
- [Partitioning](partitioning.md)
- [Soft Delete](soft-delete.md)
- [Backups](backups.md)
