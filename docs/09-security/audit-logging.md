# Audit Logging

> This document details our audit logging strategy, covering what events to log, log structure, tamper evidence, retention policies, and SIEM integration.

Audit logs provide the evidentiary foundation for security investigations, compliance audits, and incident response. We log security-relevant events in an append-only, tamper-evident log that supports 7-year retention requirements under DPDPA.

---

## What to Log

We categorize audit events into security, operational, and compliance:

### Security Events (Mandatory)

| Event | Fields | Rationale |
|---|---|---|
| Authentication success | user_id, tenant_id, IP, timestamp | Account usage tracking |
| Authentication failure | email, IP, reason, timestamp | Intrusion detection |
| Authorization failure | user_id, resource, action, timestamp | Privilege escalation detection |
| Role/permission change | user_id, target_user, old_role, new_role, timestamp | Insider threat |
| Password change | user_id, timestamp | Account takeover detection |
| MFA enabled/disabled | user_id, method, timestamp | Security setting changes |
| Token issued | user_id, token_type, jti, timestamp | Session tracking |
| Token revoked | user_id, jti, reason, timestamp | Session termination |

### Financial Events

| Event | Fields | Rationale |
|---|---|---|
| Payment initiated | amount, currency, method, user_id, timestamp | Financial audit |
| Payment completed | transaction_id, amount, gateway, timestamp | Financial audit |
| Refund issued | original_txn_id, amount, reason, admin_id, timestamp | Financial audit |
| Subscription created/modified | plan_id, user_id, timestamp | Billing audit |

### Data Events

| Event | Fields | Rationale |
|---|---|---|
| Data export | user_id, export_type, record_count, timestamp | GDPR/DPDPA compliance |
| Bulk data change | admin_id, table, affected_rows, timestamp | Administrative audit |
| Tenant settings change | admin_id, setting_key, old_value, new_value, timestamp | Configuration audit |

---

## Log Structure

We use structured JSON logs for all audit events:

```python
import json
from datetime import datetime
from uuid import uuid4

class AuditEvent:
    def __init__(
        self,
        event_type: str,
        actor_id: str,
        tenant_id: str,
        resource_type: str = None,
        resource_id: str = None,
        action: str = None,
        outcome: str = "success",
        details: dict = None,
        ip_address: str = None,
        user_agent: str = None
    ):
        self.event_id = str(uuid4())
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.event_type = event_type
        self.actor = {
            "user_id": actor_id,
            "tenant_id": tenant_id,
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        self.resource = {
            "type": resource_type,
            "id": resource_id,
            "action": action
        }
        self.outcome = outcome
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "resource": self.resource,
            "outcome": self.outcome,
            "details": self.details
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
```

---

## Append-Only with Tamper Evidence

We implement tamper-evident logging using a hash chain:

```python
import hashlib
import json

class TamperEvidentLog:
    def __init__(self, previous_hash: str = "0" * 64):
        self.previous_hash = previous_hash

    def compute_hash(self, event: dict) -> str:
        """Compute SHA-256 hash of event."""
        # Include previous hash to create chain
        event_with_prev = {**event, "previous_hash": self.previous_hash}
        serialized = json.dumps(event_with_prev, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def append(self, event: AuditEvent) -> str:
        """Append event and return its hash."""
        event_dict = event.to_dict()
        event_hash = self.compute_hash(event_dict)

        # Store with hash
        event_dict["hash"] = event_hash
        # Store hash for next event
        self.previous_hash = event_hash

        # Write to database
        self._write_to_log(event_dict)

        return event_hash
```

> **Why hash chain** — Each log entry contains the hash of the previous entry. If anyone modifies a past entry, the hash chain breaks, making tampering detectable.

---

## Database Schema

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_user_id UUID,
    actor_tenant_id UUID NOT NULL,
    actor_ip INET,
    resource_type VARCHAR(100),
    resource_id UUID,
    action VARCHAR(100),
    outcome VARCHAR(20) NOT NULL,
    details JSONB,
    hash VARCHAR(64) NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,

    -- Indexes for common queries
    INDEX idx_audit_tenant_time (actor_tenant_id, timestamp),
    INDEX idx_audit_user_time (actor_user_id, timestamp),
    INDEX idx_audit_type (event_type),
    INDEX idx_audit_resource (resource_type, resource_id)
);

-- Partition by month for performance
CREATE TABLE audit_log_2024_01 PARTITION OF audit_log
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

---

## Retention Policy

| Data Category | Retention | Legal Basis |
|---|---|---|
| Audit logs | 7 years | DPDPA, tax records |
| Security logs | 3 years | Internal policy |
| Operational logs | 1 year | Operational needs |
| Debug logs | 30 days | Debugging only |

---

## SIEM Integration

We export audit logs to a SIEM for real-time monitoring:

```python
import httpx

async def export_to_siem(event: AuditEvent):
    """Export audit event to SIEM (e.g., Splunk, Datadog)."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{SIEM_ENDPOINT}/api/v1/events",
            json=event.to_dict(),
            headers={
                "Authorization": f"Bearer {SIEM_API_KEY}",
                "X-Splashh-Event": event.event_type
            }
        )
```

### Alert Rules (Examples)

| Rule | Condition | Action |
|---|---|---|
| Impossible travel | Login from different countries < 1 hour | Block account, alert security |
| Mass permission change | > 10 role changes in 1 minute | Page on-call |
| Data export spike | > 1000 records exported | Alert DPO |
| Failed MFA attempts | > 5 failures in 10 minutes | Alert security |

---

## Logged vs. Not Logged

> **Rule** — Never log sensitive data in audit logs:

| Should Log | Should NOT Log |
|---|---|
| User ID | Passwords, hashes |
| Tenant ID | Full PAN numbers |
| Action performed | CVV, card numbers |
| Timestamp | API keys, secrets |
| IP address | Medical/health data |
| Resource ID | Biometric data |

---

## Cross-Reference

- [Incident Response](incident-response.md) — Security incident handling
- [Encryption](encryption.md) — Log encryption at rest
- [Disaster Recovery](disaster-recovery.md) — Log recovery
