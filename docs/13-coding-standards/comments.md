# Comments

> When to comment: explaining WHY, not WHAT. Anti-pattern: redundant comments. TODO/FIXME/XXX conventions. Code reference: never comment-out, delete.

This document defines when and how to comment code. We prioritize comments that explain rationale, not code that explains itself.

---

## Comment Philosophy

> **Rule** — If you need to explain WHAT the code does, the code is poorly written. Rewrite the code instead. Comments should explain WHY.

```python
# BAD: Comments explaining WHAT (code should be clear)
# Loop through bookings and add to list if active
active_bookings = []
for booking in bookings:
    if booking.status == "active":  # Check if active
        active_bookings.append(booking)  # Add to list


# GOOD: No comments needed (code is self-explanatory)
active_bookings = [b for b in bookings if b.status == "active"]


# GOOD: Comment explaining WHY (non-obvious rationale)
# Sorting by end_time ensures fair slot allocation when
# multiple customers request the same time slot.
bookings.sort(key=lambda b: b.end_time)


# We use bcrypt with cost 12 because cost 10 was vulnerable
# to GPU-accelerated attacks (2023 research).
# See: https://example.com/bcrypt-cost-study
HASH_COST = 12
```

---

## When to Comment

### 1. Business Logic Rationale

```python
# Tier 1 members get 20% discount to match competitor pricing.
# This was a strategic decision by Product in Q3 2024.
def calculate_discount(member_tier: str, base_price: Decimal) -> Decimal:
    if member_tier == "tier_1":
        return base_price * Decimal("0.20")
    return Decimal("0")


# Cancellation within 24 hours charges 50% because courts cannot
# be reliably rebooked on short notice during peak hours.
def calculate_cancellation_fee(
    booking: Booking,
    cancelled_at: datetime,
) -> Money:
    hours_until = (booking.start_time - cancelled_at).total_seconds() / 3600
    if hours_until < 24:
        return booking.total_amount * Decimal("0.50")
    return Money.ZERO
```

### 2. Non-Obvious Workarounds

```python
# Workaround for PostgreSQL 14 connection timeout issue.
# See: https://github.com/psycopg/psycopg2/issues/1288
# Fixed in psycopg2 2.9.4, but we support 2.9.3 for RHEL 8.
import time
time.sleep(0.1)  # Allow connection to stabilize


# SQLite doesn't support RETURNING clause before version 3.35.
# This polyfill emulates the behavior.
if db_version < (3, 35):
    cursor.execute("SELECT last_insert_rowid()")
    return cursor.fetchone()[0]
```

### 3. Complex Algorithms

```python
# Recursive implementation with memoization for O(n) performance.
# The naive recursive solution is O(2^n) which times out for n > 30.
# This uses the recurrence relation: f(n) = f(n-1) + f(n-2)
def fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number efficiently."""
    if n <= 1:
        return n

    memo: dict[int, int] = {0: 0, 1: 1}

    def fib(n: int) -> int:
        if n in memo:
            return memo[n]
        memo[n] = fib(n - 1) + fib(n - 2)
        return memo[n]

    return fib(n)
```

### 4. External References

```python
# Stripe API reference for payment intents:
# https://stripe.com/docs/api/payment_intents
# We use payment_intent.created because it's more reliable than
# webhook events for our reconciliation process.
async def reconcile_payment(payment_intent_id: str) -> None:
    ...
```

---

## Anti-Pattern: Redundant Comments

> **Anti-pattern** — Never comment what is already obvious from reading the code.

```python
# BAD: Redundant comments
# Increment counter
counter += 1

# Get user by ID
user = get_user(user_id)

# If booking is active, return true
if booking.is_active:
    return True

# Return the booking
return booking


# BAD: Commented-out code
# def old_function(x):
#     return x * 2


# BAD: Self-fulfilling comments
# This is a function
def do_something():
    """Do something."""
    pass
```

---

## TODO/FIXME/XXX Conventions

Use standardized prefixes for actionable comments:

| Prefix | Meaning | Action |
|---|---|---|
| TODO | Work to be done | Plan to implement |
| FIXME | Known bug that needs fix | Fix before merge |
| XXX | Critical problem | Fix immediately |
| HACK | Workaround or ugly fix | Refactor when possible |
| NOTE | Important information | Be aware |

```python
# TODO(sarah): Implement waitlist functionality.
# We're deprioritizing this for the v1 launch but need it for v2.
def join_waitlist(booking_request: BookingRequest) -> WaitlistEntry:
    ...


# FIXME(john): This query is slow for tenants with 10k+ bookings.
# Need to add an index on (tenant_id, status, created_at).
# Tracking in JIRA-1234.
def get_active_bookings(tenant_id: str) -> list[Booking]:
    ...


# XXX: This creates a race condition under high load.
# We need to add distributed locking. Issue: JIRA-4567
async def reserve_slot(slot: TimeSlot) -> Reservation:
    ...


# HACK: Temporary workaround for Stripe webhook delay.
# Remove after Stripe fixes webhook ordering.
# Tracking: JIRA-7890
await asyncio.sleep(2)  # Allow webhook to propagate


# NOTE: This function is called from multiple places.
# Any changes need careful review to avoid breaking callers.
def calculate_price(booking: Booking) -> Money:
    ...
```

> **Rule** — All TODO/FIXME/XXX comments must have a JIRA ticket or GitHub issue reference.

---

## Comment Style

```python
# Style: Sentence case, period at end for sentences.
# Use full sentences for complex explanations.

# Good
# Sorting by priority ensures high-value customers are processed first.
# This improves customer satisfaction for our enterprise tier.

# Also good for short comments (no period needed)
# TODO: Add caching for frequently accessed courts


# Bad: No period, inconsistent
# sorting by priority
# ensures high value customers
```

---

## Docstrings vs. Comments

- **Docstrings**: Document public APIs (functions, classes, modules)
- **Comments**: Explain implementation details in private code

```python
def calculate_total(bookings: list[Booking]) -> Money:
    """Calculate total amount for a list of bookings.

    This is a public method used by multiple services.

    Args:
        bookings: List of bookings to sum.

    Returns:
        Total amount as Money.

    Raises:
        ValueError: If bookings is empty.
    """
    # Implementation detail: we use sum() with generator
    # because it's faster than reduce() for this case.
    return sum((b.total_amount for b in bookings), Money.ZERO)
```

---

## Summary

| Rule | Implementation |
|---|---|
| Explain WHY | Not WHAT the code does |
| Avoid redundant | If code is clear, don't comment |
| Use TODO/FIXME/XXX | With issue references |
| No commented-out code | Delete instead |
| Be concise | One sentence for simple, paragraphs for complex |

---

## Related Documents

- [Python Style](./python-style.md) — Formatting rules
- [Documentation](./documentation.md) — Docstring standards
- [Code Review Checklist](./code-review-checklist.md) — Review standards
