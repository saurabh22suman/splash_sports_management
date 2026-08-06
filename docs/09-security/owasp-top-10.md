# OWASP Top 10 (2021)

> This document maps each OWASP Top 10 (2021) risk to our platform context, our specific mitigations, and our testing approach. We target full coverage of these risks in our security program.

The OWASP Top 10 is the industry-standard taxonomy for web application security risks. Every engineer must understand these risks and how they apply to the Splashh platform. This document provides specific, actionable guidance for each risk.

---

## A01:2021 Broken Access Control

**Description** — Users acting outside their intended permissions. Failures lead to unauthorized information disclosure, modification, or destruction of data or functionality.

### Our Context

- Multi-tenant SaaS: cross-tenant access is the highest-severity risk
- Role-based access: privilege escalation could allow members to access admin functions
- API-first: every endpoint must enforce authorization

### Mitigations

| Control | Implementation |
|---|---|
| RBAC | [Authorization & RBAC](authorization-rbac.md) — permission matrix, decorator enforcement |
| ABAC | Tenant context propagation, ownership checks |
| RLS | PostgreSQL Row-Level Security on every table |
| Default-deny | Explicit permission grants; no implicit permissions |

### Testing

- Automated API tests for each role-permission combination
- Manual penetration testing for BOLA scenarios
- RLS verification tests in CI

---

## A02:2021 Cryptographic Failures

**Description** — Failures related to cryptography, which often lead to sensitive data exposure. Includes improper key management, weak encryption, or lack of encryption.

### Our Context

- PII storage (member names, emails, phone numbers)
- Payment token storage (via third-party processor, not raw cards)
- Backup encryption for disaster recovery

### Mitigations

| Control | Implementation |
|---|---|
| TLS 1.3 | All external communication encrypted |
| Field-level encryption | pgcrypto for PII at rest |
| Key hierarchy | KMS → DEK → encrypted data |
| HSM | Signing keys in cloud HSM (AWS KMS) |

See [Encryption](encryption.md) for details.

### Testing

- TLS configuration scanning (testssl, nmap)
- Encryption verification in data layer tests
- Key rotation verification

---

## A03:2021 Injection

**Description** — Applications interpret untrusted data as code, most commonly SQL injection, but also OS command injection, LDAP, XPath, etc.

### Our Context

- SQL injection is the primary risk given our PostgreSQL backend
- User input flows through Pydantic validation → SQLAlchemy ORM → parameterized queries

### Mitigations

| Control | Implementation |
|---|---|
| Parameterized queries | SQLAlchemy with bound parameters, no string interpolation |
| Input validation | Pydantic schemas with allow-lists |
| Stored procedures | Used sparingly; only when ORM is insufficient |
| ORM abstraction | SQLAlchemy abstracts away raw SQL |

See [SQL Injection](sql-injection.md) for details.

### Testing

- SQLMap automated scanning
- Code review checklist: no f-strings in SQL
- Integration tests with injection payloads

---

## A04:2021 Insecure Design

**Description** — Risks arising from missing or ineffective security controls. This is a new category focused on design flaws rather than implementation flaws.

### Our Context

- Multi-tenant data model design
- Payment flow design (tokenization, not storing cards)
- Authentication flow design (short-lived tokens, rotation)

### Mitigations

| Control | Implementation |
|---|---|
| Threat modeling | [Threat Modeling](threat-modeling.md) — STRIDE per feature |
| Security architecture review | Required for new features |
| Secure design patterns | Documented in handbook |
| Code review | Security-aware reviewers |

### Testing

- Architecture review in design phase
- Threat model documentation
- Security design review checklist

---

## A05:2021 Security Misconfiguration

**Description** — Insecure configurations at any level: missing security hardening, unnecessary features enabled, default credentials, verbose error messages.

### Our Context

- FastAPI configuration
- PostgreSQL configuration
- Redis configuration
- Container image configuration
- Cloud infrastructure

### Mitigations

| Control | Implementation |
|---|---|
| Hardened base images | Distroless, minimal attack surface |
| Security headers | Strict CSP, X-Frame-Options, HSTS |
| Error handling | Generic error messages in production |
| Configuration validation | Schema validation for all config |
| Automated scanning | Trivy for container vulnerabilities |

See [Container Security](container-security.md).

### Testing

- CIS benchmark scanning
- Configuration review in CI
- Penetration testing for info disclosure

---

## A06:2021 Vulnerable and Outdated Components

**Description** — Using components with known vulnerabilities. The platform is vulnerable if dependencies are not monitored and updated.

### Our Context

- Python backend (FastAPI, SQLAlchemy, Pydantic)
- React frontend
- Infrastructure (containers, Redis, PostgreSQL)

### Mitigations

| Control | Implementation |
|---|---|
| SCA scanning | Dependabot/Renovate for dependency updates |
| SBOM | CycloneDX generation |
| Vulnerability SLAs | Critical: 7 days, High: 30 days |
| Private package allowlist | Only approved packages |
| License compliance | FOSSA or equivalent |

See [Dependency Scanning](dependency-scanning.md).

### Testing

- Automated Dependabot PRs reviewed weekly
- CI blocks on critical CVEs
- Quarterly dependency audit

---

## A07:2021 Identification and Authentication Failures

**Description** — Weaknesses in authentication mechanisms: credential stuffing, session fixation, improper session handling.

### Our Context

- JWT-based authentication
- Refresh token rotation
- MFA for admins
- Password breach detection (HIBP)

### Mitigations

| Control | Implementation |
|---|---|
| Argon2id | Password hashing, not MD5/SHA |
| Short-lived tokens | 15-minute access token expiry |
| Token rotation | Every refresh rotates the token |
| MFA | TOTP required for TenantAdmin |
| Breach detection | HIBP k-anonymity check |
| Account lockout | 10 attempts, 15-minute lockout |

See [Authentication](authentication.md), [JWT Best Practices](jwt-best-practices.md).

### Testing

- Credential stuffing simulation
- Token expiry verification
- MFA bypass attempts

---

## A08:2021 Software and Data Integrity Failures

**Description** — Risks from code and infrastructure that does not protect against integrity violations: CI/CD pipeline attacks, insecure deserialization, supply chain attacks.

### Our Context

- CI/CD pipeline (GitHub Actions)
- Third-party dependencies
- Container image supply chain

### Mitigations

| Control | Implementation |
|---|---|
| Signed commits | GPG/SSH signing required |
| Signed images | cosign for container signatures |
| SLSA | Supply-chain security levels |
| Dependency pinning | Lock files, no floating versions |
| Private registry | Approved package sources |

See [Supply Chain](supply-chain.md).

### Testing

- cosign verification in CI
- SLSA level verification
- Dependency integrity checks

---

## A09:2021 Security Logging and Monitoring Failures

**Description** — Insufficient logging, detection, monitoring, and active response. Breaches cannot be detected without logging and monitoring.

### Our Context

- Authentication events
- Authorization failures
- Payment events
- Data exports

### Mitigations

| Control | Implementation |
|---|---|
| Audit logging | Append-only, tamper-evident |
| Structured logging | JSON with correlation IDs |
| SIEM integration | Export to security monitoring |
| Alerting | Anomaly detection |
| Retention | 7 years for compliance |

See [Audit Logging](audit-logging.md), [Incident Response](incident-response.md).

### Testing

- Log completeness verification
- Alert testing
- SIEM integration tests

---

## A10:2021 Server-Side Request Forgery (SSRF)

**Description** — Fetching remote resources without validating user-supplied URLs. Enables scanning internal networks, cloud metadata services.

### Our Context

- Webhook delivery to external systems
- URL-based integrations (future)
- CDN configuration

### Mitigations

| Control | Implementation |
|---|---|
| Egress allowlist | Only approved external domains |
| Block internal IPs | Reject requests to 10.x, 192.168.x, 169.254.x (IMDS) |
| DNS pinning | Resolve once, use only that IP |
| URL validation | Strict URL parsing, no redirect following |

See [SSRF](ssrf.md).

### Testing

- SSRF payload scanning
- Internal network access tests
- Metadata service access tests

---

## OWASP Risk Rating Summary

| Risk | Likelihood | Impact | Priority | Status |
|---|---|---|---|---|
| A01: Broken Access Control | High | Critical | P0 | Mitigated |
| A02: Cryptographic Failures | Medium | Critical | P1 | Mitigated |
| A03: Injection | Low | Critical | P1 | Mitigated |
| A04: Insecure Design | Medium | High | P1 | In Progress |
| A05: Security Misconfiguration | Medium | High | P1 | Mitigated |
| A06: Vulnerable Components | High | High | P0 | Mitigated |
| A07: Auth Failures | High | High | P0 | Mitigated |
| A08: Integrity Failures | Medium | High | P1 | Mitigated |
| A09: Logging Failures | Medium | High | P1 | Mitigated |
| A10: SSRF | Low | High | P2 | Mitigated |

---

## Cross-Reference

- [OWASP ASVS](owasp-asvs.md) — Comprehensive verification standard
- [Security Testing](security-testing.md) — Automated scanning
- [Penetration Testing](penetration-testing.md) — Annual third-party assessment
