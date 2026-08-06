# Services

> This document covers application service design. Services orchestrate use cases, coordinate repositories, and publish domain events. They are the entry point for business operations.

## Overview

Application services (sometimes called **use case services** or **interactors**) sit between the HTTP layer (routers) and the domain layer. Their responsibilities:

1. **Orchestration** — Coordinate multiple repositories and domain operations
2. **Transaction management** — Ensure atomicity via Unit of Work
3. **Event publishing** — Emit domain events for downstream processing
4. **Authorization** — Verify permissions for the operation
5. **Validation** — Beyond input validation, verify business rules

> **Rule** — Services accept domain types and primitives, NOT HTTP types (Request models) or ORM types.

## Service Structure

```python
# src/booking/application/services.py
from uuid import UUID
from datetime import datetime, date
from typing import List, Optional

from booking.application.ports import (
    BookingRepository,
    EventBus,
    SlotAvailabilityService,
)
from booking.domain.entities import Booking
from booking.domain.value_objects import BookingStatus, TimeSlot
from booking.domain.exceptions import (
    SlotNotAvailableError,
    BookingNotFoundError,
    BookingAlreadyConfirmedError,
)
from booking.application.dtos import (
    CreateBookingCommand,
    BookingResult,
    BookingListResult,
)


class BookingService:
    """Application service for booking operations."""

    def __init__(
        self,
        repository: BookingRepository,
        event_bus: EventBus,
        slot_service: SlotAvailabilityService,
        uow: UnitOfWork,
    ):
        self._repository = repository
        self._event_bus = event_bus
        self._slot_service = slot_service
        self._uow = uow

    def create_booking(self, command: CreateBookingCommand) -> BookingResult:
        """Create a new booking."""
        # 1. Validate slot availability
        slot = TimeSlot(
            facility_id=command.facility_id,
            date=command.date,
            start_time=command.start_time,
            end_time=command.end_time,
        )

        if not self._slot_service.is_available(slot):
            raise SlotNotAvailableError(
                f"Slot {slot.start_time}-{slot.end_time} on {slot.date} is not available"
            )

        # 2. Create aggregate
        booking = Booking(
            id=command.booking_id or UUID(),
            customer_id=command.customer_id,
            facility_id=command.facility_id,
            slot=slot,
            status=BookingStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 3. Persist within transaction
        try:
            with self._uow:
                self._repository.save(booking)

                # 4. Emit domain event
                self._event_bus.publish(BookingCreatedEvent(
                    booking_id=booking.id,
                    customer_id=booking.customer_id,
                    facility_id=booking.facility_id,
                    slot_start=datetime.combine(booking.slot.date, booking.slot.start_time),
                    slot_end=datetime.combine(booking.slot.date, booking.slot.end_time),
                ))

                self._uow.commit()

        except Exception as e:
            self._uow.rollback()
            raise

        return BookingResult.from_entity(booking)

    def confirm_booking(self, booking_id: UUID, actor_id: UUID) -> BookingResult:
        """Confirm a pending booking."""
        with self._uow:
            booking = self._repository.get(booking_id)
            if not booking:
                raise BookingNotFoundError(f"Booking {booking_id} not found")

            # Business rule: can only confirm pending bookings
            if booking.status != BookingStatus.PENDING:
                raise BookingAlreadyConfirmedError(
                    f"Booking is in {booking.status} status"
                )

            booking.confirm()
            self._repository.save(booking)

            self._event_bus.publish(BookingConfirmedEvent(booking_id=booking_id))

            self._uow.commit()

        return BookingResult.from_entity(booking)

    def cancel_booking(
        self,
        booking_id: UUID,
        reason: str,
        actor_id: UUID,
    ) -> BookingResult:
        """Cancel a booking."""
        with self._uow:
            booking = self._repository.get(booking_id)
            if not booking:
                raise BookingNotFoundError(f"Booking {booking_id} not found")

            booking.cancel(reason=reason)
            self._repository.save(booking)

            self._event_bus.publish(BookingCancelledEvent(
                booking_id=booking_id,
                reason=reason,
                cancelled_by=actor_id,
            ))

            self._uow.commit()

        return BookingResult.from_entity(booking)

    def list_bookings(
        self,
        customer_id: Optional[UUID] = None,
        facility_id: Optional[UUID] = None,
        status: Optional[BookingStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> BookingListResult:
        """List bookings with filtering and cursor pagination."""
        query = BookingQuery(
            customer_id=customer_id,
            facility_id=facility_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )

        bookings, next_cursor = self._repository.query(
            query=query,
            limit=limit,
            cursor=cursor,
        )

        return BookingListResult(
            items=[BookingResult.from_entity(b) for b in bookings],
            next_cursor=next_cursor,
        )
```

## DTOs (Data Transfer Objects)

Services should not return domain entities to the HTTP layer. Use DTOs.

```python
# src/booking/application/dtos.py
from uuid import UUID
from datetime import datetime, date, time
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class CreateBookingCommand(BaseModel):
    """Command to create a booking."""
    customer_id: UUID
    facility_id: UUID
    date: date
    start_time: time
    end_time: time
    notes: Optional[str] = None
    booking_id: Optional[UUID] = None


class BookingResult(BaseModel):
    """Result of a booking operation."""
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

    @classmethod
    def from_entity(cls, booking: "Booking") -> "BookingResult":
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
        )


class BookingListResult(BaseModel):
    """Paginated list of bookings."""
    items: List[BookingResult]
    next_cursor: Optional[str] = None
    has_more: bool = False
```

## Service Layer Rules

> **Rule** — No HTTP types in services.

```python
# BAD
class BookingService:
    def create_booking(self, request: BookingCreateRequest):  # HTTP type
        ...

# GOOD
class BookingService:
    def create_booking(self, command: CreateBookingCommand):  # Domain command
        ...
```

> **Rule** — No ORM types in services.

```python
# BAD
class BookingService:
    def create_booking(self, db: Session, data: dict):
        ...

# GOOD
class BookingService:
    def create_booking(self, command: CreateBookingCommand):
        ...
```

> **Rule** — Return domain results, not ORM models.

```python
# BAD
class BookingService:
    def get_booking(self, booking_id: UUID) -> BookingModel:  # ORM model
        ...

# GOOD
class BookingService:
    def get_booking(self, booking_id: UUID) -> Booking:  # Domain entity
        ...
```

## Error Handling

Services raise **domain exceptions**, not HTTP exceptions. The router translates them.

```python
# src/booking/application/services.py
from booking.domain.exceptions import (
    SlotNotAvailableError,
    BookingNotFoundError,
    AuthorizationError,
)


class BookingService:
    def confirm_booking(self, booking_id: UUID, actor_id: UUID) -> BookingResult:
        booking = self._repository.get(booking_id)
        if not booking:
            raise BookingNotFoundError(f"Booking {booking_id} not found")

        # Authorization check - raises DomainError subclass
        if not booking.can_be_confirmed_by(actor_id):
            raise AuthorizationError(
                f"User {actor_id} is not authorized to confirm booking {booking_id}"
            )

        booking.confirm()
        self._repository.save(booking)

        return BookingResult.from_entity(booking)
```

```python
# src/booking/interfaces/router.py
from fastapi import APIRouter, HTTPException, status
from booking.application.services import BookingService
from booking.domain.exceptions import (
    SlotNotAvailableError,
    BookingNotFoundError,
    AuthorizationError,
)


@router.post("/bookings/{booking_id}/confirm")
async def confirm_booking(
    booking_id: UUID,
    service: BookingService = Depends(get_booking_service),
):
    try:
        return service.confirm_booking(booking_id)
    except BookingNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
```

## Testing Services

```python
# tests/booking/test_services.py
import pytest
from unittest.mock import MagicMock, call
from uuid import uuid4

from booking.application.services import BookingService
from booking.application.ports import BookingRepository, EventBus
from booking.application.dtos import CreateBookingCommand
from booking.domain.entities import Booking
from booking.domain.value_objects import BookingStatus, TimeSlot
from booking.domain.exceptions import SlotNotAvailableError


@pytest.fixture
def mock_repository():
    return MagicMock(spec=BookingRepository)


@pytest.fixture
def mock_event_bus():
    return MagicMock(spec=EventBus)


@pytest.fixture
def mock_slot_service():
    service = MagicMock()
    service.is_available.return_value = True
    return service


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=None)
    uow.__exit__ = MagicMock(return_value=None)
    uow.commit = MagicMock()
    uow.rollback = MagicMock()
    return uow


@pytest.fixture
def service(mock_repository, mock_event_bus, mock_slot_service, mock_uow):
    return BookingService(
        repository=mock_repository,
        event_bus=mock_event_bus,
        slot_service=mock_slot_service,
        uow=mock_uow,
    )


def test_create_booking_success(service, mock_repository, mock_event_bus, mock_uow):
    # Arrange
    command = CreateBookingCommand(
        customer_id=uuid4(),
        facility_id=uuid4(),
        date="2024-01-15",
        start_time="10:00",
        end_time="11:00",
    )

    mock_repository.save.return_value = None

    # Act
    result = service.create_booking(command)

    # Assert
    mock_repository.save.assert_called_once()
    mock_event_bus.publish.assert_called_once()
    mock_uow.commit.assert_called_once()
    assert result.customer_id == command.customer_id


def test_create_booking_slot_unavailable(service, mock_slot_service):
    # Arrange
    command = CreateBookingCommand(...)
    mock_slot_service.is_available.return_value = False

    # Act & Assert
    with pytest.raises(SlotNotAvailableError):
        service.create_booking(command)

    mock_repository.save.assert_not_called()
```

## Anti-Patterns

1. **Anemic services** — Services that just delegate to repositories without orchestration
2. **Fat services** — Services doing too much; extract to domain services
3. **Business logic in routers** — Controllers should not contain business rules
4. **Leaking ORM types** — Domain should not know about SQLAlchemy

## Related Documents

- [Module Structure](module-structure.md)
- [Dependency Injection](dependency-injection.md)
- [Error Handling](error-handling.md)
- [Domain Events](../07-events/event-catalog.md)
