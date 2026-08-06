# Splashh Sports Platform

PWA-first multi-tenant SaaS for sports clubs (swimming, badminton, tennis, pickleball, gym, cricket nets, football, indoor games, coaching academies).

This monorepo currently contains the **backend prototype**. Frontend PWAs (`apps/admin-pwa`, `apps/customer-pwa`) will be added in the next phase.

The complete engineering reference lives in [`docs/`](./docs/README.md).

---

## Stack

- **Backend:** FastAPI + SQLAlchemy 2 (async) + Alembic + PostgreSQL 16 + Redis 7
- **Auth:** Argon2id passwords, RS256 JWT (15min access) + opaque refresh tokens (30d, rotated)
- **Multi-tenancy:** shared schema with `tenant_id` on every business table + Postgres RLS
- **Quality:** Ruff + mypy strict + pytest (TDD)
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
docs/                     # Engineering handbook (read this!)
docker-compose.yml
pyproject.toml            # Workspace root
```

## Local development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- Docker + Docker Compose
- openssl (for JWT keypair generation, optional)

### First-time setup

```bash
# 1. Copy env template
cp .env.example .env

# 2. Generate JWT keypair (for RS256)
mkdir -p secrets
openssl genrsa -out secrets/jwt_private.pem 2048
openssl rsa -in secrets/jwt_private.pem -pubout -out secrets/jwt_public.pem

# 3. Start Postgres + Redis
docker compose up -d postgres redis

# 4. Install backend deps
cd apps/backend
uv sync --extra dev
cd ../..

# 5. Apply migrations
docker compose run --rm migrate
# or: cd apps/backend && uv run alembic upgrade head

# 6. Run the backend
docker compose up backend
# or: cd apps/backend && uv run uvicorn common.interfaces.http.app:create_app --factory --reload
```

The API will be at <http://localhost:8000>. OpenAPI docs at <http://localhost:8000/docs>.

### Run tests

```bash
cd apps/backend
uv run pytest              # all tests
uv run pytest -m unit      # unit only
uv run pytest --cov=src    # with coverage
```

## What's in this prototype

| Module | Status | Notes |
|---|---|---|
| `common` | Skeleton | Base repo, errors, tenant context, structured logging |
| `auth` | Skeleton | User + Tenant aggregates, login/refresh endpoints |
| `customer` | Stub | Coming next |
| `facility` | Stub | Coming next |
| `booking` | Stub | Coming next |

## Next phase

After the backend is stable, the prototype will add:
- `apps/admin-pwa` (React 18 + Vite + TanStack Query + shadcn/ui)
- `apps/customer-pwa` (same stack, installable PWA)
- Stripe/Razorpay integration
- SMS / email notifications
- Background workers
