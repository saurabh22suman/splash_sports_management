# Security Testing

> This document covers our security testing strategy, including SAST, DAST, IAST, secrets scanning, and CI security gates.

We integrate security testing throughout the development lifecycle. Automated security tests run on every PR, with deeper scanning in the CI pipeline.

---

## Testing Layers

| Layer | Tool | When | Purpose |
|---|---|---|---|
| **SAST** | Semgrep | Every PR | Source code analysis |
| **DAST** | OWASP ZAP | Staging | Runtime testing |
| **Secrets** | gitleaks | Every PR | Detect leaked secrets |
| **Dependency** | pip-audit, npm audit | Every PR | Vulnerability scanning |
| **Container** | Trivy | Build | Image vulnerabilities |
| **IAST** | Contrast Security | Production | Runtime protection |

---

## SAST: Semgrep

```yaml
# .github/workflows/sast.yml
name: SAST Analysis

on: [push, pull_request]

jobs:
  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: returntocorp/semgrep-action@v1
        with:
          config: semgrep/security-rules
```

### Rules Example

```yaml
# semgrep/security-rules.yaml
rules:
  - id: python-sql-injection
    pattern: f"SELECT ... {$VAR} ..."
    message: Potential SQL injection
    severity: ERROR
    languages: [python]

  - id: hardcoded-password
    pattern: password = "..."
    message: Hardcoded password detected
    severity: ERROR
    languages: [python]
```

---

## DAST: OWASP ZAP

```yaml
# .github/workflows/dast.yml
name: DAST Scan

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  zap-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Start application
        run: docker-compose up -d
      - name: Run ZAP
        uses: zaproxy/action-baseline@v0.9.0
        with:
          target: 'http://localhost:8000'
```

---

## Secrets Scanning: gitleaks

```yaml
# .github/workflows/secrets-scan.yml
name: Secrets Scanning

on: [push, pull_request]

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## CI Security Gate

```yaml
# .github/workflows/security-gate.yml
name: Security Gate

on:
  push:
    branches: [main]

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Dependency scan
        run: |
          pip-audit -r requirements.txt || exit 1

      - name: Container scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'splashh/backend:${{ github.sha }}'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      - name: SAST scan
        run: |
          semgrep --config=auto --error --quiet || exit 1
```

---

## Test Categories

| Category | Tool | Fail Build |
|---|---|---|
| Secrets in code | gitleaks | Yes |
| Critical CVE | pip-audit | Yes |
| High CVE | Trivy | Yes |
| SQL injection | Semgrep | Yes |
| Hardcoded credentials | Semgrep | Yes |
| XSS patterns | Semgrep | Yes |
| DAST findings | OWASP ZAP | No (report only) |

---

## Cross-Reference

- [Dependency Scanning](dependency-scanning.md) — SCA
- [Container Security](container-security.md) — Image scanning
- [Secrets Management](secrets-management.md) — Secret handling
