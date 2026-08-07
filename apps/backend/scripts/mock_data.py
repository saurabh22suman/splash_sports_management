"""Curated mock data for stakeholder demos.

Run via:
    make -C apps/backend seed-mock
or:
    pnpm seed:mock

Idempotent: re-runs are no-ops once the demo tenant + 5 facilities + 15 customers
are seeded. Re-runnable after destructive local testing without rebuilding the
demo from scratch.

Phone number format: the spec lists `+61 4 1200 0001` style with spaces. The
customer entity's `phone` regex (no spaces) requires E.164, so we strip spaces
in `_to_e164()` before passing to `Customer.create`.

Booking status transitions: `Booking.create()` always sets status to CONFIRMED.
For non-confirmed bookings, we call `bookings.add_safe()` (creates CONFIRMED),
then mutate via `b.cancel(reason=...)` / `b.complete()` / `b.mark_no_show()`
and persist via `bookings.update(b)`.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TextIO

# ----- Curated dataset constants (copied from spec) -----

TENANT_SLUG = "demo"
TENANT_NAME = "Demo Sports Club"
TENANT_CONTACT_EMAIL = "admin@demo.splashh.dev"

ADMIN_EMAIL = "admin@demo.splashh.dev"
ADMIN_PASSWORD = "Admin!Demo2026"
ADMIN_FULL_NAME = "Demo Admin"


@dataclass(frozen=True, slots=True)
class _UserSpec:
    email: str
    password: str
    full_name: str
    role: str  # "tenant_admin" | "customer"


CUSTOMER_USERS: tuple[_UserSpec, ...] = (
    _UserSpec("alex@demo.splashh.dev", "Customer!Demo1", "Alex Chen", "customer"),
    _UserSpec("priya@demo.splashh.dev", "Customer!Demo2", "Priya Patel", "customer"),
    _UserSpec("jordan@demo.splashh.dev", "Customer!Demo3", "Jordan Lee", "customer"),
)


@dataclass(frozen=True, slots=True)
class _CustomerSpec:
    full_name: str
    email: str
    phone: str


DEMO_CUSTOMERS: tuple[_CustomerSpec, ...] = (
    # 3 customers share emails with the customer users (so they can log in)
    _CustomerSpec("Alex Chen", "alex@demo.splashh.dev", "+61 4 1200 0001"),
    _CustomerSpec("Priya Patel", "priya@demo.splashh.dev", "+61 4 1200 0002"),
    _CustomerSpec("Jordan Lee", "jordan@demo.splashh.dev", "+61 4 1200 0003"),
    # 12 standalone customers
    _CustomerSpec("Sam Wilson", "sam@example.com", "+61 4 1200 0004"),
    _CustomerSpec("Maya Singh", "maya@example.com", "+61 4 1200 0005"),
    _CustomerSpec("Chris Brown", "chris@example.com", "+61 4 1200 0006"),
    _CustomerSpec("Taylor Reed", "taylor@example.com", "+61 4 1200 0007"),
    _CustomerSpec("Morgan Cole", "morgan@example.com", "+61 4 1200 0008"),
    _CustomerSpec("Riley Adams", "riley@example.com", "+61 4 1200 0009"),
    _CustomerSpec("Casey Bell", "casey@example.com", "+61 4 1200 0010"),
    _CustomerSpec("Drew Murphy", "drew@example.com", "+61 4 1200 0011"),
    _CustomerSpec("Skylar Hayes", "skylar@example.com", "+61 4 1200 0012"),
    _CustomerSpec("Quinn Foster", "quinn@example.com", "+61 4 1200 0013"),
    _CustomerSpec("Avery Stone", "avery@example.com", "+61 4 1200 0014"),
    _CustomerSpec("Reese Walsh", "reese@example.com", "+61 4 1200 0015"),
)


@dataclass(frozen=True, slots=True)
class _FacilitySpec:
    slug: str
    name: str
    city: str
    state: str
    postal_code: str
    country: str
    timezone: str
    phone: str
    resource_slug: str
    resource_name: str
    resource_type: str  # "pool" | "court" | "gym_floor"
    capacity: int
    attributes: dict[str, object]
    open_start_hour: int
    open_end_hour: int
    open_start_minute: int
    open_end_minute: int


FACILITIES: tuple[_FacilitySpec, ...] = (
    _FacilitySpec(
        slug="sydney-aquatic-centre",
        name="Sydney Aquatic Centre",
        city="Sydney",
        state="NSW",
        postal_code="2000",
        country="AU",
        timezone="Australia/Sydney",
        phone="+61 2 0000 0001",
        resource_slug="main-pool",
        resource_name="25m Indoor Pool",
        resource_type="pool",
        capacity=24,
        attributes={"lanes": 8, "length_m": 25, "min_age": 5},
        open_start_hour=6, open_start_minute=0,
        open_end_hour=21, open_end_minute=0,
    ),
    _FacilitySpec(
        slug="melbourne-swim-academy",
        name="Melbourne Swim Academy",
        city="Melbourne",
        state="VIC",
        postal_code="3000",
        country="AU",
        timezone="Australia/Melbourne",
        phone="+61 3 0000 0002",
        resource_slug="outdoor-pool",
        resource_name="50m Outdoor Pool",
        resource_type="pool",
        capacity=32,
        attributes={"lanes": 10, "length_m": 50, "min_age": 3},
        open_start_hour=5, open_start_minute=30,
        open_end_hour=22, open_end_minute=0,
    ),
    _FacilitySpec(
        slug="brisbane-sport-complex",
        name="Brisbane Sport Complex",
        city="Brisbane",
        state="QLD",
        postal_code="4000",
        country="AU",
        timezone="Australia/Brisbane",
        phone="+61 7 0000 0003",
        resource_slug="multi-sport-court",
        resource_name="Multi-Sport Court",
        resource_type="court",
        capacity=20,
        attributes={"surface": "timber", "lighting": True},
        open_start_hour=6, open_start_minute=0,
        open_end_hour=23, open_end_minute=0,
    ),
    _FacilitySpec(
        slug="auckland-marine-pool",
        name="Auckland Marine Pool",
        city="Auckland",
        state="Auckland",
        postal_code="1010",
        country="NZ",
        timezone="Pacific/Auckland",
        phone="+64 9 0000 0004",
        resource_slug="saltwater-pool",
        resource_name="Saltwater Pool",
        resource_type="pool",
        capacity=18,
        attributes={"lanes": 6, "length_m": 25, "min_age": 4},
        open_start_hour=7, open_start_minute=0,
        open_end_hour=20, open_end_minute=0,
    ),
    _FacilitySpec(
        slug="gold-coast-gym",
        name="Gold Coast Fitness",
        city="Gold Coast",
        state="QLD",
        postal_code="4217",
        country="AU",
        timezone="Australia/Brisbane",
        phone="+61 7 0000 0005",
        resource_slug="gym-floor",
        resource_name="Gym Floor",
        resource_type="gym_floor",
        capacity=40,
        attributes={"equipment_count": 60, "has_showers": True},
        open_start_hour=5, open_start_minute=0,
        open_end_hour=23, open_end_minute=0,
    ),
)


BOOKING_NOTES: tuple[str, ...] = (
    "Lane 3 reserved for swim club",
    "Birthday party — 8 kids",
    "Coach-led session",
    "Tournament practice",
    "Private 1-on-1 lesson",
)


BOOKING_STATUS_WEIGHTS: dict[str, float] = {
    "confirmed": 0.60,
    "completed": 0.20,
    "cancelled": 0.10,
    "no_show": 0.10,
}


RNG_SEED = 42


# ----- Pure helpers (unit-tested above) -----


def _to_e164(phone: str) -> str:
    """Strip spaces from a phone number to satisfy the customer entity's E.164 regex."""
    return phone.replace(" ", "")


def _weighted_status(rng: random.Random) -> str:
    """Pick a booking status according to BOOKING_STATUS_WEIGHTS."""
    statuses = list(BOOKING_STATUS_WEIGHTS.keys())
    weights = list(BOOKING_STATUS_WEIGHTS.values())
    return rng.choices(statuses, weights=weights, k=1)[0]


def _pick_window(
    status: str, rng: random.Random, now: datetime
) -> tuple[datetime, datetime]:
    """Pick a random (start_at, end_at) window for the given status.

    CONFIRMED:  80% next 14 days, 20% last 7 days
    COMPLETED:  last 30 days (ending before now)
    CANCELLED:  50% last 14 days, 50% next 14 days
    NO_SHOW:    last 30 days (ending before now)
    """
    if status == "confirmed":
        if rng.random() < 0.80:
            days_offset = rng.randint(0, 13)
        else:
            days_offset = rng.randint(-7, -1)
    elif status == "completed":
        days_offset = rng.randint(-30, -1)
    elif status == "cancelled":
        if rng.random() < 0.50:
            days_offset = rng.randint(-14, -1)
        else:
            days_offset = rng.randint(0, 13)
    elif status == "no_show":
        days_offset = rng.randint(-30, -1)
    else:
        raise ValueError(f"Unknown status: {status}")

    # Anchor on a random hour-at-midnight-on-day-N then layer in the time slot
    base_day = (now + timedelta(days=days_offset)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start = _pick_time_slot(rng, base_day)
    end = start + timedelta(minutes=60)
    return start, end


def _pick_time_slot(rng: random.Random, day: datetime) -> datetime:
    """Pick a time slot in the morning cluster (6-9am) or evening cluster (5-8pm)."""
    if rng.random() < 0.50:
        hour = rng.randint(6, 9)
    else:
        hour = rng.randint(17, 20)
    return day.replace(hour=hour, minute=0, second=0, microsecond=0)
