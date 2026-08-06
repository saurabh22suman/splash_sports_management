# JWT Best Practices

> This document details our JWT implementation standards: algorithm selection, required claims, key rotation, and revocation patterns.

We use JWTs (JSON Web Tokens) for stateless API authentication. This document specifies our implementation requirements.

---

## Algorithm: RS256 Only

> **Rule** — Never use HS256 (HMAC) with shared secrets in production.

| Algorithm | Use | Reason |
|---|---|---|
| **RS256** (RSA) | Access tokens | Asymmetric — private key signs, public key verifies |
| **ES256** | Future consideration | Smaller tokens, similar security |
| **HS256** | Never in production | Requires shared secret — compromised client = compromised system |

### Key Generation

```bash
# Generate RSA key pair
openssl genrsa -out jwt-private.pem 4096
openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem
```

---

## Required Claims

| Claim | Purpose | Value |
|---|---|---|
| `iss` | Issuer | "splashh-auth" |
| `sub` | Subject | User ID |
| `aud` | Audience | "splashh-api" |
| `exp` | Expiration | Current + 15 minutes |
| `iat` | Issued At | Current timestamp |
| `jti` | JWT ID | Unique token identifier |
| `tenant_id` | Tenant | User's tenant ID |
| `roles` | Permissions | Array of role names |

### Example Payload

```json
{
  "iss": "splashh-auth",
  "sub": "user-123",
  "aud": "splashh-api",
  "exp": 1705324800,
  "iat": 1705323900,
  "jti": "abc123def456",
  "tenant_id": "tenant-456",
  "roles": ["Manager", "Coach"]
}
```

---

## Key Rotation: JWKS

We support key rotation via JWKS (JSON Web Key Set):

```python
# JWKS endpoint
@app.get("/auth/.well-known/jwks")
async def get_jwks():
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "current-key-2024-01",
                "use": "sig",
                "alg": "RS256",
                "n": "...",  # Public modulus
                "e": "AQAB"
            },
            {
                "kty": "RSA",
                "kid": "previous-key-2023-10",
                "use": "sig",
                "alg": "RS256",
                "n": "...",  # Old key for token validation
                "e": "AQAB"
            }
        ]
    }
```

### Token Verification

```python
from jose import jwt, JWTError
import httpx

async def verify_token(token: str) -> dict:
    # Fetch JWKS
    jwks = await httpx.get("https://auth.splashh.com/auth/.well-known/jwks")
    jwks_data = jwks.json()

    # Get key ID from token header
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    # Find matching key
    key = None
    for k in jwks_data["keys"]:
        if k["kid"] == kid:
            key = k
            break

    if not key:
        raise JWTError("Unknown key ID")

    # Verify token
    return jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience="splashh-api",
        issuer="splashh-auth"
    )
```

---

## Token Revocation

Tokens are short-lived (15 min), but we support revocation:

```python
# Redis: store revoked token IDs
async def revoke_token(jti: str):
    await redis.setex(f"revoked:{jti}", 900, "true")  # Until expiry

async def is_token_revoked(jti: str) -> bool:
    return await redis.exists(f"revoked:{jti}")
```

---

## Cross-Reference

- [Authentication](authentication.md) — Auth architecture
- [Refresh Token Rotation](refresh-token-rotation.md) — Token lifecycle
- [Key Rotation](key-rotation.md) — Key management
