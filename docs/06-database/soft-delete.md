# Soft Delete

> This document covers soft delete patterns, implementation, and when to use hard delete.

## Overview

**Soft delete** marks records as deleted without physically removing them. This preserves data for auditing, allows accidental deletion recovery, and maintains referential integrity.

## Implementation

### Database Column

```sql
-- Add deleted_at column to tables
ALTER TABLE bookings
ADD COLUMN deleted_at TIMESTAMPTZ;
```

### Repository Filtering

```python
# All queries filter by deleted_at
class SQLAlchemyBookingRepository:
    def get(self, booking_id: UUID, tenant_id: UUID) -> Optional[Booking]:
        return self._session.query(BookingModel).filter(
            BookingModel.id == booking_id,
            BookingModel.tenant_id == tenant_id,
            BookingModel.deleted_at.is_(None)  # Not deleted
        ).first()

    def get_including_deleted(self, booking_id: UUID) -> Optional[Booking]:
        """Get even if deleted (for admin/recovery)."""
        return self._session.query(BookingModel).filter(
            BookingModel.id == booking_id
        ).first()

    def soft_delete(self, booking_id: UUID) -> None:
        """Mark as deleted."""
        self._session.query(BookingModel).filter(
            BookingModel.id == booking_id
        ).update({"deleted_at": datetime.utcnow()})

    def restore(self, booking_id: UUID) -> None:
        """Restore deleted record."""
        self._session.query(BookingModel).filter(
            BookingModel.id == booking_id
        ).update({"deleted_at": None})
```

### Domain Entity

```python
class Booking:
    def delete(self) -> None:
        """Soft delete the booking."""
        if self.deleted_at is not None:
            raise AlreadyDeletedError(f"Booking {self.id} is already deleted")
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore the booking."""
        self.deleted_at = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

## Query Patterns

### Standard Queries (Exclude Deleted)

```sql
-- Standard: only non-deleted
SELECT * FROM bookings
WHERE tenant_id = 't1'
AND deleted_at IS NULL;

-- Count: only non-deleted
SELECT COUNT(*) FROM bookings
WHERE tenant_id = 't1'
AND deleted_at IS NULL;
```

### Include Deleted

```sql
-- For admin/recovery
SELECT * FROM bookings
WHERE tenant_id = 't1'
AND id = 'booking-123';

-- All (including deleted)
SELECT * FROM bookings
WHERE tenant_id = 't1'
AND deleted_at IS NOT NULL;
```

## Partial Indexes

Use partial indexes to make deleted-filtered queries fast:

```sql
-- Only index non-deleted records
CREATE INDEX idx_bookings_not_deleted
ON bookings(tenant_id, customer_id, slot_date)
WHERE deleted_at IS NULL;

-- This index is smaller (excludes deleted rows)
-- and only used for queries that filter deleted_at IS NULL
```

## Cascading Soft Delete

For related records, cascade the soft delete:

```sql
-- Soft delete booking lines when booking is deleted
UPDATE booking_lines
SET deleted_at = NOW()
WHERE booking_id IN (
    SELECT id FROM bookings WHERE deleted_at IS NULL
)
AND deleted_at IS NULL;
```

In code:

```python
class BookingService:
    def delete_booking(self, booking_id: UUID) -> None:
        with self._uow:
            booking = self._repo.get(booking_id)

            # Soft delete booking
            booking.soft_delete()
            self._repo.save(booking)

            # Soft delete lines
            for line in self._line_repo.list_by_booking(booking_id):
                line.soft_delete()
                self._line_repo.save(line)

            self._uow.commit()
```

## When to Hard Delete

> **Rule** — Hard delete only for compliance (GDPR, DPDPA) or data that must be removed.

### GDPR/DPDA Compliance

```sql
-- For data subject requests, hard delete PII
DELETE FROM customers
WHERE id = 'customer-123'
AND tenant_id = 'tenant-1';
```

### Cleanup Old Data

```sql
-- Archive then hard delete old soft-deleted records
-- After 90 days
DELETE FROM bookings
WHERE deleted_at < NOW() - INTERVAL '90 days';
```

## Performance Considerations

### Indexes for Deleted Filtering

```sql
-- Composite index includes tenant_id (always filtered)
CREATE INDEX idx_bookings_tenant_not_deleted
ON bookings(tenant_id, status, slot_date)
WHERE deleted_at IS NULL;
```

### Cleanup Job

```python
# Background job to hard delete old soft-deleted records
class CleanupJob:
    async def run(self):
        # Find bookings deleted > 90 days ago
        old_bookings = await self._repo.find_soft_deleted_older_than(
            days=90
        )

        for booking in old_bookings:
            await self._repo.hard_delete(booking.id)

        return {"deleted": len(old_bookings)}
```

## Anti-Patterns

1. **Soft delete everything** — Some data doesn't need it (logs, events)
2. **Missing indexes on deleted_at** — Slow queries
3. **Not cascading** — Orphaned child records
4. **No cleanup** — Table grows indefinitely with deleted rows

## Examples

### Table Definition

```sql
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    facility_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    version INTEGER NOT NULL DEFAULT 1,

    -- Audit timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,  -- Soft delete

    -- Constraints
    CONSTRAINT fk_bookings_customer
        FOREIGN KEY (customer_id, tenant_id)
        REFERENCES customers(id, tenant_id)
);

-- Partial index for fast non-deleted queries
CREATE INDEX idx_bookings_not_deleted
ON bookings(tenant_id, status, slot_date)
WHERE deleted_at IS NULL;
```

## Related Documents

- [Schema Design](schema-design.md)
- [Auditing](auditing.md)
- [Retention & Archival](archival.md)
- [GDPR Compliance](../09-security/overview.md)
