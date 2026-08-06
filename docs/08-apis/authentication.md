# Authentication

> This document covers JWT-based authentication, token management, and security best practices.

## Overview

We use **Bearer JWT** tokens for authentication. Access tokens are short-lived (15 minutes), refresh tokens are long-lived (30 days) with rotation.

## Token Flow

```mermaid
sequenceDiagram
    Client->>Server: POST /v1/auth/login
    Server->>Server: Verify credentials
    Server->>Client: {access_token, refresh_token}
    Client->>Server: GET /v1/bookings (Bearer access_token)
    Server->>Client: 200 OK
    Note over Client,Server: Access token expires
    Client->>Server: POST /v1/auth/refresh (refresh_token)
    Server->>Client: {new_access_token, new_refresh_token}
```

## Token Types

| Token | Lifetime | Use |
|-------|----------|-----|
| Access Token | 15 minutes | API requests |
| Refresh Token | 30 days | Get new access token |

## Implementation

### Token Generation

```python
# src/auth/service.py
import jwt
from datetime import datetime, timedelta
from uuid import UUID


class TokenService:
    def __init__(self, secret: str, jwt_algorithm: str = "HS256"):
        self._secret = secret
        self._algorithm = jwt_algorithm

    def create_access_token(
        self,
        user_id: UUID,
        tenant_id: UUID,
        roles: list[str],
    ) -> str:
        """Create short-lived access token."""
        now = datetime.utcnow()
        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "roles": roles,
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "type": "access",
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: UUID) -> str:
        """Create long-lived refresh token."""
        now = datetime.utcnow()
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(days=30),
            "type": "refresh",
            "jti": str(uuid4()),  # Unique identifier for rotation
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)
```

### Token Verification

```python
    def verify_token(self, token: str) -> dict:
        """Verify and decode token."""
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )

            # Verify token type
            if payload.get("type") != "access":
                raise InvalidTokenError("Invalid token type")

            return payload

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError:
            raise InvalidTokenError()
```

### Login Endpoint

```python
# src/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    token_service: TokenService = Depends(get_token_service),
):
    # Verify credentials
    user = await auth_service.verify_credentials(data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Create tokens
    access_token = token_service.create_access_token(
        user.id,
        user.tenant_id,
        user.roles,
    )
    refresh_token = token_service.create_refresh_token(user.id)

    # Store refresh token
    await auth_service.store_refresh_token(user.id, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
```

### Refresh Endpoint

```python
@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
    token_service: TokenService = Depends(get_token_service),
):
    # Verify refresh token
    payload = token_service.verify_token(data.refresh_token)
    user_id = payload["sub"]

    # Check if token is revoked
    is_valid = await auth_service.is_refresh_token_valid(user_id, data.refresh_token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Rotate: generate new tokens
    user = await auth_service.get_user(user_id)

    new_access = token_service.create_access_token(user.id, user.tenant_id, user.roles)
    new_refresh = token_service.create_refresh_token(user.id)

    # Invalidate old refresh token, store new (rotation)
    await auth_service.rotate_refresh_token(user_id, data.refresh_token, new_refresh)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)
```

## Logout

```python
@router.post("/auth/logout")
async def logout(
    token: str = Depends(get_current_token),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Logout - revoke refresh token."""
    payload = jwt.decode(token, ...)
    user_id = payload["sub"]

    # Revoke all refresh tokens for this user (or specific one)
    await auth_service.revoke_refresh_tokens(user_id)

    return {"message": "Logged out"}
```

## Protected Endpoints

```python
# Require authentication
@router.get("/bookings")
async def list_bookings(
    current_user: User = Depends(get_current_user),
):
    return [...]

# Require specific role
@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
):
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    ...
```

## Token in Requests

```python
# Client includes token in Authorization header
GET /v1/bookings HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Security Considerations

1. **Short access token** — Limits damage from token leakage
2. **Refresh token rotation** — Invalidates stolen tokens
3. **HTTPS only** — Tokens in transit are encrypted
4. **No sensitive data in tokens** — Only user ID, roles

## Related Documents

- [Security - JWT Best Practices](../09-security/jwt-best-practices.md)
- [Security - Refresh Token Rotation](../09-security/refresh-token-rotation.md)
