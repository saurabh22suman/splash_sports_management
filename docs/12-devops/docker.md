# Docker

> Multi-stage builds, distroless images, non-root users, and layer caching for production-grade containers.

This document defines our Docker standards for the Splashh Sports Platform. We prioritize security (non-root, minimal attack surface), build speed (layer caching), and debuggability (distroless with debug tools available).

---

## Image Base: Distroless or Alpine-Slim

We use **distroless** images for production and **alpine-slim** for development. The trade-off: distroless has the smallest attack surface but requires understanding of the minimal filesystem; alpine is slightly larger but more familiar to most engineers.

> **Why** — Distroless images omit shell, package managers, and most standard utilities. This reduces CVE surface dramatically. According to Docker's image vulnerability data, base image CVEs account for 40-60% of discovered vulnerabilities in containerized applications.

| Environment | Base Image | Rationale |
|---|---|---|
| Production | `gcr.io/distroless/python3-debian12` | Minimal attack surface, CVE-free base |
| Development | `python:3.11-slim-bookworm` | Familiar tooling, faster iteration |
| CI/Testing | `python:3.11-slim-bookworm` | Ephemeral, no security concerns |

### Multi-Stage Build Pattern

All Dockerfiles use multi-stage builds to minimize final image size and separate build-time from runtime dependencies.

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY apps/backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt


# Stage 2: Production
FROM gcr.io/distroless/python3-debian12 AS production

# Non-root user - CRITICAL for security
RUN addgroup --system --gid 1000 appgroup && \
    adduser --system --uid 1000 appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appgroup apps/backend/src /app/src
COPY --chown=appuser:appgroup apps/backend/alembic /app/alembic
COPY --chown=appuser:appgroup apps/backend/pyproject.toml /app/
COPY --chown=appuser:appgroup apps/backend/alembic.ini /app/

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **Rule** — Every production container must run as a non-root user with a fixed UID (1000).

---

## Layer Caching Optimization

Docker builds faster when layers that change infrequently are built first. The order matters:

1. **System dependencies** (apt packages) — rarely change
2. **Python environment** (requirements.txt) — change on dependency updates
3. **Application code** — changes on every commit

```dockerfile
# GOOD: Dependencies before code
COPY requirements.txt .
RUN pip install ...

COPY src/ ./src/  # Changes frequently

# BAD: Code before dependencies (invalidates cache on every code change)
COPY src/ ./src/
COPY requirements.txt .
RUN pip install ...
```

> **Pitfall** — Copying the entire project before installing dependencies invalidates the entire layer cache on every code change. Always copy only dependency files first.

---

## .dockerignore

Exclude files that bloat the build context and may leak secrets:

```
# Git
.git
.gitignore

# IDE
.idea/
.vscode/
*.swp
*.swo

# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.eggs/
build/
dist/
.venv/
venv/
env/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Documentation
docs/
*.md

# Local config
.env
.env.*
!.env.example

# Docker
Dockerfile
docker-compose*.yml
.docker/

# CI/CD
.github/
.gitlab-ci.yml

# Misc
*.log
*.tmp
.DS_Store
```

> **Why** — A large build context increases build time (upload to Docker daemon) and risks exposing secrets if `.env` files are accidentally copied.

---

## Health Checks

Every container must define a health check. We use HTTP checks for services with HTTP endpoints:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "
import httpx
try:
    r = httpx.get('http://localhost:8000/health', timeout=5)
    exit(0) if r.status_code == 200 else exit(1)
except Exception:
    exit(1)
"
```

For workers without HTTP endpoints:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python.*worker" > /dev/null || exit 1
```

> **Rule** — Health checks must be idempotent and check actual service health, not just process liveness.

---

## Per-Service Dockerfiles

Each service (backend API, worker, scheduler) has its own optimized Dockerfile. We do not use a single Dockerfile for everything because:

- Workers don't need the same dependencies as the API (no uvicorn)
- Different entry points require different cmd configurations
- Smaller images per service reduces attack surface

```
apps/
  backend/
    src/
    Dockerfile.api      # FastAPI with uvicorn
    Dockerfile.worker  # Celery/Redis worker
    Dockerfile.cli     # Management commands
    requirements.txt
```

---

## Docker Compose for Local Development

We use docker-compose for local development to replicate the production architecture:

```yaml
# docker-compose.yml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/splashh
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=DEBUG
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./apps/backend/src:/app/src
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: splashh
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/splashh
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

volumes:
  postgres_data:
  redis_data:
```

> **Guideline** — Use `depends_on` with `condition: service_healthy` to ensure dependencies are ready before the service starts. This prevents race conditions at startup.

---

## FastAPI Dockerfile Example

Complete example for the FastAPI backend:

```dockerfile
# apps/backend/Dockerfile.api
# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip wheel

# Install Python dependencies in one layer
COPY apps/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Production
# =============================================================================
FROM gcr.io/distroless/python3-debian12 AS production

# Security: Create non-root user
RUN addgroup --system --gid 1000 appgroup && \
    adduser --system --uid 1000 appuser

WORKDIR /app

# Copy virtual environment (includes all dependencies)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appgroup apps/backend/src /app/src
COPY --chown=appuser:appgroup apps/backend/alembic /app/alembic
COPY --chown=appuser:appgroup apps/backend/pyproject.toml /app/
COPY --chown=appuser:appgroup apps/backend/alembic.ini /app/

# Create directories for runtime (logs, etc.)
RUN mkdir -p /app/logs /app/uploads && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Health check: Test the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "
import httpx
try:
    r = httpx.get('http://localhost:8000/health', timeout=5)
    if r.status_code == 200:
        exit(0)
    exit(1)
except Exception:
    exit(1)
"

# Run uvicorn with gunicorn for production
CMD ["gunicorn", "src.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
```

> **Why Gunicorn with Uvicorn workers** — Pure Uvicorn is single-threaded. Gunicorn provides process management and worker supervision while delegating async handling to Uvicorn workers. This is the recommended deployment pattern for production FastAPI.

---

## BuildKit for Faster Builds

Enable BuildKit in CI for parallel layer building and improved caching:

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Build with BuildKit
docker build --progress=plain -t splashh-backend:latest .
```

Or enable in Docker daemon:

```json
{
  "features": {
    "buildkit": true
  }
}
```

> **Guideline** — Use `--progress=plain` in CI to avoid ANSI escape code issues in logs.

---

## Image Scanning

All images are scanned for CVEs before deployment:

```bash
# Using Trivy (can be integrated into CI)
trivy image splashh-backend:latest --severity HIGH,CRITICAL --exit-code 1
```

> **Rule** — Images with CRITICAL or HIGH vulnerabilities must not be deployed to production. Fix and rebuild before deployment.

---

## Summary

| Practice | Purpose |
|---|---|
| Distroless base | Minimal attack surface |
| Multi-stage builds | Smaller images, no build tools in production |
| Non-root user | Security, least privilege |
| Layer ordering | Faster builds via caching |
| Health checks | Container orchestration awareness |
| Per-service Dockerfiles | Optimized per-service images |
| .dockerignore | Faster builds, no secret leaks |
| Image scanning | CVE prevention |

---

## Related Documents

- [GitHub Actions](./github-actions.md) — CI/CD pipeline
- [Secrets](./secrets.md) — Secret management in containers
- [Monitoring](./monitoring.md) — Container metrics
- [Deployments](./deployments.md) — Deployment strategy
