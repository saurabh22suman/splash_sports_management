"""Shared domain primitives.

Per [Engineering Principles](../../../docs/01-vision/principles.md) the domain layer
has zero framework dependencies. These types are pure Python.
"""
from __future__ import annotations

import re
from typing import Annotated, NewType
from uuid import UUID

from pydantic import StringConstraints

# Branded primitive types for clarity at type-check time. They are the same
# as their underlying type at runtime, but mypy treats them as distinct so a
# TenantId cannot be passed where a UserId is expected.

TenantId = NewType("TenantId", UUID)
UserId = NewType("UserId", UUID)
CustomerId = NewType("CustomerId", UUID)
FacilityId = NewType("FacilityId", UUID)
ResourceId = NewType("ResourceId", UUID)
BookingId = NewType("BookingId", UUID)
SlotId = NewType("SlotId", UUID)

EmailStr = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=254,
        pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
    ),
]

PhoneStr = Annotated[
    str,
    StringConstraints(
        min_length=7,
        max_length=20,
        pattern=r"^\+?[0-9\s\-()]+$",
    ),
]

# Short, URL-safe identifier used in APIs and DB column defaults.
_SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9\-]{0,38}[a-z0-9])?$")
SlugStr = Annotated[
    str,
    StringConstraints(min_length=1, max_length=40, pattern=_SLUG_PATTERN),
]
