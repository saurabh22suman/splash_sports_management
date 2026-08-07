# Mock Data Seed for Stakeholder Demos — design

**Date:** 2026-08-07
**Status:** approved
**Owner:** soloengine

## Goal

Populate the local DB with curated, realistic data so stakeholder demos
look populated instead of empty. After this lands, `/book` shows 5
facility cards, `/book/bookings` shows varied booking statuses, and the
admin can log in to see the same data from the tenant_admin view.

## Scope

**In scope:**
- New module `apps/backend/scripts/mock_data.py` with curated datasets
- Extend `apps/backend/scripts/seed_demo.py` with a `--mock` flag that
  invokes the mock data seeder
- CLI surface: `pnpm seed:mock` and `make -C apps/backend seed-mock`
- One integration test file:
  `apps/backend/tests/integration/test_mock_data_seed.py`

**Out of scope (deferred):**
- Membership module (not implemented; per peer review 2026-08-07)
- Payments, notifications, analytics modules
- Photos / avatars — placeholder URLs only (DiceBear + picsum.photos)
- Faker-based random generation — datasets are hand-curated
- Multiple tenants with demo data — exactly one `demo` tenant
- A "reset" or "wipe" command — destructive operations live in a
  separate script (not part of this spec)

## Approach

Single-file extension of `seed_demo.py` per the user's chosen
approach (Option A). Module-level constants for the curated data
(facilities, users, customers, bookings). Sub-functions per entity
type. Idempotency at every step.

## File structure

```
apps/backend/scripts/
├── seed_demo.py          # modified: add --mock flag, delegate to mock_data
└── mock_data.py          # new: FACILITIES, USERS, CUSTOMERS, BOOKINGS +
                          #       async seed_mock_data(session, *, stdout)

apps/backend/tests/integration/
└── test_mock_data_seed.py  # new: 4 tests (happy path, idempotency,
                            #       existing-tenant-noop, status mix)

apps/backend/Makefile     # modified: add seed-mock target
package.json              # modified: add "seed:mock" script
```

## Seeding order

1. **Tenant** — slug `demo`, name `Demo Sports Club`. Skip if exists.
2. **Admin user** — `admin@demo.splashh.dev`, role `tenant_admin`,
   password `Admin!Demo2026`. Skip if email exists for this tenant.
3. **Customer users** — 3 users (alex/priya/jordan), role `customer`.
   Skip if email exists.
4. **Customers** — 15 customer profiles (linked to one of the 3 customer
   users via shared email). Skip if email exists.
5. **Facilities** — 5 facilities in AU/NZ. Skip if slug exists for tenant.
6. **Resources** — 1 per facility (pool, court, gym floor, etc.). Skip
   if slug exists for facility.
7. **Availability rules** — 7 per resource (one per day-of-week). Skip
   if `(resource_id, day_of_week)` already has a rule.
8. **Bookings** — generated per the rules below. Skip if a booking
   exists with the same `(customer_id, resource_id, start_at)` triple.

## Curated data

### Users (4)

| Email | Role | Password |
|---|---|---|
| `admin@demo.splashh.dev` | `tenant_admin` | `Admin!Demo2026` |
| `alex@demo.splashh.dev` | `customer` | `Customer!Demo1` |
| `priya@demo.splashh.dev` | `customer` | `Customer!Demo2` |
| `jordan@demo.splashh.dev` | `customer` | `Customer!Demo3` |

### Facilities (5)

| Slug | Name | City | Country | Resource | Capacity | Open hours |
|---|---|---|---|---|---|---|
| `sydney-aquatic-centre` | Sydney Aquatic Centre | Sydney NSW | AU | 25m indoor pool | 24 | 6:00-21:00 |
| `melbourne-swim-academy` | Melbourne Swim Academy | Melbourne VIC | AU | 50m outdoor pool | 32 | 5:30-22:00 |
| `brisbane-sport-complex` | Brisbane Sport Complex | Brisbane QLD | AU | Multi-sport court | 20 | 6:00-23:00 |
| `auckland-marine-pool` | Auckland Marine Pool | Auckland NZ | Saltwater pool | 18 | 7:00-20:00 |
| `gold-coast-gym` | Gold Coast Fitness | Gold Coast QLD | AU | Gym floor | 40 | 5:00-23:00 |

Each gets:
- timezone matching the country (`Australia/Sydney`, `Australia/Melbourne`,
  `Australia/Brisbane`, `Pacific/Auckland`)
- realistic phone `+61 2 0000 0000` style (placeholder numbers)
- 7 availability rules (one per day-of-week), `slot_duration_minutes=60`
- resource attributes: pools get `{lanes, length_m, min_age}`, court gets
  `{surface, lighting}`, gym gets `{equipment_count, has_showers}`

### Customers (15)

Hand-picked mix of realistic Australian/NZ names:

```python
DEMO_CUSTOMERS = [
    ("Alex Chen", "alex@demo.splashh.dev", "+61 4 1200 0001"),
    ("Priya Patel", "priya@demo.splashh.dev", "+61 4 1200 0002"),
    ("Jordan Lee", "jordan@demo.splashh.dev", "+61 4 1200 0003"),
    ("Sam Wilson", "sam@example.com", "+61 4 1200 0004"),
    ("Maya Singh", "maya@example.com", "+61 4 1200 0005"),
    ("Chris Brown", "chris@example.com", "+61 4 1200 0006"),
    ("Taylor Reed", "taylor@example.com", "+61 4 1200 0007"),
    ("Morgan Cole", "morgan@example.com", "+61 4 1200 0008"),
    ("Riley Adams", "riley@example.com", "+61 4 1200 0009"),
    ("Casey Bell", "casey@example.com", "+61 4 1200 0010"),
    ("Drew Murphy", "drew@example.com", "+61 4 1200 0011"),
    ("Skylar Hayes", "skylar@example.com", "+61 4 1200 0012"),
    ("Quinn Foster", "quinn@example.com", "+61 4 1200 0013"),
    ("Avery Stone", "avery@example.com", "+61 4 1200 0014"),
    ("Reese Walsh", "reese@example.com", "+61 4 1200 0015"),
]
```

3 customers share an email with the customer users (so the customer
users can see "their" bookings when they log in). The other 12 are
standalone customers that the admin sees but the customer users don't.

### Bookings (~50)

For each customer, generate 3-8 bookings. Date window is split by status:

- **CONFIRMED** — 60% of total bookings. Spread across the next 14 days
  (anchored to "now" at script execution time); ~20% placed in the last
  7 days (recent past, still considered upcoming for the demo).
- **COMPLETED** — 20% of total. Placed in the last 30 days, ending before
  "now".
- **CANCELLED** — 10% of total. Spread across the last 14 days and the
  next 14 days.
- **NO_SHOW** — 10% of total. Placed in the last 30 days, ending before
  "now".

The above is the intended distribution. The integration test asserts
ranges (50-70% / 15-25% / 5-15% / 5-15%) to absorb small variance from
random sampling.

Time slots: clustered around 6-9am and 5-8pm local time. Duration: 60
minutes. Prices: $15-$50 AUD (price_cents = 1500-5000). Currency: AUD.

Notes: ~30% of bookings get a note like:
- `"Lane 3 reserved for swim club"`
- `"Birthday party — 8 kids"`
- `"Coach-led session"`

## Idempotency strategy

Each entity has a unique natural key:

| Entity | Skip if exists when |
|---|---|
| Tenant | `slug == 'demo'` exists |
| User | `tenant_id + email` already has a user |
| Customer | `tenant_id + email` already has a customer |
| Facility | `tenant_id + slug` already has a facility |
| Resource | `facility_id + slug` already has a resource |
| AvailabilityRule | `(resource_id, day_of_week)` already has a rule |
| Booking | `(customer_id, resource_id, start_at)` already has a booking |

Each sub-function returns a count of `{created, skipped}` so the
final stdout summary can show both.

## CLI surface

### `seed_demo.py` extended

```python
# at the bottom of seed_demo.py
async def _main(mock: bool = False) -> int:
    # ... bootstrap engine/session ...
    if mock:
        return await seed_mock_data(session)
    return await seed_demo(session)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Seed stakeholder demo data")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main(mock=args.mock)))
```

### `Makefile`

```makefile
seed-mock:
	PYTHONPATH=src uv run python scripts/seed_demo.py --mock
```

### `package.json`

```json
"seed:mock": "make -C apps/backend seed-mock"
```

### Stdout output

```
Demo tenant: demo (id=<uuid>)
Admin: admin@demo.splashh.dev / Admin!Demo2026
Facilities: 5 created, 0 skipped (Sydney, Melbourne, Brisbane, Auckland, Gold Coast)
Customers: 15 created, 0 skipped
Bookings: 47 created, 0 skipped (29 confirmed, 10 completed, 5 cancelled, 3 no_show)
```

## Testing strategy

`apps/backend/tests/integration/test_mock_data_seed.py`:

1. **test_seed_mock_data_creates_expected_shape**
   - Empty DB, run `seed_mock_data`, assert:
     - 1 tenant with slug `demo`
     - 4 users (1 admin + 3 customer)
     - 15 customers
     - 5 facilities
     - 5 resources
     - 35+ availability rules (≥7 per resource)
     - 30+ bookings

2. **test_seed_mock_data_is_idempotent**
   - Run `seed_mock_data` twice, assert counts unchanged

3. **test_seed_mock_data_skips_existing_demo_tenant**
   - Pre-seed a tenant with slug `demo` (different name)
   - Run `seed_mock_data`, assert:
     - The pre-existing tenant is unchanged
     - No new facilities/users/bookings are created under it

4. **test_seed_mock_data_booking_status_distribution**
   - Run `seed_mock_data`, query bookings grouped by status
   - Assert roughly: 50-70% CONFIRMED, 15-25% COMPLETED, 5-15% CANCELLED, 5-15% NO_SHOW

## Done criteria

- [ ] `pnpm seed:mock` against an empty DB creates the documented shape
- [ ] Re-running `pnpm seed:mock` is a no-op (counts unchanged)
- [ ] `pnpm --filter backend test` (incl. integration) stays green
- [ ] Login as `admin@demo.splashh.dev` → admin sees the 5 facilities
- [ ] Login as `alex@demo.splashh.dev` → customer sees their bookings
- [ ] `/book` shows 5 facility cards (not the empty state)
- [ ] Spec + plan committed to git

## Why this approach

- **Single-file extension** keeps the existing pattern (`seed_demo.py`)
  and avoids growing the scripts directory with new structure for ~300
  lines of code.
- **Idempotency at every step** means stakeholders can re-run the seed
  after destructive local testing without rebuilding the demo from
  scratch, and the demo survives a `docker compose down -v` if they
  bring up a fresh DB.
- **Hand-curated data** looks intentional in screenshots. Faker would
  produce names like "John Doe" and "Lorem Ipsum Avenue" — bad for
  stakeholder demos.
- **Dedicated `demo` tenant** means no risk of polluting a tenant that
  has real data. Re-runnable without side effects on other tenants.

## Open follow-ups (not part of this spec)

- Visual regression baseline at `e2e/screenshots/polish-baseline/`
  (mentioned in the UI polish spec, not yet captured).
- Membership / payments modules (per peer review).
- A separate "reset" script that wipes the `demo` tenant before
  re-seeding, for cases where someone wants to regenerate booking
  dates anchored to "today".
