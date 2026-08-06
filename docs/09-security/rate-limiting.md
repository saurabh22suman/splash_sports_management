# Rate Limiting

> This document covers our rate limiting strategy, including tiered limits, token bucket implementation, brute-force protection, and CAPTCHA integration.

Rate limiting protects the platform from abuse: credential stuffing, denial of service, and resource exhaustion. We implement rate limiting at multiple layers (API gateway, application, Redis) with tiered limits based on identity and endpoint sensitivity.

---

## Rate Limit Tiers

| Tier | Scope | Limit | Window |
|---|---|---|---|
| **IP Global** | Per IP address | 100 requests | 1 minute |
| **IP Auth** | Auth endpoints per IP | 10 requests | 1 minute |
| **User** | Authenticated user | 1000 requests | 1 minute |
| **Tenant** | Per tenant | 5000 requests | 1 minute |
| **Endpoint Sensitive** | Login, password reset | 5 requests | 15 minutes |

---

## Token Bucket Algorithm

We use the **token bucket** algorithm via Redis:

```python
import asyncio
from dataclasses import dataclass
from typing import Optional
import redis.asyncio as redis

@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_at: int

class RateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> RateLimitResult:
        """Check and update rate limit for a key."""
        now = asyncio.get_event_loop().time()
        window_start = int(now // window_seconds) * window_seconds
        bucket_key = f"ratelimit:{key}:{window_start}"

        # Increment counter
        current = await self.redis.incr(bucket_key)

        # Set expiry if first request
        if current == 1:
            await self.redis.expire(bucket_key, window_seconds)

        # Calculate remaining
        remaining = max(0, limit - current)
        reset_at = window_start + window_seconds

        return RateLimitResult(
            allowed=current <= limit,
            remaining=remaining,
            reset_at=reset_at
        )
```

---

## Rate Limiting Middleware

```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with tiered limits."""

    # Limits by endpoint category
    LIMITS = {
        "default": {"requests": 100, "window": 60},
        "auth": {"requests": 10, "window": 60},
        "sensitive": {"requests": 5, "window": 900},  # 15 min
        "write": {"requests": 100, "window": 60},
    }

    def __init__(self, app, limiter: RateLimiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        # Determine limit tier
        tier = self._get_tier(request)

        # Get identifier (IP, user, or tenant)
        identifier = self._get_identifier(request)

        # Check rate limit
        limit_config = self.LIMITS[tier]
        result = await self.limiter.check_rate_limit(
            f"{tier}:{identifier}",
            limit_config["requests"],
            limit_config["window"]
        )

        if not result.allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": result.reset_at
                },
                headers={
                    "X-RateLimit-Limit": str(limit_config["requests"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result.reset_at),
                    "Retry-After": str(limit_config["window"])
                }
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit_config["requests"])
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_at)

        return response

    def _get_tier(self, request: Request) -> str:
        """Determine rate limit tier based on endpoint."""
        path = request.url.path

        if path.startswith("/api/v1/auth/login"):
            return "sensitive"
        if path in ["POST", "PUT", "DELETE"]:
            return "write"
        if path.startswith("/api/v1/auth"):
            return "auth"
        return "default"

    def _get_identifier(self, request: Request) -> str:
        """Get identifier for rate limiting."""
        # Prefer user ID if authenticated
        if hasattr(request.state, "user_id"):
            return request.state.user_id

        # Fall back to IP
        client_ip = request.client.host if request.client else "unknown"
        return client_ip
```

---

## Brute Force Protection

We implement specific brute-force protection for authentication endpoints:

```python
class BruteForceProtection:
    """Detect and block brute force attacks."""

    MAX_ATTEMPTS = 10
    LOCKOUT_DURATION = 900  # 15 minutes

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def record_failed_attempt(self, identifier: str):
        """Record a failed authentication attempt."""
        key = f"bruteforce:{identifier}"
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.LOCKOUT_DURATION)
        await pipe.execute()

    async def record_successful_login(self, identifier: str):
        """Clear failed attempts after successful login."""
        await self.redis.delete(f"bruteforce:{identifier}")

    async def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is blocked."""
        attempts = await self.redis.get(f"bruteforce:{identifier}")
        if attempts and int(attempts) >= self.MAX_ATTEMPTS:
            return True
        return False
```

---

## CAPTCHA Integration

After N failed attempts, we require CAPTCHA:

```python
async def require_captcha(
    request: Request,
    identifier: str,
    redis_client: redis.Redis
) -> bool:
    """Determine if CAPTCHA is required."""
    key = f"captcha_required:{identifier}"
    required = await redis_client.get(key)

    if required and int(required) >= 3:  # After 3 failures
        return True
    return False
```

> **Rule** — Require CAPTCHA after 3 failed authentication attempts on sensitive endpoints.

---

## HTTP 429 Response Format

```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded for this endpoint",
  "retry_after": 60,
  "limit": 100,
  "remaining": 0,
  "reset_at": 1705324800
}
```

---

## Testing Rate Limiting

```python
import pytest

async def test_rate_limit_exceeded():
    """Verify rate limiting blocks after limit."""
    for _ in range(101):
        response = await client.get("/api/v1/bookings")

    # 101st request should be blocked
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["error"]

async def test_brute_force_blocked():
    """Verify brute force protection after 10 failures."""
    for _ in range(10):
        await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrong"
        })

    # 11th attempt should be blocked
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "correct"
    })

    assert response.status_code == 429
    assert "Too Many Requests" in response.json()["error"]
```

---

## Cross-Reference

- [Authentication](authentication.md) — Login protection
- [API Security](api-security.md) — Endpoint-level authorization
- [Incident Response](incident-response.md) — Abuse response
