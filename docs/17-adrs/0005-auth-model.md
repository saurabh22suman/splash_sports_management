# ADR-0005: JWT + Refresh Token Authentication

> How users authenticate.

## Status
Accepted

## Context
Our API is stateless and serves multiple tenants. We need:
- Secure authentication (can't leak data)
- Multi-tenant isolation (tenant in token)
- Long sessions (users stay logged in)
- Revocation capability (logout, security events)

## Decision
We will use:
- **JWT access tokens** — Short-lived (15 min), stateless
- **Opaque refresh tokens** — Long-lived (30 days), stored in DB
- **Refresh token rotation** — New token on each use, detect reuse
- **Token family** — Detect stolen tokens via reuse detection

## Consequences

### Positive
- **Stateless API** — No session store needed
- **Security** — Short-lived access tokens limit exposure
- **Revocation** — Refresh token rotation enables revocation
- **Multi-tenant** — Tenant_id in JWT claims

### Negative
- **Complexity** — Token refresh flow is more complex
- **Storage** — Refresh tokens in DB
- **Revocation delay** — Up to access token expiry (15 min)

### Neutral
- JWT size increases with claims
- Refresh token rotation adds DB writes

## Alternatives Considered

### Alternative 1: Server-side Sessions
Rejected because:
- Requires session store (Redis)
- Not stateless
- Harder to scale
- More state to manage

### Alternative 2: JWT with Long Expiry
Rejected because:
- No revocation until expiry
- Security risk for lost tokens
- Can't force logout

## Implementation

```python
# Token generation
def create_access_token(user: User) -> str:
    return jwt.encode(
        {
            "sub": user.id,
            "tenant_id": user.tenant_id,
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(minutes=15),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

# Refresh token rotation
async def refresh(refresh_token: str) -> TokenPair:
    stored = await repo.get_refresh_token(refresh_token)

    if stored.used:
        # Token reuse = theft - revoke entire family
        await repo.revoke_token_family(stored.user_id)
        raise TokenTheftDetectedError()

    # Generate new tokens
    new_access = create_access_token(stored.user)
    new_refresh = create_refresh_token(stored.user)

    # Mark old as used, store new
    await repo.mark_used(refresh_token)
    await repo.store_refresh_token(new_refresh, stored.user_id)

    return TokenPair(access=new_access, refresh=new_refresh)
```

## References
- [Authentication](../09-security/authentication.md)
- [JWT Best Practices](../09-security/jwt-best-practices.md)
- [Refresh Token Rotation](../09-security/refresh-token-rotation.md)
