# Environment Management

> dev / preview / staging / production. Per-tenant config. Per-environment secrets.

This document defines our environment strategy: the purpose, configuration, and promotion rules for each environment. We prioritize isolation (each environment is independent) and parity (staging mirrors production).

---

## Environment Overview

| Environment | Purpose | Scope | Auto-Deploy | Data |
|---|---|---|---|---|
| Development | Local development | Per-developer | N/A | Seeded |
| Preview | PR testing | Per-PR | On PR | Ephemeral |
| Staging | Integration testing | Shared | On merge | Sanitized prod |
| Production | Live traffic | Shared | On tag | Real |

---

## Environment Architecture

```mermaid
flowchart LR
    A[Local Dev] --> B[Preview]
    B --> C[Staging]
    C --> D[Production]

    style A fill:#e1f5fe
    style B fill:#fff3e0
    style C fill:#e8f5e9
    style D fill:#ffebee
```

---

## Development Environment

Purpose: Local development and testing

```bash
# Local development with docker-compose
docker-compose up -d

# Environment variables
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/splashh_dev
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### Configuration

- Uses local database (PostgreSQL via Docker)
- Uses local Redis
- Debug logging enabled
- Mock external services where possible

---

## Preview Environment

Purpose: Test PR changes in an isolated environment

```yaml
# kubernetes/preview-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: pr-{pr_number}
  labels:
    environment: preview
```

### Auto-Creation

- Created when PR is opened
- Deleted when PR is closed/merged
- Uses ephemeral database (or database per PR for integration tests)

```yaml
# .github/workflows/preview.yml
on:
  pull_request:
    types: [opened, synchronize, closed]

jobs:
  deploy:
    if: github.event_name == 'pull_request'
    steps:
      - name: Create preview namespace
        run: |
          kubectl create namespace pr-${{ github.event.pull_request.number }}

      - name: Deploy
        run: |
          kubectl set image deployment/api api=$IMAGE -n pr-${{ github.event.pull_request.number }}

  cleanup:
    if: github.event.action == 'closed'
    steps:
      - name: Delete preview namespace
        run: |
          kubectl delete namespace pr-${{ github.event.pull_request.number }}
```

---

## Staging Environment

Purpose: Pre-production integration testing

### Configuration

```yaml
# Environment configuration
ENVIRONMENT=staging
LOG_LEVEL=INFO
DATABASE_URL=postgresql://staging-db.xxx.us-east-1.rds.amazonaws.com:5432/splashh_staging
REDIS_URL=redis://staging-redis.xxx.cache.amazonaws.com:6379/0

# Feature flags (staging-specific)
FF_NEW_BOOKING_FLOW=true
FF_DARK_MODE=true
```

### Data Strategy

- Sanitized production data (PII removed)
- Refreshed weekly from production
- Synthetic test data for edge cases

```python
# scripts/sanitize_data.py
"""
Sanitize production data for staging.
- Remove PII
- Anonymize emails
- Reset passwords
"""
import random


def sanitize_user(user):
    return {
        "id": user.id,
        "email": f"user_{user.id}@example.com",
        "name": f"Test User {user.id}",
        "phone": f"+1555{random.randint(1000000, 9999999)}",
    }
```

---

## Production Environment

Purpose: Live customer traffic

### Configuration

```yaml
ENVIRONMENT=production
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://prod-db.xxx.us-east-1.rds.amazonaws.com:5432/splashh_production
REDIS_URL=redis://prod-redis.xxx.cache.amazonaws.com:6379/0

# Production feature flags (conservative)
FF_NEW_BOOKING_FLOW=false
FF_DARK_MODE=false
```

### Security

- Secrets from AWS Secrets Manager (not in code)
- Private subnets only
- WAF in front of ALB
- VPC peering for database access

---

## Per-Tenant Configuration

Multi-tenant configuration via environment and database:

```python
# apps/backend/src/common/tenant_config.py
from functools import lru_cache
from pydantic import BaseModel


class TenantConfig(BaseModel):
    """Configuration for a specific tenant."""
    tenant_id: str
    name: str
    tier: str  # free, basic, premium
    features: list[str]
    rate_limit: int
    max_bookings: int


class TenantConfigService:
    """Service to fetch tenant configuration."""

    def __init__(self, db):
        self.db = db

    @lru_cache(maxsize=1000)
    def get_config(self, tenant_id: str) -> TenantConfig:
        """Get configuration for tenant (cached)."""
        # Fetch from database
        row = self.db.query(
            "SELECT * FROM tenant_config WHERE tenant_id = ?",
            tenant_id
        )
        return TenantConfig(**row)
```

---

## Environment Promotion

Code flows through environments in order:

```mermaid
flowchart LR
    A[dev] --> B[preview]
    B --> C[staging]
    C --> D[production]

    style A fill:#e1f5fe
    style B fill:#fff3e0
    style C fill:#e8f5e9
    style D fill:#ffebee
```

| Promotion | Trigger | Approval | Rollback |
|---|---|---|---|
| dev → preview | PR open | None | PR close |
| preview → staging | PR merge | None | Auto |
| staging → production | Release tag | On-call | Manual |

---

## Environment Differences

| Aspect | Development | Staging | Production |
|---|---|---|---|
| Database | Local Docker | Managed (smaller) | Managed (prod) |
| Cache | Local Redis | Managed | Managed |
| External APIs | Sandbox | Sandbox/Mock | Production |
| Logging | stdout | Loki | Loki |
| Monitoring | Basic | Full | Full + alerts |
| Backup | None | Daily | Continuous |
| Auto-scaling | None | Limited | Full |
| Feature flags | All on | Configurable | Conservative |

---

## Environment Verification

Before promoting to production, verify:

- [ ] All tests passing
- [ ] Smoke tests passing
- [ ] Performance acceptable
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] Feature flags configured
- [ ] Monitoring alerts tested
- [ ] Runbooks verified

---

## Summary

| Environment | Auto-Deploy | Isolation | Data |
|---|---|---|---|
| Development | N/A | Per-developer | Seeded |
| Preview | On PR | Per-PR | Ephemeral |
| Staging | On merge | Shared | Sanitized |
| Production | On tag | Shared | Real |

---

## Related Documents

- [Deployments](./deployments.md) — Deployment process
- [Release Strategy](./release-strategy.md) — Release process
- [Secrets](./secrets.md) — Secret management
- [Monitoring](./monitoring.md) — Monitoring setup
