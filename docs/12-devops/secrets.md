# Secrets Management

> Secrets in cloud secret manager. CI/CD injects at deploy time. No secrets in code.

This document defines how we handle secrets: API keys, database passwords, tokens, and certificates. We prioritize runtime injection (no secrets in images), rotation (automated), and detection (CI scanning).

---

## Secrets Architecture

```mermaid
flowchart LR
    A[Secret Manager<br/>AWS Secrets Manager<br/>HashiCorp Vault] --> B[CI/CD Pipeline]
    B --> C[Build Image<br/>No secrets]
    C --> D[Deploy]
    D --> E[Inject at runtime<br/>Environment variables<br/>Kubernetes secrets]
    E --> F[Application]
```

> **Why** — Storing secrets in containers creates security vulnerabilities. Even if the image is private, layers can be extracted. Runtime injection ensures secrets are never baked into images.

---

## Secret Storage

### Cloud Provider: AWS Secrets Manager

For production:

```bash
# Create secret
aws secretsmanager create-secret \
    --name "splashh/production/database" \
    --secret-string '{"host":"prod-db.cluster-xxx.us-east-1.rds.amazonaws.com","port":5432,"username":"app_user","password":"actual_password"}'

# Create secret with rotation
aws secretsmanager create-secret \
    --name "splashh/production/api-keys/stripe" \
    --secret-string '{"secret_key":"sk_live_xxx","publishable_key":"pk_live_xxx"}' \
    --rotation-lambda-arn "arn:aws:lambda:us-east-1:123456789:function:stripe-rotation"
```

### Secrets Structure

| Path | Contents | Rotation |
|---|---|---|
| `splashh/{env}/database` | Host, port, username, password | 90 days |
| `splashh/{env}/redis` | Host, port, password | 90 days |
| `splashh/{env}/jwt-secret` | Signing key | 30 days |
| `splashh/{env}/api-keys/*` | External service keys | Per-service |
| `splashh/{env}/smtp` | Email credentials | 180 days |

---

## Injection into Kubernetes

We use External Secrets Operator for Kubernetes:

```yaml
# kubernetes/base/secrets.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: backend-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: app-secrets
    creationPolicy: Owner
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: splashh/production/database
        property: connection_string
    - secretKey: REDIS_URL
      remoteRef:
        key: splashh/production/redis
    - secretKey: JWT_SECRET
      remoteRef:
        key: splashh/production/jwt-secret
```

Then mount as environment variables:

```yaml
# kubernetes/deployment.yaml
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: app-secrets
        key: DATABASE_URL
  - name: JWT_SECRET
    valueFrom:
      secretKeyRef:
        name: app-secrets
        key: JWT_SECRET
```

> **Why** — External Secrets Operator syncs secrets from AWS to Kubernetes automatically. This avoids manual secret management and ensures consistency.

---

## CI/CD Injection

For GitHub Actions, we inject secrets at deploy time:

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    steps:
      - name: Get secrets from AWS
        uses: aws-actions/aws-secrets-manager-get-secrets@v1
        with:
          secret-ids: |
            splashh/production/database
            splashh/production/redis
            splashh/production/api-keys/stripe
          parse-json-secrets: true
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: us-east-1

      - name: Deploy to Kubernetes
        run: |
          kubectl create secret generic app-secrets \
            --from-literal=database-url="$DATABASE_URL" \
            --from-literal=redis-url="$REDIS_URL" \
            --dry-run=client -o yaml | kubectl apply -f -
```

---

## Local Development

For local development, we use `.env` files that are never committed:

```bash
# .env.example - COPY THIS TO .env AND FILL IN VALUES
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/splashh
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=dev-secret-change-in-production
STRIPE_SECRET_KEY=sk_test_xxx
LAUNCHDARKLY_SDK_KEY=xxx
```

```bash
# .env - NEVER COMMIT THIS FILE
# This file is gitignored
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/splashh_dev
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=super-secret-dev-key-12345
STRIPE_SECRET_KEY=sk_test_51xxx
LAUNCHDARKLY_SDK_KEY=sdk-xxx
```

> **Rule** — `.env` files are in `.gitignore`. Never commit secrets.

---

## Secret Rotation

| Secret Type | Rotation Cadence | Method |
|---|---|---|
| Database password | 90 days | AWS Secrets Manager rotation |
| Redis password | 90 days | Manual or automation |
| JWT signing key | 30 days | Zero-downtime rotation |
| API keys (Stripe, etc.) | Per-vendor | Manual or scheduled |
| SMTP credentials | 180 days | Manual |

### JWT Key Rotation

```python
# apps/backend/src/auth/jwt.py
from datetime import datetime, timedelta
from typing import NewType
import jwt


# Multiple keys for rotation support
class JWTManager:
    def __init__(self):
        self._keys = [
            {"id": "current", "key": current_secret},
            {"id": "previous", "key": previous_secret},
        ]

    def encode(self, payload: dict) -> str:
        """Encode with current key."""
        return jwt.encode(payload, self._keys[0]["key"], algorithm="HS256", headers={"kid": "current"})

    def decode(self, token: str) -> dict:
        """Decode, trying all valid keys."""
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid", "current")

        for key_info in self._keys:
            if key_info["id"] == kid:
                return jwt.decode(token, key_info["key"], algorithms=["HS256"])

        raise jwt.InvalidTokenError("No valid key found")
```

---

## Secret Scanning in CI

We scan for leaked secrets in every PR:

```yaml
# .github/workflows/security.yml
jobs:
  secrets-scan:
    name: Scan for Secrets
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD
          extra_args: --regex --entropy=False

      - name: Run GitLeaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

> **Rule** — Any secret detected in code blocks CI. The secret must be rotated immediately.

---

## Secrets in Logs

> **Anti-pattern** — Never log secrets, even in error messages.

```python
# BAD: Leaking secret in logs
logger.error(f"Stripe API call failed: {stripe_secret_key}")

# GOOD: Redacted logging
logger.error(f"Stripe API call failed: api_key=***{stripe_key[-4:]}")
```

```python
# Log redaction utility
import re
import logging


class SecretRedactionFilter(logging.Filter):
    """Filter that redacts secrets from log messages."""

    PATTERNS = [
        (r'sk_(live|test)_[a-zA-Z0-9]+', 'sk_***'),
        (r'Bearer [a-zA-Z0-9\-_.~+/]+=*', 'Bearer ***'),
        (r'password["\s:]+[^\s",}]+', 'password: ***'),
        (r'secret["\s:]+[^\s",}]+', 'secret: ***'),
    ]

    def filter(self, record):
        msg = record.getMessage()
        for pattern, replacement in self.PATTERNS:
            msg = re.sub(pattern, replacement, msg)
        record.msg = msg
        return True


# Usage in logging config
logging.basicConfig(
    handlers=[logging.StreamHandler()],
    filters=[SecretRedactionFilter()],
)
```

---

## Summary

| Practice | Implementation |
|---|---|
| Storage | AWS Secrets Manager |
| Injection | Kubernetes External Secrets |
| Local dev | .env files (gitignored) |
| Rotation | 30-90 days depending on secret type |
| Scanning | TruffleHog + GitLeaks in CI |
| Logging | Redaction filter |

---

## Related Documents

- [Docker](./docker.md) — Container security
- [GitHub Actions](./github-actions.md) — CI/CD pipeline
- [Monitoring](./monitoring.md) — Security monitoring
- [Incident Response](../09-security/incident-response.md) — Secret leak response
