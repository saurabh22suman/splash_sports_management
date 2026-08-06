# Security Overview

> This document establishes the security posture, principles, and organizational structure for the Splashh Sports Club Management Platform. It is the foundation upon which all other security documentation builds.

The Splashh platform handles sensitive data: personal identity information (PII) of club members, payment card data (via tokenized third-party processors), and financial transactions subject to Indian regulatory frameworks. A security breach would cause material harm to our tenants and their members, expose us to regulatory penalties under DPDPA and PCI-DSS, and destroy trust irreparably. Security is not a feature — it is a non-functional requirement embedded in every architectural decision.

---

## Security Posture

We target **OWASP ASVS Level 2** verification. Level 2 is appropriate for applications that handle sensitive data and require moderate assurance — the right threshold for a multi-tenant SaaS platform processing payments. Level 3 (comprehensive) is reserved for high-value targets in banking and defense; the additional overhead does not justify the marginal security gain for our threat model.

| Posture Element | Target | Rationale |
|---|---|---|
| ASVS Level | 2 (2024) | Balanced assurance for SaaS with payment data |
| Vulnerability SLA | Critical: 24h, High: 7d, Medium: 30d | Aligned with industry standards |
| Pen Testing | Annual third-party | External validation of internal controls |
| Encryption | TLS 1.3 in transit, AES-256 at rest | Industry baseline |
| Audit Retention | 7 years | DPDPA + tax record requirements |

> **Why ASVS Level 2** — Level 2 requires verification of authentication mechanisms, session management, access control, input/output validation, and cryptographic practices. It provides coverage for our threat model without the overhead of Level 3's additional requirements for tamper-resistant designs, detailed logging, and formal verification that we do not need at our current scale.

---

## Security Principles

Our security philosophy derives from three foundational principles:

### 1. Defense in Depth

No single control is trusted. Authentication is verified at the API gateway, within each service, and at the database layer. Tenant isolation is enforced at the application layer, the ORM, and via PostgreSQL Row-Level Security (RLS). This layered approach ensures that a single failure does not result in data exposure.

### 2. Assume Breach

We design as if every network boundary is compromised. Internal services authenticate and authorize every request. We do not trust the internal network. We do not trust other services. Every request carries its own credentials. This principle drives our adoption of zero-trust architecture between services.

### 3. Least Privilege

Every component, identity, and user operates with the minimum permissions required. Database users have only the privileges their application role requires. Service accounts can access only the resources they need. Users see only the data their tenant owns. This principle limits blast radius when any single component is compromised.

---

## Threat Model Summary

We have modeled threats across four attack surfaces:

| Attack Surface | Primary Threats | Key Mitigations |
|---|---|---|
| Authentication | Credential stuffing, token theft, session hijacking | MFA, short-lived tokens, breach detection |
| Authorization | Privilege escalation, BOLA, cross-tenant access | RBAC + ABAC, RLS, explicit tenant filtering |
| Data Layer | SQL injection, data exfiltration | Parameterized queries, encryption, RLS |
| External Integrations | SSRF, webhook tampering, supply chain | Egress allowlists, signature verification, SCA |

The highest-probability threats are credential-based attacks (credential stuffing, phishing) and authorization failures (BOLA, cross-tenant leakage). Our security investments prioritize these areas.

---

## Security Responsibilities

Security is a shared responsibility across the organization:

| Role | Responsibilities |
|---|---|
| **Security Lead** | Threat model maintenance, security review sign-off, incident response lead, compliance oversight |
| **Engineering Lead** | Ensuring security is embedded in design, security-aware code review |
| **All Engineers** | Following secure coding practices, identifying and reporting security issues |
| **DevOps** | Infrastructure security, secrets management, monitoring, incident detection |
| **Product** | Privacy-by-design in features, data minimization in requirements |

### Security Review Gate

Every PR that touches authentication, authorization, payment processing, PII handling, or tenant-scoped data requires a **security review**. The Security Agent in our CI pipeline performs automated checks (SAST, dependency scanning, secrets detection), but human review is mandatory for security-sensitive changes.

> **Rule** — No code merging for security-sensitive changes without explicit security approval from the Security Lead or a designated senior engineer with security expertise.

---

## Cross-Reference

- [Authentication](authentication.md) — Identity verification and token management
- [Authorization & RBAC](authorization-rbac.md) — Role-based access control model
- [Tenant Isolation](tenant-isolation.md) — Multi-tenant data separation
- [OWASP Top 10](owasp-top-10.md) — Coverage of web application risks
- [Incident Response](incident-response.md) — Detection, containment, and recovery from security events
- [Compliance & Privacy](compliance-privacy.md) — DPDPA, PCI-DSS, RBI alignment
