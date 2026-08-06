# Refresh Token Rotation

> This document details our refresh token rotation strategy, including token families, reuse detection, and revocation patterns.

Refresh tokens are long-lived credentials that maintain sessions. Rotation (generating a new token on each use) detects token theft by invalidating stolen tokens when the legitimate user refreshes.

---

## Opaque Token Design

Refresh tokens are **opaque** (not JWTs). They are stored server-side:

```python
import secrets
import hashlib
from datetime import timedelta

class RefreshTokenManager:
    """Manage refresh token rotation and storage."""

    def __init__(self, redis_client):
        self.redis = redis_client

    def create_token(self, user_id: str, tenant_id: str) -> tuple[str, str]:
        """Create new refresh token pair: (raw, hashed)."""
        raw = secrets.token_urlsafe(32)
        hashed = hashlib.sha256(raw.encode()).hexdigest()

        family = secrets.token_hex(16)

        # Store hashed token
        key = f"refresh:{hashed}"
        self.redis.setex(
            key,
            timedelta(days=30),
            f"{user_id}:{tenant_id}:{family}"
        )

        # Track token family
        family_key = f"family:{family}"
        self.redis.sadd(family_key, hashed)
        self.redis.expire(family_key, timedelta(days=30))

        return raw, hashed
```

---

## Rotation with Reuse Detection

```python
async def rotate_token(
    self,
    raw_token: str,
    user_id: str
) -> tuple[str, str] | None:
    """Rotate token on refresh. Detect theft via reuse."""
    hashed = hashlib.sha256(raw_token.encode()).hexdigest()

    # Get stored token data
    key = f"refresh:{hashed}"
    stored = await self.redis.get(key)

    if not stored:
        return None  # Token already used

    stored_user_id, tenant_id, family = stored.split(":")

    if stored_user_id != user_id:
        # Token stolen — revoke entire family
        await self._revoke_family(family)
        # TODO: Alert security team
        return None

    # Valid token — rotate
    # 1. Delete old token
    await self.redis.delete(key)
    await self.redis.srem(f"family:{family}", hashed)

    # 2. Create new token
    new_raw, new_hashed = self.create_token(user_id, tenant_id)

    return new_raw
```

---

## Family Revocation

If reuse is detected, revoke all tokens in the family:

```python
async def _revoke_family(self, family: str):
    """Revoke all tokens in a family (theft detected)."""
    family_key = f"family:{family}"

    # Get all tokens in family
    tokens = await self.redis.smembers(family_key)

    # Delete all tokens
    for token_hash in tokens:
        await self.redis.delete(f"refresh:{token_hash}")

    # Delete family tracking
    await self.redis.delete(family_key)

    # Log security event
    await self._log_security_event(
        event_type="token_family_revoked",
        family=family,
        reason="reuse_detected"
    )
```

---

## Logout Revocation

```python
async def logout(self, user_id: str):
    """Revoke all refresh tokens for user."""
    # Find all active tokens for user (requires additional index)
    pattern = f"user_tokens:{user_id}:*"
    keys = await self.redis.keys(pattern)

    for key in keys:
        family = await self.redis.get(key)
        if family:
            await self._revoke_family(family)
        await self.redis.delete(key)
```

---

## Cross-Reference

- [Authentication](authentication.md) — Auth architecture
- [JWT Best Practices](jwt-best-practices.md) — JWT usage
- [Session Management](session-management.md) — Session patterns
