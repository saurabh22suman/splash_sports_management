# Penetration Testing

> This document details our annual third-party penetration testing program, including scope, methodology, SLA for critical findings, and retest requirements.

Penetration testing provides external validation of our security controls. We engage qualified third-party testers annually to assess our attack surface.

---

## Annual Pen Test Program

| Aspect | Requirement |
|---|---|
| Frequency | Annual |
| Provider | Qualified external firm (OWASP, CREST, or equivalent) |
| Scope | All production applications, APIs, infrastructure |
| Timing | Q4 (before annual compliance review) |

---

## Scope

### In Scope

- Public API endpoints (REST)
- Web application (customer PWA)
- Admin console
- Authentication flows
- Payment processing
- Internal APIs (if accessible)

### Out of Scope

- Social engineering
- Physical security
- DoS attacks (rate-limited)
- Third-party vendor systems

---

## Testing Methodology

| Phase | Activities |
|---|---|
| 1. Reconnaissance | OSINT, subdomain enumeration |
| 2. Mapping | Application mapping, endpoint discovery |
| 3. Vulnerability | Manual testing, automated scanning |
| 4. Exploitation | Attempt to exploit findings |
| 5. Reporting | Detailed findings with PoC |

---

## Critical Findings SLA

| Severity | Fix SLA | Retest SLA |
|---|---|---|
| Critical | 7 days | 14 days |
| High | 30 days | 45 days |
| Medium | 90 days | 120 days |
| Low | Next release | Next release |

---

## Cross-Reference

- [Security Testing](security-testing.md) — Automated testing
- [OWASP Top 10](owasp-top-10.md) — Risk coverage
- [Incident Response](incident-response.md) — Response to findings
