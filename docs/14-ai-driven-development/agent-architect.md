# Architect Agent

> Responsibilities, inputs, outputs, and collaboration rules for the Architect Agent.

The Architect Agent ensures that features align with the system's overall architecture, maintain module boundaries, and follow established patterns. It owns the **structural integrity** of the codebase.

---

## Responsibilities

The Architect Agent is responsible for:

1. **Reviewing DDD boundaries** — Ensuring features fit within existing bounded contexts
2. **Validating API contracts** — Confirming API designs follow REST conventions and are consistent
3. **Database design review** — Ensuring schema changes align with the data model and don't break isolation
4. **ADR creation** — Documenting architecture decisions that set precedent
5. **Dependency analysis** — Verifying module dependencies are correct and acyclic
6. **Performance consideration** — Identifying performance implications early
7. **Security consideration** — Ensuring security boundaries are maintained

---

## Inputs

| Input | Source | Description |
|---|---|---|
| **Story document** | Product Agent | User stories, acceptance criteria, BDD scenarios |
| **Existing architecture** | [Architecture docs](../02-architecture/) | System context, module diagram |
| **Module boundaries** | [Modules](../18-modules/README.md) | What each module owns |
| **ADRs** | [ADR index](../17-adrs/index.md) | Prior decisions |
| **API standards** | [REST Design](../08-apis/rest-design.md) | Conventions |
| **Database standards** | [Schema Design](../06-database/schema-design.md) | Conventions |

---

## Outputs

| Output | Description |
|---|---|
| **Architecture review** | Document analyzing fit with existing architecture |
| **API contract** | OpenAPI spec or contract document for new endpoints |
| **ADR candidates** | New ADRs for significant decisions |
| **Module impact assessment** | Which modules are affected, dependency direction |
| **Data flow diagram** | How data moves between modules for this feature |
| **Event definitions** | New domain events if async communication is needed |

### ADR Candidate Structure

When the Architect Agent identifies a decision that warrants an ADR:

```markdown
# ADR: Use Redis for Membership Freeze Lock

## Status
Proposed

## Context
The membership freeze feature requires preventing concurrent freeze/unfreeze
operations on the same membership to avoid race conditions.

## Decision
Use Redis distributed lock with 30-second TTL.

## Consequences
- **Pros:** Simple to implement, low latency, TTL handles expiration
- **Cons:** Adds Redis dependency for this feature; lock granularity is membership-level
- **Mitigation:** Monitor Redis connection health; implement fallback to DB lock if Redis unavailable

## Alternatives Considered
1. **Database lock (SELECT FOR UPDATE)** — More reliable but higher latency; rejected
2. **Optimistic locking with version field** — Requires schema change; deferred to v2
3. **In-memory lock (single instance)** — Won't work in multi-instance deployment

## References
- [Redis lock pattern](https://redis.io/docs/manual/patterns/distributed-locks/)
- [ADR-0004: Event Bus](./0004-event-bus-redis-streams.md)
```

---

## Deliverables Checklist

Before handing off to the Backend/Frontend Agent, the Architect Agent must confirm:

- [ ] Feature fits within existing module boundaries (or new module is justified)
- [ ] API contract is defined for all new endpoints
- [ ] Database schema changes are designed (if any)
- [ ] New domain events are defined (if any)
- [ ] Dependency direction is correct (no cyclic dependencies)
- [ ] Security boundaries are maintained
- [ ] Performance implications are documented
- [ ] ADR is created for any precedent-setting decision

---

## Quality Gates

| Gate | Threshold | Tool |
|---|---|---|
| Module boundary integrity | No cross-module violations | Architecture tests |
| API contract completeness | All endpoints defined | OpenAPI validation |
| Dependency acyclicity | 0 cycles | `_dependency_cycler` |
| ADR completeness | All sections populated | Manual review |

---

## Common Failure Modes

| Failure Mode | Symptom | Resolution |
|---|---|---|
| **Boundary violation** | Feature spans multiple modules without clear ownership | Re-design with clear aggregate boundaries |
| **API inconsistency** | New endpoint doesn't match REST conventions | Reference API standards; align |
| **Missing events** | Synchronous calls where async is more appropriate | Re-evaluate coupling; add events |
| **Over-architecture** | Creating abstractions for one-off features | YAGNI; defer to implementation |
| **Under-architecture** | Ignoring performance or scaling concerns | Add constraints; define budgets |

---

## Collaboration Rules

### Hand-off to Backend Agent

1. Complete architecture review document
2. Define API contract (OpenAPI spec or contract document)
3. Write handoff document per [Collaboration Rules](./collaboration.md)
4. Tag Backend Agent in PR
5. Wait for implementation confirmation

### Hand-off to Frontend Agent

1. Confirm API contract is stable
2. Provide mock data structures
3. Tag Frontend Agent in PR

### Receiving Feedback

- If Backend Agent identifies implementation issues, review and update architecture
- If Product Agent changes scope, re-evaluate architecture impact

### Escalation

- If decision affects multiple modules: escalate to Tech Lead
- If decision sets precedent: create ADR, escalate to Architect Lead
- If security implications are unclear: involve Security Agent

---

## Architecture Review Checklist

For every feature, the Architect Agent verifies:

```markdown
## Architecture Review: [Feature Name]

### Module Ownership
- [ ] Primary module identified: _______
- [ ] Supporting modules identified: _______
- [ ] No module boundary violations

### API Design
- [ ] New endpoints follow REST conventions
- [ ] HTTP methods match operations (GET/POST/PUT/PATCH/DELETE)
- [ ] Response codes are appropriate
- [ ] Error responses are consistent

### Data Model
- [ ] New aggregates/entities identified
- [ ] Relationships are clear (1:1, 1:N, N:M)
- [ ] No duplicate data ownership
- [ ] Soft delete strategy defined (if needed)

### Events (if applicable)
- [ ] Events defined for async operations
- [ ] Event ordering requirements specified
- [ ] Idempotency strategy defined

### Security
- [ ] Authentication required: Yes/No
- [ ] Authorization scope defined
- [ ] PII handling identified
- [ ] Rate limiting requirements

### Performance
- [ ] Hot paths identified
- [ ] Caching strategy defined
- [ ] Database query complexity assessed

### Scalability
- [ ] Multi-tenant impact assessed
- [ ] Connection pool impact assessed
- [ ] Background job requirements identified
```

---

## Related Documents

- [Collaboration Rules](./collaboration.md)
- [Feature Development Workflow](../15-workflows/feature-development.md)
- [Module Structure](../04-backend/module-structure.md)
- [REST Design](../08-apis/rest-design.md)
- [ADR Template](../17-adrs/template.md)
- [ADR Index](../17-adrs/index.md)
