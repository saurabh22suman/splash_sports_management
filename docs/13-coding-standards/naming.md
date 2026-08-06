# Naming

> snake_case for files/functions/variables. PascalCase for classes. SCREAMING_SNAKE for constants. Test files: test_<module>.py.

This document defines our naming conventions. Consistent naming makes code readable and helps developers find what they need. We follow Python's PEP 8 with specific adaptations.

---

## File Names

| Type | Convention | Example |
|---|---|---|
| Python modules | snake_case | `booking_service.py` |
| Test files | `test_<module>.py` | `test_booking_service.py` |
| Configuration | snake_case | `app_config.py` |
| Package directories | snake_case | `apps/backend/src/booking/` |
| Django/FastAPI apps | snake_case | `apps/booking/` |

> **Why** — Python convention is snake_case for modules. Test files with `test_` prefix are automatically discovered by pytest.

```python
# GOOD: Clear file names
apps/
  backend/
    src/
      booking/
        service.py
        repository.py
        models.py
        schemas.py
        router.py
      tests/
        booking/
          test_service.py
          test_repository.py

# BAD: Inconsistent naming
Apps/
  backend/
    src/
      Booking/
        Service.py  # PascalCase in Python is non-standard
      test_booking.py  # Not in test directory
```

---

## Function and Variable Names

Use **snake_case** for functions and variables:

```python
# GOOD: snake_case
def calculate_total_with_tax(subtotal, tax_rate):
    """Calculate total including tax."""
    discount = apply_discount(subtotal)
    return discount * (1 + tax_rate)


def get_active_bookings(tenant_id: str) -> list[Booking]:
    """Fetch all active bookings for a tenant."""
    active_bookings = []
    for booking in bookings:
        if booking.is_active:
            active_bookings.append(booking)
    return active_bookings


# BAD: camelCase or other
def calculateTotalWithTax(subtotal, taxRate):  # camelCase
    return subtotal * (1 + taxRate)


getActiveBookings = lambda x: x  # Inconsistent
```

### Boolean Names

Use `is_`, `has_`, `can_`, `should_` prefixes:

```python
# GOOD: Clear boolean intent
is_active: bool
has_permission: bool
can_book: bool
should_notify: bool
is_available: bool
has_reached_limit: bool

# Usage
if user.is_active and user.can_book:
    await create_booking(user)


# BAD: Unclear boolean purpose
active = True  # What does it mean?
flag = False  # What flag?
status = "active"  # Should be enum, not string
```

### Function Names: Verb Phrases

Functions perform actions; name them with verbs:

```python
# GOOD: Verb phrases
def calculate_total():
    """Compute something."""
    ...


def validate_booking():
    """Check if valid."""
    ...


def fetch_bookings():
    """Retrieve data."""
    ...


def send_notification():
    """Perform side effect."""
    ...


def process_payment():
    """Execute operation."""
    ...


# BAD: Nouns or unclear
def calculation():  # What does it do?
    ...


def booking_validate():  # Noun instead of verb
    ...


def data():  # Too vague
    ...
```

---

## Class Names

Use **PascalCase** for classes:

```python
# GOOD: PascalCase
class BookingService:
    """Service for managing bookings."""
    ...


class CourtRepository:
    """Repository for court persistence."""
    ...


class PaymentProcessor:
    """Process payments."""
    ...


class BookingNotFoundError(Exception):
    """Raised when booking not found."""
    ...


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


# BAD: snake_case or other
class booking_service:  # snake_case is for functions
    ...


class bookingService:  # camelCase is for JavaScript
    ...
```

---

## Constants

Use **SCREAMING_SNAKE_CASE** for constants:

```python
# GOOD: SCREAMING_SNAKE_CASE
MAX_BOOKING_DURATION_MINUTES = 180
DEFAULT_COURT_RATE = Decimal("50.00")
SUPPORTED_SPORTS = ["tennis", "badminton", "squash"]

# Module-level constants at top of file
import math

# Mathematical constants
PI = math.pi
E = math.e

# Configuration constants
DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRY_ATTEMPTS = 3


# BAD: Regular variables
max_booking_duration = 180  # Looks like a variable
defaultCourtRate = 50.00  # Mixed case
```

---

## Module Names Match Bounded Contexts

```python
# GOOD: Domain-driven module names
apps/backend/src/
  auth/
    service.py      # AuthService
    repository.py    # AuthRepository
    router.py       # auth router
    schemas.py      # Pydantic models
  booking/
    service.py
    repository.py
    router.py
  membership/
    service.py
    repository.py
    router.py
  facility/
    service.py
    repository.py
    router.py


# BAD: Technical layer naming (old style)
apps/backend/src/
  services/
    booking_service.py
    user_service.py
  controllers/
    booking_controller.py
    user_controller.py
  models/
    booking_model.py
    user_model.py
```

---

## Naming Examples by Context

| Context | Name | Example |
|---|---|---|
| Database model | `<Entity>` | `User`, `Booking` |
| Pydantic schema | `<Entity><Type>Schema` | `BookingCreateSchema`, `BookingResponseSchema` |
| Repository | `<Entity>Repository` | `BookingRepository` |
| Service | `<Entity>Service` | `BookingService` |
| Router/API | `<entity>_router` | `booking_router` |
| Exception | `<Entity>Error` | `BookingNotFoundError` |
| Test class | `Test<Entity>` | `TestBookingService` |
| Test function | `test_<action>_<entity>` | `test_create_booking_success` |

---

## Anti-Patterns

```python
# BAD: Single-letter names (except in comprehensions/loops)
def f(x):  # What is x?
    return x * 2


# BAD: Abbreviations that reduce clarity
def get_bkg(id):  # What is bkg? ID of what?
    ...


def calc_amt(prc, qty):  # Ambiguous
    return prc * qty


# BAD: Hungarian notation
str_name = "John"  # Type in name is redundant
int_count = 5
b_is_active = True


# GOOD: Descriptive names
def calculate_total_price(price_per_unit: Decimal, quantity: int) -> Decimal:
    """Calculate total price for an order."""
    return price_per_unit * quantity


# GOOD: Acceptable abbreviations for well-known terms
def get_api_key() -> str:
    """Get API key for external service."""
    ...


def configure_smtp() -> None:
    """Configure SMTP settings."""
    ...
```

---

## Summary

| Element | Convention | Example |
|---|---|---|
| Files | snake_case | `booking_service.py` |
| Functions | snake_case | `create_booking()` |
| Variables | snake_case | `booking_id` |
| Classes | PascalCase | `BookingService` |
| Constants | SCREAMING_SNAKE | `MAX_DURATION` |
| Booleans | is_/has_/can_ | `is_active` |
| Test files | test_<module>.py | `test_booking.py` |

---

## Related Documents

- [Python Style](./python-style.md) — Formatting rules
- [Comments](./comments.md) — Comment conventions
- [Code Review Checklist](./code-review-checklist.md) — Review standards
