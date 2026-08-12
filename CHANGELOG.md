# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Phase 0 — Block-Release Security (in progress)

Closed P0 findings (17 of 19):

- **F-01** — RS256 JWT — `ba12454`
- **F-02** — RBAC on all admin endpoints — `ba12454`
- **F-03** — Postgres RLS on all business tables — migration `0005_enable_rls_all_tables`
- **F-04** — JWT secret fail-fast on startup — `ba12454`
- **F-05** — Server-computed booking price — `7af5802`
- **F-06** — RefreshToken lookup filters by `tenant_id` — `7af5802`
- **F-07** — Webhook `tenant_id` resolved from DB — `7af5802`
- **F-08** — Tenant-scoped refund lookup — `7af5802`
- **F-09** — `app_url` setting defined in settings.py — `7af5802`
- **F-10** — Cross-module DB model import removed — `c943664`
- **F-12** — OpenAPI codegen script + `gen:types` / `gen:types:check` npm scripts — `7af5802`
- **F-13** — CI/CD workflows (ci.yml + release.yml) — `7af5802`
- **F-15** — Tenant-isolation test suite — `ba12454`
- **F-16** — Tenant-isolation tests (RLS + matrix) — `7af5802`
- **F-17** — Booking API endpoint tests — `7af5802`
- **F-18** — Admin bookings page (filter/paginate/status) — `7af5802`
- **F-19** — Offline booking queue (IndexedDB) — `7af5802`

Phase 0 exit criteria (see [CODEBASE_REVIEW.md](./docs/CODEBASE_REVIEW.md)):
0 P0 findings open; penetration-test scenarios blocked.

**Remaining 2 P0 findings (real work):**
- **F-11** — Redis Streams outbox wiring (plumbing done, not connected) — `7af5802` partial
- **F-14** — Backup infrastructure (docs exist, scripts/cron missing)

[FINDINGS_ROADMAP.md](./docs/FINDINGS_ROADMAP.md) has the full Phase 0 plan.
