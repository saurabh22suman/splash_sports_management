# Imports

> Import order: stdlib → third-party → local. Ruff enforces. Forbidden imports: circular, wildcard. Lazy imports only for circular resolution.

This document defines our import conventions. Consistent imports improve readability and prevent bugs from circular dependencies.

---

## Import Order

Imports must be in the following order, with blank lines between groups:

```python
# 1. Standard library
import asyncio
import os
import re
from collections import defaultdict
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Literal

# 2. Third-party packages
import httpx
import pydantic
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, relationship
from sqlalchemy.dialects.postgresql import ARRAY

# 3. Local application - absolute imports
from apps.backend.src.auth import schemas as auth_schemas
from apps.backend.src.auth.service import AuthService
from apps.backend.src.common.database import get_db
from apps.backend.src.common.dependencies import get_current_user
from apps.backend.src.common.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
    ValidationError,
)
from apps.backend.src.common.logging import get_logger
from apps.backend.src.common.types import Money

# 4. Relative imports (when needed)
from ..common.config import get_settings
from ..common.feature_flags import FeatureFlags
```

> **Rule** — Ruff enforces import order. Run `ruff check --fix` to auto-sort.

---

## Ruff Configuration for Imports

```toml
# pyproject.toml
[tool.ruff.isort]
known-first-party = ["apps", "tests"]
force-single-line = false
order-by-type = false
```

---

## Forbidden Imports

### No Wildcard Imports

> **Anti-pattern** — Never use wildcard imports (`from module import *`).

```python
# BAD: Wildcard import
from apps.backend.src.booking import *  # What is actually imported?


# GOOD: Explicit imports
from apps.backend.src.booking.service import BookingService
from apps.backend.src.booking.repository import BookingRepository
from apps.backend.src.booking.schemas import BookingCreate, BookingResponse
```

### No Circular Imports

> **Anti-pattern** — Avoid circular imports at all costs.

```python
# BAD: Circular import
# file_a.py
from file_b import ClassB  # Imports B


# file_b.py
from file_a import ClassA  # Imports A - CIRCULAR!


# GOOD: Restructure to avoid
# common/base.py  - Base classes only
# a.py - Imports from common, defines A
# b.py - Imports from common, defines B
```

### Resolving Circular Imports with Lazy Imports

If circular import is unavoidable, use lazy imports:

```python
# Use TYPE_CHECKING for type hints only
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only for type hints, not executed at runtime
    from apps.backend.src.booking.service import BookingService


class SomeClass:
    def __init__(self):
        # Lazy import at runtime
        from apps.backend.src.booking.service import BookingService
        self._service = BookingService()
```

---

## Import Aliases

Use aliases to avoid conflicts:

```python
# GOOD: Alias to avoid conflict with stdlib
import pydantic
from pydantic import BaseModel as PydanticBaseModel

# GOOD: Shorten long module names
from apps.backend.src.common import logging as common_logging
from apps.backend.src.common import exceptions as common_exceptions

# GOOD: Schema aliases
from apps.backend.src.auth import schemas as auth_schemas
from apps.backend.src.booking import schemas as booking_schemas
from apps.backend.src.membership import schemas as membership_schemas
```

---

## Import Best Practices

### Don't Import What You Don't Use

```python
# BAD: Unused imports (ruff will catch)
from typing import Any, List, Dict, Optional  # Only use some
import httpx  # Never used


# GOOD: Only import what's used
from typing import Any
import httpx
```

### Import in Function When Needed

```python
# GOOD: Import where used (if only used in one function)
def process_booking(booking_id: str) -> None:
    from apps.backend.src.notifications.service import NotificationService

    service = NotificationService()
    await service.send_confirmation(booking_id)
```

### Don't Re-export Builtins

```python
# BAD: Shadowing builtins
def list():
    """List something."""
    return [1, 2, 3]  # Shadows built-in list!


# GOOD: Use different names
def get_items():
    """Get items."""
    return [1, 2, 3]
```

---

## Module Structure

Organize modules with clear imports:

```python
# apps/backend/src/booking/__init__.py
"""Booking module.

Public API:
    - BookingService
    - BookingRepository
    - BookingCreate, BookingResponse
"""

from apps.backend.src.booking.service import BookingService
from apps.backend.src.booking.repository import BookingRepository
from apps.backend.src.booking.schemas import BookingCreate, BookingResponse

__all__ = [
    "BookingService",
    "BookingRepository",
    "BookingCreate",
    "BookingResponse",
]
```

---

## Summary

| Rule | Implementation |
|---|---|
| Order | stdlib → third-party → local |
| Wildcard | Never |
| Circular | Avoid, use lazy imports |
| Aliases | Use for disambiguation |
| Unused | Remove |

---

## Related Documents

- [Python Style](./python-style.md) — Formatting rules
- [Dependency Rules](./dependency-rules.md) — Layer dependencies
- [Code Review Checklist](./code-review-checklist.md) — Review standards
