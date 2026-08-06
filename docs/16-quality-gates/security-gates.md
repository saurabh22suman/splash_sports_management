# Security Gates

> Security-specific quality requirements.

Security gates prevent vulnerable code from reaching production. These gates are non-negotiable.

---

## Gate List

| Gate | Tool | Threshold | Stage |
|---|---|---|---|
| SAST | Bandit, Semgrep | 0 critical/high | PR |
| SCA | Safety, Dependabot | 0 critical | PR + Release |
| Secrets Scan | TruffleHog, Gitleaks | 0 findings | PR |
| Container Scan | Trivy | 0 critical | Release |
| Dependency Freshness | Dependabot | <30 days | PR |
| Pen Test | Annual | No critical | Annual |

---

## SAST (Static Application Security Testing)

```bash
# Run Bandit
bandit -r app/ -f json -o bandit-report.json

# Run Semgrep
semgrep --config=auto --json --output=semgrep-report.json app/
```

---

## SCA (Software Composition Analysis)

```bash
# Check for vulnerabilities
pip freeze | safety check --json > safety-report.json

# Check dependencies
pip install pip-audit
pip-audit --format=json > pip-audit-report.json
```

---

## Secrets Scanning

```bash
# TruffleHog
trufflehog filesystem app/ --json > secrets-report.json

# Gitleaks
gitleaks detect --source=. --report-format=json --report=gitleaks-report.json
```

---

## Container Scanning

```dockerfile
# Dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . /app
CMD ["uvicorn", "main:app"]
```

```bash
# Scan image
trivy image splash-backend:latest --severity CRITICAL,HIGH --exit-code 1
```

---

## Critical CVE Block

> **Rule** — Any critical CVE blocks deployment. High CVEs require security team approval.

| CVE Severity | Gate Action |
|---|---|
| Critical | Block deployment |
| High | Block deployment (requires approval) |
| Medium | Warning (fix in next sprint) |
| Low | Info (fix when possible) |

---

## Penetration Testing

| Frequency | Scope | Findings |
|---|---|---|
| Annual | Full application | All critical/high must be fixed |
| Quarterly | High-risk areas | All critical must be fixed |
| After major changes | Changed components | All critical must be fixed |

---

## Related Documents

- [Security Overview](../09-security/overview.md)
- [OWASP Top 10](../09-security/owasp-top-10.md)
- [Dependency Scanning](../09-security/dependency-scanning.md)
- [Container Security](../09-security/container-security.md)
