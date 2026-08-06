# Code Review Checklist

> Comprehensive reviewer checklist. Categories: correctness, tests, security, performance, readability, architecture, documentation, observability. PR size guideline. Review SLA.

This document provides a comprehensive checklist for code reviewers. It covers all aspects of code quality and serves as the standard for PR approvals.

---

## General Guidelines

### PR Size

| Size | Lines of Diff | Review Time | Approval |
|---|---|---|---|
| Small | < 100 | 10 min | 1 reviewer |
| Medium | 100-400 | 30 min | 1 reviewer |
| Large | 400-600 | 1 hour | 2 reviewers |
| X-Large | > 600 | Split into multiple PRs | N/A |

> **Guideline** — If PR exceeds 400 lines, request the author split it. Large PRs lead to insufficient review.

### Review SLA

| Priority | Response Time | Review Complete |
|---|---|---|
| Normal | 4 hours | 24 hours |
| Hotfix | 1 hour | 4 hours |
| Blocking | 15 min | 1 hour |

---

## Checklist by Category

### 1. Correctness

- [ ] Code does what the ticket/issue describes
- [ ] Edge cases are handled
- [ ] No off-by-one errors
- [ ] Null/None cases handled
- [ ] Error conditions return appropriate errors
- [ ] Data validation is correct
- [ ] Business logic is correct
- [ ] No hardcoded values that should be configurable

### 2. Tests

- [ ] Unit tests added for new functionality
- [ ] Unit tests pass locally
- [ ] Edge cases covered in tests
- [ ] Tests follow naming conventions (`test_<feature>_<scenario>`)
- [ ] Test data is realistic
- [ ] No test interdependencies
- [ ] Integration tests added for DB/external calls
- [ ] Test coverage maintained or improved

> **Rule** — New code must have tests. No PR merged without test coverage for new functionality.

### 3. Security

- [ ] No secrets hardcoded (check `.env` files, comments)
- [ ] Input validation on all user inputs
- [ ] SQL injection prevented (parameterized queries)
- [ ] XSS prevented (output encoding)
- [ ] CSRF handled (tokens for state-changing operations)
- [ ] Authorization checks on all endpoints
- [ ] Tenant isolation enforced
- [ ] Rate limiting in place
- [ ] No sensitive data in logs

### 4. Performance

- [ ] No N+1 queries (use eager loading)
- [ ] Database indexes used where needed
- [ ] Caching considered for expensive operations
- [ ] No unnecessary database calls in loops
- [ ] Pagination for large datasets
- [ ] Async/await used for I/O operations
- [ ] Connection pooling configured

### 5. Readability

- [ ] Code follows style guide (ruff, black)
- [ ] Variable names are descriptive
- [ ] Functions are small and focused (< 30 lines)
- [ ] No magic numbers (use constants)
- [ ] Complex logic has comments explaining WHY
- [ ] No nested callbacks (use async/await or separate functions)
- [ ] No commented-out code

### 6. Architecture

- [ ] Follows layer structure (domain → application → infrastructure)
- [ ] No framework imports in domain layer
- [ ] Dependency injection used (not direct instantiation)
- [ ] Repository pattern for data access
- [ ] Service classes for business logic
- [ ] No tight coupling between modules
- [ ] Feature flags used for incomplete work

### 7. Documentation

- [ ] Public functions have docstrings
- [ ] Docstrings include Args, Returns, Raises
- [ ] Complex functions have examples in docstrings
- [ ] README updated if needed
- [ ] API schema documented
- [ ] Configuration documented

### 8. Observability

- [ ] Important operations are logged
- [ ] Errors logged with sufficient context
- [ ] Metrics added for key operations
- [ ] Trace context propagated
- [ ] Health check endpoint exists
- [ ] Alert thresholds documented

---

## Reviewer Guidelines

### Before Reviewing

1. Read the ticket/issue to understand what is being built
2. Check the PR description for context
3. Review any linked design documents

### During Review

1. **Approach**: Be constructive, not critical
2. **Questions**: Ask, don't demand
3. **Nits**: Mark minor issues as "nit" (optional)
4. **Blocking**: Clearly mark blocking issues
5. **Praise**: Acknowledge good solutions

### Example Comments

```markdown
# Blocking (must fix)
> **BLOCKING** - This query has an N+1 problem. For tenants with many bookings,
> this will cause significant performance issues. Consider using eager loading:
> `select(options(joinedload(Booking.customer)))`

# Suggestion
> Consider extracting this validation into a separate function to improve readability.

# Question
> What's the reasoning behind this approach? I'm curious if there's a simpler solution.

# Nit
> Nit: Minor style - could use f-string here.

# Praise
> Nice solution! The use of the builder pattern here makes this very readable.
```

---

## Author Responsibilities

1. **Self-review** before requesting review
2. **Keep PR small** (split if needed)
3. **Respond to feedback** promptly
4. **Don't take feedback personally** - it's about code
5. **Update PR description** with context
6. **Re-request review** after changes

---

## Approval Requirements

| Type | Required Approvers | Notes |
|---|---|---|
| Normal PR | 1 reviewer | Tech Lead for architecture changes |
| Security changes | 1 reviewer + Security | Additional sign-off |
| Infrastructure | 1 reviewer + DevOps | Infrastructure changes |
| Breaking changes | 2 reviewers | Must document migration |

---

## Automated Checks

All PRs must pass these automated checks before review:

- [ ] `ruff check` passes
- [ ] `ruff format --check` passes
- [ ] `mypy` passes
- [ ] `pytest` tests pass
- [ ] No new security vulnerabilities (bandit, safety)
- [ ] Build succeeds

---

## Review Checklist Template

```markdown
## Code Review

### Correctness
- [ ]

### Tests
- [ ]

### Security
- [ ]

### Performance
- [ ]

### Readability
- [ ]

### Architecture
- [ ]

### Documentation
- [ ]

### Observability
- [ ]

---

**Verdict**: [ ] Approve [ ] Request Changes [ ] Block

**Notes**:
```

---

## Summary

| Category | Focus |
|---|---|
| Correctness | Does it work right? |
| Tests | Is it tested? |
| Security | Is it safe? |
| Performance | Is it fast enough? |
| Readability | Can others understand? |
| Architecture | Does it follow structure? |
| Documentation | Is it documented? |
| Observability | Can we debug it? |

---

## Related Documents

- [Python Style](./python-style.md) — Formatting rules
- [Refactoring Rules](./refactoring-rules.md) — Safe refactoring
- [Branch Strategy](../12-devops/branch-strategy.md) — Branching model
- [Code Review Workflow](../15-workflows/code-review.md) — Review process
