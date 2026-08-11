# Phase 0 Security — Test Isolation Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the test isolation regression in `apps/backend/tests/api/test_rbac.py` (introduced by F-04 JWT work) so all 25 RBAC tests pass when run with other test files, then update `docs/CODEBASE_REVIEW.md` to mark the related P0 findings resolved.

**Architecture:** Move JWT env-var mutation from module-level (`os.environ["JWT_SECRET"] = ...` at import time) to a per-test pytest fixture using `monkeypatch` (which pytest auto-restores after each test). No production code changes. Audit doc update is a separate task.

**Tech Stack:** Python 3.12, pytest 9.x, pytest's `monkeypatch` fixture, FastAPI dependency injection, Pydantic Settings.

## Global Constraints

- Production code behavior must not change. The fix is purely in `apps/backend/tests/`.
- All 25 RBAC tests in `tests/api/test_rbac.py` must pass when run as part of a multi-file pytest invocation (currently 8/25 fail with 401 "Invalid access token").
- All RLS tests (15/15 currently pass) must remain green — no regression.
- Full `apps/backend` test suite must remain green (no regressions in passing tests).
- Audit doc `docs/CODEBASE_REVIEW.md` must reflect the resolved state with the closing commit SHAs.
- Use `monkeypatch.setenv()` instead of direct `os.environ` mutation. `monkeypatch` is pytest's standard env-isolation primitive and auto-restores state per test.

---

## File Structure

This plan modifies 3 files across 3 tasks. Each task is independently testable.

| File | Responsibility | Task |
|---|---|---|
| `apps/backend/tests/api/test_rbac.py` | Replace module-level `os.environ` mutation with per-test `monkeypatch` fixture; verify all 25 RBAC tests pass | Task 1 |
| `docs/CODEBASE_REVIEW.md` | Mark F-02, F-03, F-15 (audit numbering) resolved with closing commit SHAs | Task 2 |
| (no new files; no production code changes) | — | — |

---

## Tasks

### Task 1: Refactor `test_rbac.py` to use `monkeypatch` fixture

**Files:**
- Modify: `apps/backend/tests/api/test_rbac.py:1-45` (remove module-level env mutation; add autouse `monkeypatch` fixture; simplify `_create_token` default arg)
- Test: `apps/backend/tests/api/test_rbac.py` (the file IS the test — verify 25/25 pass when run alongside other test files)

**Interfaces:**
- Consumes: nothing (no prior task in this plan)
- Produces: a pytest fixture `jwt_env` that any test in this file inherits automatically (autouse), and a module-level constant `JWT_TEST_SECRET` that both `_create_token` and the fixture reference.

**Background:** The current code at lines 21-23 mutates `os.environ` at module import time. This is invisible to `pytest.MonkeyPatch` and persists across the test session. When `test_auth_endpoints.py` or other test files run before `test_rbac.py`, their own env mutations can interact with `test_rbac.py`'s expectations, causing 8 of the 25 tests to receive `401 Invalid access token` instead of the expected `403 Forbidden` (the `requires_role` check never runs because the token fails to verify first).

**Reference signature (pytest standard):**
```python
from collections.abc import Iterator
import pytest

@pytest.fixture(autouse=True)
def jwt_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_SECRET", JWT_TEST_SECRET)
    from common.infrastructure.settings import reset_settings_cache
    reset_settings_cache()
    yield
    reset_settings_cache()
```

---

- [ ] **Step 1: Establish the baseline failure**

Run the full combined suite to confirm the 8/25 failure exists at HEAD:

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/api/test_rbac.py tests/api/test_auth_endpoints.py tests/integration/test_rls_tenant_isolation.py tests/integration/test_tenant_isolation_matrix.py 2>&1 | tail -12
```

Expected: `8 failed, 33 passed` (or similar — the RBAC-specific 8 must fail with status code 401 and detail `"Invalid access token"`).

- [ ] **Step 2: Replace the module-level env mutation**

In `apps/backend/tests/api/test_rbac.py`, **replace lines 21-23**:

```python
# Set JWT algorithm to HS256 for tests - must be set BEFORE any imports
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_SECRET"] = "dev-only-jwt-secret-change-me-in-prod-please-32chars"
```

with a module-level constant (placed right after the imports, before `_create_token`):

```python
JWT_TEST_SECRET = "dev-only-jwt-secret-change-me-in-prod-please-32chars"
```

- [ ] **Step 3: Add the autouse `jwt_env` fixture**

In `apps/backend/tests/api/test_rbac.py`, **add a new fixture** after the `JWT_TEST_SECRET` constant. Place it before the `mock_session` fixture:

```python
@pytest.fixture(autouse=True)
def jwt_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Set JWT env vars per-test using monkeypatch (auto-restored after each test).

    Replaces the previous module-level os.environ mutation, which leaked state
    across tests when run alongside other test files (causing 8/25 RBAC tests
    to receive 401 instead of the expected 403). monkeypatch is pytest's
    standard env-isolation primitive — its teardown restores prior env values
    automatically.

    Also resets the Pydantic Settings cache so the new env values are picked up
    by `_get_public_key()` and `_get_jwt_algorithm()` in
    apps/backend/src/auth/interfaces/http/dependencies.py.
    """
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_SECRET", JWT_TEST_SECRET)
    from common.infrastructure.settings import reset_settings_cache
    reset_settings_cache()
    yield
    reset_settings_cache()
```

Also update the imports at the top of the file — add `from collections.abc import Iterator` (it is already imported via `from collections.abc import AsyncIterator`; add `Iterator` to that line: `from collections.abc import AsyncIterator, Iterator`).

- [ ] **Step 4: Simplify `_create_token` to use the constant**

In `apps/backend/tests/api/test_rbac.py`, **update `_create_token`** (currently lines 26-45). Remove the `secret` parameter and its default, and reference `JWT_TEST_SECRET` directly in the `jwt.encode` call:

```python
def _create_token(
    tenant_id: UUID,
    user_id: UUID,
    roles: list[str],
    customer_id: UUID | None = None,
) -> str:
    """Create a JWT access token for testing."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "customer_id": str(customer_id) if customer_id else None,
        "type": "access",
        "exp": now + timedelta(hours=1),
        "iat": now,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, JWT_TEST_SECRET, algorithm="HS256")
```

Verify the file no longer references `os.environ["JWT_SECRET"]` or `os.environ["JWT_ALGORITHM"]`:

```bash
grep -n 'os\.environ' /home/soloengine/Github/splash_sports_management/apps/backend/tests/api/test_rbac.py
```

Expected: no output.

- [ ] **Step 5: Run RBAC tests in isolation to verify the refactor compiles**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/api/test_rbac.py -v
```

Expected: `10 passed` (or whatever the current count is when run alone — must be 100% pass, no failures).

- [ ] **Step 6: Run combined suite to verify the isolation bug is fixed**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest tests/api/test_rbac.py tests/api/test_auth_endpoints.py tests/integration/test_rls_tenant_isolation.py tests/integration/test_tenant_isolation_matrix.py 2>&1 | tail -5
```

Expected: **all tests pass**. No `8 failed` line. Verify by counting: should be ~50-60 total tests passing depending on exact test counts, **0 failed**.

- [ ] **Step 7: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add apps/backend/tests/api/test_rbac.py
git commit -m "test(rbac): use monkeypatch fixture to fix cross-test env pollution (F-02)"
```

---

### Task 2: Verify no regressions on full backend test suite

**Files:**
- (no file changes — verification only)

**Interfaces:**
- Consumes: Task 1's refactored `test_rbac.py`
- Produces: evidence that no other tests broke (for the audit doc update in Task 3)

---

- [ ] **Step 1: Run the full backend test suite**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest --tb=short 2>&1 | tail -30
```

Expected: **no new failures** compared to the pre-task baseline. If tests fail, diagnose (likely: another test file has the same module-level env mutation pattern; flag this as a follow-up but do NOT fix in this plan — out of scope).

- [ ] **Step 2: Capture the test summary for the audit commit message**

```bash
cd /home/soloengine/Github/splash_sports_management/apps/backend
PYTHONPATH=src pytest --tb=no -q 2>&1 | tail -3
```

Expected: a one-line summary like `52 passed in 12.34s` or `XXX passed, YYY skipped in ...`. Record this number — it goes into the audit doc commit message.

- [ ] **Step 3: Commit (verification gate — empty commit if no code change)**

If Task 1's commit was the only code change, this task has no commit. The verification is a precondition for Task 3, not a commit gate. Skip this step unless you discover and fix a regression.

---

### Task 3: Update audit doc to mark findings resolved

**Files:**
- Modify: `docs/CODEBASE_REVIEW.md:678-680, 691` (the findings table Status column)

**Interfaces:**
- Consumes: closing commit SHAs from Task 1 (the test fix) and the prior commits for RLS (`20260811_0005_enable_rls_all_tables.py` migration already landed in `main` before this plan)
- Produces: updated audit doc rows for F-02, F-03, F-15 (audit numbering) marked ✅ Resolved with commit references

**Finding reference (from `docs/CODEBASE_REVIEW.md:673-721`):**
- F-02 — Security, **P0** — "No RBAC enforcement on any endpoint"
- F-03 — Security, **P0** — "Missing PostgreSQL RLS" (8 of 9 tables)
- F-15 — Testing, **P0** — "Tests broken (FK naming)"

**Note on numbering:** the audit uses different F-14 vs F-15 numbering than `docs/FINDINGS_ROADMAP.md`. The audit's F-15 is what this plan closes (tests broken → tests fixed). The audit's F-14 ("Backup infrastructure missing") is out of scope here — leave it ❌ Open.

---

- [ ] **Step 1: Read the current state of the findings table**

```bash
grep -n "F-02 | Security | \*\*P0\*\*\|F-03 | Security | \*\*P0\*\*\|F-15 | Testing | \*\*P0\*\*" /home/soloengine/Github/splash_sports_management/docs/CODEBASE_REVIEW.md
```

Expected: 3 lines, each ending in `| ❌ Open |`.

- [ ] **Step 2: Mark F-02 resolved**

Edit `docs/CODEBASE_REVIEW.md`. Change the F-02 row's Status cell from `❌ Open` to:

```
✅ Resolved (`ba12454` — requires_role applied to all routers; test isolation regression fixed in this plan)
```

Use the Edit tool with the exact existing line as `old_string`. Replace just the Status cell.

- [ ] **Step 3: Mark F-03 resolved**

Edit `docs/CODEBASE_REVIEW.md`. Change the F-03 row's Status cell from `❌ Open` to:

```
✅ Resolved (migration `0005_enable_rls_all_tables` in `main`)
```

- [ ] **Step 4: Mark F-15 resolved**

Edit `docs/CODEBASE_REVIEW.md`. Change the F-15 row's Status cell from `❌ Open` to:

```
✅ Resolved (`requires_role` tests + tenant-isolation tests now pass; test isolation bug fixed in this plan)
```

- [ ] **Step 5: Verify the three rows updated cleanly**

```bash
grep -n "F-02 | Security | \*\*P0\*\*\|F-03 | Security | \*\*P0\*\*\|F-15 | Testing | \*\*P0\*\*" /home/soloengine/Github/splash_sports_management/docs/CODEBASE_REVIEW.md
```

Expected: 3 lines, each ending in `✅ Resolved`.

- [ ] **Step 6: Commit**

```bash
cd /home/soloengine/Github/splash_sports_management
git add docs/CODEBASE_REVIEW.md
git commit -m "docs(review): mark F-02, F-03, F-15 resolved — RBAC, RLS, tenant-isolation tests now pass"
```

---

## Verification (after all tasks land)

- [ ] `cd apps/backend && PYTHONPATH=src pytest tests/api/test_rbac.py tests/api/test_auth_endpoints.py tests/integration/test_rls_tenant_isolation.py tests/integration/test_tenant_isolation_matrix.py` — 100% green
- [ ] `cd apps/backend && PYTHONPATH=src pytest` — full suite, no new failures
- [ ] `docs/CODEBASE_REVIEW.md` shows F-02, F-03, F-15 as ✅ Resolved
- [ ] No production code (`apps/backend/src/`) modified

## Out of scope for this plan

- Refactoring `_reset_settings` in `apps/backend/conftest.py` (the autouse pattern is sufficient)
- Other test files that may have the same module-level env mutation pattern (audit-only follow-up)
- The complete RBAC role × endpoint matrix test (that's the "comprehensive hardening" option C, deferred)
- F-14 audit finding (Backup infrastructure) — own plan
- F-13 audit finding (CI/CD pipeline) — own plan, depends on tests passing (now unblocked)
