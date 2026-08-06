# ADR-0002: FastAPI + PostgreSQL + Redis

> The core backend technology stack.

## Status
Accepted

## Context
We need a backend stack that supports:
- Asynchronous request handling (high concurrency)
- Strong typing throughout (maintainability)
- ORM with migrations (database management)
- Caching and message queue (performance)

## Decision
We will use:
- **FastAPI** — Async Python web framework
- **PostgreSQL** — Primary database
- **Redis** — Caching, session store, message queue
- **SQLAlchemy** — ORM (async)
- **Alembic** — Migrations

## Consequences

### Positive
- **Async-first** — Native async/await, high concurrency
- **Strong typing** — Pydantic + mypy, type safety
- **Great ecosystem** — Many libraries, good documentation
- **PostgreSQL** — Reliable, feature-rich, good JSON support
- **Redis** — Versatile (cache + queue), fast, simple ops

### Negative
- **Vendor ecosystem** — Limited to Python ecosystem
- **Hiring pool** — Smaller than Node.js or Java
- **Redis persistence** — Not as durable as Kafka for events

### Neutral
- FastAPI auto-generates OpenAPI spec
- SQLAlchemy requires learning curve

## Alternatives Considered

### Alternative 1: Django
Rejected because:
- Synchronous by default, requires extra work for async
- ORM is more coupled, harder to replace
- Heavy framework, less flexibility

### Alternative 2: Node.js + Express
Rejected because:
- Less type safety without explicit effort
- Less structured than FastAPI + Pydantic
- JavaScript ecosystem is larger but more fragmented

### Alternative 3: MySQL
Rejected because:
- PostgreSQL has better JSON support
- PostgreSQL has better full-text search
- Team has more PostgreSQL experience

## References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
