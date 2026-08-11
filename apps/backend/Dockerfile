# Multi-stage build for the Splashh backend.
# Final image runs as non-root with distroless-style base.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user for runtime
RUN groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser

WORKDIR /app

# Copy workspace config + backend package
COPY pyproject.toml uv.lock* ./
COPY apps/backend/pyproject.toml apps/backend/
COPY apps/backend/src apps/backend/src
COPY apps/backend/alembic apps/backend/alembic
COPY apps/backend/alembic.ini apps/backend/

# Install dependencies
RUN cd apps/backend && uv sync --frozen --no-dev || uv sync --no-dev

ENV PATH="/app/apps/backend/.venv/bin:$PATH"

WORKDIR /app/apps/backend

# Hand ownership of the app tree to the non-root user
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "common.interfaces.http.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
