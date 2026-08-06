# Transactions & Concurrency

> This document covers the Unit of Work pattern, optimistic locking, pessimistic locking, isolation levels, and deadlock prevention.

## Overview

Database transactions ensure **atomicity** (all-or-nothing), **consistency** (valid state transitions), **isolation** (concurrent execution transparency), and **durability** (committed data survives failures).

## Unit of Work Pattern

The Unit of Work (UoW) pattern groups multiple repository operations into a single atomic transaction.

```python
# src/common/uow.py
from abc import ABC, abstractmethod
from typing import Optional
from contextlib import contextmanager

from sqlalchemy.orm import Session


class UnitOfWork(ABC):
    """Abstract Unit of Work."""

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    def commit(self):
        pass

    @abstractmethod
    def rollback(self):
        pass


class SQLAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of Unit of Work."""

    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._session: Optional[Session] = None

    def __enter__(self):
        self._session = self._session_factory()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        self._session.close()

    def commit(self):
        if self._session:
            self._session.commit()

    def rollback(self):
        if self._session:
            self._session.rollback()

    @property
    def session(self) -> Session:
        if not self._session:
            raise RuntimeError("Unit of Work not started")
        return self._session


# Context manager usage
with SQLAlchemyUnitOfWork(session_factory) as uow:
    booking = booking_repo.get(booking_id)
    booking.confirm()
    booking_repo.save(booking)
    uow.commit()
```

## Integration with Services

```python
# src/booking/application/services.py
class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        event_bus: EventBus,
        uow: UnitOfWork,
    ):
        self._booking_repo = booking_repo
        self._event_bus = event_bus
        self._uow = uow

    def create_booking(self, command: CreateBookingCommand) -> BookingResult:
        with self._uow:
            # Multiple operations in one transaction
            slot = TimeSlot(...)
            existing = self._booking_repo.find_conflicting(slot)
            if existing:
                raise SlotNotAvailableError(...)

            booking = Booking(...)
            self._booking_repo.save(booking)

            # Publish event within same transaction
            self._event_bus.publish(BookingCreatedEvent(...))

            self._uow.commit()

        return BookingResult.from_entity(booking)
```

## Optimistic Locking

Use optimistic locking when conflicts are rare. We use a **version column** to detect concurrent modifications.

### Database Model

```python
# src/booking/infrastructure/models.py
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID


class BookingModel(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True)
    customer_id = Column(UUID(as_uuid=True), nullable=False)
    facility_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False)

    # Version column for optimistic locking
    version = Column(Integer, nullable=False, default=1)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
```

### Repository Implementation

```python
# src/booking/infrastructure/repositories.py
from sqlalchemy.orm import OptimisticLockError


class SQLAlchemyBookingRepository(BookingRepository):
    def save(self, booking: Booking) -> Booking:
        model = self._to_model(booking)

        # Check if existing
        existing = self._session.query(BookingModel).filter(
            BookingModel.id == booking.id
        ).first()

        if existing:
            # Increment version - will fail if concurrent modification
            model.version = existing.version + 1
            try:
                self._session.flush()  # Triggers version check
            except StaleDataError:
                raise OptimisticLockError(
                    f"Booking {booking.id} was modified by another request"
                )

            # Merge changes
            for col in ['status', 'updated_at', 'version']:
                setattr(existing, col, getattr(model, col))
        else:
            self._session.add(model)
            self._session.flush()

        return booking
```

### Domain Entity

```python
# src/booking/domain/entities.py
@dataclass
class Booking:
    id: UUID
    status: BookingStatus
    version: int = 1

    def confirm(self) -> None:
        if self.status != BookingStatus.PENDING:
            raise InvalidStateError(...)
        self.status = BookingStatus.CONFIRMED
        self.version += 1  # Increment on every change
```

## Pessimistic Locking

Use pessimistic locking for critical sections where conflicts are likely and costly (e.g., slot booking).

```python
# src/booking/infrastructure/repositories.py
class SQLAlchemyBookingRepository:
    def get_with_lock(self, booking_id: UUID) -> Optional[Booking]:
        """Get booking with FOR UPDATE lock."""
        model = self._session.query(BookingModel).filter(
            BookingModel.id == booking_id
        ).with_for_update().first()
        return self._mapper.to_domain(model)

    def find_conflicting_with_lock(
        self,
        slot: TimeSlot,
    ) -> Optional[Booking]:
        """Find conflicting booking with lock to prevent race condition."""
        model = self._session.query(BookingModel).filter(
            BookingModel.facility_id == slot.facility_id,
            BookingModel.slot_date == slot.date,
            BookingModel.slot_start_time < slot.end_time,
            BookingModel.slot_end_time > slot.start_time,
            BookingModel.status.in_(['pending', 'confirmed']),
            BookingModel.deleted_at.is_(None)
        ).with_for_update().first()  # Lock rows

        return self._mapper.to_domain(model) if model else None
```

### Booking Flow with Pessimistic Locking

```python
# src/booking/application/services.py
class BookingService:
    def create_booking(self, command: CreateBookingCommand) -> BookingResult:
        with self._uow:
            slot = TimeSlot(...)

            # Lock the facility's schedule to prevent concurrent bookings
            conflicting = self._booking_repo.find_conflicting_with_lock(slot)
            if conflicting:
                raise SlotNotAvailableError(...)

            booking = Booking(...)
            self._booking_repo.save(booking)
            self._uow.commit()

        return BookingResult.from_entity(booking)
```

## Isolation Levels

PostgreSQL isolation levels:

| Level | Dirty Read | Non-repeatable Read | Phantom Read |
|-------|------------|---------------------|--------------|
| READ UNCOMMITTED | Not possible in PG | Possible | Possible |
| READ COMMITTED | Not possible | Possible | Possible |
| REPEATABLE READ | Not possible | Not possible | Not possible* |
| SERIALIZABLE | Not possible | Not possible | Not possible |

> **Rule** — Use **REPEATABLE READ** for booking flows to prevent phantom reads.

```python
# Set isolation level
from sqlalchemy import create_engine, event


engine = create_engine(
    "postgresql://...",
    isolation_level="REPEATABLE READ",
)


# Or per-session
@contextmanager
def repeatable_read_session():
    session = session_factory()
    session.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    try:
        yield session
    finally:
        session.close()
```

## Deadlock Prevention

Deadlocks occur when two transactions hold locks in different order. Prevent by **consistent lock ordering**.

### Bad: Inconsistent Lock Order

```python
# Transaction 1: Lock A, then B
def process_booking(booking_id):
    booking = repo.get_with_lock(booking_id)  # Lock A
    facility = facility_repo.get_with_lock(booking.facility_id)  # Lock B


# Transaction 2: Lock B, then A
def cancel_booking(booking_id):
    facility = facility_repo.get_with_lock(facility_id)  # Lock B
    booking = repo.get_with_lock(booking_id)  # Lock A
```

### Good: Consistent Lock Order

```python
# Always lock in same order: facility first, then booking
def get_booking_with_facility_lock(booking_id):
    booking = self._get_booking(booking_id)
    # Always lock facility first (if not already locked)
    self._facility_repo.get_with_lock(booking.facility_id)
    # Then lock booking
    return self._booking_repo.get_with_lock(booking_id)
```

## Error Handling

```python
# src/booking/application/services.py
from sqlalchemy.exc import OperationalError
import asyncpg


class BookingService:
    def create_booking(self, command: CreateBookingCommand) -> BookingResult:
        try:
            with self._uow:
                # ... booking logic
                self._uow.commit()
        except (OperationalError, asyncpg.exceptions.LockNotAvailableError) as e:
            # Deadlock or lock timeout - retry
            if " deadlock " in str(e).lower():
                raise RetryableError("Deadlock detected, retrying") from e
            if " lock " in str(e).lower():
                raise RetryableError("Lock timeout, retrying") from e
            raise
```

## Testing Concurrency

```python
# tests/booking/test_concurrency.py
import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor


def test_concurrent_booking_same_slot():
    """Test that only one booking succeeds for the same slot."""
    # Setup
    facility_id = create_test_facility()

    # Create two concurrent booking requests
    def create_booking():
        with UnitOfWork(session_factory) as uow:
            service = BookingService(...)
            try:
                return service.create_booking(...)
            except SlotNotAvailableError:
                return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(create_booking) for _ in range(2)]
        results = [f.result() for f in futures]

    # One should succeed, one should fail
    successes = [r for r in results if r is not None]
    assert len(successes) == 1
```

## Related Documents

- [Repositories](repositories.md)
- [Services](services.md)
- [PostgreSQL Concurrency](https://www.postgresql.org/docs/current/mvcc.html)
