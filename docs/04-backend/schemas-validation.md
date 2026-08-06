# Schemas & Validation

> This document covers Pydantic v2 patterns for input validation, output serialization, and internal data transfer.

## Overview

Pydantic is the backbone of our data validation layer. We use it for:

1. **Input schemas** — Validate API request bodies
2. **Output schemas** — Serialize API responses
3. **Internal schemas** — Type-safe internal DTOs

## Schema Types

We define three categories of schemas:

| Type | Purpose | Location |
|------|---------|----------|
| `*Create` | Input for creating resources | Request bodies |
| `*Update` | Input for updating resources | Request bodies |
| `*Out` | Output serialization | Response models |
| Internal | Cross-service communication | Application layer |

## Input Schemas

```python
# src/booking/interfaces/schemas.py
from datetime import date, time
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator


class BookingCreate(BaseModel):
    """Input schema for creating a booking."""
    model_config = ConfigDict(from_attributes=True)

    # Required fields
    customer_id: UUID = Field(..., description="ID of the customer making the booking")
    facility_id: UUID = Field(..., description="ID of the facility to book")
    date: date = Field(..., description="Date of the booking")
    start_time: time = Field(..., description="Start time (HH:MM)")
    end_time: time = Field(..., description="End time (HH:MM)")

    # Optional fields with defaults
    notes: Optional[str] = Field(None, max_length=1000)
    equipment_ids: list[UUID] = Field(default_factory=list)

    # Validation
    @field_validator("end_time")
    @classmethod
    def end_time_after_start_time(cls, v: time, info) -> time:
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v

    @field_validator("date")
    @classmethod
    def date_not_in_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("booking date cannot be in the past")
        return v

    @field_validator("equipment_ids")
    @classmethod
    def max_equipment(cls, v: list[UUID]) -> list[UUID]:
        if len(v) > 10:
            raise ValueError("maximum 10 equipment items allowed")
        return v
```

## Output Schemas

```python
# src/booking/interfaces/schemas.py
from datetime import datetime, date, time
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BookingOut(BaseModel):
    """Output schema for booking responses."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    facility_id: UUID
    date: date
    start_time: time
    end_time: time
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None

    # Computed fields
    duration_minutes: int = Field(..., description="Booking duration in minutes")

    @classmethod
    def from_entity(cls, booking: "Booking") -> "BookingOut":
        """Create from domain entity."""
        start = datetime.combine(booking.slot.date, booking.slot.start_time)
        end = datetime.combine(booking.slot.date, booking.slot.end_time)
        duration = int((end - start).total_seconds() / 60)

        return cls(
            id=booking.id,
            customer_id=booking.customer_id,
            facility_id=booking.facility_id,
            date=booking.slot.date,
            start_time=booking.slot.start_time,
            end_time=booking.slot.end_time,
            status=booking.status.value,
            version=booking.version,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            duration_minutes=duration,
        )


class BookingListOut(BaseModel):
    """Paginated list of bookings."""
    items: list[BookingOut]
    next_cursor: Optional[str] = None
    total_count: int
```

## Update Schemas (PATCH)

```python
# src/booking/interfaces/schemas.py
from datetime import date, time
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field


class BookingUpdate(BaseModel):
    """Input schema for updating a booking (PATCH)."""
    model_config = ConfigDict(from_attributes=True)

    # All fields optional for partial update
    date: Optional[date] = Field(None, description="New booking date")
    start_time: Optional[time] = Field(None, description="New start time")
    end_time: Optional[time] = Field(None, description="New end time")
    notes: Optional[str] = Field(None, max_length=1000)

    # Use model_validator for cross-field validation
    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValueError("end_time must be after start_time")
        return self
```

## Internal Schemas

For service-to-service communication, use separate internal schemas.

```python
# src/booking/application/schemas.py
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookingInternal(BaseModel):
    """Internal schema for booking data (used in events)."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    facility_id: UUID
    slot_start: datetime
    slot_end: datetime
    status: str
    version: int
```

## Strict Typing

> **Rule** — Always use strict types. Avoid `Any`, `dict`, `list` without type parameters.

```python
# BAD
class BookingCreate(BaseModel):
    data: dict
    items: list

# GOOD
class BookingCreate(BaseModel):
    data: dict[str, str]
    items: list[UUID]
```

## Validation Patterns

### Field Validators

```python
from pydantic import field_validator, model_validator


class BookingCreate(BaseModel):
    start_time: time
    end_time: time
    date: date

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, v: time) -> time:
        # Validate time format
        if v.hour < 6 or v.hour >= 22:
            raise ValueError("booking time must be between 06:00 and 22:00")
        return v

    @model_validator(mode="after")
    def validate_duration(self):
        # Cross-field validation
        from datetime import timedelta
        duration = timedelta(hours=self.end_time.hour - self.start_time.hour,
                           minutes=self.end_time.minute - self.start_time.minute)
        if duration.total_seconds() / 60 > 240:  # 4 hours max
            raise ValueError("maximum booking duration is 4 hours")
        return self
```

### Custom Validators

```python
from pydantic import AfterValidator
import re


def validate_phone(v: str) -> str:
    if not re.match(r"^\+?[1-9]\d{1,14}$", v):
        raise ValueError("invalid phone number format")
    return v


class CustomerCreate(BaseModel):
    phone: str = AfterValidator(validate_phone)
```

### Enum Validation

```python
from enum import Enum
from pydantic import ConstrainedStr, field_validator


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class BookingCreate(BaseModel):
    status: BookingStatus  # Pydantic automatically validates enum
```

## ConfigDict Settings

```python
class BookingOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,      # Allow ORM model → schema conversion
        validate_assignment=True, # Validate on assignment
        extra="forbid",           # Reject extra fields in input
        str_strip_whitespace=True,  # Trim whitespace from strings
        use_enum_values=True,     # Serialize enums as values (not objects)
    )
```

> **Guideline** — Use `from_attributes=True` for output schemas, but consider `extra="forbid"` for input schemas to catch typos.

## Nested Schemas

```python
from pydantic import BaseModel
from uuid import UUID


class EquipmentOut(BaseModel):
    id: UUID
    name: str


class BookingOut(BaseModel):
    id: UUID
    equipment: list[EquipmentOut] = []

    @classmethod
    def from_entity(cls, booking: Booking) -> "BookingOut":
        return cls(
            id=booking.id,
            equipment=[EquipmentOut(id=e.id, name=e.name) for e in booking.equipment],
        )
```

## Discriminated Unions

```python
from pydantic import BaseModel, Discriminator, Tag
from typing import Union


class PaymentSucceeded(BaseModel):
    event_type: str = "payment_succeeded"
    payment_id: UUID
    amount: int


class PaymentFailed(BaseModel):
    event_type: str = "payment_failed"
    payment_id: UUID
    reason: str


class PaymentEvent(BaseModel):
    model_config = {"discriminator": "event_type"}

    event_type: str


# Union type
PaymentEvent = Union[PaymentSucceeded, PaymentFailed]
```

## Error Response Schemas

```python
# src/common/schemas.py
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    field: str
    message: str
    code: str


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details."""
    type: str
    title: str
    status: int
    detail: Optional[str] = None
    instance: Optional[str] = None
    errors: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None
```

## Testing Schemas

```python
# tests/booking/test_schemas.py
import pytest
from datetime import date, time
from uuid import uuid4

from booking.interfaces.schemas import BookingCreate


def test_booking_create_valid():
    data = {
        "customer_id": str(uuid4()),
        "facility_id": str(uuid4()),
        "date": "2024-01-15",
        "start_time": "10:00",
        "end_time": "11:00",
    }
    schema = BookingCreate(**data)
    assert schema.start_time == time(10, 0)


def test_booking_create_invalid_dates():
    data = {
        "customer_id": str(uuid4()),
        "facility_id": str(uuid4()),
        "date": "2020-01-01",  # Past date
        "start_time": "10:00",
        "end_time": "11:00",
    }
    with pytest.raises(ValueError):
        BookingCreate(**data)
```

## Related Documents

- [Error Handling](error-handling.md)
- [API Design](../08-apis/rest-design.md)
- [Pydantic Documentation](https://docs.pydantic.dev/)
