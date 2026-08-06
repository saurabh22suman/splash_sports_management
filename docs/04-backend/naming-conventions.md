# Naming Conventions

> This document defines naming conventions for files, classes, functions, variables, and constants in the backend codebase.

## Overview

Consistent naming reduces cognitive load and makes the codebase navigable. We follow Python PEP 8 conventions with additional rules for our domain-driven architecture.

## File Names

> **Rule** — Use `snake_case` for all file names.

| Type | Convention | Example |
|------|------------|---------|
| Python modules | `snake_case.py` | `booking_service.py` |
| Test files | `test_<module>.py` | `test_booking_service.py` |
| Private modules | `_private.py` | `_helpers.py` |
| Init files | `__init__.py` | `__init__.py` |

### Module Names Match Bounded Contexts

```
src/
├── auth/
│   ├── router.py
│   ├── service.py
│   ├── repository.py
│   ├── models.py
│   ├── schemas.py
│   └── exceptions.py
├── booking/
│   ├── router.py
│   └── ...
├── customer/
│   └── ...
```

## Function Names

> **Rule** — Use `snake_case` for functions and methods.

```python
# Good
def create_booking(customer_id: UUID, facility_id: UUID) -> Booking:
    ...

def calculate_total_price(items: list[PriceItem]) -> Decimal:
    ...

def is_slot_available(slot: TimeSlot) -> bool:
    ...

# Bad - don't use camelCase
def createBooking(customerId):
    ...

# Bad - don't use PascalCase
def CreateBooking():
    ...
```

### Verb-Noun Pattern

```python
# Actions: verb_noun
def get_booking(booking_id: UUID) -> Optional[Booking]:
    ...

def list_bookings(customer_id: UUID) -> list[Booking]:
    ...

def create_booking(command: CreateBookingCommand) -> Booking:
    ...

def update_booking(booking_id: UUID, data: UpdateBookingCommand) -> Booking:
    ...

def delete_booking(booking_id: UUID) -> None:
    ...

def confirm_booking(booking_id: UUID) -> Booking:
    ...

def cancel_booking(booking_id: UUID, reason: str) -> Booking:
    ...
```

## Class Names

> **Rule** — Use `PascalCase` for class names.

```python
# Domain
class Booking:
    ...

class TimeSlot:
    ...

class BookingStatus:
    ...

# Services
class BookingService:
    ...

class PaymentService:
    ...

# Repositories
class BookingRepository:
    ...

class SQLAlchemyBookingRepository:
    ...

# Schemas (Pydantic)
class BookingCreate(BaseModel):
    ...

class BookingOut(BaseModel):
    ...
```

## Variable Names

> **Rule** — Use `snake_case` for variables.

```python
# Good
booking_id = uuid4()
customer_name = "John"
is_confirmed = True
booking_list = []

# Bad
bookingId = uuid4()  # camelCase
customerName = "John"  # camelCase
isConfirmed = True  # camelCase
bookingList = []  # PascalCase
```

### Descriptive Names

```python
# Good - descriptive
total_price = calculate_total(price_items)
confirmed_bookings = [b for b in bookings if b.status == "confirmed"]

# Bad - too short or cryptic
tp = calculate_total(price_items)
cb = [b for b in bookings if b.status == "confirmed"]
```

## Constant Names

> **Rule** — Use `SCREAMING_SNAKE_CASE` for constants.

```python
# Configuration
MAX_BOOKING_DURATION_HOURS = 4
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Status values
STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_CANCELLED = "cancelled"

# Enum values (if not using Python Enum)
class BookingStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
```

## Type Aliases

> **Rule** — Use `PascalCase` for type aliases.

```python
from typing import TypeAlias

# Custom types
BookingId: TypeAlias = UUID
CustomerId: TypeAlias = UUID

# Complex types
BookingList: TypeAlias = list[Booking]
BookingDict: TypeAlias = dict[str, Booking]
```

## Database Naming

See [Database Naming Standards](../06-database/naming-standards.md).

| Element | Convention | Example |
|---------|------------|---------|
| Table | `snake_case, plural` | `bookings` |
| Column | `snake_case, singular` | `booking_id` |
| Index | `idx_<table>_<cols>` | `idx_bookings_customer` |
| FK | `<table>_<ref>_id` | `facility_id` |

## Test Naming

> **Rule** — Test files: `test_<module>.py`, Test functions: `test_<description>`.

```python
# test_booking_service.py
def test_create_booking_success():
    ...

def test_create_booking_slot_unavailable():
    ...

def test_confirm_booking_not_found():
    ...
```

### Test Class Names

```python
class TestBookingService:
    """Tests for BookingService."""

    def test_create_booking_success(self):
        ...

    def test_create_booking_slot_unavailable(self):
        ...


class TestBookingRepository:
    """Tests for BookingRepository."""

    def test_get_returns_booking(self):
        ...
```

## Anti-Patterns

1. **Single letter variables** — Except in loops (`i`, `j`) or lambdas
2. **Abbreviations** — `cust` instead of `customer`, `qty` instead of `quantity`
3. **Inconsistent casing** — Mixing `snake_case` and `camelCase`
4. **Meaningless names** — `data`, `value`, `temp`

## Linting Enforcement

```python
# pyproject.toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "N",  # pep8-naming
]
ignore = [
    "N802",  # function name should be lowercase (we use snake_case)
    "N803",  # argument name should be lowercase
]
```

## Summary Table

| Element | Convention | Example |
|---------|------------|---------|
| Files | `snake_case.py` | `booking_service.py` |
| Functions | `snake_case()` | `get_booking()` |
| Classes | `PascalCase` | `BookingService` |
| Variables | `snake_case` | `booking_id` |
| Constants | `SCREAMING_SNAKE` | `MAX_RETRIES` |
| Type aliases | `PascalCase` | `BookingId` |
| Tables | `snake_case_plural` | `bookings` |
| Columns | `snake_case_singular` | `booking_id` |

## Related Documents

- [Python Style Guide](../13-coding-standards/python-style.md)
- [Database Naming Standards](../06-database/naming-standards.md)
- [PEP 8](https://peps.python.org/pep-0008/)
