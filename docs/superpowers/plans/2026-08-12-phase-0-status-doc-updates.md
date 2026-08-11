# Phase 0 Status Doc Updates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reflect Phase 0 progress (9 of 19 P0 findings closed) in three project-level docs so readers can see the project is mid-Phase-0 without having to discover the audit doc.

**Architecture:** Docs-only. Hybrid approach: lightweight inline progress + pointers to the audit doc (`docs/CODEBASE_REVIEW.md`) as the source of truth. No duplication of finding status across the three docs.

**Tech Stack:** Markdown, Keep a Changelog 1.1.0 convention.

## Global Constraints

- Source of truth for finding status is `docs/CODEBASE_REVIEW.md`. The three docs in this plan are pointers, not a second source of truth.
- The roadmap's per-finding "Acceptance criteria" checkboxes are deliberately left untouched (drift risk).
- No code changes. No tests. Lint rules don't apply to markdown.
- Commit style: lowercase `docs(...)` prefix, single line subject.
- All links should be relative (`./docs/...` or `../CODEBASE_REVIEW.md`).
- Keep progress counts consistent: **9 of 19 P0 findings closed** (F-01, F-02, F-03, F-04, F-05, F-07, F-08, F-10, F-15).

**Closing commits to reference (canonical):**
- `ba12454` — F-01, F-02, F-04, F-15 (group from Sub-project A)
- `0005_enable_rls_all_tables` — F-03 (migration)
- `7af5802` — F-05, F-07, F-08 (group from Sub-project B)
- `c943664` — F-10 (Sub-project C1)

---

## File Structure

| File | Type | Responsibility |
|---|---|---|
| `README.md` | Modify | Add "Phase 0 progress" subsection (≈5 lines) before "Next phase". |
| `CHANGELOG.md` | Create | New file at repo root, Keep a Changelog format, `## [Unreleased]` section with closed findings. |
| `docs/FINDINGS_ROADMAP.md` | Modify | Add "Phase 0 status snapshot" subsection at top of Phase 0 chapter (after the "Phase 0 — Block-Release Security" header, before any `### F-xx` subsection). |

---

### Task 1: Update README.md — add Phase 0 progress subsection

**Files:**
- Modify: `README.md` (insert between "What's in this prototype" table at line 114 and "Next phase" heading at line 115)

**Interfaces:**
- Consumes: `docs/CODEBASE_REVIEW.md` (the source of truth for finding status)
- Produces: a "Phase 0 progress" heading + paragraph in `README.md`

- [ ] **Step 1: Read the current README to find the exact insertion point**

```bash
sed -n '110,118p' README.md
```

Expected output ends with the "What's in this prototype" table footer `| `web-pwa` | Working | ... |` and then the `## Next phase` heading. The insertion point is between them.

- [ ] **Step 2: Insert the Phase 0 progress subsection**

Use the Edit tool. The `old_string` is the line right before `## Next phase` (the table row ending the "What's in this prototype" section + a blank line), and `new_string` is the same three lines plus the new subsection.

`old_string` (exactly):
```
| `web-pwa` | Working | Single PWA with role-based routing: /login (customer), /admin/login (admin), role-specific home pages, /admin/users for user management |

## Next phase
```

`new_string`:
```
| `web-pwa` | Working | Single PWA with role-based routing: /login (customer), /admin/login (admin), role-specific home pages, /admin/users for user management |

## Phase 0 progress

Phase 0 — Block-Release Security is in progress. 9 of 19 P0 findings closed
(RBAC, RLS, JWT, price-cents, webhook tenant-id, refund lookup, cross-module
import, tenant-isolation tests). See [CODEBASE_REVIEW.md](./docs/CODEBASE_REVIEW.md)
for the up-to-date status of every finding.

## Next phase
```

- [ ] **Step 3: Verify the edit**

```bash
grep -n "Phase 0 progress\|Next phase" README.md
```

Expected: two lines, "Phase 0 progress" before "Next phase".

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): add Phase 0 progress section pointing to audit doc"
```

---

### Task 2: Create CHANGELOG.md

**Files:**
- Create: `CHANGELOG.md` (at repo root)

**Interfaces:**
- Consumes: the closing commits listed in the Global Constraints section
- Produces: a CHANGELOG.md file following Keep a Changelog 1.1.0

- [ ] **Step 1: Verify CHANGELOG.md does not already exist**

```bash
ls CHANGELOG.md 2>&1
```

Expected: `ls: cannot access 'CHANGELOG.md': No such file or directory`. If the file already exists, stop and ask the user how to proceed.

- [ ] **Step 2: Write CHANGELOG.md**

Create the file at the repo root with the following content (use the Write tool):

```markdown
# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Phase 0 — Block-Release Security (in progress)

Closed P0 findings (9 of 19):

- **F-01** — RS256 JWT — `ba12454`
- **F-02** — RBAC on all admin endpoints — `ba12454`
- **F-03** — Postgres RLS on all business tables — migration `0005_enable_rls_all_tables`
- **F-04** — JWT secret fail-fast on startup — `ba12454`
- **F-05** — Server-computed booking price — `7af5802`
- **F-07** — Webhook `tenant_id` resolved from DB — `7af5802`
- **F-08** — Tenant-scoped refund lookup — `7af5802`
- **F-10** — Cross-module DB model import removed — `c943664`
- **F-15** — Tenant-isolation test suite — `ba12454`

Phase 0 exit criteria (see [CODEBASE_REVIEW.md](./docs/CODEBASE_REVIEW.md)):
0 P0 findings open; penetration-test scenarios blocked.

[FINDINGS_ROADMAP.md](./docs/FINDINGS_ROADMAP.md) has the full Phase 0 plan.
```

- [ ] **Step 3: Verify the file**

```bash
head -10 CHANGELOG.md && echo "---" && grep -c "^- \*\*F-" CHANGELOG.md
```

Expected: the Keep a Changelog header is on the first lines, and the grep count returns `9` (one entry per closed P0).

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): add Keep a Changelog with Phase 0 closure entries"
```

---

### Task 3: Update docs/FINDINGS_ROADMAP.md — add Phase 0 status snapshot

**Files:**
- Modify: `docs/FINDINGS_ROADMAP.md` (insert after the "Phase 0 — Block-Release Security" header at line 37, before any `### F-xx` subsection)

**Interfaces:**
- Consumes: the closing commits listed in the Global Constraints section
- Produces: a "Phase 0 status snapshot" subsection at the top of the Phase 0 chapter

- [ ] **Step 1: Find the exact insertion point**

```bash
grep -n "^## Phase 0\|^### F-0" docs/FINDINGS_ROADMAP.md | head -5
```

Expected: line 37 is `## Phase 0 — Block-Release Security`, line 43 is `### F-01 — Switch JWT to RS256 (P0)`. The insertion point is between them.

- [ ] **Step 2: Insert the snapshot subsection**

Use the Edit tool. The `old_string` ends with the header line plus an empty line, and `new_string` adds the snapshot.

`old_string`:
```
## Phase 0 — Block-Release Security

> **Why this phase exists:** Without this, the platform cannot be exposed to the public internet. All items here are P0 security/correctness issues that, in combination, let an authenticated user of one tenant become admin of any other tenant.

**Duration:** 1-2 weeks · **Engineers:** 1 backend · **Merge gate:** none of these can ship without security review by 2 reviewers.

### F-01 — Switch JWT to RS256 (P0)
```

`new_string`:
```
## Phase 0 — Block-Release Security

> **Why this phase exists:** Without this, the platform cannot be exposed to the public internet. All items here are P0 security/correctness issues that, in combination, let an authenticated user of one tenant become admin of any other tenant.

**Duration:** 1-2 weeks · **Engineers:** 1 backend · **Merge gate:** none of these can ship without security review by 2 reviewers.

### Phase 0 status snapshot

9 of 19 P0 findings closed (see [CODEBASE_REVIEW.md](../CODEBASE_REVIEW.md) for the
authoritative status column):

| Finding | Status | Closing commit |
|---|---|---|
| F-01 | ✅ Closed | `ba12454` |
| F-02 | ✅ Closed | `ba12454` |
| F-03 | ✅ Closed | migration `0005_enable_rls_all_tables` |
| F-04 | ✅ Closed | `ba12454` |
| F-05 | ✅ Closed | `7af5802` |
| F-07 | ✅ Closed | `7af5802` |
| F-08 | ✅ Closed | `7af5802` |
| F-10 | ✅ Closed | `c943664` |
| F-15 | ✅ Closed | `ba12454` |

The remaining 10 P0 findings are unchanged in this roadmap; their work plans
below remain the source of truth for scope.

### F-01 — Switch JWT to RS256 (P0)
```

- [ ] **Step 3: Verify the edit**

```bash
grep -n "Phase 0 status snapshot\|F-01 — Switch JWT" docs/FINDINGS_ROADMAP.md | head -5
```

Expected: "Phase 0 status snapshot" appears before "F-01 — Switch JWT".

- [ ] **Step 4: Verify the snapshot table content**

```bash
grep -c "✅ Closed" docs/FINDINGS_ROADMAP.md
```

Expected: `9` (one per closed P0).

- [ ] **Step 5: Commit**

```bash
git add docs/FINDINGS_ROADMAP.md
git commit -m "docs(roadmap): add Phase 0 status snapshot — 9 of 19 P0s closed"
```

---

## Verification (after all tasks land)

- [ ] `README.md` includes a "Phase 0 progress" section pointing to `docs/CODEBASE_REVIEW.md`
- [ ] `CHANGELOG.md` exists at the repo root, follows Keep a Changelog format, lists the 9 closed findings
- [ ] `docs/FINDINGS_ROADMAP.md` Phase 0 chapter has a "Phase 0 status snapshot" subsection with the 9 closed findings
- [ ] All three docs reference `docs/CODEBASE_REVIEW.md` consistently
- [ ] No `docs/plan.md` modifications
- [ ] No per-finding "Acceptance criteria" checkboxes modified in FINDINGS_ROADMAP.md
- [ ] `git log --oneline -4` shows three new commits in order: README, CHANGELOG, FINDINGS_ROADMAP

## Out of scope for this plan

- Automated changelog tooling
- README badges
- Modifying `docs/plan.md`
- Filling in per-finding "Acceptance criteria" checkboxes in FINDINGS_ROADMAP.md
- Adding new entries to the audit doc (`docs/CODEBASE_REVIEW.md`) — already current
