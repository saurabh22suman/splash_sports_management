# API Security

> This document covers API-specific security risks: BOLA, BFLA, mass assignment, over-fetching, and authorization patterns.

APIs are the primary attack surface for modern applications. We implement specific controls to prevent common API security vulnerabilities.

---

## Broken Object Level Authorization (BOLA)

BOLA occurs when users can access resources they don't own:

### Vulnerable Code

```python
# VULNERABLE - No ownership check
@app.get("/api/v1/bookings/{booking_id}")
async def get_booking(booking_id: str):
    return await booking_repo.get(booking_id)
```

### Secure Code

```python
# SECURE - Ownership check
@app.get("/api/v1/bookings/{booking_id}")
async def get_booking(
    booking_id: str,
    context: AuthorizationContext
):
    booking = await booking_repo.get(booking_id, context.tenant_id)

    if not booking:
        raise HTTPException(status_code=404)

    # Ownership check
    if booking.user_id != context.user_id:
        raise HTTPException(status_code=403)

    return booking
```

---

## Broken Function Level Authorization (BFLA)

BFLA occurs when users can access functions they shouldn't:

```python
# SECURE - Authorization decorator
@app.delete("/api/v1/users/{user_id}")
@check_permission("user:delete")
async def delete_user(user_id: str, context: AuthorizationContext):
    # Check not deleting self
    if user_id == context.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete self")

    await user_repo.delete(user_id, context.tenant_id)
    return {"status": "deleted"}
```

---

## Mass Assignment

Mass assignment occurs when attackers can set protected fields:

### Vulnerable Code

```python
# VULNERABLE - Accepts all fields
class UserUpdate(BaseModel):
    name: str
    role: str  # Should not be settable
    is_admin: bool  # Should not be settable
```

### Secure Code

```python
# SECURE - Only allowed fields
class UserUpdate(BaseModel):
    name: str = None
    phone: str = None
    # role and is_admin NOT included
    # Cannot be mass-assigned
```

---

## Schema-Driven Output

We use Pydantic to control exactly what is returned:

```python
class UserResponse(BaseModel):
    """Only return safe fields."""
    id: str
    name: str
    email: str
    # Never return: password_hash, role, internal_id

class AdminUserResponse(UserResponse):
    """Admin version with additional fields."""
    role: str
    last_login: datetime
    # Still not returning: password_hash
```

---

## Rate Limiting per Endpoint

```python
# Stricter limits for sensitive endpoints
ENDPOINT_LIMITS = {
    "/api/v1/auth/login": {"requests": 5, "window": 900},
    "/api/v1/auth/refresh": {"requests": 100, "window": 60},
    "/api/v1/payments/refund": {"requests": 10, "window": 3600},
}
```

---

## Cross-Reference

- [Authorization & RBAC](authorization-rbac.md) — Permission model
- [Tenant Isolation](tenant-isolation.md) — Tenant data access
- [Input Validation](input-validation.md) — Schema validation
