# Auth Module

> Identity, authentication, and authorization.

The auth module is the **security foundation** of the platform. It owns user identity, authentication (login/logout/token refresh), and provides authorization context for all other modules.

---

## Purpose

The auth module:
- Manages user accounts and credentials
- Handles authentication (JWT issuance and validation)
- Provides tenant and role context for authorization
- Manages MFA setup and password reset

---

## Aggregates

### User

```python
class User(AggregateRoot):
    id: UUID
    tenant_id: UUID
    email: str
    password_hash: str
    role: UserRole  # ADMIN, OPERATOR, MEMBER, GUARDIAN
    mfa_enabled: bool
    mfa_secret: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def verify_password(self, password: str) -> bool: ...
    def enable_mfa(self, secret: str) -> None: ...
    def disable_mfa(self) -> None: ...
```

### Tenant

```python
class Tenant(AggregateRoot):
    id: UUID
    name: str
    slug: str
    plan: TenantPlan  # STARTER, PROFESSIONAL, ENTERPRISE
    settings: dict
    created_at: datetime
```

---

## Public APIs

### Authentication

| Endpoint | Method | Description |
|---|---|---|
| `/auth/login` | POST | Authenticate with email/password |
| `/auth/logout` | POST | Invalidate refresh token |
| `/auth/refresh` | POST | Refresh access token |
| `/auth/mfa/setup` | POST | Initiate MFA setup |
| `/auth/mfa/verify` | POST | Verify and enable MFA |
| `/auth/password/reset` | POST | Request password reset |
| `/auth/password/reset/confirm` | POST | Confirm password reset |

### User Management

| Endpoint | Method | Description |
|---|---|---|
| `/auth/users` | GET | List users (tenant-scoped) |
| `/auth/users/{id}` | GET | Get user by ID |
| `/auth/users` | POST | Create user (operator+) |
| `/auth/users/{id}` | PATCH | Update user |
| `/auth/users/{id}` | DELETE | Deactivate user |

### Tenant Management

| Endpoint | Method | Description |
|---|---|---|
| `/auth/tenants` | GET | List tenants (admin only) |
| `/auth/tenants/{id}` | GET | Get tenant |
| `/auth/tenants` | POST | Create tenant |
| `/auth/tenants/{id}` | PATCH | Update tenant |

---

## Events

| Event | Produced By | Consumed By |
|---|---|---|
| `UserCreated` | User registration | customer, notifications |
| `UserLoggedIn` | Successful login | analytics |
| `UserLoginFailed` | Failed login attempt | security (audit) |
| `PasswordChanged` | Password update | customer, notifications |
| `MFAEnabled` | MFA enabled | notifications |
| `MFADisabled` | MFA disabled | notifications |
| `UserDeactivated` | Account deactivated | customer, notifications |

---

## Dependencies

**Upstream:** None

**Downstream:**
- All modules consume auth context (tenant_id, user_id, role)

---

## Invariants

1. **Password hashing** — Passwords are never stored in plain text. Use Argon2id.
2. **Token expiry** — Access tokens expire in 15 minutes.
3. **Tenant isolation** — Users can only access their tenant's data.
4. **Role hierarchy** — ADMIN > OPERATOR > MEMBER > GUARDIAN

---

## Open Questions

- Should we support SSO (SAML/OIDC)? — Deferred to v2
- Should we support social login? — Deferred to v2
- How to handle tenant migration? — Future consideration

---

## Related Documents

- [Authentication](../09-security/authentication.md)
- [JWT Best Practices](../09-security/jwt-best-practices.md)
- [Authorization & RBAC](../09-security/authorization-rbac.md)
