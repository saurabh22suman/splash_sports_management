# Analytics Module

> Reports, dashboards, and data exports.

The analytics module provides **business intelligence** — aggregating data for reports, dashboards, and exports. It is primarily a read model that consumes events from other modules.

> **Status — NOT YET IMPLEMENTED.** The backend module folder,
> alembic migration, FastAPI router, and PWA pages do not exist in
> `apps/backend/src/` or `apps/web-pwa/src/`. This module is a design
> placeholder; implementation has not started.

---

## Purpose

The analytics module:
- Aggregates events into analytical models
- Provides pre-built reports
- Supports ad-hoc queries
- Manages data exports

---

## Aggregates

### Report

```python
class Report(AggregateRoot):
    id: UUID
    tenant_id: UUID
    name: str
    report_type: ReportType  # BOOKINGS_REVENUE, MEMBER_ACTIVITY, UTILIZATION
    parameters: dict
    generated_at: datetime | None
    data: dict | None
```

### Dashboard

```python
class Dashboard(AggregateRoot):
    id: UUID
    tenant_id: UUID
    name: str
    widgets: list[DashboardWidget]
    layout: dict
    is_default: bool
```

---

## Public APIs

### Reports

| Endpoint | Method | Description |
|---|---|---|
| `/analytics/reports` | GET | List reports |
| `/analytics/reports/{id}` | GET | Get report |
| `/analytics/reports/{id}/run` | POST | Generate report |
| `/analytics/reports/{id}/export` | GET | Export (CSV, PDF) |

### Dashboards

| Endpoint | Method | Description |
|---|---|---|
| `/analytics/dashboards` | GET | List dashboards |
| `/analytics/dashboards/{id}` | GET | Get dashboard |
| `/analytics/dashboards/{id}` | POST | Create dashboard |

### Queries

| Endpoint | Method | Description |
|---|---|---|
| `/analytics/query` | POST | Run ad-hoc query |

---

## Events Consumed

The analytics module consumes events from:

| Event | Source | Usage |
|---|---|---|
| `BookingCreated` | booking | Revenue tracking |
| `BookingCompleted` | booking | Utilization |
| `MembershipStarted` | membership | Member counts |
| `PaymentCaptured` | payments | Revenue |
| `CustomerRegistered` | customer | Member acquisition |
| `NotificationDelivered` | notifications | Engagement |

---

## Dependencies

**Upstream:** All modules (consumes events)

**Downstream:** None (analytics is a sink)

---

## Invariants

1. **Multi-tenant aggregation** — All queries are tenant-scoped
2. **Anonymization** — Shared reports are anonymized
3. **Eventual consistency** — Analytics may lag (1-5 minutes)

---

## Open Questions

- Real-time dashboards? — Would require streaming
- Custom metrics? — Need builder UI

---

## Related Documents

- [Data Flow](../02-architecture/data-flow.md)
