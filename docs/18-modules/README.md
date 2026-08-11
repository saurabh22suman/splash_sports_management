# Modules Overview

> Module map, dependency rules, and how to add a new module.

This document defines the module structure of the Splashh backend. Each module is a bounded context with clear ownership, public APIs, and boundaries.

---

## Module Map

```mermaid
flowchart TB
    subgraph Core
        A[auth]
    end

    subgraph Customer
        B[customer]
    end

    subgraph Business
        C[membership]
        D[facility]
        E[booking]
        F[payments]
    end

    subgraph Support
        G[notifications]
        H[analytics]
    end

    I[common]

    A --> B
    B --> C
    B --> D
    C --> E
    D --> E
    C --> F
    E --> F
    A -.->|depends| G
    B -.->|depends| G
    C -.->|depends| G
    D -.->|depends| G
    E -.->|depends| G
    F -.->|depends| G
    B -.->|depends| H
    C -.->|depends| H
    E -.->|depends| H
    F -.->|depends| H

    I --> A
    I --> B
    I --> C
    I --> D
    I --> E
    I --> F
    I --> G
    I --> H
```

---

## Module List

| Module | Purpose | Owner | Status |
|---|---|---|---|
| [auth](./auth.md) | Identity, authentication, sessions | Security | ✅ Shipped |
| [customer](./customer.md) | Member profiles, guardians, waivers | Customer Team | ✅ Shipped |
| [membership](./membership.md) | Plans, subscriptions, renewals | Billing Team | ⏳ Not yet implemented |
| [facility](./facility.md) | Courts, pools, resources, availability | Operations Team | ✅ Shipped |
| [booking](./booking.md) | Reservations, slots, check-in | Operations Team | ✅ Shipped (admin view in progress) |
| [payments](./payments.md) | Invoices, payments, refunds | Billing Team | ✅ Shipped (Razorpay) |
| [notifications](./notifications.md) | Email, SMS, push notifications | Platform Team | ⏳ Not yet implemented |
| [analytics](./analytics.md) | Reports, dashboards, exports | Product Team | ⏳ Not yet implemented |
| [common](./common.md) | Shared utilities, base classes | All | ✅ Shipped |

---

## Dependency Rules

> **Rule** — Dependencies must point downward. No module may depend on a module "above" it.

```
Allowed:    auth -> common
Allowed:    customer -> auth
Allowed:    customer -> common
Forbidden:  common -> auth
Forbidden:  auth -> customer
```

### Dependency Direction

| From | To (Allowed) |
|---|---|
| auth | common |
| customer | auth, common |
| membership | customer, common |
| facility | common |
| booking | customer, facility, common |
| payments | booking, membership, common |
| notifications | (all modules) |
| analytics | (all modules) |

---

## Module Structure

Each backend module is organized by **DDD layer**, not by file role. The
layering enforces boundary discipline: the `domain/` layer has no
SQLAlchemy, Redis, or FastAPI imports, which keeps the core business
logic testable in isolation and keeps multi-tenant RLS concerns in
`infrastructure/`.

```
module_name/
├── application/             # Use cases / orchestration (depends on domain + infrastructure)
│   ├── service.py           # Public service class (e.g. PaymentService, BookingService)
│   ├── events.py            # Domain event publishers
│   └── providers.py         # External integrations (e.g. Razorpay, email)
├── domain/                  # Pure business logic, no I/O
│   ├── entities.py          # Aggregates and entities (dataclasses)
│   └── value_objects.py     # Money, IDs, status enums
├── infrastructure/          # Persistence and side-effecting adapters
│   ├── models.py            # SQLAlchemy ORM models
│   ├── repositories.py      # Data access
│   └── idempotency.py       # Module-specific persistence (only when needed)
└── interfaces/              # Transport adapters
    ├── __init__.py          # Public API exports (router, deps)
    └── http/                # FastAPI adapter
        ├── router.py        # Route handlers
        ├── schemas.py       # Pydantic request/response models
        └── deps.py          # FastAPI dependency-injection wiring
```

`common/` follows the same shape but contributes shared base classes
(`AggregateRoot`, `BaseRepository`) used by 3+ modules.

**Do not:**
- Add SQLAlchemy or Redis imports to `domain/`
- Put business logic in `interfaces/` — handlers should be thin
- Create a top-level `service.py` or `router.py` in the module root

**Test files** live inside the module at `tests/test_<layer>.py`
(e.g. `tests/test_service.py`, `tests/test_integration.py`).

---

## How to Add a New Module

### Step 1: Design

1. Define the bounded context
2. Identify aggregates and entities
3. Define public APIs (interfaces)
4. Identify events
5. Map dependencies

### Step 2: Create

1. Create folder in `app/`
2. Implement structure per above
3. Add to dependency rules
4. Create database migration

### Step 3: Register

1. Add router to main app
2. Add to module list in this document
3. Add to dependency tests
4. Document in handbook

### Step 4: Review

1. Architecture review by Architect Agent
2. Security review if sensitive
3. Peer review by module owner

---

## Common Module

The `common` module contains shared utilities used by 3+ modules:

> **Rule** — Only add to common if used by 3+ modules.

Contents:
- Base entity/repository/service classes
- Pydantic mixins
- Error types
- Audit logging
- Tenant context

Do NOT add to common:
- Business logic
- Module-specific utilities
- Things used by only 1-2 modules

---

## Related Documents

- [Bounded Contexts](../03-domain/bounded-contexts.md)
- [Aggregates](../03-domain/aggregates.md)
- [Backend Structure](../04-backend/folder-structure.md)
- [Module Structure](../04-backend/module-structure.md)
