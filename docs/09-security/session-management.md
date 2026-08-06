# Session Management

> This document compares token-based and session-based approaches, and explains our current architecture decisions.

We use stateless JWT for API authentication and opaque refresh tokens for session maintenance. This document explains the trade-offs.

---

## Token vs. Session Comparison

| Aspect | Stateless JWT | Server-side Session |
|---|---|---|
| Storage | Client (browser) | Server (database/Redis) |
| Scalability | High (stateless) | Lower (requires shared state) |
| Revocation | Complex (token blacklist) | Simple (delete session) |
| Token rotation | Required for security | Automatic |
| Size | Larger (claims in token) | Smaller (session ID) |

---

## Our Architecture: Tokens

We chose tokens for v1:

### Why Tokens

- **Scalability**: No session store bottleneck
- **Simplicity**: No session synchronization
- **Mobile-friendly**: Works across platforms
- **Microservices-ready**: Each service verifies token

### Trade-offs We Accept

- **Revocation complexity**: Use token rotation and short expiry
- **No server-side logout**: Token valid until expiry (or revocation list)

---

## Future: Server-Side Sessions for Admin

For the admin console (future), we may use server-side sessions:

```python
# Admin console session (future)
class AdminSession:
    """Server-side session for admin console."""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
```

This allows:
- Instant logout
- Session listing for users
- Concurrent session limits
- Force logout by admin

---

## Cross-Reference

- [Authentication](authentication.md) — Auth flow
- [JWT Best Practices](jwt-best-practices.md) — JWT usage
- [Refresh Token Rotation](refresh-token-rotation.md) — Token lifecycle
