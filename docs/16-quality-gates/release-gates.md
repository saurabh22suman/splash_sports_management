# Release Gates

> Pre-deploy quality requirements.

Release gates run before code is deployed to staging or production. These gates verify the system works end-to-end and is ready for users.

---

## Gate List

| Gate | Threshold | Tool | Blocking |
|---|---|---|---|
| Full Test Suite | 100% pass | pytest | Yes |
| Smoke Tests | 100% pass | Playwright | Yes |
| Security Scan Clean | 0 critical/high | Snyk, Dependabot | Yes |
| Perf Budgets Met | Pass | Lighthouse, k6 | Yes |
| SLO Budget Check | <50% consumed | Prometheus | Yes |
| Change Approval | Approved | Jira/GitHub | Yes (prod) |

---

## Smoke Tests

Smoke tests verify critical functionality works.

```python
# tests/e2e/smoke.py
import pytest
from playwright.sync_api import Page, expect

def test_user_can_login(page: Page):
    """Smoke test: user can log in."""
    page.goto("/login")
    page.fill("[name=email]", "user@example.com")
    page.fill("[name=password]", "password123")
    page.click("[type=submit]")
    expect(page).to_have_url("/dashboard")

def test_user_can_book_facility(page: Page):
    """Smoke test: user can create a booking."""
    page.goto("/bookings/new")
    page.select_option("[name=facility]", "tennis-court-1")
    page.fill("[name=date]", "2024-12-25")
    page.click("[type=submit]")
    expect(page.locator(".success")).to_be_visible()
```

---

## Change Approval

For production releases, change approval is required.

| Change Type | Approval |
|---|---|
| Bug fix | Tech Lead |
| Feature | Product + Tech Lead |
| Security fix | Security Lead |
| Infrastructure | DevOps Lead |
| Database migration | Backend Lead |

---

## SLO Budget Check

Before release, verify error budget is not exhausted.

```python
# scripts/check_slo_budget.py
from prometheus_api_client import PrometheusConnect

def check_slo_budget():
    prom = PrometheusConnect()

    # Check availability SLO (99.9%)
    query = '''
    sum(rate(http_requests_total{status=~"5.."}[5m]))
    /
    sum(rate(http_requests_total[5m]))
    '''
    error_rate = prom.custom_query(query)

    # Error budget is 0.1% * 30 days = 43.8 minutes/month
    budget_consumed = error_rate * 100

    if budget_consumed > 50:
        raise Exception(f"Error budget {budget_consumed}% consumed. Do not release.")
```

---

## Common Failures

| Failure | Cause | Fix |
|---|---|---|
| Integration test fails | Environment mismatch | Fix test or environment |
| Smoke test fails | Feature broken | Fix feature |
| Security vulnerabilities | New CVE | Update dependency |
| Performance regression | Code change | Optimize before release |
| SLO budget exhausted | Production issues | Fix production first |

---

## Related Documents

- [Quality Gates Overview](./overview.md)
- [PR Gates](./pr-gates.md)
- [Performance Gates](./performance-gates.md)
- [SLO Documentation](../12-devops/monitoring.md)
