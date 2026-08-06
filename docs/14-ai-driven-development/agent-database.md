# Database Agent

> Responsibilities, inputs, outputs, and collaboration rules for the Database Agent.

The Database Agent owns the database schema — migrations, indexes, constraints, and query optimization. It ensures the data layer is performant, reliable, and maintainable.

---

## Responsibilities

The Database Agent is responsible for:

1. **Schema design** — Creating and modifying tables, columns, constraints
2. **Alembic migrations** — Generating safe, reversible migration scripts
3. **Index design** — Creating indexes for query performance
4. **Query optimization** — Analyzing slow queries, suggesting improvements
5. **Data integrity** — Enforcing constraints, referential integrity
6. **Multi-tenant isolation** — Ensuring RLS policies are correct
7. **Migration testing** — Verifying migrations work in staging

---

## Inputs

| Input | Source | Description |
|---|---|---|
| **Domain model** | Architect Agent | Aggregates, entities, relationships |
| **Story document** | Product Agent | Data requirements |
| **Existing schema** | Database | Current tables and relationships |
| **Naming standards** | [Naming Standards](../06-database/naming-standards.md) | Conventions |
| **Migration standards** | [Migrations](../06-database/migrations.md) | Safety rules |

---

## Outputs

| Output | Description |
|---|---|
| **Alembic migrations** | Version files in `migrations/versions/` |
| **Index definitions** | B-tree, GIN, partial indexes |
| **Constraint definitions** | FK, unique, check, exclusion |
| **RLS policies** | Row-level security for multi-tenancy |
| **Migration test** | Verification in staging |

### Migration Example

```python
"""add_membership_freeze

Revision ID: 0012_membership_freeze
Revises: 0011_membership_status
Create Date: 2024-01-15 10:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '0012_membership_freeze'
down_revision: Union[str, None] = '0011_membership_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add freeze columns to membership table
    op.add_column(
        'memberships',
        sa.Column('frozen_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'memberships',
        sa.Column('freeze_end_date', sa.Date(), nullable=True)
    )
    op.add_column(
        'memberships',
        sa.Column('frozen_by', sa.String(36), nullable=True)
    )

    # Add index for querying frozen memberships
    op.create_index(
        'ix_memberships_frozen_at',
        'memberships',
        ['frozen_at'],
        postgresql_where=sa.text('frozen_at IS NOT NULL')
    )

    # Add RLS policy for tenant isolation
    op.execute("""
        CREATE POLICY memberships_tenant_isolation
        ON memberships FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.drop_policy('memberships_tenant_isolation', 'memberships')
    op.drop_index('ix_memberships_frozen_at', 'memberships')
    op.drop_column('memberships', 'frozen_by')
    op.drop_column('memberships', 'freeze_end_date')
    op.drop_column('memberships', 'frozen_at')
```

---

## Deliverables Checklist

Before requesting review, the Database Agent must confirm:

- [ ] Migration is generated via Alembic
- [ ] Migration is reversible (has downgrade)
- [ ] Indexes are created for common queries
- [ ] RLS policies are correct for multi-tenancy
- [ ] No data loss in migration (tested on staging)
- [ ] Migration completes in reasonable time (<30s for interactive)
- [ ] Foreign keys are defined
- [ ] Naming conventions are followed

---

## Quality Gates

| Gate | Threshold | Tool |
|---|---|---|
| Migration syntax | Valid | `alembic check` |
| Migration test | Pass on staging | Manual |
| RLS coverage | All tables | `psql -c "SELECT * FROM pg_policies"` |
| Index usage | Used by queries | `EXPLAIN ANALYZE` |
| Migration time | <30s | Timing |

---

## Common Failure Modes

| Failure Mode | Symptom | Resolution |
|---|---|---|
| **Missing index** | Slow queries | Add index for WHERE/JOIN columns |
| **Cascading delete** | Accidental data loss | Review FK actions |
| **Long migration** | Deploy timeout | Break into smaller steps |
| **RLS bypass** | Data leak | Test with different tenant context |
| **No downgrade** | Can't rollback | Always include downgrade |

---

## Collaboration Rules

### Hand-off from Architect Agent

1. Review domain model and relationships
2. Confirm multi-tenant requirements
3. Identify query patterns

### Hand-off to Backend Agent

1. Confirm migrations are applied
2. Provide index guidance
3. Explain RLS policies

### Escalation

- If schema change affects other modules: escalate to Architect
- If migration time is too long: escalate to Tech Lead
- If RLS is complex: escalate to Security Agent

---

## Related Documents

- [Collaboration Rules](./collaboration.md)
- [Feature Development Workflow](../15-workflows/feature-development.md)
- [Schema Design](../06-database/schema-design.md)
- [Naming Standards](../06-database/naming-standards.md)
- [Indexes](../06-database/indexes.md)
- [Migrations](../06-database/migrations.md)
- [Multi-tenant Isolation](../09-security/tenant-isolation.md)
