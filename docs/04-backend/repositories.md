# Repositories

> This document defines the repository pattern implementation. Repositories abstract persistence, providing a collection-like interface for aggregate retrieval and storage.

## Overview

Repositories are the bridge between the domain and data storage. They implement the **ports** defined in the application layer and handle all database operations. One repository per aggregate root is the fundamental rule.

## Repository Per Aggregate

> **Rule** — Each aggregate root has exactly one repository. Never create repositories for entities that are not aggregate roots.

```python
# booking/application/ports.py
class BookingRepository(ABC):
    """Port for Booking aggregate."""
    ...

class BookingLineRepository(ABC):  # BAD: Not an aggregate root
    """Port for BookingLine entity."""
    ...
```

## Standard Interface

Every repository implements these core methods:

```python
from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional, List, Protocol


class Repository(Protocol[T]):
    """Generic repository protocol."""

    @abstractmethod
    def get(self, id: UUID) -> Optional[T]:
        """Get aggregate by ID."""
        ...

    @abstractmethod
    def save(self, aggregate: T) -> T:
        """Save (create or update) aggregate."""
        ...

    @abstractmethod
    def delete(self, id: UUID) -> None:
        """Hard delete aggregate."""
        ...
```

## Concrete Implementation

```python
# src/booking/infrastructure/repositories.py
from uuid import UUID
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session, Query
from sqlalchemy import and_, or_

from booking.application.ports import BookingRepository
from booking.domain.entities import Booking
from booking.domain.value_objects import BookingStatus, TimeSlot
from booking.infrastructure.persistence.models import BookingModel
from booking.infrastructure.persistence.mappers import BookingMapper


class SQLAlchemyBookingRepository(BookingRepository):
    """SQLAlchemy implementation of BookingRepository."""

    def __init__(self, session: Session):
        self._session = session
        self._mapper = BookingMapper()

    def get(self, booking_id: UUID) -> Optional[Booking]:
        """Get booking by ID, filtering soft-deleted."""
        model = self._session.query(BookingModel).filter(
            BookingModel.id == booking_id,
            BookingModel.deleted_at.is_(None)
        ).first()

        return self._mapper.to_domain(model) if model else None

    def get_with_lock(self, booking_id: UUID) -> Optional[Booking]:
        """Get booking with pessimistic lock for critical updates."""
        model = self._session.query(BookingModel).filter(
            BookingModel.id == booking_id,
            BookingModel.deleted_at.is_(None)
        ).with_for_update().first()

        return self._mapper.to_domain(model) if model else None

    def save(self, booking: Booking) -> Booking:
        """Save booking (insert or update)."""
        existing = self._session.query(BookingModel).filter(
            BookingModel.id == booking.id
        ).first()

        if existing:
            self._mapper.update_model(existing, booking)
            model = existing
        else:
            model = self._mapper.to_model(booking)
            self._session.add(model)

        self._session.flush()
        return booking

    def delete(self, booking_id: UUID) -> None:
        """Hard delete - use sparingly, prefer soft delete."""
        self._session.query(BookingModel).filter(
            BookingModel.id == booking_id
        ).delete()
        self._session.flush()

    def list_by_customer(
        self,
        customer_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Booking]:
        """List bookings for a customer."""
        models = self._session.query(BookingModel).filter(
            BookingModel.customer_id == customer_id,
            BookingModel.deleted_at.is_(None)
        ).order_by(
            BookingModel.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [self._mapper.to_domain(m) for m in models]

    def list_by_facility(
        self,
        facility_id: UUID,
        start_date: datetime,
        end_date: datetime,
        status: Optional[BookingStatus] = None,
    ) -> List[Booking]:
        """List bookings for a facility in a date range."""
        query = self._session.query(BookingModel).filter(
            BookingModel.facility_id == facility_id,
            BookingModel.slot_date >= start_date,
            BookingModel.slot_date <= end_date,
            BookingModel.deleted_at.is_(None)
        )

        if status:
            query = query.filter(BookingModel.status == status.value)

        models = query.order_by(
            BookingModel.slot_date, BookingModel.slot_start_time
        ).all()

        return [self._mapper.to_domain(m) for m in models]

    def find_conflicting(
        self,
        slot: TimeSlot,
        exclude_booking_id: Optional[UUID] = None,
    ) -> Optional[Booking]:
        """Find a conflicting booking for the given time slot."""
        query = self._session.query(BookingModel).filter(
            BookingModel.facility_id == slot.facility_id,
            BookingModel.slot_date == slot.date,
            BookingModel.slot_start_time < slot.end_time,
            BookingModel.slot_end_time > slot.start_time,
            BookingModel.status.in_([
                BookingStatus.PENDING.value,
                BookingStatus.CONFIRMED.value,
            ]),
            BookingModel.deleted_at.is_(None)
        )

        if exclude_booking_id:
            query = query.filter(BookingModel.id != exclude_booking_id)

        model = query.first()
        return self._mapper.to_domain(model) if model else None
```

## Query Objects

For complex queries, use **query objects** to encapsulate query logic. This avoids "string-builder soup" and makes queries testable.

```python
# src/booking/infrastructure/queries.py
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Optional, List

from sqlalchemy import and_
from sqlalchemy.orm import Query

from booking.domain.value_objects import BookingStatus


@dataclass
class BookingQuery:
    """Query object for booking queries."""
    customer_id: Optional[UUID] = None
    facility_id: Optional[UUID] = None
    status: Optional[BookingStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None

    def apply(self, query: Query) -> Query:
        """Apply filters to a base query."""
        if self.customer_id:
            query = query.filter(BookingModel.customer_id == self.customer_id)

        if self.facility_id:
            query = query.filter(BookingModel.facility_id == self.facility_id)

        if self.status:
            query = query.filter(BookingModel.status == self.status.value)

        if self.date_from:
            query = query.filter(BookingModel.slot_date >= self.date_from)

        if self.date_to:
            query = query.filter(BookingModel.slot_date <= self.date_to)

        if self.search:
            query = query.filter(
                or_(
                    BookingModel.notes.ilike(f"%{self.search}%"),
                    # Join to customer for name search
                )
            )

        return query.order_by(BookingModel.created_at.desc())


# Usage
class BookingRepositoryWithQuery:
    def __init__(self, session: Session):
        self._session = session

    def query(self, booking_query: BookingQuery, limit: int = 20, offset: int = 0) -> List[Booking]:
        base_query = self._session.query(BookingModel).filter(
            BookingModel.deleted_at.is_(None)
        )
        filtered_query = booking_query.apply(base_query)
        models = filtered_query.limit(limit).offset(offset).all()
        return [self._mapper.to_domain(m) for m in models]
```

## No Repository Calling Repository

> **Rule** — A repository must not call another repository.

```python
# BAD
class BookingRepository:
    def confirm_booking(self, booking_id: UUID):
        booking = self.get(booking_id)
        customer = self._customer_repo.get(booking.customer_id)  # VIOLATION
        if not customer.is_active:
            raise CustomerInactiveError()
        booking.confirm()
        self.save(booking)


# GOOD: Orchestration in service layer
class BookingService:
    def confirm_booking(self, booking_id: UUID, customer_repo: CustomerRepository):
        booking = self._booking_repo.get(booking_id)
        customer = customer_repo.get(booking.customer_id)  # Service fetches both
        if not customer.is_active:
            raise CustomerInactiveError()
        booking.confirm()
        self._booking_repo.save(booking)
```

## Mapping Layer

Separate the ORM model from the domain entity with a mapper.

```python
# src/booking/infrastructure/persistence/mappers.py
from datetime import datetime
from uuid import UUID

from booking.domain.entities import Booking
from booking.domain.value_objects import BookingStatus, TimeSlot
from booking.infrastructure.persistence.models import BookingModel


class BookingMapper:
    """Maps between Booking domain entity and BookingModel ORM."""

    def to_domain(self, model: BookingModel) -> Booking:
        return Booking(
            id=model.id,
            customer_id=model.customer_id,
            facility_id=model.facility_id,
            slot=TimeSlot(
                facility_id=model.facility_id,
                date=model.slot_date,
                start_time=model.slot_start_time,
                end_time=model.slot_end_time,
            ),
            status=BookingStatus(model.status),
            version=model.version,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def to_model(self, entity: Booking) -> BookingModel:
        return BookingModel(
            id=entity.id,
            customer_id=entity.customer_id,
            facility_id=entity.facility_id,
            slot_date=entity.slot.date,
            slot_start_time=entity.slot.start_time,
            slot_end_time=entity.slot.end_time,
            status=entity.status.value,
            version=entity.version,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def update_model(self, model: BookingModel, entity: Booking) -> None:
        """Update existing model with entity data."""
        model.customer_id = entity.customer_id
        model.facility_id = entity.facility_id
        model.slot_date = entity.slot.date
        model.slot_start_time = entity.slot.start_time
        model.slot_end_time = entity.slot.end_time
        model.status = entity.status.value
        model.version = entity.version
        model.updated_at = entity.updated_at
```

## Soft Delete

Repositories filter soft-deleted records by default.

```python
class BookingRepository:
    def get(self, booking_id: UUID) -> Optional[Booking]:
        return self._get_query().filter(
            BookingModel.id == booking_id
        ).first()

    def _get_query(self) -> Query:
        """Base query that filters soft-deleted."""
        return self._session.query(BookingModel).filter(
            BookingModel.deleted_at.is_(None)
        )

    def get_including_deleted(self, booking_id: UUID) -> Optional[Booking]:
        """Get booking even if soft-deleted."""
        return self._session.query(BookingModel).filter(
            BookingModel.id == booking_id
        ).first()

    def hard_delete(self, booking_id: UUID) -> None:
        """Permanently delete - only for GDPR/compliance."""
        self._session.query(BookingModel).filter(
            BookingModel.id == booking_id
        ).delete()
        self._session.flush()
```

## Testing Repositories

```python
# tests/booking/test_repository.py
import pytest
from uuid import uuid4

from booking.infrastructure.repositories import SQLAlchemyBookingRepository
from booking.infrastructure.persistence.models import BookingModel
from database import SessionLocal


@pytest.fixture
def session():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def repository(session):
    return SQLAlchemyBookingRepository(session=session)


def test_save_and_get_roundtrip(repository):
    booking_id = uuid4()
    booking = Booking(
        id=booking_id,
        customer_id=uuid4(),
        facility_id=uuid4(),
        slot=TimeSlot(...),
        status=BookingStatus.PENDING,
    )

    saved = repository.save(booking)
    retrieved = repository.get(booking_id)

    assert retrieved is not None
    assert retrieved.id == saved.id
    assert retrieved.status == BookingStatus.PENDING
```

## Related Documents

- [Module Structure](module-structure.md)
- [Transactions & Concurrency](transactions-concurrency.md)
- [Soft Delete](../06-database/soft-delete.md)
- [Transactions & Concurrency](transactions-concurrency.md)
