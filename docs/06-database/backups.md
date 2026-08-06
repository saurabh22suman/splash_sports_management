# Backups

> This document covers PostgreSQL backup strategies, point-in-time recovery, and disaster recovery.

## Overview

We maintain **daily base backups** with **WAL archiving** for point-in-time recovery (PITR). This allows recovery to any point within the retention window.

## Backup Strategy

| Component | Frequency | Retention | Method |
|-----------|-----------|-----------|--------|
| Base backup | Daily | 30 days | pg_basebackup |
| WAL archives | Continuous | 30 days | pg_receivewal |
| PITR window | - | 30 days | From base + WAL |

## Configuration

### WAL Archiving

```sql
-- postgresql.conf
wal_level = replica
max_wal_senders = 3
wal_keep_size = 1GB

archive_mode = on
archive_command = 'aws s3 cp %p s3://splashh-backups/wal/%f'
archive_timeout = 300  -- 5 minutes max lag
```

### Backup Configuration

```bash
# pg_hba.conf - allow replication
host replication all 10.0.0.0/8 md5
```

## Taking Backups

### Base Backup

```bash
# Using pg_basebackup
pg_basebackup \
  -h primary_host \
  -D /backup/base \
  -Ft \
  -z \
  -P \
  -U replication

# Upload to S3
aws s3 cp /backup/base s3://splashh-backups/base/$(date +%Y%m%d)/
```

### Automated Script

```bash
#!/bin/bash
# daily_backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup"
S3_BUCKET="splashh-backups"

# Create backup
pg_basebackup -h $PGHOST -D $BACKUP_DIR/base_$DATE -Ft -z -P -U replication

# Upload
aws s3 cp $BACKUP_DIR/base_$DATE $S3_BUCKET/base/$DATE/ --recursive

# Cleanup local
rm -rf $BACKUP_DIR/base_$DATE

# Keep last 7 locally
ls -1t $BACKUP_DIR/base_* | tail -n +8 | xargs -r rm -rf
```

## Point-in-Time Recovery (PITR)

### Recovery Process

```bash
# 1. Stop PostgreSQL
pg_ctl stop -D /var/lib/postgresql/data

# 2. Clean data directory
rm -rf /var/lib/postgresql/data/*

# 3. Restore base backup
aws s3 cp s3://splashh-backups/base/20240115/ - /var/lib/postgresql/data/ --recursive

# 4. Create recovery signal
touch /var/lib/postgresql/data/recovery.signal

# 5. Configure recovery
cat >> /var/lib/postgresql/data/postgresql.conf << EOF
restore_command = 'aws s3 cp s3://splashh-backups/wal/%f %p'
recovery_target_time = '2024-01-15 14:30:00 UTC'
EOF

# 6. Start PostgreSQL
pg_ctl start -D /var/lib/postgresql/data
```

### Target Types

```bash
# Point in time
recovery_target_time = '2024-01-15 14:30:00 UTC'

# Specific transaction
recovery_target_xid = '12345'

# Named restore point
recovery_target_name = 'before_migration'
```

## Backup Verification

### Test Restore

```bash
# Restore to test instance
pg_restore -h test-db -d test_db /backup/base/backup.dump

# Verify
psql -h test-db -d test_db -c "SELECT COUNT(*) FROM bookings;"
```

### Automated Tests

```yaml
# .github/workflows/backup-test.yml
- name: Restore Backup Test
  run: |
    # Restore to test DB
    pg_restore -h test-db test_db backup.dump

    # Run verification queries
    psql -h test-db test_db -f tests/verify_data.sql
```

## Encryption

### At Rest

```bash
# S3 server-side encryption
aws s3 cp file s3://bucket/ --sse AES256

# PostgreSQL data encryption (TDE)
# Use volume-level encryption (LUKS)
```

### In Transit

```bash
# Use SSL for all connections
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
```

## Monitoring

### Backup Status

```sql
-- Check last backup
SELECT pg_current_wal_lsn();

-- Check WAL shipping
SELECT * FROM pg_stat_replication;
```

### Alerts

```yaml
# prometheus/backup_alerts.yml
- alert: BackupMissing
  expr: time() - pg_backup_last_success > 86400
  for: 5m
  labels:
    severity: critical
```

## Retention

| Backup Type | Retention |
|-------------|-----------|
| Daily base | 30 days |
| Weekly base | 90 days (monthly kept) |
| WAL archives | 30 days |
| Offsite copies | 1 year |

## Disaster Recovery Runbook

1. **Detect failure** — Alert triggered
2. **Assess** — Determine RTO (recovery time objective)
3. **Decide** — Use latest backup or PITR
4. **Restore** — Follow recovery process
5. **Verify** — Run integrity checks
6. **Notify** — Update stakeholders

### RTO/RPO Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| RTO | 4 hours | Documented recovery, tested quarterly |
| RPO | 1 hour | WAL shipping every 5 min |

## Anti-Patterns

1. **No backups** — Data loss inevitable
2. **No testing** — Backup may be corrupt
3. **No offsite** — Regional failure loses all
4. **No encryption** — Security risk

## Related Documents

- [Schema Design](schema-design.md)
- [Disaster Recovery](../02-architecture/disaster-recovery.md)
- [Security - Backup & Recovery](../09-security/backup-recovery.md)
