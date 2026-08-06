# Multi-Factor Authentication (MFA)

> This document details our MFA requirements, implementation, and supported methods.

MFA is required for privileged accounts and recommended for all users. We support TOTP as the primary method, with WebAuthn as an upgrade path.

---

## MFA Requirements

| Role | MFA Required |
|---|---|
| TenantAdmin | Yes (mandatory) |
| Manager | Recommended |
| Coach | Recommended |
| Staff | Optional |
| Member | Optional |

---

## Supported Methods

| Method | Status | Description |
|---|---|---|
| TOTP (RFC 6238) | Primary | Authenticator apps (Google, Authy) |
| WebAuthn | Recommended | Passkeys, security keys |
| Backup codes | Backup | 10 one-time codes |

---

## TOTP Implementation

```python
import pyotp
import qrcode
import io
import base64

def generate_totp_secret() -> str:
    """Generate TOTP secret for user."""
    return pyotp.random_base32()

def get_totp_uri(secret: str, email: str) -> str:
    """Generate provisioning URI for QR code."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name="Splashh")

def verify_totp(secret: str, code: str) -> bool:
    """Verify TOTP code."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # 1 step drift
```

---

## WebAuthn (Passkeys)

```python
# WebAuthn registration
async def register_webauthn(user_id: str):
    """Initiate WebAuthn registration."""
    challenge = secrets.token_bytes(32)

    options = {
        "challenge": base64.b64encode(challenge).decode(),
        "rp": {"name": "Splashh", "id": "splashh.com"},
        "user": {
            "id": user_id.encode(),
            "name": user_id,
            "displayName": user_id
        },
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7}
        ]
    }

    return options
```

---

## Backup Codes

```python
def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate one-time backup codes."""
    codes = []
    for _ in range(count):
        code = f"{secrets.randbelow(10000):04d}-{secrets.randbelow(10000):04d}"
        codes.append(code)
    return codes
```

---

## Cross-Reference

- [Authentication](authentication.md) — Auth flow
- [Password Policy](password-policy.md) — Password requirements
