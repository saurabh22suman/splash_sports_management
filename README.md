# Splashh Sports Platform

PWA-first multi-tenant SaaS for sports clubs (swimming, badminton, tennis, pickleball, gym, cricket nets, football, indoor games, coaching academies).

The complete engineering reference lives in [`docs/`](./docs/README.md).

---

## Stack

- **Backend:** FastAPI + SQLAlchemy 2 (async) + Alembic + PostgreSQL 16 + Redis 7
- **Frontend:** `apps/web-pwa` (single installable PWA; role-based home after login; admin users can create other roles)
- **Auth:** Argon2id passwords, HS256 JWT (5min access) + opaque refresh tokens (30d, rotated, httpOnly cookie)
- **Multi-tenancy:** shared schema with `tenant_id` on every business table + Postgres RLS
- **Quality:** Ruff + mypy strict + pytest (TDD) for backend; Vitest + RTL + Playwright + axe-core for frontend
- **Infra:** Docker Compose for local dev

## Repository layout

```
apps/
  backend/                # FastAPI monolith (modular by bounded context)
    src/
      common/             # Shared kernel (base repo, errors, tenant ctx)
      auth/               # Identity: User, Tenant, JWT, refresh tokens
      customer/           # Customer profiles, waivers
      facility/           # Facilities, Resources, AvailabilityRules
      booking/            # Slot reservation, double-booking prevention
    tests/
    alembic/              # Database migrations
    pyproject.toml
  web-pwa/                # Single PWA with role-based routing
packages/
  ui/                     # @splashh/ui — shadcn primitives + brand tokens
  api-client/             # @splashh/api-client — axios + auth + query keys
  config/                 # @splashh/config — shared tsconfig/vitest/biome
docs/                     # Engineering handbook (read this!)
e2e/                      # Playwright smoke specs
docker-compose.yml
playwright.config.ts
tsconfig.base.json
biome.json
```

## Local development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- Node 20+ and [pnpm](https://pnpm.io/) 9+
- Docker + Docker Compose
- openssl (for JWT keypair generation, optional)

### First-time setup

```bash
# 1. Install JS deps (workspace root)
pnpm install

# 2. Start Postgres + Redis
docker compose up -d postgres redis

# 3. Apply migrations
cd apps/backend
uv run alembic upgrade head
cd ../..

# 4. Run everything
pnpm dev
# → backend on :8765, web-pwa on :5173
```

To run just the backend: `make -C apps/backend dev`.
To run the PWA: `pnpm --filter web-pwa dev`.

### Test

```bash
# Backend
cd apps/backend && uv run pytest

# Frontend
pnpm test                  # all packages
pnpm test:e2e             # Playwright (requires pnpm dev or live servers)
```

### Add a shadcn primitive

```bash
pnpm ui:add dialog
```

This scopes the shadcn CLI to `packages/ui` per the root `ui:add` script.

## What's in this prototype

| Module | Status | Notes |
|---|---|---|
| `common` | Working | Base repo, errors, tenant context, structured logging, request context middleware |
| `auth` | Working | User + Tenant aggregates, login/refresh/logout endpoints, httpOnly refresh cookies, JWT rotation + reuse detection, admin user management |
| `customer` | Working | Customer profiles, CRUD endpoints |
| `facility` | Working | Facilities, resources, availability rules |
| `booking` | Working | Slot reservation, double-booking prevention via row-level lock |
| `web-pwa` | Working | Single PWA with role-based routing: /login (customer), /admin/login (admin), role-specific home pages, /admin/users for user management |

## Next phase

- Push notifications (VAPID + backend endpoint + SW handler)
- OpenAPI client codegen (replace hand-written `domain.ts` types)
- Stripe/Razorpay integration
- SMS / email notifications
- Background workers
- Production deploy / CI-CD
