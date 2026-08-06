# Folder Structure

> This document defines the repository layout for the backend application. The structure reflects bounded contexts (not technical layers) and enforces modularity.

## Overview

The backend lives in `apps/backend/src/`. Each subdirectory is a **bounded context** that owns its domain, persistence, and API surface. This structure makes the codebase navigable, testable, and evolve-able without cross-context coupling.

## Directory Tree

```
apps/backend/
├── src/
│   ├── auth/                  # Authentication, sessions, tokens
│   │   ├── __init__.py
│   │   ├── router.py          # FastAPI router
│   │   ├── service.py         # Application service
│   │   ├── repository.py      # Persistence
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── events.py          # Domain events
│   │   ├── exceptions.py      # Domain exceptions
│   │   └── tests/             # Module tests
│   │       ├── __init__.py
│   │       ├── unit/
│   │       └── integration/
│   │
│   ├── customer/              # Member/customer profiles
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── events.py
│   │   ├── exceptions.py
│   │   └── tests/
│   │
│   ├── membership/            # Subscription plans, renewals
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── events.py
│   │   ├── exceptions.py
│   │   └── tests/
│   │
│   ├── facility/              # Courts, pools, gyms, slots
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── events.py
│   │   ├── exceptions.py
│   │   └── tests/
│   │
│   ├── booking/               # Reservations, check-in
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── events.py
│   │   ├── exceptions.py
│   │   └── tests/
│   │
│   ├── payments/             # Pricing, invoices, refunds
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── events.py
│   │   ├── exceptions.py
│   │   └── tests/
│   │
│   ├── notifications/         # SMS, email, push
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── events.py
│   │   ├── exceptions.py
│   │   └── tests/
│   │
│   ├── analytics/             # Reports, dashboards
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── events.py
│   │   ├── exceptions.py
│   │   └── tests/
│   │
│   ├── common/                # Shared utilities
│   │   ├── __init__.py
│   │   ├── dependencies.py   # FastAPI dependencies
│   │   ├── exceptions.py    # Shared exceptions
│   │   ├── responses.py      # Shared response helpers
│   │   ├── utils.py          # Helper functions
│   │   ├── logging.py        # Logging setup
│   │   ├── config.py         # Configuration
│   │   └── pagination.py     # Pagination utilities
│   │
│   ├── main.py               # FastAPI application entry
│   ├── lifespan.py           # Startup/shutdown handlers
│   └── container.py          # Dependency injection container
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures
│   ├── factories/            # Test factories
│   └── utils/                # Test utilities
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── pyproject.toml
├── uv.lock
└── Dockerfile
```

## Module Responsibilities

Each module is a **bounded context** with clear ownership:

| Module | Domain | Key Aggregates |
|--------|--------|----------------|
| `auth` | Identity & access | User, Session, Token |
| `customer` | Member profiles | Customer, ContactInfo |
| `membership` | Subscriptions | Membership, Plan, Renewal |
| `facility` | Resources | Facility, Court, Slot, Schedule |
| `booking` | Reservations | Booking, BookingLine, CheckIn |
| `payments` | Financial | Payment, Invoice, Refund |
| `notifications` | Messaging | Notification, Channel, Template |
| `analytics` | Reporting | Report, Metric, Export |
| `common` | Cross-cutting | — |

## File Conventions

| File | Purpose |
|------|---------|
| `router.py` | FastAPI router, HTTP adapters |
| `service.py` | Application service, use case orchestration |
| `repository.py` | Persistence abstraction |
| `models.py` | SQLAlchemy ORM models |
| `schemas.py` | Pydantic validation schemas |
| `events.py` | Domain event definitions |
| `exceptions.py` | Domain exceptions |
| `tests/` | Module-specific tests |

> **Rule** — Every module MUST have all seven core files, even if some are empty stubs. This ensures consistent navigation.

## Cross-Module Dependencies

Modules communicate via:

1. **Domain events** — For eventual consistency (e.g., `BookingCreated` → `MembershipUpdated`)
2. **Public APIs** — HTTP calls for synchronous operations (rare in modular monolith)
3. **Shared ports** — Defined in `common/` when multiple modules implement the same interface

> **Anti-pattern** — Module A importing Module B's `models.py` or `repository.py` directly. Use domain events or service calls instead.

## Why This Structure

**Trade-offs:**

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Contexts over layers | Folders = bounded contexts | Mirrors domain, not technology. Easier to extract to microservices later. |
| Flat module depth | No nested subfolders per layer | Simpler navigation, less boilerplate |
| Tests co-located | `tests/` inside each module | Faster test discovery, clearer ownership |
| Shared in `common/` | Cross-cutting concerns isolated | Prevents `common` from becoming a dumping ground |

**Alternatives considered:**

- Layered structure (`domain/`, `application/`, `infrastructure/`) — Rejected because it groups unrelated code and obscures domain boundaries.
- One file per module — Rejected; too large for production modules.
- Tests in top-level `tests/` only — Rejected; co-located tests improve developer experience.

## Enforcement

This structure is enforced by:

1. **Architecture tests** — `pytest-archon` or custom tests verify module imports.
2. **Linting** — `ruff` rules can flag illegal imports.
3. **Code review** — Reviewers check import boundaries.

See [Module Structure](module-structure.md) for the internal layout of each module.
