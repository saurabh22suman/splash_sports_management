# ADR-0001: Modular Monolith First

> Start as a modular monolith, not microservices.

## Status
Accepted

## Context
We are building the Splashh Sports Platform from scratch. The team is small (3-5 engineers), and we have limited operational experience with distributed systems. We need to deliver value quickly but also maintain the ability to scale and evolve.

## Decision
We will start as a **modular monolith** with clear module boundaries. Each module will be a separate Python package with its own:
- Router (API endpoints)
- Service (business logic)
- Repository (data access)
- Models (domain entities)
- Schemas (API contracts)

Modules will communicate via:
- **Synchronous calls** for in-context operations
- **Domain events** (via Redis Streams) for cross-context operations

## Consequences

### Positive
- **Simpler deployment** — Single artifact, single process to run
- **Easier debugging** — No distributed tracing needed initially
- **Easier refactoring** — No network boundaries to cross
- **Faster development** — No service coordination overhead
- **Clear ownership** — Each module has a single owner

### Negative
- **Limited horizontal scaling** — Must scale entire application
- **Deployment coupling** — Any change requires full redeploy
- **Technology lock-in** — All modules use same language/framework
- **Failure domain** — Bug can bring down entire system

### Neutral
- Module boundaries can be evolved into service boundaries later
- Event-driven architecture provides decoupling foundation

## Alternatives Considered

### Alternative 1: Microservices from Day 1
Rejected because:
- Team lacks operational experience with distributed systems
- Increased complexity in deployment, monitoring, debugging
- Faster initial development but slower iteration
- Premature optimization for scale we don't have

### Alternative 2: Serverless (Lambda/Functions)
Rejected because:
- Cold start latency unacceptable for our use case
- Vendor lock-in concerns
- Harder to maintain consistent architecture
- Higher cost at our expected scale

## References
- [Architecture Overview](../02-architecture/overview.md)
- [Module Structure](../04-backend/module-structure.md)
- [Event Bus](./0004-event-bus-redis-streams.md)
- [Simon Brown: Modular Monolith](https://www.youtube.com/watch?v=2rJ4QqBtjhc)
