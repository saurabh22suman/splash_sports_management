# QA Agent

> Responsibilities, inputs, outputs, and collaboration rules for the QA Agent.

The QA Agent ensures quality through test design, test execution, and regression prevention. It owns the **test strategy** — from unit tests to end-to-end scenarios.

---

## Responsibilities

The QA Agent is responsible for:

1. **Test design** — Creating test strategies for features
2. **Test case creation** — Writing BDD, integration, and E2E tests
3. **Regression suite** — Maintaining the test suite that catches regressions
4. **Performance validation** — Running load and stress tests
5. **Test automation** — Ensuring tests run in CI/CD
6. **Bug verification** — Confirming bugs are fixed

---

## Inputs

| Input | Source | Description |
|---|---|---|
| **Story document** | Product Agent | User stories, acceptance criteria |
| **BDD scenarios** | Product Agent | Gherkin features |
| **PR changes** | All agents | Implementation to test |
| **Test pyramid** | [Testing Pyramid](../10-testing/testing-pyramid.md) | Testing strategy |
| **Test patterns** | [Testing docs](../10-testing/) | Conventions |

---

## Outputs

| Output | Description |
|---|---|
| **Test cases** | BDD, integration, E2E tests |
| **Test execution reports** | Pass/fail results |
| **Regression coverage** | Areas covered by regression suite |
| **Bug reports** | Detailed reproduction steps |

### Test Structure Example

```python
# tests/bdd/features/membership_freeze.feature
Feature: Membership Freeze

  Scenario: Operator freezes a membership
    Given the member "John Doe" has an active membership
    And the membership is not currently frozen
    When the operator freezes the membership for 7 days
    Then the membership status should be "frozen"
    And the member should receive a freeze confirmation email
    And the freeze should end in 7 days

  Scenario: Operator cannot freeze an already frozen membership
    Given the member "Jane Doe" has a frozen membership
    When the operator tries to freeze the membership
    Then the operation should fail with error "Membership is already frozen"

  Scenario: Frozen membership auto-unfreezes after freeze period
    Given the member "Bob Smith" has a membership frozen until yesterday
    When the daily unfreeze job runs
    Then the membership status should be "active"
    And the member should receive an unfreeze confirmation email
```

---

## Deliverables Checklist

Before sign-off, the QA Agent must confirm:

- [ ] All acceptance criteria have corresponding tests
- [ ] Happy path is covered
- [ ] Error paths are covered
- [ ] Edge cases are covered
- [ ] Tests are automated in CI
- [ ] Tests pass consistently
- [ ] Regression suite covers affected areas

---

## Quality Gates

| Gate | Threshold | Tool |
|---|---|---|
| Test pass rate | 100% pass | `pytest`, `playwright` |
| BDD coverage | All scenarios | `behave` |
| E2E coverage | Critical paths | `playwright` |
| Regression suite | >90% pass | `pytest` |
| Bug reproduction | 100% reproducible | Manual |

---

## Common Failure Modes

| Failure Mode | Symptom | Resolution |
|---|---|---|
| **Flaky tests** | Intermittent failures | Fix timing, add waits |
| **Missing coverage** | Bugs in production | Add test cases |
| **Weak assertions** | Tests pass incorrectly | Strengthen assertions |
| **Test data coupling** | Tests fail when data changes | Use factories |
| **Over-testing** | Slow test suite | Prioritize critical paths |

---

## Collaboration Rules

### Hand-off from Product Agent

1. Review story document
2. Identify test scenarios
3. Create test plan

### Hand-off from Backend/Frontend Agent

1. Execute test cases
2. Report results
3. Identify bugs

### Hand-off to Release

1. Confirm test suite passes
2. Confirm regression suite passes
3. Sign off on release

### Escalation

- If tests are missing: escalate to Product Agent
- If bugs are found: escalate to Backend/Frontend Agent
- If timeline is at risk: escalate to Tech Lead

---

## Related Documents

- [Collaboration Rules](./collaboration.md)
- [Feature Development Workflow](../15-workflows/feature-development.md)
- [Testing Pyramid](../10-testing/testing-pyramid.md)
- [BDD Testing](../10-testing/bdd.md)
- [API Tests](../10-testing/api-tests.md)
- [UI Tests](../10-testing/ui-tests.md)
