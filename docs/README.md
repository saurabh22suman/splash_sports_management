# Splashh Sports Platform — Engineering Handbook

> **The authoritative technical reference for the Splashh Sports Club Management Platform.**
> Written for senior engineers, AI coding agents, architects, QA engineers, DevOps engineers, and future contributors.

---

## What this handbook is

This handbook is the **single source of truth** for how we build, run, and evolve the Splashh Sports Platform. It covers architecture, coding standards, security, testing, deployment, and operational concerns in enough detail that an experienced engineer can build and operate the platform end-to-end without additional architectural clarification.

It is intentionally written in the style of an internal engineering handbook used at companies like Stripe, Uber, Shopify, Netflix, and Microsoft. Every decision documented here explains **why**, the **trade-offs** considered, and the **anti-patterns** we are explicitly avoiding.

## What this handbook is not

- It is **not** a tutorial on Python, React, FastAPI, or PostgreSQL. We assume the reader has prior experience.
- It is **not** a marketing document. It is a working engineering reference.
- It is **not** frozen. The platform will evolve over the next 5–10 years, and so will this handbook.

---

## How to use this handbook

1. **New engineer onboarding** — read the [Vision & Principles](./01-vision/overview.md), then [Architecture](./02-architecture/system-context.md), then your team's module docs in [Modules](./18-modules/README.md).
2. **Building a feature** — read [Feature Development Workflow](./15-workflows/feature-development.md) end-to-end before writing any code.
3. **Reviewing a PR** — use the [Code Review Checklist](./13-coding-standards/code-review-checklist.md) and the [Quality Gates](./16-quality-gates/overview.md).
4. **Responding to an incident** — jump straight to [Incident Response](./09-security/incident-response.md).
5. **AI coding agent** — read [AI-Driven Development](./14-ai-driven-development/overview.md) and respect the [Collaboration Rules](./14-ai-driven-development/collaboration.md).

---

## Table of Contents

### 00 — Handbook

| Document | Purpose |
|---|---|
| [README](./README.md) | This file — entry point & navigation |
| [Conventions](./00-handbook/conventions.md) | How to read & write this handbook |
| [Glossary](./00-handbook/glossary.md) | Shared vocabulary across documents |

### 01 — Vision & Principles

| Document | Purpose |
|---|---|
| [Overview](./01-vision/overview.md) | Platform vision, scope, success metrics |
| [Engineering Philosophy](./01-vision/principles.md) | Principles, anti-patterns, decision heuristics |

### 02 — Architecture

| Document | Purpose |
|---|---|
| [System Context (C4 L1)](./02-architecture/system-context.md) | Actors, external systems, system boundary |
| [Container Diagram (C4 L2)](./02-architecture/container-diagram.md) | Apps, databases, queues, object stores |
| [Component Diagram (C4 L3)](./02-architecture/component-diagram.md) | Backend modules, frontend shells |
| [Module Diagram](./02-architecture/module-diagram.md) | Bounded contexts, dependencies, integration |
| [Request Lifecycle](./02-architecture/request-lifecycle.md) | How a request moves through the stack |
| [Authentication Flow](./02-architecture/flow-authentication.md) | End-to-end auth |
| [Booking Flow](./02-architecture/flow-booking.md) | End-to-end booking |
| [Payment Flow](./02-architecture/flow-payment.md) | End-to-end payment |
| [Membership Flow](./02-architecture/flow-membership.md) | End-to-end membership lifecycle |
| [Notification Flow](./02-architecture/flow-notification.md) | End-to-end notification dispatch |
| [Event Flow](./02-architecture/flow-events.md) | How domain events flow |
| [Data Flow](./02-architecture/data-flow.md) | Data ownership and movement |
| [Caching Strategy](./02-architecture/caching-strategy.md) | What to cache, where, for how long |
| [Scaling Strategy](./02-architecture/scaling-strategy.md) | Horizontal & vertical scaling |
| [Disaster Recovery](./02-architecture/disaster-recovery.md) | RTO/RPO, multi-region, backup |

### 03 — Domain

| Document | Purpose |
|---|---|
| [Ubiquitous Language](./03-domain/ubiquitous-language.md) | Glossary of terms used across the codebase |
| [Bounded Contexts](./03-domain/bounded-contexts.md) | Context boundaries and ownership |
| [Aggregates](./03-domain/aggregates.md) | Aggregate roots and consistency boundaries |

### 04 — Backend

| Document | Purpose |
|---|---|
| [Folder Structure](./04-backend/folder-structure.md) | Repository layout & module boundaries |
| [Module Structure](./04-backend/module-structure.md) | Standard layout inside a module |
| [Dependency Injection](./04-backend/dependency-injection.md) | Container, lifetimes, scoping |
| [Repositories](./04-backend/repositories.md) | Persistence patterns |
| [Services](./04-backend/services.md) | Application service patterns |
| [Schemas & Validation](./04-backend/schemas-validation.md) | Pydantic models, validation |
| [Error Handling](./04-backend/error-handling.md) | Exception hierarchy, error responses |
| [Logging](./04-backend/logging.md) | Structured logging, log levels, PII |
| [Configuration](./04-backend/configuration.md) | 12-factor config, env layering |
| [Migrations](./04-backend/migrations.md) | Alembic usage & standards |
| [Transactions & Concurrency](./04-backend/transactions-concurrency.md) | ACID, locking, optimistic concurrency |
| [Background Tasks](./04-backend/background-tasks.md) | Workers, scheduling, retries |
| [Idempotency](./04-backend/idempotency.md) | Idempotency keys, safe retries |
| [Versioning](./04-backend/versioning.md) | API & data-model versioning |
| [Pagination, Filtering, Sorting](./04-backend/pagination-filtering.md) | Cursor pagination, query patterns |
| [OpenAPI](./04-backend/openapi.md) | Spec generation, docs, client codegen |
| [Naming Conventions](./04-backend/naming-conventions.md) | Names for files, classes, functions |

### 05 — Frontend

| Document | Purpose |
|---|---|
| [Folder Structure](./05-frontend/folder-structure.md) | Repo layout for PWAs |
| [Component Design](./05-frontend/component-design.md) | Composition, props, state ownership |
| [Hooks](./05-frontend/hooks.md) | Custom hook patterns |
| [Forms](./05-frontend/forms.md) | React Hook Form + Zod |
| [Accessibility](./05-frontend/accessibility.md) | WCAG 2.2 AA, keyboard, ARIA |
| [Responsive Design](./05-frontend/responsive-design.md) | Breakpoints, fluid layouts |
| [Offline Support](./05-frontend/offline-support.md) | Service worker, sync, conflict resolution |
| [Caching](./05-frontend/caching.md) | TanStack Query caching strategy |
| [State Management](./05-frontend/state-management.md) | Server vs. client state |
| [Error Handling](./05-frontend/error-handling.md) | Boundaries, fallbacks, retry |
| [PWA Strategy](./05-frontend/pwa-strategy.md) | Install, push, background sync |
| [Performance](./05-frontend/performance.md) | Bundle size, runtime perf budgets |
| [Lazy Loading & Code Splitting](./05-frontend/lazy-loading.md) | Route-level & component-level splitting |
| [Design Tokens](./05-frontend/design-tokens.md) | Token architecture |
| [Theme Strategy](./05-frontend/theme-strategy.md) | Light/dark, brand theming |

### 06 — Database

| Document | Purpose |
|---|---|
| [Schema Design](./06-database/schema-design.md) | Normalization, denormalization patterns |
| [Naming Standards](./06-database/naming-standards.md) | Tables, columns, indexes |
| [Indexes](./06-database/indexes.md) | B-tree, GIN, partial, covering |
| [Constraints](./06-database/constraints.md) | FK, unique, check, exclusion |
| [Relationships](./06-database/relationships.md) | Cardinality, polymorphism |
| [Migrations](./06-database/migrations.md) | Safe online migrations |
| [Soft Delete](./06-database/soft-delete.md) | When to soft-delete, when to hard-delete |
| [Auditing](./06-database/auditing.md) | Audit tables, change tracking |
| [Partitioning](./06-database/partitioning.md) | When & how to partition |
| [Archival](./06-database/archival.md) | Cold data lifecycle |
| [Backups](./06-database/backups.md) | PITR, snapshots, restore drills |
| [Performance Optimization](./06-database/performance-optimization.md) | Query plans, vacuum, stats |

### 07 — Events

| Document | Purpose |
|---|---|
| [Event Catalog](./07-events/event-catalog.md) | Every event, its producer/consumer, payload, retry |
| [Event Bus](./07-events/event-bus.md) | Transport choice, semantics, ordering |
| [Retry & Failure](./07-events/retry-failure.md) | DLQ, poison messages, backoff |
| [Idempotency](./07-events/idempotency.md) | Event idempotency & dedup |

### 08 — APIs

| Document | Purpose |
|---|---|
| [REST Design](./08-apis/rest-design.md) | Resource modeling, verbs, conventions |
| [Versioning](./08-apis/versioning.md) | URL vs. header versioning |
| [Error Responses](./08-apis/error-responses.md) | RFC 7807 problem details |
| [Status Codes](./08-apis/status-codes.md) | When to use what |
| [OpenAPI](./08-apis/openapi.md) | Spec as contract, codegen |
| [Rate Limiting](./08-apis/rate-limiting.md) | Per-tenant, per-IP, per-user limits |
| [Idempotency](./08-apis/idempotency.md) | Idempotency-Key header patterns |
| [Authentication](./08-apis/authentication.md) | Bearer JWT, refresh tokens |
| [Pagination](./08-apis/pagination.md) | Cursor vs. offset |
| [Filtering, Search, Sorting](./08-apis/filtering-search.md) | Query parameters |
| [File Uploads](./08-apis/file-uploads.md) | Direct upload, pre-signed URLs |

### 09 — Security

| Document | Purpose |
|---|---|
| [Overview](./09-security/overview.md) | Security principles & posture |
| [Authentication](./09-security/authentication.md) | Identity, JWT, refresh, MFA |
| [Authorization & RBAC](./09-security/authorization-rbac.md) | Role & permission model |
| [Tenant Isolation](./09-security/tenant-isolation.md) | Multi-tenant data isolation |
| [OWASP Top 10](./09-security/owasp-top-10.md) | Coverage of each risk |
| [OWASP ASVS](./09-security/owasp-asvs.md) | Verification level alignment |
| [SQL Injection](./09-security/sql-injection.md) | Parameterized queries, ORM safety |
| [XSS](./09-security/xss.md) | Output encoding, CSP |
| [CSRF](./09-security/csrf.md) | Token & SameSite strategies |
| [SSRF](./09-security/ssrf.md) | Egress controls |
| [Secrets Management](./09-security/secrets-management.md) | Vault, secret rotation |
| [Dependency Scanning](./09-security/dependency-scanning.md) | SCA, SBOM, Renovate |
| [Container Security](./09-security/container-security.md) | Image scanning, distroless |
| [Rate Limiting](./09-security/rate-limiting.md) | Brute force & abuse mitigation |
| [Input Validation](./09-security/input-validation.md) | Allow-listing, schemas |
| [Output Encoding](./09-security/output-encoding.md) | Context-aware encoding |
| [Audit Logging](./09-security/audit-logging.md) | Tamper-evident audit trail |
| [Encryption](./09-security/encryption.md) | At rest, in transit, field-level |
| [Backup & Recovery](./09-security/backup-recovery.md) | Encrypted backups, restore tests |
| [Disaster Recovery](./09-security/disaster-recovery.md) | DR runbooks |
| [Incident Response](./09-security/incident-response.md) | Detection → containment → lessons |
| [Threat Modeling](./09-security/threat-modeling.md) | STRIDE, attack trees |
| [Security Code Reviews](./09-security/security-code-reviews.md) | Review checklist |
| [Security Testing](./09-security/security-testing.md) | SAST, DAST, IAST |
| [Penetration Testing](./09-security/penetration-testing.md) | Annual pen test scope |
| [API Security](./09-security/api-security.md) | BOLA, BFLA, mass assignment |
| [JWT Best Practices](./09-security/jwt-best-practices.md) | Algorithm, claims, rotation |
| [Refresh Token Rotation](./09-security/refresh-token-rotation.md) | Reuse detection |
| [Session Management](./09-security/session-management.md) | Session vs. token trade-offs |
| [Password Policy](./09-security/password-policy.md) | Length, breach check, MFA |
| [MFA](./09-security/mfa.md) | TOTP, WebAuthn, backup codes |
| [Key Rotation](./09-security/key-rotation.md) | Signing key, JWT key, DB keys |
| [Supply Chain](./09-security/supply-chain.md) | SLSA, signed images |
| [Zero Trust](./09-security/zero-trust.md) | Principles & implementation |

### 10 — Testing

| Document | Purpose |
|---|---|
| [TDD Handbook](./10-testing/tdd-handbook.md) | Red → Green → Refactor in depth |
| [Unit Tests](./10-testing/unit-tests.md) | Pure function & domain testing |
| [Integration Tests](./10-testing/integration-tests.md) | DB, queue, external service |
| [API Tests](./10-testing/api-tests.md) | End-to-end HTTP tests |
| [UI Tests](./10-testing/ui-tests.md) | Playwright component & e2e |
| [Contract Tests](./10-testing/contract-tests.md) | Producer/consumer contracts |
| [Performance Tests](./10-testing/performance-tests.md) | Micro-benchmarks |
| [Load Tests](./10-testing/load-tests.md) | Locust scenarios |
| [Regression Tests](./10-testing/regression-tests.md) | Bug-prevention suite |
| [Mutation Testing](./10-testing/mutation-testing.md) | Verifying test quality |
| [Coverage Strategy](./10-testing/coverage-strategy.md) | Targets, what to cover, what not to |
| [Mocking Strategy](./10-testing/mocking-strategy.md) | What to mock, what not to |
| [Test Data Management](./10-testing/test-data-management.md) | Factories, fixtures, anonymization |
| [Testing Pyramid](./10-testing/testing-pyramid.md) | Test ratio strategy |
| [Testing Diamond](./10-testing/testing-diamond.md) | When diamond beats pyramid |
| [BDD](./10-testing/bdd.md) | Gherkin scenarios as executable spec |
| [Property-Based Testing](./10-testing/property-based-testing.md) | Hypothesis & Schemathesis |

### 11 — Performance

| Document | Purpose |
|---|---|
| [Caching](./11-performance/caching.md) | Layers, TTLs, invalidation |
| [Redis](./11-performance/redis.md) | Data structures, Lua, eviction |
| [Database Optimization](./11-performance/database-optimization.md) | Query plans, hot paths |
| [Connection Pooling](./11-performance/connection-pooling.md) | Pool sizing & leak detection |
| [Async Processing](./11-performance/async-processing.md) | When to async |
| [Queue Design](./11-performance/queue-design.md) | Throughput, fairness, starvation |
| [Response Time Goals](./11-performance/response-time-goals.md) | SLOs per endpoint |
| [Memory Usage](./11-performance/memory-usage.md) | Profiling & leak hunting |
| [Observability](./11-performance/observability.md) | OTel, RED, USE |
| [Performance Budgets](./11-performance/performance-budgets.md) | Bundle, network, CPU budgets |

### 12 — DevOps

| Document | Purpose |
|---|---|
| [Docker](./12-devops/docker.md) | Images, multi-stage, distroless |
| [GitHub Actions](./12-devops/github-actions.md) | Pipeline design |
| [Branch Strategy](./12-devops/branch-strategy.md) | Trunk-based with short-lived branches |
| [Release Strategy](./12-devops/release-strategy.md) | Semver, blue/green, canary |
| [Feature Flags](./12-devops/feature-flags.md) | Decoupling deploy from release |
| [Secrets](./12-devops/secrets.md) | Runtime secret injection |
| [Monitoring](./12-devops/monitoring.md) | Prometheus, SLO alerts |
| [Logging](./12-devops/logging.md) | Structured logs, retention |
| [Tracing](./12-devops/tracing.md) | OpenTelemetry end-to-end |
| [Deployments](./12-devops/deployments.md) | CI/CD to staging & prod |
| [Rollback Strategy](./12-devops/rollback-strategy.md) | Auto-rollback triggers |
| [Disaster Recovery](./12-devops/disaster-recovery.md) | Region failover runbook |
| [Environment Management](./12-devops/environment-management.md) | dev/staging/preview/prod |

### 13 — Coding Standards

| Document | Purpose |
|---|---|
| [Python Style](./13-coding-standards/python-style.md) | Black, isort, ruff, formatting |
| [Type Hints](./13-coding-standards/type-hints.md) | Strict typing, mypy |
| [Naming](./13-coding-standards/naming.md) | Variables, functions, classes, modules |
| [Comments](./13-coding-standards/comments.md) | When to comment, what to avoid |
| [Documentation](./13-coding-standards/documentation.md) | Docstring conventions |
| [Error Handling](./13-coding-standards/error-handling.md) | Exceptions vs. result types |
| [Imports](./13-coding-standards/imports.md) | Import order, forbidden imports |
| [Dependency Rules](./13-coding-standards/dependency-rules.md) | Layer dependency matrix |
| [Code Review Checklist](./13-coding-standards/code-review-checklist.md) | Reviewer guide |
| [Refactoring Rules](./13-coding-standards/refactoring-rules.md) | Safe refactor playbook |

### 14 — AI-Driven Development

| Document | Purpose |
|---|---|
| [Overview](./14-ai-driven-development/overview.md) | How we work with AI agents |
| [Collaboration Rules](./14-ai-driven-development/collaboration.md) | Conflict prevention |
| [Product Agent](./14-ai-driven-development/agent-product.md) | Requirements, stories, acceptance |
| [Architect Agent](./14-ai-driven-development/agent-architect.md) | Boundaries, contracts, ADRs |
| [Backend Agent](./14-ai-driven-development/agent-backend.md) | FastAPI, SQLAlchemy, Alembic |
| [Frontend Agent](./14-ai-driven-development/agent-frontend.md) | React PWA, a11y |
| [Database Agent](./14-ai-driven-development/agent-database.md) | Schema, migrations, perf |
| [Security Agent](./14-ai-driven-development/agent-security.md) | OWASP, threat model |
| [QA Agent](./14-ai-driven-development/agent-qa.md) | Test design, regression |
| [Performance Agent](./14-ai-driven-development/agent-performance.md) | Profiling, budgets |
| [DevOps Agent](./14-ai-driven-development/agent-devops.md) | CI/CD, infra |
| [Documentation Agent](./14-ai-driven-development/agent-documentation.md) | Docs & examples |
| [Code Review Agent](./14-ai-driven-development/agent-code-review.md) | Review checklist |

### 15 — Workflows

| Document | Purpose |
|---|---|
| [Feature Development](./15-workflows/feature-development.md) | End-to-end feature workflow |
| [Code Review](./15-workflows/code-review.md) | Review process & etiquette |
| [Incident Response](./15-workflows/incident-response.md) | On-call runbook |

### 16 — Quality Gates

| Document | Purpose |
|---|---|
| [Overview](./16-quality-gates/overview.md) | Gate philosophy |
| [PR Gates](./16-quality-gates/pr-gates.md) | Pre-merge requirements |
| [Release Gates](./16-quality-gates/release-gates.md) | Pre-deploy requirements |
| [Security Gates](./16-quality-gates/security-gates.md) | Security-specific checks |
| [Performance Gates](./16-quality-gates/performance-gates.md) | Performance budgets |

### 17 — Architecture Decision Records

| Document | Purpose |
|---|---|
| [Template](./17-adrs/template.md) | ADR structure |
| [Index](./17-adrs/index.md) | All ADRs |
| [ADR-0001](./17-adrs/0001-modular-monolith.md) | Modular monolith first |
| [ADR-0002](./17-adrs/0002-fastapi-postgres-redis.md) | Core backend stack |
| [ADR-0003](./17-adrs/0003-multi-tenant-strategy.md) | Multi-tenant strategy |
| [ADR-0004](./17-adrs/0004-event-bus-redis-streams.md) | Event bus choice |
| [ADR-0005](./17-adrs/0005-auth-model.md) | Authentication & token model |
| [ADR-0006](./17-adrs/0006-repository-pattern.md) | Persistence pattern |
| [ADR-0007](./17-adrs/0007-pwa-over-native.md) | PWA vs. native |

### 18 — Modules

| Document | Purpose |
|---|---|
| [Overview](./18-modules/README.md) | Module map & dependency rules |
| [auth](./18-modules/auth.md) | Identity, sessions, MFA |
| [customer](./18-modules/customer.md) | Member/customer profiles |
| [membership](./18-modules/membership.md) | Plans, subscriptions, renewals |
| [facility](./18-modules/facility.md) | Courts, pools, gyms, slots |
| [booking](./18-modules/booking.md) | Reservations, calendar, check-in |
| [payments](./18-modules/payments.md) | Pricing, invoices, refunds |
| [notifications](./18-modules/notifications.md) | SMS, email, push, in-app |
| [analytics](./18-modules/analytics.md) | Reports, dashboards, exports |
| [common](./18-modules/common.md) | Shared building blocks |

---

## Conventions used throughout this handbook

- **Code blocks** are real, runnable examples unless explicitly marked `# illustrative`.
- **Mermaid diagrams** render in GitHub, GitLab, VS Code, and most modern Markdown viewers.
- **Cross-references** are relative links — keep the folder structure intact.
- **Tables** summarize decisions, trade-offs, and checklists.
- **Callouts** use blockquotes:
  > **Rule** — a binding rule that must be followed unless an ADR explicitly overrides it.
  > **Guideline** — a strong recommendation; deviate only with justification.
  > **Anti-pattern** — something we explicitly avoid.
  > **Why** — the rationale for a non-obvious decision.

See [Conventions](./00-handbook/conventions.md) for the full conventions reference and [Glossary](./00-handbook/glossary.md) for shared terms.

---

## How this handbook evolves

- Changes are proposed via PR.
- Material changes (new principles, new rules) require sign-off from at least two of: Architect, Tech Lead, Security.
- Editorial changes (typos, broken links, examples) can be merged by any reviewer.
- Each ADR captures a meaningful decision; the [ADR index](./17-adrs/index.md) is the changelog of architecture.

---

## Status

| Section | Owner | Status |
|---|---|---|
| 01 Vision | Architect | Draft |
| 02 Architecture | Architect | Draft |
| 03 Domain | Domain Lead | Draft |
| 04 Backend | Backend Lead | Draft |
| 05 Frontend | Frontend Lead | Draft |
| 06 Database | Backend Lead | Draft |
| 07 Events | Architect | Draft |
| 08 APIs | Backend Lead | Draft |
| 09 Security | Security Lead | Draft |
| 10 Testing | QA Lead | Draft |
| 11 Performance | Performance Lead | Draft |
| 12 DevOps | DevOps Lead | Draft |
| 13 Coding Standards | Tech Lead | Draft |
| 14 AI-Driven Development | Architect | Draft |
| 15 Workflows | Tech Lead | Draft |
| 16 Quality Gates | QA Lead | Draft |
| 17 ADRs | Architect | Draft |
| 18 Modules | Module Owners | Draft |
