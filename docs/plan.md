# Splashh Sports Platform - Engineering Plan

## Vision

Build a PWA-first, multi-tenant Sports Club SaaS using **React +
FastAPI + PostgreSQL + Redis**. Primary goal: solve Splashh's
operational problems first, then evolve into a SaaS platform.

------------------------------------------------------------------------

# Engineering Principles

1.  Modular Monolith first
2.  Domain Driven Design (DDD)
3.  Test Driven Development (Red → Green → Refactor)
4.  Security by Default
5.  Event-driven internal architecture
6.  Metadata/configuration over hardcoding
7.  CI/CD with automated quality gates

------------------------------------------------------------------------

# Development Lifecycle

``` text
Requirement
    ↓
BDD Scenario
    ↓
Write Failing Test (RED)
    ↓
Minimal Code (GREEN)
    ↓
Refactor
    ↓
Security Review
    ↓
Code Review
    ↓
Merge
```

Every feature follows: - Unit tests - Integration tests - API tests -
Authorization tests - Regression tests

------------------------------------------------------------------------

# TDD Rules

## RED

-   Write the failing test first.
-   Define acceptance criteria.
-   No production code before a failing test.

## GREEN

-   Write the minimum code required.
-   Avoid optimization.

## REFACTOR

-   Remove duplication.
-   Improve naming.
-   Preserve passing tests.

Coverage targets: - Domain: 95%+ - Services: 90%+ - API: 80%+

------------------------------------------------------------------------

# Multi-Agent Development

## Product Agent

-   Refines requirements
-   Creates user stories
-   Defines acceptance criteria

## Architect Agent

-   Reviews DDD boundaries
-   API contracts
-   Database design

## Backend Agent

-   FastAPI implementation
-   SQLAlchemy models
-   Alembic migrations

## Frontend Agent

-   React PWA
-   Accessibility
-   Responsive UI

## QA Agent

-   Generates test cases
-   Regression suite
-   Performance validation

## Security Agent

Checks: - OWASP Top 10 - Authorization - Secrets - Dependency scanning -
Input validation - Rate limiting

## DevOps Agent

-   Docker
-   GitHub Actions
-   Deployments
-   Monitoring

No PR is merged until every agent signs off.

------------------------------------------------------------------------

# Repository Layout

``` text
apps/
  backend/
  admin-pwa/
  customer-pwa/

packages/
  shared/
  contracts/

tests/
docs/
```

------------------------------------------------------------------------

# Backend Structure

``` text
auth/
customer/
membership/
facility/
booking/
payments/
notifications/
analytics/
common/
```

Each module contains: - router.py - service.py - repository.py -
models.py - schemas.py - tests/

------------------------------------------------------------------------

# Security Checklist

Authentication - JWT access + refresh - MFA for admins - Password
hashing (Argon2)

Authorization - RBAC - Tenant isolation - Row-level filtering

Input - Pydantic validation - File type validation - Size limits

API - HTTPS only - CORS - Rate limiting - Idempotency keys - Request IDs

Database - Parameterized queries - Encryption at rest - Daily backups -
PITR enabled

Secrets - Vault or cloud secret manager - Never commit secrets

Dependencies - Dependabot/Renovate - SAST - Dependency scanning

Logging - Structured logs - Audit trail - No sensitive data in logs

------------------------------------------------------------------------

# Testing Pyramid

-   Unit Tests (largest)
-   Integration Tests
-   API Tests
-   End-to-End Tests
-   Load Tests

Use: - pytest - httpx - Playwright - Locust

------------------------------------------------------------------------

# CI Pipeline

1.  Lint
2.  Type Check
3.  Unit Tests
4.  Integration Tests
5.  Security Scan
6.  Build
7.  Deploy Preview

Production requires all checks green.

------------------------------------------------------------------------

# Architecture Evolution

Phase 1 - Modular Monolith

Phase 2 - Redis - Background Workers - Event Bus

Phase 3 - Extract Booking Service if required - AI Service (Python)

Never introduce microservices before measurable need.

------------------------------------------------------------------------

# Non-functional Goals

-   API \<200 ms (P95)
-   99.9% uptime
-   Zero cross-tenant leakage
-   OWASP ASVS alignment
-   Automated backups
-   Observability (OpenTelemetry)

------------------------------------------------------------------------

# Definition of Done

-   Acceptance criteria met
-   Tests written first
-   Tests passing
-   Security review passed
-   Documentation updated
-   Monitoring added
-   Feature flag considered
-   Code reviewed
