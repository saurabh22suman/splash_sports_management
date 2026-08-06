# Type Hints

> Strict mypy. Use `from __future__ import annotations`. Prefer specific types (Sequence vs. list, Mapping vs. dict). Avoid `Any`.

This document defines our type hinting standards. We use strict type checking because it catches bugs at development time, documents the API, and enables refactoring with confidence.

---

## Strict Type Checking

We enable strict mode in mypy:

```toml
# mypy.ini
[mypy]
python_version = 3.11
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_calls = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true

# Ignore common third-party libraries without stubs
[mypy-pytest.*]
ignore_missing_imports = true

[mypy-sqlalchemy.*]
ignore_missing_imports = true
```

---

## Future Annotations

Use `from __future__ import annotations` for forward references:

```python
# Required at the top of EVERY file
from __future__ import annotations

from datetime import datetime
from decimal import Decimal


class Booking:
    """A booking for a court."""

    id: str
    customer_id: str
    court_id: str
    start_time: datetime
    end_time: datetime
    total_amount: Decimal
    status: BookingStatus

    def calculate_price(self, rate: Decimal) -> Decimal:
        """Calculate price based on hourly rate."""
        # No forward reference needed!
        return self.total_amount * rate


# Without `from __future__ import annotations`:
# def calculate_price(self, rate: Decimal) -> 'Decimal':  # Quote needed
```

---

## Prefer Specific Types

Use the most specific type available:

| Generic | Specific | When to Use |
|---|---|---|
| `list` | `list[T]` | Always specify T |
| `list` | `Sequence` | If read-only and type doesn't matter |
| `list` | `Collection` | If iterating only |
| `dict` | `dict[K, V]` | Always specify K and V |
| `dict` | `Mapping` | If read-only |
| `dict` | `dict[str, Any]` | Only if truly heterogeneous |
| `tuple` | `tuple[A, B, C]` | Fixed length |
| `set` | `set[T]` | Always specify T |
| `Iterable` | `Generator` | If yielding values |

```python
# GOOD: Specific types
def process_bookings(bookings: list[Booking]) -> dict[str, list[Booking]]:
    """Group bookings by court."""
    result: dict[str, list[Booking]] = defaultdict(list)
    for booking in bookings:
        result[booking.court_id].append(booking)
    return dict(result)


def get_booking_ids(customer_id: str) -> list[str]:
    """Get all booking IDs for a customer."""
    ...


def find_booking(query: str) -> Booking | None:
    """Find booking by ID or return None."""
    ...


# BAD: Too generic
def process_bookings(bookings: list) -> dict:
    result = {}
    for booking in bookings:
        result.setdefault(booking.court_id, []).append(booking)
    return result
```

---

## Avoid Any

`Any` defeats the purpose of type checking. Avoid it entirely:

```python
# BAD: Any defeats type checking
def process_data(data: Any) -> Any:
    return data

# GOOD: Use object with protocols or specific types
def process_data(data: dict[str, object]) -> dict[str, object]:
    return data

# GOOD: Use Protocol for duck typing
from typing import Protocol


class HasId(Protocol):
    id: str


def find_by_id(items: list[HasId], target_id: str) -> HasId | None:
    """Find item by ID."""
    for item in items:
        if item.id == target_id:
            return item
    return None
```

---

## Type Aliases

Create aliases for clarity and reuse:

```python
# Type aliases for domain concepts
from decimal import Decimal
from datetime import datetime

# Money
Money = Decimal  # or use a custom class

# Identifiers
TenantId = str
UserId = str
BookingId = str
CourtId = str

# Time
Timestamp = datetime

# Statuses
BookingStatus = Literal["pending", "confirmed", "cancelled", "completed"]
PaymentStatus = Literal["pending", "completed", "failed", "refunded"]

# Collections
BookingList = list[Booking]
CourtMap = dict[CourtId, Court]


# Usage
def get_tenant_bookings(tenant_id: TenantId) -> BookingList:
    """Get all bookings for a tenant."""
    ...
```

---

## Generic Types for Collections

Use generics properly:

```python
# GOOD: Proper generic types
def first_item(items: Sequence[str]) -> str | None:
    """Get first item or None."""
    return items[0] if items else None


def lookup(
    mapping: Mapping[str, int],
    key: str,
    default: int = 0,
) -> int:
    """Look up value in mapping."""
    return mapping.get(key, default)


def transform(items: Iterable[int]) -> Generator[str, None, None]:
    """Transform items to strings."""
    for item in items:
        yield f"item_{item}"


# BAD: Missing type parameters
def first_item(items):
    return items[0] if items else None
```

---

## Optional vs. None

Use `Optional[T]` (or `T | None`) instead of `None` as default:

```python
# GOOD: Explicit Optional
def find_court(court_id: str | None = None) -> Court | None:
    """Find court by ID, or return None."""
    if court_id is None:
        return None
    return db.query(Court).get(court_id)


# GOOD: Using Optional
from typing import Optional


def get_booking(booking_id: str) -> Optional[Booking]:
    ...


# BAD: Confusing default with type
def find_court(court_id: str = None) -> Court:  # Type is wrong!
    return db.query(Court).get(court_id)
```

---

## Literal Types

Use `Literal` for exact string/enum values:

```python
from typing import Literal


def set_booking_status(
    booking_id: str,
    status: Literal["pending", "confirmed", "cancelled"],
) -> Booking:
    """Set booking status."""
    ...


# Can also use Enum for more complex cases
from enum import Enum


class BookingStatusEnum(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


def set_booking_status_enum(
    booking_id: str,
    status: BookingStatusEnum,
) -> Booking:
    """Set booking status using enum."""
    ...
```

---

## Code Examples

### Complex Type Hints

```python
from collections.abc import Callable, Awaitable
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator, overload


# Callable types
PaymentProcessor = Callable[[Money], Awaitable[PaymentResult]]


async def process_with_retry(
    processor: PaymentProcessor,
    amount: Money,
    max_retries: int = 3,
) -> PaymentResult:
    """Process payment with retry logic."""
    for attempt in range(max_retries):
        try:
            return await processor(amount)
        except PaymentError:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)


# Async generators
async def stream_bookings(
    tenant_id: TenantId,
) -> AsyncGenerator[Booking, None]:
    """Stream bookings for a tenant."""
    async for booking in db.stream(Booking).where(tenant_id=tenant_id):
        yield booking


# Overloads for different argument types
@overload
def parse_amount(value: str) -> Decimal: ...


@overload
def parse_amount(value: int) -> Decimal: ...


@overload
def parse_amount(value: Decimal) -> Decimal: ...


def parse_amount(value: str | int | Decimal) -> Decimal:
    """Parse amount from various types."""
    return Decimal(str(value))
```

---

## Summary

| Rule | Standard |
|---|---|
| mypy | Strict mode |
| Future imports | `from __future__ import annotations` |
| Collection types | Always specify type parameters |
| Optional | Use `T | None` or `Optional[T]` |
| Any | Never use |
| Aliases | Use for domain concepts |
| Literal | Use for exact values |

---

## Related Documents

- [Python Style](./python-style.md) — Formatting rules
- [Imports](./imports.md) — Import conventions
- [Error Handling](./error-handling.md) — Exception types
- [Code Review Checklist](./code-review-checklist.md) — Review standards
