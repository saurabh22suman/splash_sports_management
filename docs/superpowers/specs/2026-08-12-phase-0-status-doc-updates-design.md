# Phase 0 — Project-Level Doc Updates (Status Snapshot)

> **For agentic workers:** This is a design spec. After approval, use superpowers:writing-plans to produce an implementation plan.

**Date:** 2026-08-12
**Status:** Design (approved)
**Scope:** Docs-only. Reflect Phase 0 progress (8 P0 closures: F-01, F-02, F-03, F-04, F-05, F-07, F-08, F-10, F-15) in three project-level surfaces: README, a new CHANGELOG, and the findings roadmap.

---

## Context

The Phase 0 audit (`docs/CODEBASE_REVIEW.md`, 2026-08-11) flagged 19 P0 findings. Over the past session, Sub-projects A, B, and C1 closed 9 of them:

| Finding | Closing commit | Sub-project |
|---|---|---|
| F-01 (RS256) | `ba12454` | A |
| F-02 (RBAC) | `ba12454` | A |
| F-03 (RLS) | `0005_enable_rls_all_tables` migration | A |
| F-04 (JWT secret) | `ba12454` | A |
| F-05 (price_cents) | `7af5802` | B |
| F-07 (webhook tenant_id) | `7af5802` | B |
| F-08 (refund lookup) | `7af5802` | B |
| F-10 (cross-module import) | `c943664` | C1 |
| F-15 (tenant-isolation tests) | `ba12454` (`requires_role` group) | A |

Wait — that's 9 entries. F-15 is bundled with the `ba12454` group. The audit doc records F-15 as `✅ Resolved (requires_role` tests + tenant-isolation tests now pass; test isolation bug fixed in this plan)`. Treating F-15 as part of the A closure block is consistent.

The audit doc (`docs/CODEBASE_REVIEW.md`) is the source of truth — it already lists the status column. The three docs in scope have **no visibility** into Phase 0 progress. A reader landing on the repo's README sees no sign that the project is mid-Phase-0; a reader looking at FINDINGS_ROADMAP.md sees no closed-finding markers.

---

## Goal

Make Phase 0 progress discoverable from three project-level surfaces without duplicating the audit doc's content. The audit doc remains the source of truth; the three updated docs are pointers.

---

## Approach

Hybrid: **light inline progress + pointers to the audit doc**. No full duplication of finding status.

### Why hybrid

- **Pure pointers** (audit doc only): lowest maintenance but invisible to readers who don't know to look at the audit doc. A new contributor reading the README has no signal that the project is mid-Phase-0.
- **Full duplication** (every roadmap finding's checkboxes filled): most visible but creates drift risk — three docs must stay in sync with the audit doc. The user has already accepted the audit doc as the source of truth (Sub-projects B and C1 closed findings by editing only the audit doc).
- **Hybrid**: a one-line summary plus a link is enough to make progress discoverable without creating a sync burden.

---

## Components

### 1. README.md — add a "Phase 0 progress" subsection

Insert after the "What's in this prototype" table (line 114), before the "Next phase" heading (line 115). Content:

```markdown
## Phase 0 progress

Phase 0 — Block-Release Security is in progress. 9 of 19 P0 findings closed
(RBAC, RLS, JWT, price-cents, webhook tenant-id, refund lookup, cross-module
import, tenant-isolation tests). See [CODEBASE_REVIEW.md](./docs/CODEBASE_REVIEW.md)
for the up-to-date status of every finding.
```

This is a single paragraph. No list, no table. The audit doc is the source of truth.

### 2. CHANGELOG.md — create from scratch

Follow [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) format. Future entries will be appended as work proceeds.

Initial content:

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

### 3. docs/FINDINGS_ROADMAP.md — add a "Phase 0 status snapshot" subsection

Insert at the top of the Phase 0 chapter (line 37, after the "Phase 0 — Block-Release Security" header, before any `### F-xx` subsection). Content:

```markdown
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

The remaining 11 P0 findings are unchanged in this roadmap; their work plans
below remain the source of truth for scope.
```

---

## Files modified

- `README.md` — add "Phase 0 progress" subsection (≈5 lines)
- `CHANGELOG.md` — **new file** (≈30 lines)
- `docs/FINDINGS_ROADMAP.md` — add "Phase 0 status snapshot" subsection (≈15 lines)

## Files NOT modified

- `docs/CODEBASE_REVIEW.md` — already current; remains the source of truth
- `docs/plan.md` — out of scope (not in user request)
- Per-finding "Acceptance criteria" checkboxes in FINDINGS_ROADMAP.md — those are per-finding work plans, not status trackers

---

## Verification

- [ ] `README.md` includes a "Phase 0 progress" section pointing to the audit doc
- [ ] `CHANGELOG.md` exists at the repo root, follows Keep a Changelog format, lists the 9 closed findings
- [ ] `docs/FINDINGS_ROADMAP.md` Phase 0 chapter has a "Phase 0 status snapshot" table with the 9 closed findings
- [ ] No other docs modified
- [ ] All three docs reference each other / the audit doc consistently

---

## Out of scope

- Adding CI/release tooling that auto-updates CHANGELOG.md from commit messages
- Automated badges in README
- Updating `docs/plan.md` (user did not request)
- Filling in per-finding "Acceptance criteria" checkboxes in FINDINGS_ROADMAP.md (drift risk)

---

## Risk

Very low. Docs-only. No code changes. The audit doc is the source of truth, so even if the three docs drift, the project state is unambiguous.
