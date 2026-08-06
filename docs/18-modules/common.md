# Common Module

> Shared building blocks used by all modules.

The common module contains utilities, base classes, and patterns used by 3 or more other modules. It is NOT a dumping ground for any shared code — only genuinely common infrastructure.

---

## Purpose

The common module provides:
- Base classes for aggregates, repositories, services
- Pydantic mixins for shared validation
- Error types used across modules
- Tenant context management
- Audit logging utilities

---

## Contents

### Base Classes

```python
# Aggregate base
class AggregateRoot:
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    def validate(self) -> None: ...

# Repository base
class Repository(Generic[T]):
    async def get_by_id(self, id: UUID) -> T | None: ...
    async def save(self, entity: T) -> T: ...
    async def delete(self, id: UUID) -> None: ...

# Service base
class Service:
    def __init__(self, db: AsyncSession): ...
```

### Pydantic Mixins

```python
# Timestamp mixin
class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime

# Tenant mixin
class TenantMixin(BaseModel):
    tenant_id: UUID
```

### Error Types

```python
class DomainError(Exception):
    code: str
    message: str

class NotFoundError(DomainError): ...
class ValidationError(DomainError): ...
class ConflictError(DomainError): ...
class UnauthorizedError(DomainError): ...
class ForbiddenError(DomainError): ...
```

### Tenant Context

```python
class TenantContext:
    tenant_id: UUID
    user_id: UUID
    role: str

    @asynccontextmanager
    async def set(cls, tenant_id: UUID): ...

    def get() -> TenantContext: ...
```

### Audit Logger

```python
class AuditLogger:
    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID,
        changes: dict | None = None,
    ): ...
```

---

## Usage Rules

> **Rule** — Only add to common if used by 3+ modules.

> **Anti-pattern** — Adding module-specific utilities to common because "it's convenient."

### Examples of What Goes in Common

- Base `AggregateRoot` class
- Standard error types
- Tenant context
- Audit logging

### Examples of What Does NOT Go in Common

- Membership-specific validation (goes in membership module)
- Booking-specific exceptions (goes in booking module)
- Stripe client (goes in payments module)

---

## Related Documents

- [Backend Structure](../04-backend/folder-structure.md)
- [Dependency Injection](../04-backend/dependency-injection.md)
