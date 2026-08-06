# Secrets Management

> This document details our secrets management strategy, covering secret storage, rotation, injection, and scanning in CI/CD pipelines.

Secrets (API keys, database passwords, signing keys, tokens) are the highest-value targets for attackers. A single leaked secret can compromise the entire platform. We use a defense-in-depth approach: secrets are never committed to repositories, they are stored in secret managers, injected at runtime, and rotated automatically.

---

## Secret Storage: Cloud Secret Manager

We use **AWS Secrets Manager** (or HashiCorp Vault as an alternative) for secret storage. Secrets are stored with:

- **Encryption at rest** — AES-256 via AWS KMS
- **Access control** — IAM policies enforce least privilege
- **Audit logging** — CloudTrail logs all access
- **Rotation** — Automatic rotation on defined schedules

```json
{
  "secret_name": "splashh/prod/database/master",
  "secret_value": {
    "host": "prod-db.cluster-xxx.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "username": "splashh_master",
    "password": "ENC[AES256_GCM,data:xxx]"
  },
  "rotation": {
    "enabled": true,
    "schedule": "30days",
    "lambda": "arn:aws:lambda:xxx:rotate_secret"
  }
}
```

> **Rule** — No secrets in environment files in production. All secrets must be retrieved from the secret manager at runtime.

---

## Environment-Specific Secrets

| Environment | Storage | Access |
|---|---|---|
| Development | AWS Secrets Manager (dev prefix) | Developers via AWS profile |
| Staging | AWS Secrets Manager (staging prefix) | CI/CD via service role |
| Production | AWS Secrets Manager (prod prefix) | App via IAM role |

---

## Secret Injection at Runtime

We inject secrets into application containers via:

### 1. Kubernetes Secrets (from AWS Secrets Manager)

```yaml
# kubernetes/deployment.yaml
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: backend
      image: splashh/backend:latest
      env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: splashh-db-credentials
              key: connection_string
        - name: JWT_PRIVATE_KEY
          valueFrom:
            secretKeyRef:
              name: splashh-jwt-keys
              key: private_key
        - name: STRIPE_API_KEY
          valueFrom:
            secretKeyRef:
              name: splashh-stripe
              key: api_key
```

### 2. External Secrets Operator

We use the External Secrets Operator to sync AWS Secrets Manager secrets to Kubernetes:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: splashh-db-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: splashh-db-credentials
    creationPolicy: Owner
  data:
    - secretKey: connection_string
      remoteRef:
        key: splashh/prod/database/master
        property: connection_string
```

---

## Secret Rotation

We rotate secrets on defined schedules:

| Secret Type | Rotation Cadence | Method |
|---|---|---|
| Database password | 90 days | AWS Secrets Manager rotation |
| JWT signing keys | 90 days | Manual with JWKS rollover |
| API keys (Stripe, etc.) | Per provider max | Manual |
| Encryption keys | 365 days | Re-encryption process |

### Database Password Rotation

```python
# AWS Secrets Manager handles this automatically
# The rotation lambda updates the password in RDS
# and updates the secret

# Application code reads the secret as usual:
import boto3
import os

def get_db_connection_string():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(
        SecretId="splashh/prod/database/master"
    )
    return response["SecretString"]["connection_string"]
```

### JWT Key Rotation

JWT signing keys are rotated using a JWKS (JSON Web Key Set) pattern:

```python
# Multiple keys in JWKS, identified by 'kid' (key ID)
# Current key signs new tokens
# Old key validates existing tokens until expiry

JWKS = {
    "keys": [
        {
            "kty": "RSA",
            "kid": "current-key-id",
            "use": "sig",
            "alg": "RS256",
            "n": "...",  # Public modulus
            "e": "AQAB"  # Public exponent
        },
        {
            "kty": "RSA",
            "kid": "previous-key-id",
            "use": "sig",
            "alg": "RS256",
            "n": "...",  # Old key for token validation
            "e": "AQAB"
        }
    ]
}
```

See [Key Rotation](key-rotation.md) for details.

---

## Secret Scanning in CI

We scan for secrets in every commit using **gitleaks**:

```yaml
# .github/workflows/security-scan.yml
name: Secrets Scanning

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_CONFIG_PATH: .gitleaks.toml
```

### Gitleaks Configuration

```toml
# .gitleaks.toml
title = "Splashh Gitleaks Configuration"

[[rules]]
description = "AWS Access Key"
regex = '''(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}'''
tags = ["key", "aws"]

[[rules]]
description = "AWS Secret Key"
regex = '''(?i)(aws_secret_access_key|aws_secret|secret_key)(.{0,20})?['\"][0-9a-zA-Z/+]{40}['\"]'''
tags = ["key", "aws"]

[[rules]]
description = "JWT Token"
regex = '''eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]*'''
tags = ["token", "jwt"]

[allowlist]
paths = [".gitleaks.toml", "tests/fixtures/"]
```

---

## Secrets That Should Never Be Committed

| Secret Type | Risk | Where to Store |
|---|---|---|
| Database passwords | Full data breach | AWS Secrets Manager |
| API keys (Stripe, Razorpay) | Financial fraud | AWS Secrets Manager |
| JWT signing keys | Token forgery | AWS Secrets Manager / HSM |
| Encryption keys | Data decryption | AWS KMS / HSM |
| OAuth client secrets | Account takeover | AWS Secrets Manager |
| SSH keys | Server access | AWS Secrets Manager |

> **Rule** — Any secret committed to the repository must be considered compromised and rotated immediately.

---

## Cross-Reference

- [Encryption](encryption.md) — Key hierarchy and management
- [Key Rotation](key-rotation.md) — Rotation procedures
- [Dependency Scanning](dependency-scanning.md) — Dependency security
