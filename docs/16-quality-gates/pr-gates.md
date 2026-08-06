# PR Gates

> Pre-merge quality requirements.

PR gates run on every pull request before it can be merged. These gates ensure code quality, security, and test coverage meet our standards.

---

## Gate List

| Gate | Command | Threshold | Blocking |
|---|---|---|---|
| Lint | `ruff check .` | 0 errors | Yes |
| Type Check | `mypy .` | 0 errors | Yes |
| Unit Tests | `pytest tests/unit` | 100% pass | Yes |
| Test Coverage | `pytest --cov` | >80% overall | Yes |
| Security Scan | `bandit -r .` | 0 critical/high | Yes |
| Secrets Scan | `trufflehog .` | 0 findings | Yes |
| Architecture Tests | `pytest tests/arch` | Pass | Yes |
| Docs Check | `lychee docs/` | 0 broken links | No |

---

## Configuration

### CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on: [pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v1

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v1
      - run: pip install mypy && mypy .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pytest pytest-cov && pytest --cov --cov-fail-under=80

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install bandit && bandit -r . -ll
      - run: pip install trufflehog && trufflehog .
```

---

## Coverage Requirements

| Module | Minimum Coverage |
|---|---|
| Domain (entities, value objects) | 95% |
| Services (application logic) | 90% |
| API (routes, schemas) | 80% |
| Infrastructure | 70% |

---

## Architecture Tests

Architecture tests verify module boundaries and dependency rules.

```python
# tests/arch/test_module_dependencies.py
import pytest

class TestModuleDependencies:
    """Verify module dependency rules."""

    def test_must_not_import_auth_into_customer(self):
        """Customer module should not depend on auth internals."""
        from pathlib import Path

        customer_path = Path("app/customer")
        auth_internals = list(customer_path.rglob("*.py"))

        for file in auth_internals:
            content = file.read_text()
            assert "app.auth" not in content or "app.auth.schemas" in content

    def test_must_not_use_raw_sql(self):
        """No raw SQL in services."""
        service_files = Path("app").glob("*/service.py")

        for file in service_files:
            content = file.read_text()
            assert "text(" not in content  # SQLAlchemy raw SQL
```

---

## Common Failures

| Failure | Cause | Fix |
|---|---|---|
| Lint errors | Formatting, unused imports | Run `ruff format && ruff check --fix` |
| Type errors | Missing type hints | Add type annotations |
| Test failures | Logic bugs | Fix implementation |
| Coverage <80% | Missing tests | Add test cases |
| Security findings | Vulnerable code | Refactor to fix |
| Secrets found | API key committed | Remove secret, rotate |

---

## Related Documents

- [Quality Gates Overview](./overview.md)
- [Release Gates](./release-gates.md)
- [Code Review Workflow](../15-workflows/code-review.md)
