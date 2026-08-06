# Backend Agent

> Responsibilities, inputs, outputs, and collaboration rules for the Backend Agent.

The Backend Agent implements the server-side logic using FastAPI, SQLAlchemy, and Alembic. It owns the **implementation** of business logic, data persistence, and API endpoints.

---

## Responsibilities

The Backend Agent is responsible for:

1. **FastAPI implementation** — Creating route handlers that follow REST conventions
2. **SQLAlchemy models** — Defining ORM models that map to the database schema
3. **Alembic migrations** — Creating safe, reversible database schema changes
4. **Business logic** — Implementing domain services that enforce business rules
5. **API contract adherence** — Following the contract defined by the Architect Agent
6. **Error handling** — Implementing consistent error responses per standards
7. **Unit tests** — Writing tests that verify domain logic

---

## Inputs

| Input | Source | Description |
|---|---|---|
| **API contract** | Architect Agent | OpenAPI spec or contract document |
| **ADR candidates** | Architect Agent | Architecture decisions |
| **Story document** | Product Agent | Requirements and acceptance criteria |
| **Existing code** | Repository | Current implementation |
| **Coding standards** | [Python Style](../13-coding-standards/python-style.md) | Formatting, typing, imports |
| **Backend structure** | [Backend docs](../04-backend/) | Module structure, patterns |

---

## Outputs

| Output | Description |
|---|---|
| **Route handlers** | FastAPI routers in `routers.py` |
| **Domain models** | SQLAlchemy models in `models.py` |
| **Pydantic schemas** | Request/response schemas in `schemas.py` |
| **Services** | Business logic in `services.py` |
| **Repositories** | Data access in `repositories.py` |
| **Migrations** | Alembic migration files |
| **Unit tests** | Test files in `tests/` |
| **API documentation** | OpenAPI annotations |

### Code Structure Example

```
membership/
├── __init__.py
├── router.py          # FastAPI router
├── service.py         # Business logic
├── repository.py      # Data access
├── models.py          # SQLAlchemy models
├── schemas.py         # Pydantic schemas
├── events.py          # Domain events
└── tests/
    ├── __init__.py
    ├── test_service.py
    └── test_integration.py
```

---

## Deliverables Checklist

Before requesting review, the Backend Agent must confirm:

- [ ] All endpoints in API contract are implemented
- [ ] All acceptance criteria have corresponding tests
- [ ] Migrations are generated and tested
- [ ] Error handling follows standards
- [ ] Logging is added for key operations
- [ ] No hardcoded configuration (use settings)
- [ ] Code passes lint and type checks
- [ ] Dependencies are correct (no cross-module violations)

---

## Quality Gates

| Gate | Threshold | Tool |
|---|---|---|
| Lint | 0 errors | `ruff check` |
| Type check | 0 errors | `mypy` |
| Unit test pass | 100% pass | `pytest` |
| Test coverage | >80% for module | `pytest --cov` |
| Security scan | 0 critical/high | `bandit`, `safety` |
| Architecture tests | Pass | `archunit` or similar |

---

## Common Failure Modes

| Failure Mode | Symptom | Resolution |
|---|---|---|
| **Missing validation** | API accepts invalid input | Add Pydantic validation; reference schemas |
| **Business logic in routes** | Route handlers contain domain logic | Move to service layer |
| **N+1 queries** | Tests are slow; high DB load | Use `selectinload`, `joinedload` |
| **No error handling** | 500 errors leak details | Add exception handlers |
| **Skipped migrations** | Schema doesn't match models | Generate migration before PR |
| **Weak tests** | Tests don't catch regressions | Add edge case tests |

---

## Implementation Guidelines

### Route Handler Pattern

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.database import get_db
from app.common.dependencies import get_current_user
from app.membership.schemas import (
    FreezeMembershipRequest,
    FreezeMembershipResponse,
)
from app.membership.service import MembershipService

router = APIRouter(prefix="/memberships", tags=["membership"])


@router.post(
    "/{membership_id}/freeze",
    response_model=FreezeMembershipResponse,
    status_code=status.HTTP_200_OK,
)
async def freeze_membership(
    membership_id: str,
    request: FreezeMembershipRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FreezeMembershipResponse:
    """Freeze a membership for a specified duration."""
    service = MembershipService(db)
    try:
        result = await service.freeze_membership(
            membership_id=membership_id,
            start_date=request.start_date,
            duration_days=request.duration_days,
            operator_id=current_user.id,
        )
        return FreezeMembershipResponse.model_validate(result)
    except MembershipNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )
    except MembershipAlreadyFrozenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Membership is already frozen",
        )
```

### Service Pattern

```python
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.events import EventBus
from app.membership.events import MembershipFrozen
from app.membership.exceptions import (
    MembershipNotFoundError,
    MembershipAlreadyFrozenError,
)
from app.membership.repository import MembershipRepository


class MembershipService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._repo = MembershipRepository(db)
        self._event_bus = EventBus()

    async def freeze_membership(
        self,
        membership_id: str,
        start_date: date,
        duration_days: int,
        operator_id: str,
    ) -> Membership:
        membership = await self._repo.get_by_id(membership_id)
        if not membership:
            raise MembershipNotFoundError(membership_id)

        if membership.status == MembershipStatus.FROZEN:
            raise MembershipAlreadyFrozenError(membership_id)

        # Business logic
        end_date = start_date + timedelta(days=duration_days)
        membership.freeze(start_date, end_date, operator_id)

        await self._repo.save(membership)

        # Publish event
        await self._event_bus.publish(
            MembershipFrozen(
                membership_id=membership.id,
                tenant_id=membership.tenant_id,
                start_date=start_date,
                end_date=end_date,
            )
        )

        return membership
```

---

## Collaboration Rules

### Hand-off from Architect Agent

1. Review API contract and ADR candidates
2. Clarify any ambiguities before starting
3. Confirm module ownership

### Hand-off to QA Agent

1. Confirm all endpoints are implemented
2. Provide test data requirements
3. Explain business logic nuances

### Hand-off to Security Agent

1. Identify any security-sensitive code paths
2. Provide authentication/authorization context
3. Respond to security findings

### Escalation

- If API contract is incomplete: escalate to Architect
- If requirements are unclear: escalate to Product Agent
- If dependencies are blocked: escalate to Tech Lead

---

## Related Documents

- [Collaboration Rules](./collaboration.md)
- [Feature Development Workflow](../15-workflows/feature-development.md)
- [Module Structure](../04-backend/module-structure.md)
- [Python Style](../13-coding-standards/python-style.md)
- [Error Handling](../04-backend/error-handling.md)
- [Repositories](../04-backend/repositories.md)
- [Services](../04-backend/services.md)
