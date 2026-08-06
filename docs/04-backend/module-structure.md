# Module Structure

> This document defines the internal structure of a single module (bounded context). Every module follows a consistent internal architecture based on Clean Architecture principles.

## Overview

Each module implements **domain-driven design** with clear separation between domain logic, application services, infrastructure implementations, and HTTP interfaces. The dependency rule is absolute: **domain has zero dependencies on external frameworks**.

## Layer Architecture

```
src/<module>/
├── domain/           # Pure business logic, no framework deps
│   ├── __init__.py
│   ├── entities.py   # Core domain entities
│   ├── value_objects.py
│   ├── aggregates.py
│   ├── events.py     # Domain events
│   ├── exceptions.py # Domain exceptions
│   └── services.py   # Domain services (optional)
│
├── application/      # Use cases, orchestration
│   ├── __init__.py
│   ├── ports.py      # Interfaces (repository, external service)
│   ├── services.py  # Application services
│   └── queries/     # Query handlers (optional)
│
├── infrastructure/   # Implementations
│   ├── __init__.py
│   ├── repositories.py      # SQLAlchemy implementations
│   ├── gateways.py          # External service adapters
│   └── persistence/         # DB-specific code
│
├── interfaces/       # HTTP adapters
│   ├── __init__.py
│   ├── router.py    # FastAPI router
│   ├── schemas.py   # Pydantic DTOs
│   └── middleware.py
│
├── __init__.py
├── models.py         # SQLAlchemy ORM models (legacy compat)
├── repository.py     # Re-export for convenience
├── service.py        # Re-export for convenience
├── schemas.py        # Re-export for convenience
└── tests/
```

> **Guideline** — New modules should use this full structure. Small modules may collapse layers, but the dependency direction must always point inward.

## Domain Layer

The domain layer is the **core** of the module. It contains:

### Entities

```python
# src/booking/domain/entities.py
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass, field
from typing import Optional

from .value_objects import BookingStatus, TimeSlot
from .exceptions import InvalidBookingStateError


@dataclass
class Booking:
    """Booking aggregate root."""
    id: UUID
    customer_id: UUID
    facility_id: UUID
    slot: TimeSlot
    status: BookingStatus
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def confirm(self) -> None:
        """Confirm the booking."""
        if self.status != BookingStatus.PENDING:
            raise InvalidBookingStateError(
                f"Cannot confirm booking in {self.status} status"
            )
        self.status = BookingStatus.CONFIRMED
        self.updated_at = datetime.utcnow()

    def cancel(self, reason: str) -> None:
        """Cancel the booking."""
        if self.status in (BookingStatus.CANCELLED, BookingStatus.COMPLETED):
            raise InvalidBookingStateError(
                f"Cannot cancel booking in {self.status} status"
            )
        self.status = BookingStatus.CANCELLED
        self._cancellation_reason = reason
        self.updated_at = datetime.utcnow()
```

### Value Objects

```python
# src/booking/domain/value_objects.py
from dataclasses import dataclass
from datetime import datetime, time
from uuid import UUID


@dataclass(frozen=True)
class TimeSlot:
    """Immutable time slot value object."""
    facility_id: UUID
    date: datetime
    start_time: time
    end_time: time

    def overlaps(self, other: "TimeSlot") -> bool:
        """Check if this slot overlaps with another."""
        if self.facility_id != other.facility_id:
            return False
        if self.date != other.date:
            return False
        return not (self.end_time <= other.start_time or other.end_time <= self.start_time)


class BookingStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
```

### Domain Events

```python
# src/booking/domain/events.py
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class BookingCreatedEvent:
    booking_id: UUID
    customer_id: UUID
    facility_id: UUID
    slot_start: datetime
    slot_end: datetime
    occurred_at: datetime = None

    def __post_init__(self):
        if self.occurred_at is None:
            from datetime import datetime
            self.occurred_at = datetime.utcnow()


@dataclass
class BookingConfirmedEvent:
    booking_id: UUID
    occurred_at: datetime = None


@dataclass
class BookingCancelledEvent:
    booking_id: UUID
    reason: str
    occurred_at: datetime = None
```

> **Rule** — Domain layer must have ZERO imports from `fastapi`, `sqlalchemy`, `redis`, or any external framework. Test with: `python -c "import ast; ... check_no_framework_imports('src/booking/domain')"`

## Application Layer

The application layer orchestrates use cases. It depends on domain (interfaces) and infrastructure (implementations).

### Ports (Interfaces)

```python
# src/booking/application/ports.py
from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional, List

from booking.domain.entities import Booking
from booking.domain.value_objects import BookingStatus, TimeSlot


class BookingRepository(ABC):
    """Port for booking persistence."""

    @abstractmethod
    def get(self, booking_id: UUID) -> Optional[Booking]:
        """Get a booking by ID."""
        pass

    @abstractmethod
    def save(self, booking: Booking) -> Booking:
        """Save (create or update) a booking."""
        pass

    @abstractmethod
    def list_by_customer(
        self, customer_id: UUID, limit: int = 20, offset: int = 0
    ) -> List[Booking]:
        """List bookings for a customer."""
        pass


class EventBus(ABC):
    """Port for publishing domain events."""

    @abstractmethod
    def publish(self, event: object) -> None:
        """Publish a domain event."""
        pass

    @abstractmethod
    def publish_batch(self, events: List[object]) -> None:
        """Publish multiple events."""
        pass
```

### Application Services

```python
# src/booking/application/services.py
from uuid import UUID, uuid4
from datetime import datetime
from typing import List

from booking.application.ports import BookingRepository, EventBus
from booking.domain.entities import Booking
from booking.domain.value_objects import BookingStatus, TimeSlot
from booking.domain.events import BookingCreatedEvent, BookingConfirmedEvent
from booking.domain.exceptions import (
    SlotNotAvailableError,
    BookingNotFoundError,
)


class BookingService:
    """Application service for booking use cases."""

    def __init__(self, repository: BookingRepository, event_bus: EventBus):
        self._repository = repository
        self._event_bus = event_bus

    def create_booking(
        self,
        customer_id: UUID,
        facility_id: UUID,
        slot: TimeSlot,
    ) -> Booking:
        """Create a new booking."""
        # Check slot availability
        existing = self._repository.find_conflicting(slot)
        if existing:
            raise SlotNotAvailableError(
                f"Slot {slot.start_time}-{slot.end_time} on {slot.date} is not available"
            )

        # Create booking
        booking = Booking(
            id=uuid4(),
            customer_id=customer_id,
            facility_id=facility_id,
            slot=slot,
            status=BookingStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Persist
        saved = self._repository.save(booking)

        # Publish event
        self._event_bus.publish(BookingCreatedEvent(
            booking_id=saved.id,
            customer_id=saved.customer_id,
            facility_id=saved.facility_id,
            slot_start=datetime.combine(saved.slot.date, saved.slot.start_time),
            slot_end=datetime.combine(saved.slot.date, saved.slot.end_time),
        ))

        return saved

    def confirm_booking(self, booking_id: UUID) -> Booking:
        """Confirm a pending booking."""
        booking = self._repository.get(booking_id)
        if not booking:
            raise BookingNotFoundError(f"Booking {booking_id} not found")

        booking.confirm()
        saved = self._repository.save(booking)

        self._event_bus.publish(BookingConfirmedEvent(booking_id=booking_id))

        return saved
```

## Infrastructure Layer

Implements the ports defined in the application layer.

```python
# src/booking/infrastructure/repositories.py
from uuid import UUID
from typing import Optional, List
from datetime import datetime

from booking.application.ports import BookingRepository
from booking.domain.entities import Booking
from booking.infrastructure.persistence.models import BookingModel
from sqlalchemy.orm import Session


class SQLAlchemyBookingRepository(BookingRepository):
    """SQLAlchemy implementation of BookingRepository."""

    def __init__(self, session: Session):
        self._session = session

    def get(self, booking_id: UUID) -> Optional[Booking]:
        model = self._session.query(BookingModel).filter(
            BookingModel.id == booking_id,
            BookingModel.deleted_at.is_(None)
        ).first()
        return self._to_entity(model) if model else None

    def save(self, booking: Booking) -> Booking:
        model = self._to_model(booking)
        self._session.add(model)
        self._session.flush()
        return booking

    def _to_entity(self, model: BookingModel) -> Booking:
        # Mapping logic
        ...

    def _to_model(self, booking: Booking) -> BookingModel:
        # Mapping logic
        ...
```

## Interfaces Layer

HTTP adapters that translate between HTTP and the application layer.

```python
# src/booking/interfaces/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from booking.application.services import BookingService
from booking.application.ports import BookingRepository, EventBus
from booking.interfaces.schemas import (
    BookingCreate,
    BookingOut,
    BookingConfirm,
)
from common.dependencies import get_booking_repository, get_event_bus
from common.exceptions import handle_domain_error


router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def create_booking(
    data: BookingCreate,
    service: BookingService = Depends(get_booking_service),
):
    """Create a new booking."""
    try:
        booking = service.create_booking(
            customer_id=data.customer_id,
            facility_id=data.facility_id,
            slot=data.to_slot(),
        )
        return BookingOut.from_entity(booking)
    except SlotNotAvailableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
```

## Dependency Rule Enforcement

> **Rule** — Domain layer imports NOTHING from outside the domain folder.

Verify with:

```bash
# Check domain has no framework imports
python -c "
import ast
import sys

forbidden = {'fastapi', 'sqlalchemy', 'redis', 'pydantic', 'jwt', 'bcrypt'}

def check_file(path):
    with open(path) as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(forbidden in alias.name for forbidden in forbidden):
                    print(f'{path}: forbidden import {alias.name}')
        if isinstance(node, ast.ImportFrom):
            if node.module and any(forbidden in node.module for forbidden in forbidden):
                print(f'{path}: forbidden import {node.module}')

import sys
for f in sys.argv[1:]:
    check_file(f)
" src/booking/domain/*.py
```

## Why This Structure

| Aspect | Benefit |
|--------|---------|
| Domain independence | Domain logic is testable without FastAPI, DB, or Redis |
| Port/Adapter pattern | Easy to swap implementations (SQLAlchemy → ORM, Redis → Kafka) |
| Explicit dependencies | Application layer shows what it needs |
| Testable | Each layer can be mocked independently |

## Common Pitfalls

1. **Domain importing infrastructure** — Violates the dependency rule. Domain becomes untestable.
2. **Business logic in routers** — Controllers should only translate HTTP; business logic belongs in services.
3. **Anemic domain** — Entities with no behavior, just data. Domain logic leaks into services.
4. **Fat services** — Services doing too much. Extract to domain services.

## Related Documents

- [Dependency Injection](dependency-injection.md)
- [Repositories](repositories.md)
- [Services](services.md)
- [Schemas & Validation](schemas-validation.md)
