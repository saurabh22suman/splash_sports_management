# Splashh Sports Platform

PWA-first multi-tenant SaaS for sports clubs (swimming, badminton, tennis, pickleball, gym, cricket nets, football, indoor games, coaching academies).

The complete engineering reference lives in [`docs/`](./docs/README.md).

---

## Stack

- **Backend:** FastAPI + SQLAlchemy 2 (async) + Alembic + PostgreSQL 16 + Redis 7
- **Frontend:** `apps/web-pwa` — React 19 + Vite 6 + Tailwind 4 (`@theme`-based tokens), single installable PWA with role-based home after login
- **UI kit:** `packages/ui` — shadcn-style primitives (`Button`, `Card`, `Input`, `FormField`, `EmptyState`, `ErrorState`, `LoadingSkeleton`, `Badge`, `StatusPill`) styled against a single dark + volt athletic palette (Oswald display, Plus Jakarta Sans body)
- **Auth:** Argon2id passwords, RS256/HS256 JWT (5min access) + opaque refresh tokens (30d, rotated, httpOnly cookie)
- **Multi-tenancy:** shared schema with `tenant_id` on every business table + Postgres RLS
- **Payments:** Razorpay payment links + webhooks (multi-currency)
- **Quality:** Ruff + mypy strict + pytest (TDD) for backend; Vitest + RTL + Playwright + axe-core for frontend
- **Infra:** `docker-compose.dev.yml` (local Postgres + Redis + backend with `--reload`) and `docker-compose.prod.yml` (Dokploy + Traefik) — see [`docs/docker.md`](./docs/docker.md)

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
      payments/           # Razorpay invoices, payment links, webhooks
    tests/
    alembic/              # Database migrations
    pyproject.toml
    Dockerfile
  web-pwa/                # Single PWA with role-based routing
    Dockerfile            # Multi-stage Node build + nginx runtime
    nginx.conf            # SPA fallback + asset cache headers
packages/
  ui/                     # @splashh/ui — shadcn primitives + dark+volt theme
  api-client/             # @splashh/api-client — axios + auth + query keys
  config/                 # @splashh/config — shared tsconfig/vitest/biome
docs/                     # Engineering handbook (read this!)
e2e/                      # Playwright smoke specs
docker-compose.dev.yml    # Local dev: Postgres + Redis + backend (+ optional Vite in 'ui' profile)
docker-compose.prod.yml   # Production: Dokploy + Traefik labels + secrets
.env.prod.example         # Template for production env vars
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

# 2. Start Postgres + Redis + backend
docker compose -f docker-compose.dev.yml up -d

# 3. Apply migrations + seed demo data
docker compose -f docker-compose.dev.yml --profile tools run --rm migrate
docker compose -f docker-compose.dev.yml --profile tools run --rm seed-demo

# 4. Start the PWA (locally — or use the 'ui' profile to run it inside Docker)
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
| `payments` | Working | Razorpay payment links + webhooks (INR); admin invoice list, customer pay page; HMAC-verified webhooks |
| `web-pwa` | Working | Single PWA with role-based routing: /login (customer), /admin/login (admin), role-specific home pages, /admin/users for user management |

## Next phase

- Push notifications (VAPID + backend endpoint + SW handler)
- OpenAPI client codegen (replace hand-written `domain.ts` types)
- SMS / email notifications
- Background workers
- Production deploy / CI-CD
- `membership` module — in progress on `feature/membership-v1` worktree
