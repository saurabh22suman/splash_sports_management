# ADR-0003: Multi-tenant Strategy

> How we isolate tenant data.

## Status
Accepted

## Context
Splashh is a SaaS platform serving multiple sports clubs. Each club (tenant) must have:
- Isolated data (no cross-tenant access)
- Customizable configuration (pricing, policies)
- Fast onboarding (self-serve signup)
- Cost efficiency (share infrastructure)

## Decision
We will use **shared schema with tenant_id**:
- All tables have a `tenant_id` column
- Row-level security (RLS) enforces isolation at DB level
- Application always sets tenant context from JWT
- No schema migration per tenant

## Consequences

### Positive
- **Fast onboarding** — New tenant in seconds, no infra provisioning
- **Cost efficient** — Single database, shared resources
- **Easy operations** — One schema to backup, migrate, optimize
- **RLS defense** — Database enforces isolation even if app has bugs

### Negative
- **Schema coupling** — All tenants on same schema version
- **Noisy neighbor** — One tenant's load affects others
- **Complex queries** — Always need tenant_id filter
- **Limited isolation** — DB-level isolation, not network-level

### Neutral
- Works well for our expected tenant count (100s, not 1000s)
- Can evolve to schema-per-tenant if needed

## Alternatives Considered

### Alternative 1: Schema-per-tenant
Rejected because:
- Slower provisioning (requires DDL)
- More complex operations (100s of schemas)
- Harder to query across tenants (analytics)
- Increased storage overhead

### Alternative 2: Database-per-tenant
Rejected because:
- Overkill for our scale
- Operational complexity
- Much higher cost
- Harder to migrate

## Implementation

```sql
-- Example RLS policy
CREATE POLICY bookings_tenant_isolation ON bookings
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Application sets tenant context
async def get_db():
    async with get_engine().connect() as conn:
        await conn.execute(
            text(f"SET app.current_tenant_id = '{tenant_id}'")
        )
        yield conn
```

## References
- [Tenant Isolation](../09-security/tenant-isolation.md)
- [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
