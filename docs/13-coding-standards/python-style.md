# Python Style

> Ruff (lint + format, replacing black/isort/flake8). Line length 100. Import sorting. Type hints everywhere.

This document defines our Python code style. We use Ruff as our linter and formatter because it replaces multiple tools (black, isort, flake8, pyflakes) with a single fast tool, reducing configuration complexity and build time.

---

## Tool Selection

| Tool | Replacement | Rationale |
|---|---|---|
| black | ruff format | Ruff is 10-100x faster |
| isort | ruff (import sorting) | Single tool, consistent |
| flake8 | ruff | Unified linting |
| pyupgrade | ruff | Modern syntax |
| autoflake | ruff | Remove unused imports |

> **Why** — Ruff is written in Rust and is dramatically faster than Python-based formatters. For large codebases, this reduces CI time by minutes.

---

## Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"
extend-select = [
    "E",     # pycodestyle errors
    "W",     # pycodestyle warnings
    "F",     # pyflakes
    "I",     # isort
    "N",     # pep8-naming
    "UP",    # pyupgrade
    "B",     # flake8-bugbear
    "C4",    # flake8-comprehensions
    "FA",    # flake8-future-annotations
    "PIE",   # flake8-pie
    "T20",   # flake8-print
    "RSE",   # flake-raise
    "RET",   # flake8-return
    "SLF",   # flake8-self
    "SIM",   # flake8-simplify
]
ignore = [
    "E501",  # line too long (handled by formatter)
    "B008",  # do not perform function calls in argument defaults
    "C901",  # too complex (handled by complexity rule)
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

[tool.ruff.isort]
known-first-party = ["src"]
```

---

## Line Length

We use **100 characters** as the maximum line length, compared to black's default 88. This is a deliberate choice:

> **Why** — 100 characters fits most IDEs at default window sizes while allowing more content per line. The trade-off: slightly longer lines but less vertical scrolling.

```python
# GOOD: Within 100 characters
def calculate_total_with_tax(
    subtotal: Decimal,
    tax_rate: Decimal,
    discount: Decimal = Decimal("0"),
) -> Decimal:
    """Calculate total including tax and discount."""
    return (subtotal - discount) * (1 + tax_rate)


# BAD: Exceeds 100 characters
def calculate_total_with_tax(subtotal: Decimal, tax_rate: Decimal, discount: Decimal = Decimal("0")) -> Decimal:
    return (subtotal - discount) * (1 + tax_rate)
```

---

## Import Sorting

Ruff enforces import order:

```python
# 1. Standard library
import asyncio
import os
from collections import defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

# 2. Third-party packages
import httpx
import pydantic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

# 3. Local application
from apps.backend.src.auth import schemas as auth_schemas
from apps.backend.src.auth.service import AuthService
from apps.backend.src.common.dependencies import get_db
from apps.backend.src.common.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
)

# 4. Relative imports (when needed)
from ..common.logging import get_logger

# GOOD: Separate sections with blank lines
# BAD: Mixed import order
import os  # stdlib
import httpx  # third-party
from apps.backend.src.auth import models  # local
```

---

## Docstring Style

We use Google-style docstrings:

```python
# GOOD: Google-style docstring
def calculate_booking_price(
    court_id: str,
    start_time: datetime,
    duration_minutes: int,
    member_tier: str = "standard",
) -> Money:
    """Calculate the total price for a booking.

    Args:
        court_id: The ID of the court to book.
        start_time: The start time of the booking.
        duration_minutes: Duration in minutes (must be multiple of 30).
        member_tier: Member tier affecting the base price.

    Returns:
        Money object containing amount and currency.

    Raises:
        ValueError: If duration is not a multiple of 30.
        CourtNotFoundError: If court_id doesn't exist.

    Example:
        >>> price = calculate_booking_price(
        ...     court_id="court-1",
        ...     start_time=datetime(2024, 1, 15, 10, 0),
        ...     duration_minutes=60,
        ... )
        >>> print(price.amount)
        Decimal('50.00')
    """
    if duration_minutes % 30 != 0:
        raise ValueError("Duration must be a multiple of 30 minutes")
    # ... implementation


# BAD: Missing docstring or wrong style
def calc_price(court_id, start_time, duration, tier="standard"):
    return 50  # What?
```

---

## Type Hints

Type hints are required for all public functions and classes:

```python
# GOOD: Full type hints
def process_bookings(
    tenant_id: str,
    booking_ids: list[str],
    action: Literal["confirm", "cancel"],
) -> ProcessBookingsResult:
    """Process multiple bookings in bulk."""
    ...


# GOOD: Type alias for clarity
BookingStatus = Literal["pending", "confirmed", "cancelled", "completed"]


class Booking:
    """Represents a court booking."""

    id: str
    status: BookingStatus
    start_time: datetime
    end_time: datetime
    customer_id: str


# BAD: Missing type hints
def process_bookings(tenant_id, booking_ids, action):
    ...
```

---

## Code Examples

### Good vs. Bad Style

```python
# ============================================
# GOOD: Clear, readable, typed
# ============================================

from decimal import Decimal
from datetime import datetime


class BookingService:
    """Service for managing court bookings."""

    def __init__(self, repository: BookingRepository, notifier: Notifier):
        self._repository = repository
        self._notifier = notifier

    async def create_booking(
        self,
        customer_id: str,
        court_id: str,
        start_time: datetime,
        duration_minutes: int,
    ) -> Booking:
        """Create a new booking for a court.

        Args:
            customer_id: The customer making the booking.
            court_id: The court to book.
            start_time: When the booking starts.
            duration_minutes: How long (multiple of 30).

        Returns:
            The created booking.

        Raises:
            CourtNotAvailableError: If court is already booked.
        """
        # Validate
        await self._validate_availability(court_id, start_time, duration_minutes)

        # Create
        booking = Booking(
            customer_id=customer_id,
            court_id=court_id,
            start_time=start_time,
            end_time=start_time + timedelta(minutes=duration_minutes),
            status=BookingStatus.PENDING,
        )

        # Persist
        created = await self._repository.create(booking)

        # Notify
        await self._notifier.send_booking_confirmation(created)

        return created


# ============================================
# BAD: Untyped, unclear, no validation
# ============================================

class booking_service():
    def __init__(self, repo, notif):
        self.repo = repo
        self.notif = notif

    async def create(self, customer, court, start, duration):
        # What validation? What exceptions?
        b = {'customer': customer, 'court': court, 'start': start}
        created = self.repo.create(b)
        self.notif.send(created)
        return created
```

---

## Running Ruff

```bash
# Format code
ruff format apps/backend/src/

# Check code
ruff check apps/backend/src/

# Auto-fix issues
ruff check apps/backend/src/ --fix

# Run with config
ruff check --config pyproject.toml apps/backend/src/
```

---

## CI Integration

```yaml
# .github/workflows/lint.yml
- name: Run Ruff
  run: ruff check apps/backend/src/

- name: Run Ruff (formatter check)
  run: ruff format --check apps/backend/src/
```

---

## Summary

| Rule | Standard |
|---|---|
| Formatter | ruff format |
| Linter | ruff check |
| Line length | 100 characters |
| Import order | stdlib → third-party → local |
| Docstrings | Google style |
| Type hints | Required everywhere |

---

## Related Documents

- [Type Hints](./type-hints.md) — Strict typing rules
- [Imports](./imports.md) — Import conventions
- [Documentation](./documentation.md) — Docstring requirements
- [Code Review Checklist](./code-review-checklist.md) — Review standards
