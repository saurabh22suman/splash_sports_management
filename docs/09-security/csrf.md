# Cross-Site Request Forgery (CSRF) Prevention

> This document details ourCSRF prevention strategy, including SameSite cookies, Bearer token authentication, and double-submit token patterns for cookie-based endpoints.

Cross-Site Request Forgery (CSRF) tricks users into performing unintended actions on a site where they are authenticated. Our architecture minimizes CSRF risk by using Bearer token authentication (stateless JWTs) rather than cookie-based sessions, with SameSite cookies as a defense-in-depth measure.

---

## Why Bearer Tokens Minimize CSRF

Our authentication uses **Bearer tokens** in the `Authorization` header, not cookies:

```javascript
// Correct - Bearer token (not sent automatically by browsers)
fetch('/api/resource', {
  headers: {
    'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIs...'
  }
});

// Incorrect - cookie-based (vulnerable to CSRF)
fetch('/api/resource');  // Browser automatically sends cookies
```

> **Why** — Browsers do not automatically send Bearer tokens in cross-site requests. This eliminates the primary attack vector for CSRF. The `Authorization` header cannot be set by malicious websites due to the Same-Origin Policy.

---

## SameSite Cookies (Defense in Depth)

For endpoints that must use cookies (e.g., admin console sessions), we use `SameSite=Lax`:

```python
response.set_cookie(
    key="session",
    value=session_token,
    httponly=True,           # Cannot be read by JavaScript
    secure=True,             # HTTPS only
    samesite="lax",          # CSRF protection
    max_age=3600,            # 1 hour
    domain=None              # Current domain only
)
```

| SameSite Value | Behavior | Security |
|---|---|---|
| `Strict` | Never sent in cross-site requests | Most secure, poor UX |
| `Lax` | Sent with top-level GET only | Balanced |
| `None` | Sent in all requests | Requires Secure flag |

> **Rule** — Use `SameSite=Lax` for all cookie-based authentication. Never use `SameSite=None` without explicit security review.

---

## Double-Submit Token Pattern

For endpoints that use cookies (if we add them in the future), we implement the double-submit pattern:

### Token Generation

```python
import secrets

def generate_csrf_token() -> tuple[str, str]:
    """Generate a CSRF token pair: secret and form field value."""
    secret = secrets.token_hex(32)
    # The value sent in forms is: secret + fingerprint
    return secret, f"{secret}:{get_fingerprint()}"

def get_fingerprint() -> str:
    """Get a simple browser fingerprint."""
    # In production, use a proper fingerprinting library
    # This is a simplified example
    return "default"
```

### Token Validation

```python
async def validate_csrf_token(request: Request) -> bool:
    """Validate CSRF token from header matches cookie."""
    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")

    if not cookie_token or not header_token:
        return False

    # Verify using constant-time comparison
    return secrets.compare_digest(cookie_token, header_token)
```

### Middleware Enforcement

```python
from fastapi import Request, HTTPException

class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    # Routes that require CSRF protection
    PROTECTED_METHODS = ["POST", "PUT", "DELETE", "PATCH"]
    # Routes that don't need CSRF (API uses Bearer)
    EXEMPT_ROUTES = ["/api/"]

    async def dispatch(self, request: Request, call_next):
        # Skip for safe methods or API routes
        if (request.method in self.PROTECTED_METHODS and
            not any(request.url.path.startswith(p) for p in self.EXEMPT_ROUTES)):
            if not await validate_csrf_token(request):
                raise HTTPException(
                    status_code=403,
                    detail="CSRF token missing or invalid"
                )

        return await call_next(request)
```

---

## Origin/Referer Validation

We validate the Origin or Referer header as an additional check:

```python
ALLOWED_ORIGINS = [
    "https://splashh.com",
    "https://app.splashh.com",
    "https://admin.splashh.com"
]

async def validate_origin(request: Request) -> bool:
    """Validate request origin against allow-list."""
    origin = request.headers.get("Origin") or request.headers.get("Referer")

    if not origin:
        return False  # Reject requests without origin

    # Parse origin
    from urllib.parse import urlparse
    parsed = urlparse(origin)

    # Check against allow-list
    allowed = any(
        parsed.netloc == urlparse(allowed).netloc
        for allowed in ALLOWED_ORIGINS
    )

    return allowed
```

---

## CSRF in Our Architecture

Given our Bearer token architecture, CSRF risk is minimal:

| Authentication Method | CSRF Risk | Mitigation |
|---|---|---|
| Bearer JWT | None | Tokens not sent automatically |
| Opaque Refresh Token | None | Not in cookies |
| Future Admin Cookies | Medium | SameSite=Lax + double-submit |

```mermaid
flowchart TD
    A[User submits form] --> B{Bearer Token?}
    B -->|Yes| C[Browser does NOT auto-send]
    B -->|No (cookies)| D[SameSite=Lax]
    D --> E{Top-level GET?}
    E -->|Yes| F[Cookie sent]
    E -->|No| G[Cookie blocked]
    F --> H[Additional: CSRF token check]
```

---

## Testing CSRF Protection

### Test 1: Cross-Origin Request Blocked

```python
async def test_csrf_blocked_from_other_origin():
    """Verify CSRF tokens are required for cross-origin requests."""
    response = await client.post(
        "/api/admin/settings",
        json={"key": "value"},
        headers={
            "Origin": "https://malicious-site.com",
            "Authorization": "Bearer valid-token"
        }
    )
    # Should be blocked by CSRF or CORS
    assert response.status_code in [403, 403]
```

### Test 2: Same-Origin Request Allowed

```python
async def test_csrf_allowed_same_origin():
    """Verify requests from same origin work with valid token."""
    # Set CSRF cookie
    client.cookies.set("csrf_token", "valid-token")
    response = await client.post(
        "/api/admin/settings",
        json={"key": "value"},
        headers={
            "Origin": "https://app.splashh.com",
            "X-CSRF-Token": "valid-token",
            "Authorization": "Bearer valid-token"
        }
    )
    assert response.status_code == 200
```

---

## Cross-Reference

- [Authentication](authentication.md) — JWT and refresh token architecture
- [JWT Best Practices](jwt-best-practices.md) — Token security
- [CORS](cors.md) — Cross-Origin Resource Sharing
