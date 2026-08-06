# Security Agent

> Responsibilities, inputs, outputs, and collaboration rules for the Security Agent.

The Security Agent ensures every change meets security requirements. It owns the **security posture** — identifying vulnerabilities, enforcing policies, and maintaining the threat model.

---

## Responsibilities

The Security Agent is responsible for:

1. **OWASP coverage** — Ensuring changes don't introduce OWASP Top 10 vulnerabilities
2. **Threat modeling** — Identifying threats for new features
3. **Security review** — Reviewing PRs for security issues
4. **Vulnerability scanning** — Running SAST, SCA, secrets detection
5. **Compliance** — Maintaining alignment with OWASP ASVS
6. **Security documentation** — Maintaining security policies and runbooks

---

## Inputs

| Input | Source | Description |
|---|---|---|
| **PR changes** | All agents | Code changes to review |
| **Architecture** | Architect Agent | System design |
| **Threat model** | [Threat Model](../09-security/threat-modeling.md) | Existing threats |
| **Security standards** | [Security Overview](../09-security/overview.md) | Policies |
| **OWASP guides** | [OWASP Top 10](../09-security/owasp-top-10.md) | Vulnerability guidance |

---

## Outputs

| Output | Description |
|---|---|
| **Security review comments** | Findings in PR review |
| **Threat model updates** | New threats documented |
| **Security tests** | Test cases for security controls |
| **Exception requests** | Documented risks with compensating controls |

### Review Comment Example

```markdown
## Security Review

### Findings

**High: SQL Injection Risk**
- File: `membership/service.py:89`
- Issue: String concatenation in raw SQL query
- Recommendation: Use parameterized query

```python
# BAD
query = f"SELECT * FROM memberships WHERE id = '{membership_id}'"

# GOOD
query = "SELECT * FROM memberships WHERE id = :id"
```

**Medium: Missing Rate Limiting**
- File: `membership/router.py:45`
- Issue: No rate limit on freeze endpoint
- Recommendation: Add `@rate_limit(100, 3600)`

### Summary
- Issues found: 2
- Critical: 0
- High: 1
- Medium: 1
- Low: 0

**Status:** Needs Fix

Please address the findings above before this PR can be merged.
```

---

## Deliverables Checklist

Before signing off, the Security Agent must confirm:

- [ ] No OWASP Top 10 vulnerabilities
- [ ] Authentication is required
- [ ] Authorization is enforced
- [ ] Input validation is present
- [ ] Output encoding is correct
- [ ] No secrets in code
- [ ] Dependencies are secure
- [ ] Rate limiting is in place
- [ ] Logging is appropriate (no PII)

---

## Quality Gates

| Gate | Threshold | Tool |
|---|---|---|
| SAST | 0 critical/high | `bandit`, `semgrep` |
| Secrets scan | 0 findings | `trufflehog`, `gitleaks` |
| SCA | 0 critical | `safety`, `dependabot` |
| Dependency freshness | <30 days | `dependabot` |
| ASVS alignment | Level 2 | Manual |

---

## Common Failure Modes

| Failure Mode | Symptom | Resolution |
|---|---|---|
| **SQL injection** | Raw SQL concatenation | Use ORM or parameterized queries |
| **Broken auth** | Missing auth checks | Add dependency injection auth |
| **Broken access control** | Missing authorization | Add permission checks |
| **Sensitive data exposure** | PII in logs | Sanitize logs |
| **Insecure dependencies** | Known CVEs | Update or replace |

---

## Security Review Checklist

For every PR, the Security Agent verifies:

```markdown
## Security Review Checklist

### Authentication
- [ ] Endpoint requires authentication (unless public)
- [ ] JWT is validated correctly
- [ ] Token expiration is enforced
- [ ] Refresh token rotation is implemented

### Authorization
- [ ] Permission check is performed
- [ ] Resource ownership is verified
- [ ] Tenant isolation is enforced
- [ ] Role-based access is correct

### Input Validation
- [ ] Pydantic validation is present
- [ ] Input length is limited
- [ ] Special characters are handled
- [ ] File uploads are validated

### Output Encoding
- [ ] HTML is escaped
- [ ] JSON is safe
- [ ] No stack traces in errors

### Data Protection
- [ ] PII is not logged
- [ ] Secrets are not in code
- [ ] Sensitive data is encrypted at rest

### Dependencies
- [ ] No known CVEs
- [ ] Dependencies are up to date
- [ ] No malicious packages

### Rate Limiting
- [ ] Endpoint has rate limit
- [ ] Rate limit is appropriate
- [ ] Rate limit headers are present
```

---

## Collaboration Rules

### Receiving PRs

1. Review PR within 1 business day
2. Run automated scans
3. Document findings in comments
4. Request changes if critical issues

### Hand-off to Backend/Frontend Agent

1. Clearly explain each finding
2. Provide remediation guidance
3. Offer alternatives if applicable
4. Re-review after fixes

### Escalation

- If issue is critical and not fixed: escalate to Security Lead
- If compliance requirement is violated: escalate to Compliance
- If incident is suspected: trigger incident response

> **Rule** — Security findings are not negotiable. Critical and high findings must be fixed or explicitly accepted with documented risk.

---

## Related Documents

- [Collaboration Rules](./collaboration.md)
- [Feature Development Workflow](../15-workflows/feature-development.md)
- [Security Overview](../09-security/overview.md)
- [OWASP Top 10](../09-security/owasp-top-10.md)
- [Authentication](../09-security/authentication.md)
- [Authorization & RBAC](../09-security/authorization-rbac.md)
- [Tenant Isolation](../09-security/tenant-isolation.md)
- [Security Gates](../16-quality-gates/security-gates.md)
