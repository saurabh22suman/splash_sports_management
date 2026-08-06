# OWASP ASVS Verification

> This document details our OWASP Application Security Verification Standard (ASVS) alignment, target level, covered chapters, gaps, and remediation roadmap.

The OWASP ASVS provides a comprehensive framework for verifying application security. We target **Level 2** verification, which is appropriate for applications that handle sensitive data and require moderate assurance.

---

## ASVS Level Selection

| Level | Description | Our Context |
|---|---|---|
| **Level 1** | Basic — for low-risk applications | Insufficient for payment-processing SaaS |
| **Level 2** | Standard — for most web applications | **Our target** — appropriate for multi-tenant SaaS |
| **Level 3** | Comprehensive — for high-assurance systems | Overkill for our current threat model |

> **Why Level 2** — Level 2 requires verification of authentication, session management, access control, input validation, error handling, data protection, and cryptographic practices. This aligns with our threat model without the overhead of Level 3's formal methods, source code review, and detailed penetration testing requirements.

---

## Chapter Coverage

| Chapter | Level 2 Requirement | Our Status | Evidence |
|---|---|---|---|
| **V1: Architecture** | All requirements | Complete | Documented in handbook, threat model |
| **V2: Authentication** | All requirements | Complete | [Authentication](authentication.md), MFA policy |
| **V3: Session Management** | All requirements | Complete | [JWT Best Practices](jwt-best-practices.md), token rotation |
| **V4: Access Control** | All requirements | Complete | [Authorization & RBAC](authorization-rbac.md), RLS |
| **V5: Input Validation** | All requirements | Complete | [Input Validation](input-validation.md), Pydantic |
| **V6: Output Encoding** | All requirements | Complete | [Output Encoding](output-encoding.md), React escaping |
| **V7: Error Handling** | All requirements | Complete | Generic errors, logging, no stack traces |
| **V8: Data Protection** | All requirements | Complete | [Encryption](encryption.md), TLS, field encryption |
| **V9: Communication Security** | All requirements | Complete | TLS 1.3, certificate pinning |
| **V10: Malicious Code** | All requirements | Complete | No dynamic code execution, dependency scanning |
| **V11: Business Logic** | All requirements | Partial | Threat model covers critical flows |
| **V12: File Upload** | All requirements | Complete | MIME validation, size limits, storage隔离 |
| **V13: API Security** | All requirements | Complete | [API Security](api-security.md), schema validation |
| **V14: Configuration** | All requirements | Complete | Hardened images, minimal features |

---

## Detailed Gap Analysis

### V1: Architecture (Complete)

- [x] Security architecture documented
- [x] Threat model maintained
- [x] Security requirements in user stories
- [x] Component dependency documentation

### V2: Authentication (Complete)

- [x] Password complexity requirements
- [x] Account lockout after failed attempts
- [x] Password breach detection (HIBP)
- [x] MFA for privileged accounts
- [x] Secure password reset flow

### V3: Session Management (Complete)

- [x] JWT with short expiry (15 min)
- [x] Refresh token rotation
- [x] Secure token storage
- [x] Session invalidation on logout

### V4: Access Control (Complete)

- [x] RBAC implemented
- [x] Default-deny policy
- [x] Tenant isolation (RLS)
- [x] Ownership checks

### V5: Input Validation (Complete)

- [x] Pydantic validation at API boundary
- [x] Allow-list over deny-list
- [x] Length limits
- [x] File upload validation

### V6: Output Encoding (Complete)

- [x] React automatic escaping
- [x] CSP headers
- [x] No dangerouslySetInnerHTML without review
- [x] DOMPurify for user HTML

### V7: Error Handling (Complete)

- [x] Generic error messages in production
- [x] Stack traces only in development
- [x] Structured error logging

### V8: Data Protection (Complete)

- [x] TLS in transit
- [x] Field-level encryption for PII
- [x] Key hierarchy (KMS → DEK)
- [x] Backup encryption

### V9: Communication Security (Complete)

- [x] TLS 1.3 only
- [x] Modern cipher suites
- [x] HSTS enabled

### V10: Malicious Code (Complete)

- [x] No eval() or dynamic code
- [x] Dependency scanning
- [x] SBOM generation

### V11: Business Logic (Partial)

- [x] Threat model for critical flows
- [ ] Formal abuse case testing
- [ ] Business logic test cases in suite

### V12: File Upload (Complete)

- [x] MIME type validation
- [x] File size limits
- [x] Magic byte verification
- [x] Separate storage bucket

### V13: API Security (Complete)

- [x] BOLA protection
- [x] Rate limiting
- [x] Schema validation
- [x] No over-fetching

### V14: Configuration (Complete)

- [x] Hardened container images
- [x] Minimal feature set
- [x] Configuration validation

---

## Roadmap

| Gap | Priority | Effort | Target Date |
|---|---|---|---|
| Formal abuse case testing | P2 | Medium | Q1 2025 |
| Business logic test suite | P2 | Medium | Q1 2025 |
| Advanced threat model updates | P1 | Low | Q4 2024 |
| ASVS Level 3 for auth module | P2 | High | 2025 |

---

## Verification Process

We verify ASVS compliance through:

1. **Automated tests** — Security-specific test cases in CI
2. **Code review** — Security checklist for PRs
3. **Penetration testing** — Annual third-party assessment
4. **Architecture review** — Security design review for new features

---

## Cross-Reference

- [OWASP Top 10](owasp-top-10.md) — Risk-specific guidance
- [Security Testing](security-testing.md) — Automated verification
- [Penetration Testing](penetration-testing.md) — External validation
- [Threat Modeling](threat-modeling.md) — Design-phase security
