# Docker

Two compose files live in the repo root:

| File | Purpose |
|---|---|
| `docker-compose.dev.yml` | Local development stack (Postgres + Redis + FastAPI with `--reload` + optional Vite UI). |
| `docker-compose.prod.yml` | Production deployment for [Dokploy](https://dokploy.com) — Traefik labels, healthchecks, secrets, prod secrets management. |

## Local development

```bash
# Infra + backend (no UI — run Vite locally with pnpm dev if you prefer)
docker compose -f docker-compose.dev.yml up -d

# Apply migrations
docker compose -f docker-compose.dev.yml --profile tools run --rm migrate

# Seed demo data
docker compose -f docker-compose.dev.yml --profile tools run --rm seed-demo

# Bring up Vite inside Docker too (optional — keeps a single `docker compose up`)
docker compose -f docker-compose.dev.yml --profile ui up -d

# Tear down (deletes volumes)
docker compose -f docker-compose.dev.yml down -v
```

The backend listens on `localhost:8765` (mapped from container port 8000) so it
matches the dev proxy target in `apps/web-pwa/vite.config.ts`. Vite (whether
running locally or in the `web-pwa` service) talks to it on that port.

## Production (Dokploy)

1. Create a new **Compose** service in Dokploy, pointing it at this repo.
2. Copy `.env.prod.example` → `.env` in the same directory as
   `docker-compose.prod.yml`. Fill in:
   - `POSTGRES_PASSWORD`, `DATABASE_URL`
   - `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`
   - `DOMAIN_WEB`, `DOMAIN_API`
   - `CORS_ALLOWED_ORIGINS` (must include `https://${DOMAIN_WEB}`)
3. If you use RS256 JWTs (recommended for prod), drop the PEM files into
   `./secrets/jwt_private.pem` and `./secrets/jwt_public.pem`.
4. In the Dokploy **Domains** tab:
   - Bind `web-pwa` → `${DOMAIN_WEB}` (container port `80`)
   - Bind `backend` → `${DOMAIN_API}` (container port `8000`)
5. Deploy. Dokploy runs `docker compose -p ${COMPOSE_PROJECT_NAME} -f
   docker-compose.prod.yml up -d --build`.

### How Traefik labels work here

Both `web-pwa` and `backend` define two routers — one HTTP that redirects to
HTTPS, one HTTPS with the `letsencrypt` cert resolver. Hostnames are
templated from the `DOMAIN_*` env vars. Service ports come from the container
itself (nginx on 80 for the PWA, uvicorn on 8000 for the API).

If you set `COMPOSE_PROJECT_NAME=splashh`, the routers are named
`splashh-api-https` and `splashh-web-https`. Dokploy reads those names to
generate the matching Traefik config; renaming the project just renames
them.

### Backing up

The named volumes `splashh_postgres_data` and `splashh_redis_data` are
visible to Dokploy under **Backups**. Configure your backup target there.
