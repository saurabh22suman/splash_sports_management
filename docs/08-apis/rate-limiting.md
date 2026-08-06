# Rate Limiting

> This document covers rate limiting strategies, Redis-based implementation, and response headers.

## Overview

Rate limiting protects the API from abuse and ensures fair usage. We use a **token bucket** algorithm implemented with Redis.

## Rate Limits

| Tier | Requests | Window | Scope |
|------|----------|--------|-------|
| Anonymous | 60 | 1 minute | IP |
| Authenticated | 1000 | 1 minute | User |
| Premium | 5000 | 1 minute | User |
| Admin | 10000 | 1 minute | User |

## Implementation

### Redis Token Bucket

```python
# src/common/rate_limit.py
import redis.asyncio as redis
from datetime import datetime


class RateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(self, redis: redis.Redis):
        self._redis = redis

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit.
        Returns (allowed, info)
        """
        now = datetime.utcnow()
        window_key = f"ratelimit:{key}:{int(now.timestamp() / window_seconds)}"

        # Increment counter
        current = await self._redis.incr(window_key)

        # Set expiry on first request
        if current == 1:
            await self._redis.expire(window_key, window_seconds)

        # Get remaining
        remaining = max(0, limit - current)
        reset_time = (int(now.timestamp() / window_seconds) + 1) * window_seconds

        info = {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_time,
        }

        return current <= limit, info
```

### Middleware

```python
# src/common/middleware.py
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse


class RateLimitMiddleware:
    """Rate limiting middleware."""

    def __init__(self, app, rate_limiter: RateLimiter):
        self._app = app
        self._limiter = rate_limiter

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        # Extract rate limit key
        request = Request(scope, receive)
        key = self._get_rate_limit_key(request)

        # Get limit based on tier
        limit = self._get_rate_limit(request)
        window = 60  # 1 minute

        allowed, info = await self._limiter.check_rate_limit(key, limit, window)

        if not allowed:
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "type": "https://api.splashh.com/errors/rate_limit_exceeded",
                    "title": "RateLimitError",
                    "status": 429,
                    "detail": f"Rate limit exceeded. Limit: {limit} requests per minute.",
                    "retry_after": info["reset"] - int(datetime.utcnow().timestamp()),
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["reset"] - int(datetime.utcnow().timestamp())),
                },
            )
            await response(scope, receive, send)
            return

        # Add rate limit headers
        response = await self._app(scope, receive, send)

        # Add headers to response (requires custom response)
        # ...

    def _get_rate_limit_key(self, request: Request) -> str:
        """Get rate limit key based on authentication."""
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        return f"ip:{request.client.host}"

    def _get_rate_limit(self, request: Request) -> int:
        """Get rate limit based on tier."""
        # Default limits
        limits = {
            "admin": 10000,
            "premium": 5000,
            "authenticated": 1000,
            "anonymous": 60,
        }

        tier = getattr(request.state, "user_tier", "anonymous")
        return limits.get(tier, limits["anonymous"])
```

## Response Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Rate Limit Exceeded Response

```json
{
  "type": "https://api.splashh.com/errors/rate_limit_exceeded",
  "title": "RateLimitError",
  "status": 429,
  "detail": "Rate limit exceeded. Limit: 1000 requests per minute.",
  "retry_after": 45
}
```

## Client Handling

```javascript
// JavaScript - handle rate limiting
async function apiRequest(url, options = {}) {
  const response = await fetch(url, options);

  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After') || 60;
    console.log(`Rate limited. Retrying in ${retryAfter} seconds...`);

    await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
    return apiRequest(url, options);  // Retry
  }

  return response;
}
```

## Per-Endpoint Limits

```python
# Stricter limits for sensitive endpoints
@router.post("/payments")
async def create_payment(
    rate_limit: int = Depends(lambda: 60),  # 60/min for payments
    ...
):
    ...
```

## Monitoring

```yaml
# prometheus/metrics
- name: rate_limit_exceeded_total
  help: Total number of rate limited requests
  type: counter
  labels:
    endpoint: true
    user_tier: true
```

## Related Documents

- [Status Codes](status-codes.md)
- [Error Responses](error-responses.md)
- [Security - Rate Limiting](../09-security/rate-limiting.md)
