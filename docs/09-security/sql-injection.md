# SQL Injection Prevention

> This document details ourSQL injection prevention strategy, covering parameterized queries, ORM usage, input validation, code review practices, and testing approaches.

SQL injection is one of the most severe vulnerabilities in web applications. A successful injection can result in complete data breach, data modification, or database compromise. We prevent SQL injection through defense in depth: parameterized queries at the database layer, ORM abstraction, and input validation at the application layer.

---

## Primary Defense: Parameterized Queries

We **never** construct SQL queries using string interpolation or f-strings with user input. Every query uses parameterized statements:

### Anti-pattern (NEVER DO THIS)

```python
# NEVER - vulnerable to SQL injection
user_input = request.query_params.get("name")
query = f"SELECT * FROM users WHERE name = '{user_input}'"
```

### Correct Pattern

```python
# CORRECT - parameterized query
user_input = request.query_params.get("name")
query = "SELECT * FROM users WHERE name = :name"
result = await db.fetchone(query, {"name": user_input})
```

---

## SQLAlchemy: Our ORM Layer

We use SQLAlchemy as our ORM. SQLAlchemy automatically uses parameterized queries when using its Query API:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

# SQLAlchemy uses parameterized queries automatically
def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

# For complex queries, use text() with parameters
def search_bookings(db: Session, tenant_id: str, sport: str | None = None):
    query = text("""
        SELECT b.* FROM bookings b
        WHERE b.tenant_id = :tenant_id
    """)
    params = {"tenant_id": tenant_id}

    if sport:
        query += " AND b.sport = :sport"
        params["sport"] = sport

    return db.execute(query, params)
```

> **Rule** — All database queries must use SQLAlchemy or raw parameterized queries. Raw string concatenation with user input is prohibited at all levels.

---

## Pydantic: Input Validation Gate

Before any user input reaches the database layer, it passes through Pydantic validation. This provides an early defense layer:

```python
from pydantic import BaseModel, Field
from typing import Optional

class BookingSearchParams(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    sport: Optional[str] = Field(None, max_length=50)
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, le=10000)

    # Pydantic validates types, length, and format
    # before the query is constructed
```

Pydantic's validation ensures:
- Type safety (strings are strings, dates are dates)
- Length limits (no buffer overflow attacks)
- Format validation (email regex, UUID format)
- Allow-list enforcement (enum values)

---

## Code Review Checklist

Every code review must verify SQL injection defenses:

> **Rule** — A PR that introduces raw SQL queries (via `text()` or direct cursor execution) requires explicit security review and approval.

### Checklist

- [ ] Are all queries using parameterized statements?
- [ ] Is user input bound via parameters, not string interpolation?
- [ ] Is SQLAlchemy used where possible?
- [ ] Is Pydantic validation in place for all inputs?
- [ ] Are dynamic column/table names validated against an allow-list?
- [ ] Are ORDER BY columns validated against an allow-list?

### Dynamic Query Construction

If dynamic column names are necessary (e.g., for sortable tables), use an allow-list:

```python
ALLOWED_SORT_COLUMNS = {
    "booking": ["created_at", "sport", "status", "date"],
    "member": ["created_at", "name", "email"],
    "payment": ["created_at", "amount", "status"]
}

def get_sort_column(table: str, param: str) -> str:
    """Safely resolve sort column using allow-list."""
    allowed = ALLOWED_SORT_COLUMNS.get(table, [])
    if param not in allowed:
        return "created_at"  # Default to safe default
    return param
```

---

## Testing for SQL Injection

We test for SQL injection at multiple levels:

### 1. Unit Tests with Injection Payloads

```python
import pytest

@pytest.mark.parametrize("payload", [
    "' OR '1'='1",
    "'; DROP TABLE users;--",
    "1' UNION SELECT * FROM users--",
    "<script>alert('xss')</script>",
    "$$; SELECT 1"
])
async def test_sql_injection_rejected(payload):
    """Verify injection payloads are rejected or handled safely."""
    response = await client.get(
        "/api/v1/bookings",
        params={"sport": payload}
    )
    # Should either return empty or 400
    assert response.status_code in [200, 400]
    # Should not return unexpected data
    # (additional assertions for specific payloads)
```

### 2. Integration Testing with SQLMap

We run SQLMap against staging environments in the security test suite:

```bash
# Run SQLMap against a specific endpoint
sqlmap -u "https://staging-api.splashh.com/api/v1/bookings?sport=test" \
    --level=5 --risk=3 \
    --batch \
    --output-dir=reports/sqlmap
```

### 3. Code Analysis (Semgrep)

We use Semgrep to detect potential SQL injection patterns:

```yaml
# .semgrep/rules/sql-injection.yaml
rules:
  - id: sql-injection-fstring
    pattern: f"SELECT ... {$VARIABLE} ..."
    message: Potential SQL injection via f-string
    severity: ERROR
    languages:
      - python
```

---

## Additional Protections

### Database User Permissions

Database users should have minimal privileges:

```sql
-- Application user should not be able to:
-- - DROP TABLE
-- - CREATE USER
-- - GRANT
-- - pg_read/Write_files

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA public
TO splashh_app;

-- Separate read-only user for reporting
GRANT SELECT
ON ALL TABLES IN SCHEMA public
TO splashh_readonly;
```

### Web Application Firewall (WAF)

A WAF provides an additional layer of protection:

- Blocks known SQL injection patterns
- Rate limits based on anomaly detection
- Provides logging for investigation

---

## Cross-Reference

- [Input Validation](input-validation.md) — Pydantic as validation gate
- [Tenant Isolation](tenant-isolation.md) — Tenant ID in every query
- [Authorization & RBAC](authorization-rbac.md) — Query-level authorization
- [Security Testing](security-testing.md) — SAST and DAST
