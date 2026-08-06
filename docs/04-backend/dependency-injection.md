# Dependency Injection

> This document covers dependency injection patterns in the FastAPI application. We use FastAPI's native `Depends` system augmented with a custom container for complex scenarios.

## Overview

Dependency injection (DI) is the mechanism by which components declare their dependencies and have those dependencies provided at runtime. In our architecture, DI enables:

1. **Testability** — Dependencies are easily swapped for mocks
2. **Loose coupling** — Components depend on abstractions, not implementations
3. **Lifetime management** — Singleton, request-scoped, and transient lifecycles

## FastAPI Depends

FastAPI's `Depends` is the primary DI mechanism. It integrates with the request lifecycle and supports async dependencies.

### Basic Usage

```python
# src/common/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session

from database import SessionLocal


def get_db() -> Session:
    """Provide a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

```python
# src/booking/interfaces/router.py
from fastapi import APIRouter, Depends

from booking.application.services import BookingService
from booking.application.ports import BookingRepository
from booking.infrastructure.repositories import SQLAlchemyBookingRepository
from common.dependencies import get_db


def get_booking_repository(db: Session = Depends(get_db)) -> BookingRepository:
    """Provide booking repository."""
    return SQLAlchemyBookingRepository(session=db)


def get_booking_service(
    repository: BookingRepository = Depends(get_booking_repository),
    event_bus: EventBus = Depends(get_event_bus),
) -> BookingService:
    """Provide booking service."""
    return BookingService(repository=repository, event_bus=event_bus)


router = APIRouter()


@router.post("/bookings")
async def create_booking(
    data: BookingCreate,
    service: BookingService = Depends(get_booking_service),
):
    return service.create_booking(...)
```

## Custom Container Pattern

For complex scenarios (multi-tenant isolation, scoped dependencies, complex wiring), we use a custom container built on `di` (a Python DI library) or manual factory pattern.

### Container Implementation

```python
# src/container.py
from contextlib import contextmanager
from typing import TypeVar, Type, Callable, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session
import redis.asyncio as redis

from database import SessionLocal, engine
from redis import Redis


T = TypeVar("T")


@dataclass
class Container:
    """Simple dependency container with lifetime management."""

    _singletons: dict[Type, object] = {}
    _factories: dict[Type, Callable] = {}

    def register_singleton(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a singleton (created once, shared across requests)."""
        self._factories[interface] = factory
        self._singletons[interface] = None  # Lazy init

    def register_transient(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a transient (new instance per request)."""
        self._factories[interface] = factory

    def register_scoped(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a scoped (instance per scope, e.g., request)."""
        self._factories[interface] = factory

    def get(self, interface: Type[T]) -> T:
        """Resolve a dependency."""
        if interface not in self._factories:
            raise KeyError(f"No registration for {interface}")

        # Check if singleton already exists
        if interface in self._singletons and self._singletons[interface] is not None:
            return self._singletons[interface]

        # Create instance
        factory = self._factories[interface]
        instance = factory()

        # Cache if singleton
        if interface in self._singletons:
            self._singletons[interface] = instance

        return instance


# Global container instance
container = Container()


def setup_container() -> None:
    """Setup container registrations."""

    # Database - request-scoped
    def db_factory() -> Session:
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    container.register_scoped(Session, db_factory)

    # Redis - singleton (connection pool)
    def redis_factory() -> Redis:
        return Redis.from_url(
            get_settings().REDIS_URL,
            decode_responses=True,
        )

    container.register_singleton(redis.Redis, redis_factory)

    # Repositories - request-scoped
    from booking.infrastructure.repositories import SQLAlchemyBookingRepository

    def booking_repo_factory() -> BookingRepository:
        session = container.get(Session)
        return SQLAlchemyBookingRepository(session=session)

    container.register_scoped(BookingRepository, booking_repo_factory)

    # Event bus - singleton
    def event_bus_factory() -> EventBus:
        redis_client = container.get(redis.Redis)
        return RedisEventBus(redis_client)

    container.register_singleton(EventBus, event_bus_factory)
```

### Integrating with FastAPI

```python
# src/main.py
from fastapi import FastAPI, Request
from contextvars import ContextVar

from container import container, setup_container


# Context variable for request-scoped dependencies
_request_container: ContextVar[dict] = ContextVar("request_container", default={})


def get_from_container(interface: Type[T]) -> T:
    """Get dependency from container, respecting scope."""
    # Check if we're in a request context
    try:
        request_container = _request_container.get()
        if interface in request_container:
            return request_container[interface]
    except LookupError:
        pass

    # Fall back to global container
    return container.get(interface)


app = FastAPI()


@app.on_event("startup")
async def startup():
    setup_container()


@app.middleware("http")
async def container_middleware(request: Request, call_next):
    """Initialize request-scoped dependencies."""
    request_container = {}

    # Provide request-scoped database session
    db = SessionLocal()
    request_container[Session] = db

    token = _request_container.set(request_container)
    try:
        response = await call_next(request)
        return response
    finally:
        _request_container.reset(token)
        db.close()
```

## Lifetime Management

> **Rule** — Choose the appropriate lifetime for each dependency.

| Lifetime | When to Use | Example |
|----------|-------------|---------|
| **Singleton** | State that can be safely shared across all requests | Connection pools, config, loggers |
| **Request-scoped** | Per-request state that should be isolated | DB sessions, current user |
| **Transient** | Stateless factories that create new instances each time | View models, DTOs |

### Singleton Examples

```python
# Good: Redis connection pool is thread-safe and expensive to create
container.register_singleton(redis.Redis, lambda: Redis.from_url(settings.REDIS_URL))

# Good: Event bus is stateless and shared
container.register_singleton(EventBus, lambda: RedisEventBus(redis_client))

# Bad: DB session as singleton - sessions are not thread-safe
# container.register_singleton(Session, lambda: SessionLocal())
```

### Request-Scoped Examples

```python
# Good: DB session - must be isolated per request
container.register_scoped(Session, lambda: SessionLocal())

# Good: Repository using the session
container.register_scoped(
    BookingRepository,
    lambda: SQLAlchemyBookingRepository(session=container.get(Session))
)
```

### Transient Examples

```python
# Good: Each request gets a fresh service instance (if stateless)
container.register_transient(BookingService, lambda: BookingService(...))

# Good: Request-specific view models
container.register_transient(BookingListViewModel, lambda: BookingListViewModel(...))
```

## Avoiding Global State

> **Anti-pattern** — Never use module-level globals for dependencies.

```python
# BAD: Global state
class BookingService:
    def __init__(self):
        self.repo = some_global_repo  # Not injectable!


# GOOD: Explicit dependencies
class BookingService:
    def __init__(self, repository: BookingRepository):
        self._repository = repository
```

## Testing with DI

The primary benefit of DI is testability.

```python
# tests/booking/test_services.py
import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from booking.application.services import BookingService
from booking.application.ports import BookingRepository, EventBus
from booking.domain.value_objects import TimeSlot


@pytest.fixture
def mock_repository():
    return MagicMock(spec=BookingRepository)


@pytest.fixture
def mock_event_bus():
    return MagicMock(spec=EventBus)


@pytest.fixture
def booking_service(mock_repository, mock_event_bus):
    return BookingService(
        repository=mock_repository,
        event_bus=mock_event_bus,
    )


def test_create_booking_success(booking_service, mock_repository, mock_event_bus):
    # Arrange
    customer_id = uuid4()
    facility_id = uuid4()
    slot = TimeSlot(...)

    mock_repository.find_conflicting.return_value = None

    # Act
    result = booking_service.create_booking(customer_id, facility_id, slot)

    # Assert
    mock_repository.save.assert_called_once()
    mock_event_bus.publish.assert_called_once()
```

## Circular Dependencies

If you encounter circular dependencies, refactor:

1. **Extract interfaces** — Both classes depend on abstractions
2. **Lazy injection** — Use `Depends(lazy_getter)`
3. **Event-driven** — Decouple with domain events

```python
# Avoid circular: Use interface
class OrderService:
    def __init__(self, payment_gateway: PaymentGateway):
        self._payment_gateway = payment_gateway


class PaymentService:
    def __init__(self, order_repository: OrderRepository):
        self._order_repository = order_repository
```

## Related Documents

- [Module Structure](module-structure.md)
- [Repositories](repositories.md)
- [Services](services.md)
- [Configuration](configuration.md)
