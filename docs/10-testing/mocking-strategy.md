# Mocking Strategy

> Mock at the dependency boundary, not at the domain core. External services (payment gateways, SMS, external APIs) are mocked. Our own database and domain logic are not mocked in tests where we test behavior.

This document covers our mocking strategy: what to mock (external services), what NOT to mock (domain logic, own database), using pytest-mock, dependency injection patterns, and avoiding global mocks.

---

## What to Mock

### External Services

```python
# MOCK THESE - external dependencies
class PaymentGateway:
    def charge(self, amount, payment_method):
        # HTTP call to Stripe/PayPal - MOCK THIS
        response = requests.post("https://api.stripe.com/charges", ...)
        return response.json()
```

```python
# GOOD: Mock external payment gateway
def test_charge_payment_mocks_stripe(self):
    mock_gateway = MagicMock()
    mock_gateway.charge.return_value = {"id": "ch_123", "status": "succeeded"}

    service = PaymentService(gateway=mock_gateway)
    result = service.charge(amount=1000, payment_method="pm_card")

    assert result["status"] == "succeeded"
    mock_gateway.charge.assert_called_once_with(1000, "pm_card")
```

### External APIs

```python
# MOCK THESE - external HTTP calls
class NotificationClient:
    def send_sms(self, phone, message):
        # HTTP call to Twilio - MOCK THIS
        return twilio_client.messages.create(...)
```

### Third-Party Libraries

```python
# MOCK THESE - third-party with side effects
class CacheClient:
    def get(self, key):
        # Redis call - can mock for speed
        return self.redis.get(key)
```

---

## What NOT to Mock

### Domain Logic

```python
# DON'T MOCK THIS - pure domain logic
class Booking:
    @property
    def duration_minutes(self):
        return (self.end_time - self.start_time).total_seconds() / 60


# GOOD: Test domain directly
def test_booking_duration_calculation():
    booking = Booking(
        start_time=datetime(2024, 1, 15, 10, 0),
        end_time=datetime(2024, 1, 15, 11, 0),
    )
    assert booking.duration_minutes == 60
```

### Our Own Database (in Integration Tests)

```python
# DON'T MOCK THIS - in integration tests, use real DB
class TestBookingRepository:
    def test_create_and_retrieve(self):
        # REAL database - test the actual SQL
        repo = BookingRepository(session=real_db_session)

        booking = repo.create(...)
        retrieved = repo.get_by_id(booking.id)

        assert retrieved.id == booking.id
```

### Our Own Services (in Integration Tests)

```python
# DON'T MOCK THIS - test real composition
class TestBookingService:
    def test_create_booking_with_real_repo(self):
        # REAL repository - test integration
        service = BookingService(repository=real_repo)

        result = service.create_booking(...)
        assert result.id is not None
```

---

## Using pytest-mock

### Fixture-Based Mocks

```python
# conftest.py
import pytest


@pytest.fixture
def mock_payment_gateway():
    return MagicMock()


@pytest.fixture
def mock_redis():
    return MagicMock()


# Use in tests
def test_payment_charge(mocker, mock_payment_gateway):
    """Using mocker fixture."""
    service = PaymentService(gateway=mock_payment_gateway)

    service.charge(1000, "pm_card")

    mock_payment_gateway.charge.assert_called_once()
```

### Dependency Injection

```python
# GOOD: Dependency injection for testability
class BookingService:
    def __init__(self, repository, payment_gateway, notification_service):
        self._repository = repository
        self._payment_gateway = payment_gateway
        self._notification_service = notification_service


# Inject mocks in tests
def test_booking_with_payment():
    mock_repo = MagicMock()
    mock_gateway = MagicMock()
    mock_notifications = MagicMock()

    service = BookingService(
        repository=mock_repo,
        payment_gateway=mock_gateway,
        notification_service=mock_notifications,
    )
```

---

## Good vs. Bad Mocking

### Good Mocking: External Service

```python
# GOOD: Mock at the boundary
def test_cancel_booking_triggers_refund():
    mock_payment = MagicMock()
    mock_payment.refund.return_value = {"id": "rf_123", "status": "succeeded"}

    service = BookingService(
        repository=real_repo,  # Real - test integration
        payment_gateway=mock_payment,  # Mock external
    )

    service.cancel_booking("booking-123")

    mock_payment.refund.assert_called_once()
```

### Bad Mocking: Internal Logic

```python
# BAD: Mocking our own domain logic
def test_booking_cancellation():
    mock_booking = MagicMock()
    mock_booking.duration_minutes = 60
    mock_booking.start_time = datetime.utcnow() + timedelta(hours=2)

    service = BookingService(repository=MagicMock())

    # Wrong: Mocking the domain object we're testing
    service.cancel_booking(mock_booking)
```

> **Anti-pattern** — Mocking internal objects defeats the purpose of testing.

---

## Avoiding Global Mocks

### Bad: Global Mock Patch

```python
# BAD: Global patch affects all tests
@pytest.fixture(autouse=True)
def mock_database():
    with patch("database.get_db") as mock:
        yield mock
```

> **Anti-pattern** — Global mocks make tests隐形 (invisible) and cause interdependencies.

### Good: Local Fixture

```python
# GOOD: Local fixture per test
@pytest.fixture
def mock_database():
    return MagicMock()


def test_booking_creation(mock_database):
    # Only affects this test
    service = BookingService(repository=mock_database)
```

---

## Mocking Examples

### Payment Gateway

```python
class TestPaymentGateway:
    def test_successful_charge(self, mocker):
        """Mock Stripe API."""
        mock_stripe = mocker.patch("payments.stripe.Client")
        mock_stripe.return_value.charges.create.return_value = {
            "id": "ch_123",
            "status": "succeeded",
            "amount": 4000,
        }

        gateway = StripePaymentGateway()
        result = gateway.charge(amount=4000, payment_method="pm_card")

        assert result["status"] == "succeeded"

    def test_card_declined(self, mocker):
        """Mock Stripe decline."""
        mock_stripe = mocker.patch("payments.stripe.Client")
        mock_stripe.return_value.charges.create.side_effect = CardDeclinedError(
            "Your card was declined"
        )

        gateway = StripePaymentGateway()

        with pytest.raises(CardDeclinedError):
            gateway.charge(amount=4000, payment_method="pm_card_declined")
```

### SMS Notification

```python
class TestNotificationService:
    def test_sends_sms_via_twilio(self, mocker):
        """Mock Twilio client."""
        mock_twilio = mocker.patch("notifications.TwilioClient")
        mock_twilio.return_value.messages.create.return_value = {"sid": "SM123"}

        service = NotificationService()
        result = service.send_sms(to="+447700000000", message="Your booking is confirmed")

        assert result["sid"] == "SM123"
```

---

## Summary

| Mock | Don't Mock |
|------|------------|
| External APIs | Domain logic |
| Third-party services | Our own repositories (in integration) |
| Payment gateways | Our own services (in integration) |
| SMS/Email providers | Internal business rules |

---

## Anti-patterns

### 1. Mocking Everything

```python
# BAD: Over-mocked
def test_booking():
    mock_repo = MagicMock()
    mock_service = MagicMock()
    mock_cache = MagicMock()

    service = BookingService(mock_repo, mock_service, mock_cache)

    # Nothing is real - not testing anything
```

> **Anti-pattern** — Too many mocks mean you're not testing real behavior.

### 2. Mocking Domain Objects

```python
# BAD: Mocking the object under test
def test_booking_duration():
    mock_booking = MagicMock()
    mock_booking.duration_minutes = 60

    # Testing the mock, not the real object
    assert mock_booking.duration_minutes == 60
```

> **Anti-pattern** — Test real objects, not mocks of them.

### 3. Global Patches

```python
# BAD: Patch affecting all tests
patch("requests.get")
```

> **Anti-pattern** — Global patches cause hard-to-debug test failures.

---

## See Also

- [Unit Tests](unit-tests.md)
- [Integration Tests](integration-tests.md)
- [Test Data Management](test-data-management.md)
