# GitHub Actions

> Pipeline design: lint → type check → unit → integration → security → build → deploy.

This document defines our CI/CD pipeline architecture using GitHub Actions. We prioritize fast feedback (linting in seconds), comprehensive quality gates, and clear separation between PR workflows and deployment workflows.

---

## Pipeline Architecture

We use a **multi-stage pipeline** with distinct workflows for PR validation and deployment:

```mermaid
flowchart LR
    A[Push/PR] --> B[Lint & Type Check]
    B --> C[Unit Tests]
    C --> D[Integration Tests]
    D --> E[Security Scan]
    E --> F[Build Image]
    F --> G{Is Main Branch?}
    G -->|Yes| H[Deploy Staging]
    G -->|No| I[Deploy Preview]
    H --> J[Tag Release]
    J --> K[Deploy Prod]
```

> **Why** — Parallel execution of independent stages (lint, type check) maximizes feedback speed. Sequential execution of dependent stages (unit → integration) ensures quality gates pass before proceeding.

---

## Pull Request Workflow

Every PR triggers the validation workflow at `.github/workflows/ci.yml`:

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"
  NODE_VERSION: "20"

jobs:
  # =============================================================================
  # Stage 1: Fast Feedback (seconds)
  # =============================================================================
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
          cache-dependency-path: apps/backend/requirements*.txt

      - name: Install dependencies
        run: |
          pip install -r apps/backend/requirements-dev.txt

      - name: Run Ruff
        run: ruff check apps/backend/src/

      - name: Run Ruff (formatter check)
        run: ruff format --check apps/backend/src/

      - name: ESLint (Frontend)
        if: steps.files.outputs.changed == 'true'
        run: |
          npm ci
          npm run lint
        working-directory: apps/customer-pwa

  type-check:
    name: Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Install dependencies
        run: |
          pip install -r apps/backend/requirements-dev.txt

      - name: Run mypy
        run: mypy apps/backend/src/

      - name: TypeScript Type Check
        if: steps.files.outputs.changed == 'true'
        run: |
          npm ci
          npm run type-check
        working-directory: apps/customer-pwa

  # =============================================================================
  # Stage 2: Test Execution (minutes)
  # =============================================================================
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Install dependencies
        run: |
          pip install -r apps/backend/requirements-dev.txt

      - name: Run pytest
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest apps/backend/src --cov=apps/backend/src --cov-report=xml --cov-report=term-missing

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Install dependencies
        run: |
          pip install -r apps/backend/requirements-dev.txt

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379/0
          API_BASE_URL: http://localhost:8000
        run: |
          pytest tests/integration/ -v

  # =============================================================================
  # Stage 3: Security (minutes)
  # =============================================================================
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r apps/backend/src/ -x tests/

      - name: Run Safety
        run: |
          pip install safety
          safety check --file=apps/backend/requirements.txt

      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: auto

      - name: Run Trivy (container scan)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: .
          severity: 'CRITICAL,HIGH'

  # =============================================================================
  # Stage 4: Build & Push
  # =============================================================================
  build:
    name: Build & Push Image
    needs: [lint, type-check, unit-tests, integration-tests, security]
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}/backend
          tags: |
            type=ref,event=branch
            type=sha,prefix=
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

> **Why** — Running security scans in parallel with tests maximizes utilization of CI minutes. The `needs` declaration ensures security only runs after code quality passes.

---

## Deployment Workflow

Deployment workflows are separate to enable manual approval for production:

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        type: choice
        options:
          - staging
          - production
      tag:
        description: 'Release tag to deploy'
        required: false

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/backend

jobs:
  deploy-staging:
    name: Deploy Staging
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    environment: staging
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to staging
        run: |
          # kubectl or cloud-specific deployment
          kubectl set image deployment/backend api=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

      - name: Run smoke tests
        run: |
          ./scripts/smoke-tests.sh staging

  deploy-production:
    name: Deploy Production
    runs-on: ubuntu-latest
    if: github.event_name == 'workflow_dispatch'
    environment: production
    needs: deploy-staging
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to production
        run: |
          # Blue/green or canary deployment
          ./scripts/deploy-production.sh ${{ github.event.inputs.tag }}
```

---

## Reusable Workflows

We extract common patterns into reusable workflows:

```yaml
# .github/workflows/reusable-test.yml
name: Reusable Test Workflow

on:
  workflow_call:
    inputs:
      python-version:
        type: string
        default: "3.11"
      test-path:
        type: string
        required: true
      coverage:
        type: boolean
        default: true

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python-version }}

      - name: Install dependencies
        run: pip install pytest pytest-cov

      - name: Run tests
        run: pytest ${{ inputs.test-path }}
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test
```

Usage in main workflow:

```yaml
jobs:
  backend-test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      test-path: apps/backend/src
      python-version: "3.11"
```

> **Why** — Reusable workflows reduce duplication, ensure consistent behavior across services, and make it easier to add new services.

---

## Workflow Templates

For new services, we use workflow templates:

```yaml
# .github/workflows/template-service.yml
# Template: Copy to .github/workflows/service-{name}.yml
name: Service CI/CD

on:
  push:
    paths:
      - 'apps/service-*/**'
      - '.github/workflows/service-*.yml'
  pull_request:
    paths:
      - 'apps/service-*/**'

jobs:
  ci:
    uses: ./.github/workflows/reusable-ci.yml
    with:
      service-path: apps/service-${{ github.event.inputs.service }}
```

---

## Caching Strategy

We cache dependencies to speed up builds:

| Cache Type | Strategy | Key |
|---|---|---|
| pip | `cache: pip` in setup-python | Hash of requirements.txt |
| npm | `cache: npm` in setup-node | Hash of package-lock.json |
| Docker | BuildKit cache | Git SHA + dependencies |
| Go | `go mod cache` | go.sum hash |

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: ${{ env.PYTHON_VERSION }}
    cache: pip
    cache-dependency-path: apps/backend/requirements*.txt
```

> **Guideline** — Cache keys should include the dependency file hash to invalidate when dependencies change.

---

## Parallel Execution

Independent jobs run in parallel to minimize total execution time:

```yaml
jobs:
  lint-python:
    runs-on: ubuntu-latest
    steps: ...

  lint-typescript:
    runs-on: ubuntu-latest
    steps: ...

  lint-dockerfile:
    runs-on: ubuntu-latest
    steps: ...

  # All three run in parallel, then...
  test:
    needs: [lint-python, lint-typescript, lint-dockerfile]
    runs-on: ubuntu-latest
    steps: ...
```

---

## Secret Management

Secrets are injected via environment variables, not hardcoded:

```yaml
jobs:
  deploy:
    steps:
      - name: Deploy
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          STRIPE_SECRET_KEY: ${{ secrets.STRIPE_SECRET_KEY }}
        run: |
          kubectl create secret generic app-secrets \
            --from-literal=database-url="$DATABASE_URL" \
            --from-literal=stripe-key="$STRIPE_SECRET_KEY"
```

> **Rule** — Never log secrets. Use `set -o pipefail` and `| grep -v` patterns if secrets might appear in logs.

---

## Matrix Builds

For testing across multiple Python versions or configurations:

```yaml
jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
        django-version: ["3.2", "4.0", "5.0"]
        exclude:
          - python-version: "3.10"
            django-version: "5.0"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
```

---

## Summary

| Stage | Jobs | Time Target | Failure Impact |
|---|---|---|---|
| Fast Feedback | lint, type-check | < 2 min | Block PR |
| Tests | unit, integration | < 10 min | Block PR |
| Security | bandit, safety, trivy | < 5 min | Block PR |
| Build | docker build + push | < 5 min | Block deploy |
| Deploy | staging, production | < 10 min | Affects users |

---

## Related Documents

- [Docker](./docker.md) — Container standards
- [Branch Strategy](./branch-strategy.md) — Branching model
- [Deployments](./deployments.md) — Deployment process
- [Feature Flags](./feature-flags.md) — Release control
