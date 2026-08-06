# Splashh Sports Platform

PWA-first multi-tenant SaaS for sports clubs (swimming, badminton, tennis, pickleball, gym, cricket nets, football, indoor games, coaching academies).

The complete engineering reference lives in [`docs/`](./docs/README.md).

---

## Stack

- **Backend:** FastAPI + SQLAlchemy 2 (async) + Alembic + PostgreSQL 16 + Redis 7
- **Frontend PWAs:** Vite + React 18 + TypeScript + TanStack Query + shadcn/ui + vite-plugin-pwa
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
  admin-pwa/              # Operator PWA (facility admin, bookings)
  customer-pwa/           # End-user PWA (browse + book)
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
# → backend on :8765, admin-pwa on :5173, customer-pwa on :5174
```

To run just the backend: `make -C apps/backend dev`.
To run a single PWA: `pnpm --filter customer-pwa dev`.

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
| `auth` | Working | User + Tenant aggregates, login/refresh/logout endpoints, httpOnly refresh cookies, JWT rotation + reuse detection |
| `customer` | Working | Customer profiles, CRUD endpoints |
| `facility` | Working | Facilities, resources, availability rules |
| `booking` | Working | Slot reservation, double-booking prevention via row-level lock |
| `admin-pwa` | Thin slice | Login, facilities list/create/detail, resource form, PWA install + update |
| `customer-pwa` | Thin slice | Login, browse facilities, booking dialog, my bookings, PWA install + update |

## Next phase

- Push notifications (VAPID + backend endpoint + SW handler)
- OpenAPI client codegen (replace hand-written `domain.ts` types)
- Stripe/Razorpay integration
- SMS / email notifications
- Background workers
- Production deploy / CI-CD
