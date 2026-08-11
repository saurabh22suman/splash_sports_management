# Phase 0 Security — Test Isolation Fix Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close 4 P0 findings (F-02 RBAC, F-03 RLS, F-14 tests-broken per roadmap numbering, F-15 tenant-isolation tests) by fixing the test isolation regression introduced by the F-04 JWT work and updating the audit doc.

**Architecture:** Test-only fix. Move `os.environ["JWT_SECRET"]` mutation from module import-time to a per-test fixture with proper cleanup. Verify all 25 RBAC tests pass. Update `docs/CODEBASE_REVIEW.md` to mark findings resolved.

**Tech Stack:** Python 3.12, pytest 9.x, FastAPI dependency injection, Pydantic Settings.

## Global Constraints

- Production code behavior must not change. The fix is purely in `apps/backend/tests/`.
- All 25 RBAC tests in `tests/api/test_rbac.py` must pass when run as a single pytest invocation (currently 17/25 pass; 8 fail with 401 "Invalid access token").
- All RLS tests (15/15 currently pass) must remain green — no regression.
- Full `apps/backend` test suite must remain green (no regressions in passing tests).
- Audit doc `docs/CODEBASE_REVIEW.md` must reflect the resolved state with the closing commit SHAs.

---

## Root cause

`apps/backend/tests/api/test_rbac.py:23` mutates `os.environ["JWT_SECRET"]` at module import time:

```python
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_SECRET"] = "dev-only-jwt-secret-change-me-in-prod-please-32chars"
```

The HS256 token verification path in `apps/backend/src/auth/interfaces/http/dependencies.py:76-80` reads `os.environ["JWT_SECRET"]` at request time. When `tests/api/test_rbac.py` runs alongside other tests in the suite, the order of test discovery + the `_reset_settings` autouse fixture (which only invalidates the `get_settings()` cache, not `os.environ`) causes the `JWT_SECRET` value seen by `_get_public_key()` to diverge from the value used to sign the token in the `customer_token` fixture. Result: 8 of 25 tests get 401 instead of 403.

When the failing test runs alone (`pytest tests/api/test_rbac.py::TestFacilityRBAC::test_update_facility_customer_forbidden`), it passes — confirming this is a state-pollution issue, not a logic bug.

## Design

### Strategy: per-test fixture with cleanup

Replace module-level `os.environ` mutation with a per-test pytest fixture that sets and unsets `JWT_SECRET` and `JWT_ALGORITHM` cleanly. The fixture yields; the test runs; the fixture's teardown restores previous values (or removes them).

### Components

**1. `apps/backend/tests/api/test_rbac.py` — refactor:**
   - Remove module-level `os.environ["JWT_ALGORITHM"] = "HS256"` and `os.environ["JWT_SECRET"] = ...` (lines 21-23).
   - Add a pytest fixture `jwt_env` (autouse, function scope) that:
     - Sets `JWT_ALGORITHM=HS256` and `JWT_SECRET=<stable test value>` before the test runs.
     - Calls `reset_settings_cache()` so the cached `Settings` object re-reads env.
     - In teardown, restores prior env values (or removes) and calls `reset_settings_cache()` again.
   - Replace the default argument `secret: str = "dev-only-..."` in `_create_token` with the same stable value (no longer sourced from `os.environ`).

**2. `apps/backend/conftest.py` — harden `_reset_settings`:**
   - Document the invariant that fixtures must use the autouse `_reset_settings` for any env mutation, and that direct `os.environ` mutation at module level is forbidden.
   - No code change required if option (1) above is implemented cleanly — the autouse fixture ensures proper teardown.

**3. `docs/CODEBASE_REVIEW.md` — update findings table:**
   - F-02 → ✅ Resolved (with the closing commit SHA once the fix lands).
   - F-03 → ✅ Resolved (RLS migration `0005_enable_rls_all_tables` already in `main`).
   - F-14 → ✅ Resolved (per roadmap numbering — fix-broken-tests interpretation).
   - F-15 → ✅ Resolved (per roadmap numbering — tenant-isolation test suite).

### Why option (a) and not (b)

The original brainstorm offered two approaches: (a) per-test fixture with env mutation + cleanup, or (b) FastAPI `dependency_overrides` to inject the secret directly into `auth_required`. Option (a) is chosen because:
- It preserves the existing test pattern (`os.environ`-driven config).
- It minimizes the diff — only `test_rbac.py` changes meaningfully.
- The reviewer can flag a preference for (b) during plan review.

### Data flow

No runtime data flow changes. The fix moves state mutation from "module import" to "per-test fixture lifecycle". The auth flow at request time is unchanged: `_get_jwt_algorithm()` reads `JWT_ALGORITHM` env → "HS256"; `_get_public_key()` reads `JWT_SECRET` env → stable test value; `jwt.decode(token, secret, algorithms=["HS256"])` succeeds.

### Error handling

No production error handling changes. Test-side: when a future fixture regresses and pollutes env, the symptom will be the same 401-vs-403 mismatch. To improve diagnosis, add a one-line comment in `test_rbac.py` documenting the invariant and pointing at this spec for context.

### Testing

**In-order verification gates:**

1. **Reproduce:** before the fix, run `pytest tests/api/test_rbac.py` and confirm 8/25 fail with 401. This is the regression baseline.
2. **Fix:** apply the refactor.
3. **Targeted pass:** `pytest tests/api/test_rbac.py -v` → **25/25 pass**.
4. **No regression on RLS:** `pytest tests/integration/test_rls_tenant_isolation.py tests/integration/test_tenant_isolation_matrix.py` → **15/15 pass** (unchanged from baseline).
5. **No regression on auth:** `pytest tests/api/test_auth_endpoints.py` → **16/16 pass** (unchanged from baseline).
6. **Full suite:** `pytest --tb=short` from `apps/backend/` → no new failures.

### Verification & Rollback

- **Verification:** all six gates above green.
- **Rollback:** revert the single commit touching `test_rbac.py`. No DB migration, no production code change, so rollback is trivial.

## Out of scope

- Changes to `requires_role` itself (the implementation is correct; only tests were broken).
- New endpoint × role matrix tests (that's sub-project C / option C from the brainstorm — deferred).
- Settings-cache hardening (option B from brainstorm — deferred).
- Updates to `apps/backend/conftest.py` beyond documentation comment (the autouse fixture pattern is sufficient).
