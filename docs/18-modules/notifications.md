# Notifications Module

> Email, SMS, push, and in-app notifications.

The notifications module handles **outbound communication** — sending emails, SMS, push notifications, and in-app messages to users.

> **Status — NOT YET IMPLEMENTED.** The backend module folder,
> alembic migration, FastAPI router, and PWA pages do not exist in
> `apps/backend/src/` or `apps/web-pwa/src/`. This module is a design
> placeholder; implementation has not started.

---

## Purpose

The notifications module:
- Renders notification templates
- Selects delivery channel (email, SMS, push)
- Manages delivery attempts and retries
- Handles opt-out preferences

---

## Aggregates

### NotificationTemplate

```python
class NotificationTemplate(AggregateRoot):
    id: UUID
    tenant_id: UUID
    name: str  # "booking_confirmation"
    channel: Channel  # EMAIL, SMS, PUSH, IN_APP
    subject: str | None  # For email
    body_template: str  # Jinja2 template
    variables: list[str]  # Expected variables
    is_active: bool
```

### NotificationDelivery

```python
class NotificationDelivery(AggregateRoot):
    id: UUID
    tenant_id: UUID
    template_id: UUID
    recipient_id: UUID
    channel: Channel
    status: DeliveryStatus  # PENDING, SENT, DELIVERED, FAILED
    channel_message_id: str | None  # Provider's ID
    sent_at: datetime | None
    delivered_at: datetime | None
    error_message: str | None
    retry_count: int
```

---

## Public APIs

### Send Notifications

| Endpoint | Method | Description |
|---|---|---|
| `/notifications/send` | POST | Send notification (internal) |
| `/notifications/send-bulk` | POST | Send bulk (internal) |

### Templates

| Endpoint | Method | Description |
|---|---|---|
| `/notifications/templates` | GET | List templates |
| `/notifications/templates/{id}` | GET | Get template |
| `/notifications/templates` | POST | Create template |
| `/notifications/templates/{id}` | PATCH | Update template |

### Deliveries

| Endpoint | Method | Description |
|---|---|---|
| `/notifications/deliveries` | GET | List deliveries |
| `/notifications/deliveries/{id}` | GET | Get delivery status |

---

## Events

| Event | Produced By | Consumed By |
|---|---|---|
| `NotificationRequested` | Any module | notifications (process) |
| `NotificationDelivered` | Delivery success | analytics |
| `NotificationFailed` | Delivery failure | analytics, (retry) |

---

## Dependencies

**Upstream:** All modules (produce notification requests)

**Downstream:** None (notifications is a sink)

---

## Invariants

1. **Template rendering** — All notifications use templates
2. **Channel selection** — Based on user preference and template
3. **Opt-out** — Users can opt out of channels
4. **Retry** — Failed deliveries retry up to 3 times

---

## Open Questions

- Support for custom templates per tenant? — Need multi-tenancy
- Push notifications on iOS? — Requires native wrapper

---

## Related Documents

- [Email Service Integration](./docs/12-devops/external-services.md)
- [Push Notifications](../05-frontend/pwa-strategy.md)
