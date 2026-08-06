# Documentation

> Google-style docstrings. Required sections (Args, Returns, Raises, Example). Module docstrings. Public API must be documented. Examples in docstrings are tested.

This document defines our documentation standards. We use docstrings as the primary documentation source because they're always in sync with code (unlike separate docs that drift).

---

## Docstring Style

We use **Google-style** docstrings:

```python
def function_name(param1: str, param2: int, param3: bool = True) -> ReturnType:
    """Short one-line description.

    Longer description if needed. Explain what the function does,
    why it exists, and any important context.

    Args:
        param1: Description of first parameter.
        param2: Description of second parameter.
        param3: Description of optional parameter (default: True).

    Returns:
        Description of return value.

    Raises:
        ValueError: When this condition occurs.
        TypeError: When that condition occurs.

    Example:
        >>> result = function_name("hello", 42)
        >>> print(result)
        'hello42'
    """
```

---

## Required Sections

All public functions must include:

| Section | Required | Description |
|---|---|---|
| Summary | Always | One-line description |
| Args | If parameters | Each parameter with type and description |
| Returns | If returns value | Return type and description |
| Raises | If raises exceptions | Each exception with condition |
| Example | For complex functions | Working code example |

```python
# Complete example
def calculate_booking_price(
    court_id: str,
    start_time: datetime,
    duration_minutes: int,
    member_tier: str = "standard",
) -> Money:
    """Calculate the total price for a booking.

    Applies member tier discounts and peak-hour surcharges.
    This is the main pricing function used by the booking flow.

    Args:
        court_id: ID of the court to book.
        start_time: Start time of the booking.
        duration_minutes: Duration in minutes (must be multiple of 30).
        member_tier: Member tier (standard, silver, gold, platinum).

    Returns:
        Money object with amount and currency.

    Raises:
        ValueError: If duration is not a multiple of 30.
        CourtNotFoundError: If court_id doesn't exist.
        SlotUnavailableError: If no slots available.

    Example:
        >>> from datetime import datetime
        >>> from decimal import Decimal
        >>> price = calculate_booking_price(
        ...     court_id="court-1",
        ...     start_time=datetime(2024, 1, 15, 10, 0),
        ...     duration_minutes=60,
        ...     member_tier="gold",
        ... )
        >>> price.amount
        Decimal('40.00')
    """
```

---

## Module Docstrings

Every module (`.py` file) must have a docstring:

```python
"""Booking service module.

This module provides the BookingService class for managing court bookings.

Main functionality:
    - Create, update, and cancel bookings
    - Check availability
    - Calculate prices
    - Handle waitlists

The service uses the booking repository for persistence and dispatches
domain events for booking state changes.

Example:
    >>> service = BookingService(repository, event_dispatcher)
    >>> booking = await service.create_booking(
    ...     customer_id="cust-1",
    ...     court_id="court-1",
    ...     start_time=datetime(2024, 1, 15, 10, 0),
    ...     duration_minutes=60,
    ... )
"""

from datetime import datetime
from decimal import Decimal

# Rest of module...
```

---

## Class Docstrings

```python
class BookingService:
    """Service for managing court bookings.

    The BookingService handles all booking-related operations including
    creation, modification, cancellation, and availability checking.

    The service ensures business invariants:
        - Bookings cannot overlap
        - Payment must be collected before confirmation
        - Cancellation policies are enforced

    Attributes:
        repository: Database repository for bookings.
        event_dispatcher: Dispatches domain events.

    Example:
        >>> service = BookingService(booking_repo, event_dispatcher)
        >>> await service.create_booking(
        ...     customer_id="cust-1",
        ...     court_id="court-1",
        ...     start_time=datetime(2024, 1, 15, 10, 0),
        ...     duration_minutes=60,
        ... )
    """

    def __init__(
        self,
        repository: BookingRepository,
        event_dispatcher: EventDispatcher,
    ):
        """Initialize the booking service.

        Args:
            repository: Repository for booking persistence.
            event_dispatcher: For dispatching booking events.
        """
        self._repository = repository
        self._event_dispatcher = event_dispatcher
```

---

## Testing Docstring Examples

Examples in docstrings should be runnable and tested:

```python
def format_price(amount: Decimal, currency: str = "USD") -> str:
    """Format a price for display.

    Args:
        amount: The monetary amount.
        currency: ISO 4217 currency code (default: USD).

    Returns:
        Formatted price string.

    Example:
        >>> format_price(Decimal("99.99"))
        '$99.99'
        >>> format_price(Decimal("1234.56"), "EUR")
        '€1,234.56'
    """
    import locale

    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    formatted = f"{abs(amount):,.2f}"
    if amount < 0:
        return f"-{symbol}{formatted}"
    return f"{symbol}{formatted}"
```

> **Guideline** — Run doctests to verify examples work:
> ```bash
> python -m doctest -v module.py
> ```

---

## What to Document

| Element | Document | Why |
|---|---|---|
| Public functions | All | API contract |
| Public classes | All | Usage guidance |
| Public constants | Complex ones | Configuration |
| Exceptions | All raised | Error handling |
| Complex algorithms | Implementation | Maintenance |
| Configuration | N/A | Use config schema |

### Not Documented (Obvious)

- Private methods (prefixed with `_`)
- Internal helper functions
- Simple properties
- Type definitions

```python
# Documented
class BookingService:
    async def create_booking(...) -> Booking:
        """Create a new booking."""

# Not documented (private/internal)
    def _validate_slot(self, slot: TimeSlot) -> None:
        # Internal implementation detail
        ...
```

---

## Cross-References

Use cross-references for related documentation:

```python
def create_booking(request: BookingRequest) -> Booking:
    """Create a new booking.

    See Also:
        - :func:`cancel_booking` for cancellation.
        - :class:`BookingRequest` for request schema.
        - :doc:`/08-apis/booking` for API endpoint.

    Example:
        >>> request = BookingRequest(...)
        >>> booking = await create_booking(request)
    """
```

---

## Summary

| Element | Required | Style |
|---|---|---|
| Modules | Yes | Google |
| Public classes | Yes | Google |
| Public functions | Yes | Google |
| Public constants | If complex | Summary |
| Examples | For complex | Runnable |
| Private | No | Optional |

---

## Related Documents

- [Python Style](./python-style.md) — Formatting rules
- [Comments](./comments.md) — Comment conventions
- [Code Review Checklist](./code-review-checklist.md) — Review standards
- [API Documentation](../08-apis/openapi.md) — API docs
