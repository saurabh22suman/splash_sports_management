# Encryption

> This document covers our encryption strategy, including TLS for transit, field-level encryption for PII at rest, key hierarchy, HSM usage, and backup encryption.

Encryption protects data at rest and in transit. We use TLS 1.3 for all network communication, AES-256 field-level encryption for sensitive data at rest, and a key hierarchy with AWS KMS at the top.

---

## Encryption in Transit: TLS 1.3

All network communication uses TLS 1.3:

### Server Configuration (Nginx)

```nginx
# /etc/nginx/nginx.conf
server {
    listen 443 ssl http2;
    server_name api.splashh.com;

    # TLS 1.3 only
    ssl_protocols TLSv1.3;

    # Strong cipher suites
    ssl_ciphers 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
}
```

### Client Configuration

```python
import httpx

# Verify certificates, use TLS 1.3
client = httpx.AsyncClient(
    verify=True,  # Verify certificate
    http2=True,  # Prefer HTTP/2
)

# For internal services, use custom CA
internal_client = httpx.AsyncClient(
    verify="/path/to/internal-ca.crt",
)
```

> **Rule** — TLS 1.2 and below are disabled. No exceptions.

---

## Encryption at Rest: Field-Level

We encrypt sensitive PII at the database field level using **pgcrypto**:

### Database Extension

```sql
-- Enable pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### Column-Level Encryption

```sql
-- Encrypt PII columns
ALTER TABLE members
    ALTER COLUMN email TYPE bytea USING pgp_sym_encrypt(email::bytea, current_setting('app.encryption_key')),
    ALTER COLUMN phone TYPE bytea USING pgp_sym_encrypt(phone::bytea, current_setting('app.encryption_key')),
    ALTER COLUMN emergency_contact TYPE bytea USING pgp_sym_encrypt(emergency_contact::bytea, current_setting('app.encryption_key'));
```

### Application-Level Encryption (Alternative)

For additional control, we encrypt at the application layer:

```python
from cryptography.fernet import Fernet
import base64
import boto3

class FieldEncryptor:
    """Field-level encryption using Fernet (AES-128) with KMS-managed keys."""

    def __init__(self):
        self.kms = boto3.client('kms')
        self._key_cache = {}
        self._key_version = None

    def _get_dek(self, tenant_id: str) -> bytes:
        """Get or create Data Encryption Key for tenant."""
        if tenant_id in self._key_cache:
            return self._key_cache[tenant_id]

        # Generate DEK from KMS
        response = self.kms.generate_data_key(
            KeyId='alias/splashh-dek',
            KeySpec='AES_128',
            EncryptionContext={'tenant_id': tenant_id}
        )

        # Store encrypted version for later key rotation
        encrypted_dek = response['CiphertextBlob']
        plaintext_dek = response['Plaintext']

        self._key_cache[tenant_id] = base64.b64decode(plaintext_dek)
        return self._key_cache[tenant_id]

    def encrypt(self, plaintext: str, tenant_id: str) -> str:
        """Encrypt field value."""
        key = self._get_dek(tenant_id)
        f = Fernet(key)
        return f.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str, tenant_id: str) -> str:
        """Decrypt field value."""
        key = self._get_dek(tenant_id)
        f = Fernet(key)
        return f.decrypt(ciphertext.encode()).decode()
```

---

## Key Hierarchy

We use a three-level key hierarchy:

```mermaid
flowchart TD
    A[AWS KMS (HSM-backed)] --> B[Data Encryption Keys DEK]
    B --> C[Encrypted Data]

    A --- A1["Root Key - never leaves HSM"]
    B --- B1["Per-tenant DEKs"]
    C --- C1["PII, sensitive fields"]
```

| Level | Key Type | Storage | Rotation |
|---|---|---|---|
| 1 | KMS Key (Root) | AWS CloudHSM/KMS | Manual (yearly) |
| 2 | DEK (Data Encryption Key) | Encrypted in KMS, decrypted at runtime | 90 days |
| 3 | Encrypted Data | PostgreSQL (pgcrypto) | N/A |

---

## HSM for Signing Keys

JWT signing keys and other cryptographic signing keys are stored in AWS KMS with HSM backing:

```python
import boto3

def create_signing_key():
    """Create RSA key pair in KMS for JWT signing."""
    response = boto3.client('kms').create_key(
        KeyUsage='SIGN_VERIFY',
        KeySpec='RSA_4096',
        Description='JWT Signing Key'
    )
    return response['KeyMetadata']['KeyId']

def sign_jwt(payload: dict) -> str:
    """Sign JWT payload using KMS."""
    message = json.dumps(payload).encode()
    response = boto3.client('kms').sign(
        KeyId=JWT_SIGNING_KEY_ID,
        Message=message,
        MessageType='RAW',
        SigningAlgorithm='RSASSA_PKCS1_V1_5_SHA_256'
    )
    return base64.b64encode(response['Signature']).decode()
```

---

## Encrypted Backups

Database backups are encrypted:

```python
import subprocess

def create_encrypted_backup(backup_id: str):
    """Create encrypted PostgreSQL backup."""
    # Generate one-time password
    password = secrets.token_hex(32)

    # Create backup with encryption
    subprocess.run([
        "pg_dump",
        "-Fc",  # Custom format
        "-f", f"/backups/{backup_id}.dump",
        "-v"
    ], env={**os.environ, "PGPASSWORD": password})

    # Encrypt backup file
    subprocess.run([
        "openssl", "enc",
        "-aes-256-cbc",
        "-salt",
        "-pbkdf2",
        "-in", f"/backups/{backup_id}.dump",
        "-out", f"/backups/{backup_id}.dump.enc",
        "-pass", f"pass:{password}"
    ])

    # Store password in KMS for recovery
    boto3.client('kms').encrypt(
        KeyId='alias/splashh-backup',
        Plaintext=password
    )

    # Upload to S3 with SSE
    s3.upload_file(
        f"/backups/{backup_id}.dump.enc",
        "splashh-backups",
        f"{backup_id}.dump.enc",
        ExtraArgs={
            'ServerSideEncryption': 'AES256'
        }
    )
```

---

## Encryption Decision Matrix

| Data Type | At Rest | In Transit | Key Management |
|---|---|---|---|
| PII (name, email, phone) | AES-256 (pgcrypto) | TLS 1.3 | Per-tenant DEK |
| Payment tokens | N/A (tokenized) | TLS 1.3 | Third-party |
| JWT signing keys | N/A | N/A | AWS KMS |
| Database backups | AES-256 | TLS 1.3 + SSE | AWS KMS |
| Logs | AES-256 (optional) | TLS 1.3 | N/A |

---

## Cross-Reference

- [Key Rotation](key-rotation.md) — Key rotation procedures
- [Secrets Management](secrets-management.md) — Secret storage
- [Backup & Recovery](backup-recovery.md) — Backup procedures
