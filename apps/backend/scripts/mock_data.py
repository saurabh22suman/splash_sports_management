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
import uuid
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
        open_start_hour=6,
        open_start_minute=0,
        open_end_hour=21,
        open_end_minute=0,
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
        open_start_hour=5,
        open_start_minute=30,
        open_end_hour=22,
        open_end_minute=0,
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
        open_start_hour=6,
        open_start_minute=0,
        open_end_hour=23,
        open_end_minute=0,
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
        open_start_hour=7,
        open_start_minute=0,
        open_end_hour=20,
        open_end_minute=0,
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
        open_start_hour=5,
        open_start_minute=0,
        open_end_hour=23,
        open_end_minute=0,
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


def _pick_window(status: str, rng: random.Random, now: datetime) -> tuple[datetime, datetime]:
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


# ----- DB helpers (integration-tested) -----

from auth.domain.entities import Tenant, User, UserRole  # noqa: E402
from auth.infrastructure.models import TenantModel, UserModel  # noqa: E402
from auth.infrastructure.password_hasher import Argon2PasswordHasher  # noqa: E402
from auth.infrastructure.repositories import TenantRepository, UserRepository  # noqa: E402
from customer.domain.entities import Customer  # noqa: E402
from customer.infrastructure.models import CustomerModel  # noqa: E402
from customer.infrastructure.repositories import CustomerRepository  # noqa: E402
from facility.application.facility_service import FacilityService  # noqa: E402
from facility.domain.entities import ResourceType  # noqa: E402
from facility.infrastructure.models import AvailabilityRuleModel, FacilityModel, ResourceModel  # noqa: E402
from facility.infrastructure.repositories import (  # noqa: E402
    AvailabilityRuleRepository,
    FacilityRepository,
    ResourceRepository,
)
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from datetime import time


async def seed_tenant(session: AsyncSession, *, stdout: TextIO | None = None) -> "uuid.UUID":
    """Idempotently create the demo tenant. Returns the tenant id."""
    result = await session.execute(select(TenantModel).where(TenantModel.slug == TENANT_SLUG))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing.id

    tenants = TenantRepository(session)
    tenant = Tenant.create(
        name=TENANT_NAME,
        slug=TENANT_SLUG,
        primary_contact_email=TENANT_CONTACT_EMAIL,
    )
    tenant = await tenants.add(tenant)
    # Activate (status moves ONBOARDING -> ACTIVE)
    tenant.activate()
    m = await session.get(TenantModel, tenant.id)
    m.status = tenant.status.value
    await session.flush()
    return tenant.id


async def seed_users(
    session: AsyncSession, tenant_id, *, stdout: TextIO | None = None
) -> dict[str, "uuid.UUID"]:
    """Idempotently create the admin + 3 customer users. Returns {email: user_id}."""
    users_repo = UserRepository(session)
    hasher = Argon2PasswordHasher()

    # Admin user
    admin = await users_repo.get_by_email(tenant_id, ADMIN_EMAIL)
    if admin is None:
        admin = User.create(
            tenant_id=tenant_id,
            email=ADMIN_EMAIL,
            password_hash=hasher.hash(ADMIN_PASSWORD),
            full_name=ADMIN_FULL_NAME,
            roles=[UserRole.TENANT_ADMIN],
        )
        admin = await users_repo.add(admin)

    user_ids: dict[str, "uuid.UUID"] = {ADMIN_EMAIL: admin.id}

    # 3 customer users
    for spec in CUSTOMER_USERS:
        u = await users_repo.get_by_email(tenant_id, spec.email)
        if u is None:
            u = User.create(
                tenant_id=tenant_id,
                email=spec.email,
                password_hash=hasher.hash(spec.password),
                full_name=spec.full_name,
                roles=[UserRole(spec.role)],
            )
            u = await users_repo.add(u)
        user_ids[spec.email] = u.id

    return user_ids


async def seed_customers(
    session: AsyncSession,
    tenant_id,
    user_ids_by_email: dict[str, "uuid.UUID"],
    *,
    stdout: TextIO | None = None,
) -> dict[str, "uuid.UUID"]:
    """Idempotently create 15 customer profiles. Returns {email: customer_id}."""
    customers_repo = CustomerRepository(session)
    users_repo = UserRepository(session)
    hasher = Argon2PasswordHasher()

    # Build a quick lookup of existing customers by email
    existing_rows = (
        (await session.execute(select(CustomerModel).where(CustomerModel.tenant_id == tenant_id)))
        .scalars()
        .all()
    )
    existing_by_email: dict[str, CustomerModel] = {c.email: c for c in existing_rows}

    # Track which emails already have users (from CUSTOMER_USERS)
    # For other customer emails, we'll need to create users

    customer_ids: dict[str, "uuid.UUID"] = {}
    for spec in DEMO_CUSTOMERS:
        if spec.email in existing_by_email:
            customer_ids[spec.email] = existing_by_email[spec.email].id
            continue

        # Check if we already have a user for this email (from CUSTOMER_USERS)
        user_id = user_ids_by_email.get(spec.email)

        # If no user exists for this customer email, create one
        if user_id is None:
            # Create a new user for this customer (without login credentials stored)
            new_user = User.create(
                tenant_id=tenant_id,
                email=spec.email,
                password_hash=hasher.hash("Customer!Demo"),  # Default password
                full_name=spec.full_name,
                roles=[UserRole.CUSTOMER],
            )
            new_user = await users_repo.add(new_user)
            user_id = new_user.id

        customer = Customer.create(
            tenant_id=tenant_id,
            user_id=user_id,
            full_name=spec.full_name,
            email=spec.email,
            phone=_to_e164(spec.phone),
        )
        customer = await customers_repo.add(customer)
        customer_ids[spec.email] = customer.id

    return customer_ids


async def seed_facilities_and_resources(
    session: AsyncSession, tenant_id, *, stdout: TextIO | None = None
) -> dict[str, dict[str, "uuid.UUID"]]:
    """Idempotently create 5 facilities, 1 resource each, and 7 availability rules per resource.

    Returns {facility_slug: {"facility_id": ..., "resource_id": ...}}.
    """
    facilities_repo = FacilityRepository(session)
    resources_repo = ResourceRepository(session)
    rules_repo = AvailabilityRuleRepository(session)
    service = FacilityService(
        session=session,
        facilities=facilities_repo,
        resources=resources_repo,
        rules=rules_repo,
    )

    result: dict[str, dict[str, "uuid.UUID"]] = {}

    for spec in FACILITIES:
        # 1. Facility
        existing_facility = (
            await session.execute(
                select(FacilityModel).where(
                    FacilityModel.tenant_id == tenant_id,
                    FacilityModel.slug == spec.slug,
                )
            )
        ).scalar_one_or_none()
        if existing_facility is not None:
            facility_id = existing_facility.id
        else:
            facility = await service.create_facility(
                tenant_id=tenant_id,
                name=spec.name,
                slug=spec.slug,
                address_line1="1 Aquatic Drive",
                address_line2=None,
                city=spec.city,
                state=spec.state,
                postal_code=spec.postal_code,
                country=spec.country,
                timezone_=spec.timezone,
                phone=spec.phone,
            )
            facility_id = facility.id

        # 2. Resource
        existing_resource = (
            await session.execute(
                select(ResourceModel).where(
                    ResourceModel.facility_id == facility_id,
                    ResourceModel.slug == spec.resource_slug,
                )
            )
        ).scalar_one_or_none()
        if existing_resource is not None:
            resource_id = existing_resource.id
        else:
            resource = await service.create_resource(
                tenant_id=tenant_id,
                facility_id=facility_id,
                name=spec.resource_name,
                slug=spec.resource_slug,
                resource_type=ResourceType(spec.resource_type),
                capacity=spec.capacity,
                attributes=spec.attributes,
            )
            resource_id = resource.id

        # 3. Availability rules (one per day-of-week)
        existing_rules = (
            (
                await session.execute(
                    select(AvailabilityRuleModel).where(
                        AvailabilityRuleModel.resource_id == resource_id
                    )
                )
            )
            .scalars()
            .all()
        )
        existing_days = {r.day_of_week for r in existing_rules}

        start_time = time(spec.open_start_hour, spec.open_start_minute)
        end_time = time(spec.open_end_hour, spec.open_end_minute)
        for day_of_week in range(7):
            if day_of_week in existing_days:
                continue
            await service.create_availability_rule(
                tenant_id=tenant_id,
                resource_id=resource_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                slot_duration_minutes=60,
            )

        result[spec.slug] = {"facility_id": facility_id, "resource_id": resource_id}

    return result


from booking.domain.entities import Booking, BookingStatus, CancellationReason  # noqa: E402
from booking.infrastructure.models import BookingModel  # noqa: E402
from booking.infrastructure.repositories import BookingRepository  # noqa: E402


async def seed_bookings(
    session: AsyncSession,
    tenant_id,
    customer_ids: dict[str, "uuid.UUID"],
    resource_ids: list["uuid.UUID"],
    *,
    stdout: TextIO | None = None,
) -> dict[str, int]:
    """Idempotently create 3-8 bookings per customer with the documented status distribution.

    Returns counts with keys: created, skipped, confirmed, completed, cancelled, no_show.
    """
    bookings_repo = BookingRepository(session)
    rng = random.Random(RNG_SEED)
    now = datetime.now(timezone.utc)

    # 1. Distribute total bookings across customers (3-8 each)
    customer_id_list = list(customer_ids.values())
    per_customer = [rng.randint(3, 8) for _ in customer_id_list]
    total = sum(per_customer)

    # 2. Pre-allocate status counts to match 60/20/10/10 distribution
    target = {
        "confirmed": round(total * 0.60),
        "completed": round(total * 0.20),
        "cancelled": round(total * 0.10),
        "no_show": total - round(total * 0.60) - round(total * 0.20) - round(total * 0.10),
    }
    # Materialize the status sequence
    status_sequence: list[str] = []
    for status, count in target.items():
        status_sequence.extend([status] * count)
    rng.shuffle(status_sequence)

    # Check if bookings already exist for this tenant (idempotency)
    existing_count = (
        (await session.execute(select(BookingModel).where(BookingModel.tenant_id == tenant_id)))
        .scalars()
        .all()
    )
    if existing_count:
        # Bookings already exist, count them and return
        counts = {
            "created": 0,
            "skipped": len(existing_count),
            "confirmed": 0,
            "completed": 0,
            "cancelled": 0,
            "no_show": 0,
        }
        # Just count statuses (don't update, just return)
        for b in existing_count:
            if b.status == "confirmed":
                counts["confirmed"] += 1
            elif b.status == "completed":
                counts["completed"] += 1
            elif b.status == "cancelled":
                counts["cancelled"] += 1
            elif b.status == "no_show":
                counts["no_show"] += 1
        await session.commit()
        return counts

    counts = {
        "created": 0,
        "skipped": 0,
        "confirmed": 0,
        "completed": 0,
        "cancelled": 0,
        "no_show": 0,
    }

    status_idx = 0
    for customer_id, n_bookings in zip(customer_id_list, per_customer, strict=True):
        for _ in range(n_bookings):
            if status_idx >= len(status_sequence):
                break
            status = status_sequence[status_idx]
            status_idx += 1

            start_at, end_at = _pick_window(status, rng, now)
            resource_id = rng.choice(resource_ids)

            # ~30% of bookings get a note
            notes = rng.choice(BOOKING_NOTES) if rng.random() < 0.30 else None
            price_cents = rng.randint(1500, 5000)

            booking = Booking.create(
                tenant_id=tenant_id,
                customer_id=customer_id,
                resource_id=resource_id,
                start_at=start_at,
                end_at=end_at,
                price_cents=price_cents,
                currency="AUD",
                notes=notes,
            )
            try:
                booking = await bookings_repo.add(booking)
            except Exception:
                # Seed data is allowed to overlap (we use add() not add_safe()),
                # so this only fires on hard constraint violations.
                counts["skipped"] += 1
                continue

            # Mutate status if needed
            if status == "completed":
                booking.complete()
                await bookings_repo.update(booking)
            elif status == "cancelled":
                booking.cancel(reason=CancellationReason.CUSTOMER_REQUEST)
                await bookings_repo.update(booking)
            elif status == "no_show":
                booking.mark_no_show()
                await bookings_repo.update(booking)

            counts["created"] += 1
            counts[status] += 1

    await session.commit()
    return counts


# ----- Orchestrator -----

import sys
from typing import TextIO


async def seed_mock_data(
    session: AsyncSession, *, stdout: TextIO = sys.stdout
) -> dict[str, object]:
    """Orchestrator: run all seeders in dependency order.

    Idempotent: skips seed_tenant if demo tenant already exists.
    Returns a dict with tenant_id and seeding results.
    """
    # 1. Seed tenant (with gate: skip if demo tenant already exists)
    from sqlalchemy import select

    existing_tenant = (
        await session.execute(select(TenantModel).where(TenantModel.slug == TENANT_SLUG))
    ).scalar_one_or_none()
    if existing_tenant is not None:
        tenant_id = existing_tenant.id
        print(
            f"Demo tenant already exists: {TENANT_NAME} (slug={TENANT_SLUG}, id={tenant_id})",
            file=stdout,
        )
    else:
        tenant_id = await seed_tenant(session, stdout=stdout)
        print(f"Demo tenant: {TENANT_NAME} (slug={TENANT_SLUG}, id={tenant_id})", file=stdout)

    # 2. Seed users
    user_ids = await seed_users(session, tenant_id, stdout=stdout)
    print(f"Seeded {len(user_ids)} users", file=stdout)

    # 3. Seed customers
    customer_ids = await seed_customers(session, tenant_id, user_ids, stdout=stdout)
    print(f"Seeded {len(customer_ids)} customers", file=stdout)

    # 4. Seed facilities and resources
    fr = await seed_facilities_and_resources(session, tenant_id, stdout=stdout)
    print(f"Seeded {len(fr)} facilities", file=stdout)

    # 5. Seed bookings
    resource_ids = [ids["resource_id"] for ids in fr.values()]
    booking_counts = await seed_bookings(
        session, tenant_id, customer_ids, resource_ids, stdout=stdout
    )
    print(f"Seeded {booking_counts['created']} bookings", file=stdout)

    # 6. Commit all changes
    await session.commit()

    return {
        "tenant_id": tenant_id,
        "user_ids": user_ids,
        "customer_ids": customer_ids,
        "facilities": fr,
        "bookings": booking_counts,
    }
