# ADR-0006: Repository Pattern

> How we abstract data access.

## Status
Accepted

## Context
We need clean separation between:
- **Domain logic** — Business rules, validation
- **Data access** — Database queries, ORM

The repository pattern provides this separation, making domain code testable and data access interchangeable.

## Decision
We will use **per-aggregate repositories** with **query objects**:
- Each aggregate has its own repository
- Complex queries use dedicated query objects
- Repositories return domain entities
- SQLAlchemy is the implementation detail

## Consequences

### Positive
- **Testable** — Domain logic can be tested without DB
- **Flexible** — Can swap data source (e.g., to HTTP API)
- **Clear ownership** — One repository per aggregate
- **Query objects** — Complex queries are encapsulated

### Negative
- **Boilerplate** — More files to write
- **Overhead** — For simple CRUD, it feels like overkill
- **Learning curve** — Pattern requires understanding

### Neutral
- Similar to Laravel/Eloquent patterns
- Works well with DDD

## Implementation

```python
# Repository per aggregate
class BookingRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: str) -> Booking | None:
        result = await self._session.execute(
            select(BookingModel).where(BookingModel.id == id)
        )
        return self._to_entity(result.scalar_one_or_none())

    async def save(self, booking: Booking) -> Booking:
        model = self._to_model(booking)
        self._session.add(model)
        await self._session.flush()
        return self._from_model(model)

# Query object for complex queries
class BookingQueryObject:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_available_slots(
        self,
        facility_id: str,
        date: date,
    ) -> list[Slot]:
        # Complex query logic here
        ...
```

## Alternatives Considered

### Alternative 1: Active Record (Rails style)
Rejected because:
- Domain logic mixes with persistence
- Harder to test in isolation
- Less explicit boundaries

### Alternative 2: Generic Repository
Rejected because:
- Too generic, loses type safety
- Becomes a "god repository"
- Hard to maintain

### Alternative 3: Raw Query Builder
Rejected because:
- No abstraction at all
- Hard to test
- Database logic scattered

## References
- [Repositories](../04-backend/repositories.md)
- [Domain Model](../03-domain/aggregates.md)
