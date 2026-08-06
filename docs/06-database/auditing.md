# Auditing

> This document covers audit trail implementation, tracking changes, and compliance logging.

## Overview

Auditing tracks who changed what and when. We maintain audit trails for **compliance** (GDPR, financial), **security** (unauthorized access), and **debugging** (data issues).

## Standard Audit Columns

Every table includes:

```sql
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,

    -- ... business columns ...

    -- Standard audit columns
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    deleted_at TIMESTAMPTZ
);
```

## Audit Log Table

For sensitive operations, use a separate audit log:

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,

    -- What
    entity_type VARCHAR(100) NOT NULL,  -- 'booking', 'customer', 'payment'
    entity_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL,  -- 'create', 'update', 'delete'

    -- Who
    user_id UUID,
    user_email VARCHAR(255),
    ip_address INET,

    -- Change details
    changes JSONB,  -- {"old": {...}, "new": {...}}
    reason TEXT,  -- Optional reason for change

    -- Metadata
    request_id UUID,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, timestamp);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
```

## Trigger-Based Auditing

Automatically capture changes:

```sql
-- Function to record changes
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_logs (
            tenant_id,
            entity_type,
            entity_id,
            action,
            changes,
            timestamp
        ) VALUES (
            NEW.tenant_id,
            TG_TABLE_NAME,
            NEW.id,
            'create',
            jsonb_build_object('new', to_jsonb(NEW)),
            NOW()
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_logs (
            tenant_id,
            entity_type,
            entity_id,
            action,
            changes,
            timestamp
        ) VALUES (
            NEW.tenant_id,
            TG_TABLE_NAME,
            NEW.id,
            'update',
            jsonb_build_object(
                'old', to_jsonb(OLD),
                'new', to_jsonb(NEW)
            ),
            NOW()
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_logs (
            tenant_id,
            entity_type,
            entity_id,
            action,
            changes,
            timestamp
        ) VALUES (
            OLD.tenant_id,
            TG_TABLE_NAME,
            OLD.id,
            'delete',
            jsonb_build_object('old', to_jsonb(OLD)),
            NOW()
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger
CREATE TRIGGER audit_bookings
AFTER INSERT OR UPDATE OR DELETE ON bookings
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
```

## Application-Level Auditing

For more control, log in application code:

```python
# src/common/audit.py
from datetime import datetime
import json


class AuditLogger:
    def __init__(self, db_session):
        self._session = db_session

    def log(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        action: str,
        changes: dict,
        user_id: UUID = None,
        reason: str = None,
    ):
        """Log an audit event."""
        audit_log = AuditLog(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            changes=json.dumps(changes),
            user_id=user_id,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
        self._session.add(audit_log)
        self._session.flush()


# Usage in service
class BookingService:
    def confirm_booking(self, booking_id: UUID, actor_id: UUID) -> BookingResult:
        booking = self._repo.get(booking_id)

        old_status = booking.status
        booking.confirm()
        self._repo.save(booking)

        # Audit log
        self._audit.log(
            tenant_id=booking.tenant_id,
            entity_type="booking",
            entity_id=booking_id,
            action="confirm",
            changes={"old": old_status, "new": booking.status},
            user_id=actor_id,
        )

        return BookingResult.from_entity(booking)
```

## Sensitive Operations to Audit

| Operation | Why |
|-----------|-----|
| Membership cancellation | Financial, refund tracking |
| Refund issued | Financial reconciliation |
| Role/permission change | Security |
| Customer data export | GDPR compliance |
| Customer data deletion | GDPR/DPDPA |
| Price changes | Financial |
| Bulk operations | Accountability |

## Audit Query Examples

```sql
-- Find all changes to a booking
SELECT * FROM audit_logs
WHERE entity_type = 'bookings'
AND entity_id = 'booking-123'
ORDER BY timestamp DESC;

-- Find all changes by a user
SELECT * FROM audit_logs
WHERE user_id = 'user-123'
AND timestamp > NOW() - INTERVAL '30 days';

-- Find all deletions in last week
SELECT * FROM audit_logs
WHERE action = 'delete'
AND timestamp > NOW() - INTERVAL '7 days';
```

## Retention

| Audit Type | Retention |
|------------|-----------|
| Login/logout | 1 year |
| Data changes | 7 years |
| Financial transactions | 7 years |
| Security events | 1 year |
| Access logs | 90 days |

See [Archival](archival.md) for long-term storage.

## Tamper-Evidence

Make audit logs hard to modify:

```sql
-- Append-only (no updates)
-- Revoke UPDATE on audit_logs
REVOKE UPDATE ON audit_logs FROM app_user;

-- Or use trigger to prevent updates
CREATE OR REPLACE FUNCTION prevent_audit_update()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs cannot be updated';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_audit_update
BEFORE UPDATE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_update();
```

## Anti-Patterns

1. **Not auditing critical operations** — Compliance violations
2. **Storing full objects** — Version everything instead
3. **No index on audit queries** — Slow historical lookups
4. **Allowing audit modification** — Breaks integrity

## Related Documents

- [Soft Delete](soft-delete.md)
- [Archival](archival.md)
- [Backup & Recovery](backups.md)
- [Security Logging](../04-backend/logging.md)
