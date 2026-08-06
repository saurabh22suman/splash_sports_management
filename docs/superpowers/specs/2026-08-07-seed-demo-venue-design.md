# Seed demo venue — design

**Date:** 2026-08-07
**Status:** approved
**Owner:** soloengine

## Goal

Make the app immediately demoable on a fresh dev DB by seeding a single
representative venue — **Splash Sports Club** — with one swimming pool resource
and standard availability rules, so that after running `pnpm seed:demo` a
customer can log in, browse to `/book`, see the facility, and create a booking
without any manual setup.

## Scope

In scope:

- One Python seed script runnable from the repo root.
- Idempotent on re-run (safe to invoke repeatedly).
- Targets the first/only tenant in the dev DB.
- Reuses `FacilityService` so the seed flows through the same validation and
  event handlers as the real API path.

Out of scope:

- Auto-seeding on tenant registration. The product remains multi-tenant; the
  demo data lives only where the operator runs the script.
- Migrating to single-tenant mode.
- Payment integration, notification wiring, additional facilities or sports.
- Refactoring `FacilityService` or `AvailabilityRule`.

## Data seeded

### Facility

| Field        | Value                  |
|--------------|------------------------|
| tenant_id    | from tenant lookup     |
| slug         | `splash-sports-club` (idempotency key) |
| name         | `Splash Sports Club`   |
| address      | `123 Aquatic Drive`    |
| city         | `Sydney`               |
| state        | `NSW`                  |
| postal_code  | `2000`                 |
| country      | `AU`                   |
| timezone     | `Australia/Sydney`     |
| phone        | `+61 2 0000 0000`      |

### Resource (1 × Pool)

| Field        | Value                                       |
|--------------|---------------------------------------------|
| tenant_id    | from above                                  |
| facility_id  | from above                                  |
| slug         | `main-pool`                                 |
| name         | `Main Pool`                                 |
| resource_type| `ResourceType.POOL`                         |
| capacity     | `20`                                        |
| attributes   | `{ "lanes": 6, "length_m": 25, "min_age": 5 }` |

### AvailabilityRule (7 rows — one per day_of_week)

For `day_of_week` ∈ `0..6`:

| Field                 | Value     |
|-----------------------|-----------|
| tenant_id             | from above|
| resource_id           | from above|
| start_time            | `06:00`   |
| end_time              | `22:00`   |
| slot_duration_minutes | `60`      |
| valid_from            | `None`    |
| valid_until           | `None`    |

## Code structure

**New file:** `apps/backend/scripts/seed_demo.py`

The script:

1. Bootstraps the same async DB session factory the app uses.
2. Picks the first tenant: `SELECT * FROM tenants ORDER BY created_at ASC LIMIT 1`.
   If none → print `No tenant found. Run register-tenant first.` and exit 1.
3. Idempotency check:
   `SELECT facility WHERE tenant_id = :t AND slug = 'splash-sports-club'`.
   If found → print `Already seeded for tenant <slug>; nothing to do.` and exit 0.
4. Calls `FacilityService.create_facility(...)` with the values above.
5. Calls `FacilityService.create_resource(...)` with the pool values.
6. Loops `day_of_week` in `0..6` and calls
   `FacilityService.create_availability_rule(...)` for each.
7. Commits the session.
8. Prints a summary line and exits 0.

**Package script:** add `seed:demo` to the repo-root `package.json` (or
`apps/backend/pyproject.toml` — whichever pattern the repo already uses for
Python scripts) so the operator runs `pnpm seed:demo`.

## Error handling

| Condition                              | Behavior                                                  |
|----------------------------------------|-----------------------------------------------------------|
| No tenant in DB                        | print message, exit 1                                     |
| Facility slug already exists           | print message, exit 0 (no-op)                             |
| `Validation` / `Conflict` from service | bubble up with traceback, exit 1 (loud failures preferred)|
| Unexpected DB error                    | bubble up; script does not swallow                       |

## Testing (TDD)

Three tests, written against an ephemeral test DB:

1. **`seed_demo creates facility, pool, and 7 availability rules when DB has
   one tenant and no matching facility`**
   - Pre-seed one tenant.
   - Call `seed_demo(session)`.
   - Assert: exactly one `Facility` with slug `splash-sports-club`,
     exactly one `Resource` with type `POOL`, exactly seven
     `AvailabilityRule` rows for that resource (one per `day_of_week` 0–6).

2. **`seed_demo is a no-op when facility slug already exists`**
   - Pre-seed one tenant and one `Facility` with slug `splash-sports-club`.
   - Call `seed_demo(session)`.
   - Assert: facility count unchanged, no resources created, no rules created,
     no exception.

3. **`seed_demo returns 1 with a clear message when no tenant exists`**
   - Empty tenants table.
   - Call `seed_demo(session)`.
   - Assert: returns 1, captured stdout contains the substring `No tenant found`.

## Why this approach

- **Reuses services** — keeps the seed aligned with the real API path. If
  `AvailabilityRule` validation rules change, the seed follows automatically.
- **No Alembic data migration** — data migrations in Alembic are an
  anti-pattern (mix schema and data, hard to skip on prod); a runnable script
  is the standard answer for dev/demo seeds.
- **Slug-based idempotency** — `Facility.slug` is unique per tenant in the
  domain, so a single SELECT is enough to make the seed a no-op on re-run.

## Open follow-ups (not part of this spec)

- Add a `BookingRule` concept if/when the booking module needs cancellation
  windows and max-advance rules. Out of scope for the demo seed.
- Wire `pnpm seed:demo` into the repo's `pnpm db:reset` flow so a single
  command brings up a demoable environment.