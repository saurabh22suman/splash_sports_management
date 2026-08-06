# Glossary

> Shared vocabulary used across the handbook. If a term is not defined here, it is either self-evident or defined in the document where it is used.

---

## A

**Aggregate**
A cluster of domain objects treated as a single unit for data changes. Has one aggregate root and a consistency boundary. See [Aggregates](../03-domain/aggregates.md).

**ADR (Architecture Decision Record)**
A short document capturing a significant architectural decision, its context, consequences, and alternatives. See [ADRs](../17-adrs/index.md).

**API Contract**
The agreed-upon shape of an API between producer and consumer, expressed as an OpenAPI document or event schema. See [API Authentication](../08-apis/authentication.md) and [Event Catalog](../07-events/event-catalog.md).

**ASVS**
OWASP Application Security Verification Standard. See [OWASP ASVS](../09-security/owasp-asvs.md).

## B

**BDD (Behavior-Driven Development)**
Development methodology where scenarios are written in natural language (Given/When/Then) and serve as executable tests. See [BDD](../10-testing/bdd.md).

**Bounded Context**
An explicit boundary within which a domain model is consistent. See [Bounded Contexts](../03-domain/bounded-contexts.md).

**BFF (Backend for Frontend)**
A server-side component tailored to the needs of a specific frontend (admin PWA, customer PWA). See [Container Diagram](../02-architecture/container-diagram.md).

## C

**C4 Model**
A hierarchical way to describe architecture using Context, Container, Component, and Code diagrams. See [System Context](../02-architecture/system-context.md).

**CQRS (Command Query Responsibility Segregation)**
A pattern that separates reads (queries) from writes (commands), often using different models. We use a **light** form of CQRS in read-heavy areas like reporting.

## D

**DDD (Domain-Driven Design)**
A methodology for designing software around the domain model. See [Engineering Philosophy](../01-vision/principles.md).

**DLQ (Dead Letter Queue)**
A queue that receives messages that failed processing after the maximum retry count. See [Retry & Failure](../07-events/retry-failure.md).

**DRY (Don't Repeat Yourself)**
A principle that every piece of knowledge has a single, authoritative representation. See [Engineering Philosophy](../01-vision/principles.md).

## E

**Eventual Consistency**
A consistency model where replicas converge over time, accepting temporary divergence. See [Transactions & Concurrency](../04-backend/transactions-concurrency.md).

## G

**GLBA / GDPR / DPDPA**
Regulations governing data privacy and security. We comply with applicable regulations in regions we operate in. See [Compliance & Privacy](../09-security/overview.md).

## H

**HPA (Horizontal Pod Autoscaler)**
Kubernetes-native auto-scaling by replica count. See [Scaling Strategy](../02-architecture/scaling-strategy.md).

## I

**Idempotency**
The property that an operation produces the same result regardless of how many times it is applied. See [Idempotency](../04-backend/idempotency.md).

**Invariant**
A business rule that must always hold true. See [Module Overviews](../18-modules/README.md).

## J

**JWT (JSON Web Token)**
A compact, signed token format used for stateless authentication. See [JWT Best Practices](../09-security/jwt-best-practices.md).

## K

**KISS (Keep It Simple, Stupid)**
A principle favoring the simplest solution that works. See [Engineering Philosophy](../01-vision/principles.md).

## L

**Linting**
Static analysis to enforce style and catch common bugs. See [Python Style](../13-coding-standards/python-style.md).

## M

**Modular Monolith**
A single deployable application structured as clearly separated modules. See [ADR-0001](../17-adrs/0001-modular-monolith.md).

**MFA (Multi-Factor Authentication)**
Authentication requiring more than one factor. See [MFA](../09-security/mfa.md).

## N

**N+1 Problem**
A performance anti-pattern where fetching N records causes N additional queries. See [Performance Optimization](../06-database/performance-optimization.md).

## O

**OTel (OpenTelemetry)**
A vendor-neutral observability framework for traces, metrics, and logs. See [Tracing](../12-devops/tracing.md).

**OWASP**
Open Worldwide Application Security Project. See [OWASP Top 10](../09-security/owasp-top-10.md).

## P

**PII (Personally Identifiable Information)**
Any data that can identify an individual. Treated as sensitive. See [Audit Logging](../09-security/audit-logging.md).

**PITR (Point-in-Time Recovery)**
The ability to restore a database to a specific point in time. See [Backups](../06-database/backups.md).

**PWA (Progressive Web App)**
A web application that uses modern capabilities to deliver app-like experiences. See [PWA Strategy](../05-frontend/pwa-strategy.md).

## Q

**QPS (Queries Per Second)**
A throughput metric. See [Response Time Goals](../11-performance/response-time-goals.md).

## R

**RBAC (Role-Based Access Control)**
An authorization model based on roles assigned to users. See [Authorization & RBAC](../09-security/authorization-rbac.md).

**RPO (Recovery Point Objective)**
The maximum acceptable data loss measured in time. See [Disaster Recovery](../02-architecture/disaster-recovery.md).

**RTO (Recovery Time Objective)**
The maximum acceptable downtime after a disaster. See [Disaster Recovery](../02-architecture/disaster-recovery.md).

## S

**SAST / DAST / IAST**
Static, Dynamic, and Interactive Application Security Testing. See [Security Testing](../09-security/security-testing.md).

**SLO (Service Level Objective)**
A target reliability metric, e.g., 99.9% of requests succeed. See [Response Time Goals](../11-performance/response-time-goals.md).

**SOLID**
Five object-oriented design principles (Single responsibility, Open/closed, Liskov, Interface segregation, Dependency inversion). See [Engineering Philosophy](../01-vision/principles.md).

## T

**Tenant**
An organization (e.g., a sports club) using our SaaS. Data is isolated per tenant. See [Tenant Isolation](../09-security/tenant-isolation.md).

**TDD (Test-Driven Development)**
Red → Green → Refactor. See [TDD Handbook](../10-testing/tdd-handbook.md).

## U

**Uptime**
The percentage of time a system is operational. Target: 99.9% (≈ 8.7 hours/year of downtime). See [Non-functional Goals](#).

## V

**Versioning**
The strategy for evolving APIs without breaking clients. See [API Versioning](../08-apis/versioning.md).

## W

**WCAG**
Web Content Accessibility Guidelines. We target WCAG 2.2 AA. See [Accessibility](../05-frontend/accessibility.md).

## Y

**YAGNI (You Aren't Gonna Need It)**
A principle against building features until they are actually needed. See [Engineering Philosophy](../01-vision/principles.md).

## Z

**Zero Trust**
A security model assuming no implicit trust and verifying every request. See [Zero Trust](../09-security/zero-trust.md).
