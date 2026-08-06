# Backup & Recovery

> This document details our backup strategy, including encrypted backups, restore procedures, RPO/RTO targets, and testing cadence.

Data is the core asset of the platform. We maintain a comprehensive backup strategy with automated backups, encrypted storage, regular restore testing, and clear RPO/RTO targets.

---

## RPO and RTO Targets

| Metric | Target | Definition |
|---|---|---|
| **RPO** (Recovery Point Objective) | 1 hour | Maximum data loss acceptable |
| **RTO** (Recovery Time Objective) | 4 hours | Maximum downtime before recovery |

---

## Backup Types

### 1. Automated Daily Backups

PostgreSQL Point-in-Time Recovery (PITR) is enabled:

```python
# AWS RDS configuration
# - Daily automated backups with 30-day retention
# - Point-in-time recovery to any second in last 7 days
# - Cross-region backup copy for disaster recovery
```

### 2. Continuous Archiving (WAL)

Write-Ahead Logs are archived continuously:

```sql
-- wal_level = replica
-- archive_mode = on
-- archive_command = aws s3 cp %p s3://splashh-backups/wal/%f
```

### 3. Logical Backups (Weekly)

Weekly full logical backups for long-term retention:

```bash
#!/bin/bash
# Weekly full backup
pg_dump -Fc splashh_prod | gzip > /backups/weekly_$(date +%Y%m%d).dump.gz
aws s3 cp /backups/weekly_*.dump.gz s3://splashh-backups/weekly/
```

---

## Backup Encryption

All backups are encrypted at rest:

| Backup Type | Encryption Method |
|---|---|
| AWS RDS automated | AWS-managed (AES-256) |
| WAL archives | SSE-S3 (AES-256) |
| Logical backups | OpenSSL + AES-256 |
| S3 buckets | SSE-KMS |

---

## Backup Retention

| Backup Type | Retention | Storage |
|---|---|---|
| Daily automated | 30 days | AWS RDS |
| Point-in-time | 7 days | S3 |
| Weekly logical | 90 days | S3 Glacier |
| Monthly | 7 years | S3 Glacier |

---

## Restore Procedures

### 1. Point-in-Time Recovery

```bash
#!/bin/bash
# Restore to specific point in time
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier splashh-prod \
    --target-db-instance-name splashh-prod-restore \
    --restore-time 2024-01-15T10:30:00Z
```

### 2. Full Database Restore

```bash
#!/bin/bash
# Restore from latest daily backup
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier splashh-prod-restore \
    --db-snapshot-identifier splashh-prod-latest

# Restore logical backup
pg_restore -d splashh_prod_restore /backups/weekly_20240115.dump.gz
```

---

## Restore Testing Cadence

| Test Type | Frequency | Scope |
|---|---|---|
| Automated restore verification | Weekly | Full backup restored to test DB |
| Manual restore drill | Quarterly | Full production-like scenario |
| Disaster recovery drill | Annually | Cross-region failover |

### Automated Verification Script

```bash
#!/bin/bash
# Weekly restore test
BACKUP_FILE=$(aws s3 ls splashh-backups/weekly/ | sort | tail -1 | awk '{print $4}')

# Restore to test instance
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier splashh-test-restore \
    --db-snapshot-identifier $BACKUP_FILE

# Wait for restore
aws rds wait db-instance-available --db-instance-identifier splashh-test-restore

# Run verification queries
psql -h splashh-test-restore.xxx.rds.amazonaws.com -U splashh_test \
    -c "SELECT COUNT(*) FROM users;" \
    -c "SELECT COUNT(*) FROM bookings;"

# Report success/failure
if [ $? -eq 0 ]; then
    echo "Restore verification PASSED"
else
    echo "Restore verification FAILED"
    # Alert team
fi
```

---

## Backup Access Controls

| Role | Backup Access |
|---|---|
| Automated systems | Full read/write (via IAM role) |
| DevOps | Read (for restore) |
| Security | Audit (logs only) |
| No individuals | Direct access |

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::splashh-backups/*"
      ],
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": "10.0.0.0/8"  # Only from VPC
        }
      }
    }
  ]
}
```

---

## Cross-Reference

- [Disaster Recovery](disaster-recovery.md) — DR scenarios
- [Encryption](encryption.md) — Backup encryption
- [Incident Response](incident-response.md) — Data breach response
