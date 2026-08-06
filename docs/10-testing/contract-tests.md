# Contract Tests

> Contract tests verify that services adhere to agreed-upon interfaces. Producer-driven tests ensure providers don't break consumers; consumer-driven tests (Pact) verify that consumers correctly handle provider responses.

This document covers our contract testing strategy: producer-driven tests for internal services, consumer-driven contract tests (Pact) for external integrations, event schema validation, and CI gates for contract drift. These tests prevent integration failures before they happen in production.

---

## What is a Contract Test

A contract test verifies:
- **Provider adherence** — The API returns what consumers expect
- **Consumer tolerance** — Consumers handle provider variations correctly
- **Schema compatibility** — JSON schemas, OpenAPI specs, event shapes

> **Rule** — Every service integration must have contract tests that run in CI before deployment.

---

## Producer-Driven Contract Tests

### OpenAPI Schema Validation

```python
# apps/backend/tests/contracts/test_openapi_contract.py
import pytest
from openapi_schema_validator import validate
import yaml


class TestOpenAPIContract:
    """Validate that API conforms to OpenAPI spec."""

    @pytest.fixture
    def openapi_spec(self):
        """Load the current OpenAPI spec."""
        with open("apps/backend/src/openapi.yaml") as f:
            return yaml.safe_load(f)

    def test_all_endpoints_have_responses_defined(self, openapi_spec):
        """Contract: every endpoint defines all response codes."""
        paths = openapi_spec.get("paths", {})

        for path, methods in paths.items():
            for method, spec in methods.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    assert "responses" in spec, f"{method.upper()} {path} missing responses"

                    # Must have success response
                    assert "200" in spec["responses"] or "201" in spec["responses"], \
                        f"{method.upper()} {path} missing success response"

    def test_all_endpoints_have_security(self, openapi_spec):
        """Contract: all endpoints require authentication."""
        paths = openapi_spec.get("paths", {})

        for path, methods in paths.items():
            for method, spec in methods.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    # Skip public endpoints
                    if path in ["/health", "/metrics", "/docs"]:
                        continue

                    # Must have security scheme
                    security = spec.get("security", openapi_spec.get("security", []))
                    assert security, f"{method.upper()} {path} missing security"

    def test_schema_definitions_are_valid(self, openapi_spec):
        """Contract: all referenced schemas exist."""
        definitions = openapi_spec.get("components", {}).get("schemas", {})

        # Check all $ref targets exist
        paths = openapi_spec.get("paths", {})

        def extract_refs(obj):
            refs = []
            if isinstance(obj, dict):
                if "$ref" in obj:
                    refs.append(obj["$ref"])
                for v in obj.values():
                    refs.extend(extract_refs(v))
            elif isinstance(obj, list):
                for item in obj:
                    refs.extend(extract_refs(item))
            return refs

        for path, methods in paths.items():
            for method, spec in methods.items():
                refs = extract_refs(spec)
                for ref in refs:
                    # Extract name from #/components/schemas/Booking
                    if ref.startswith("#/components/schemas/"):
                        schema_name = ref.split("/")[-1]
                        assert schema_name in definitions, \
                            f"Missing schema: {schema_name}"
```

### Response Schema Validation

```python
# apps/backend/tests/contracts/test_response_schemas.py
import pytest
from fastapi.testclient import TestClient
from main import app


class TestBookingResponseContract:
    """Validate booking endpoint responses match schema."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_create_booking_response_matches_schema(self, client, auth_headers):
        """Contract: POST /bookings returns correct schema."""
        response = client.post(
            "/api/v1/bookings",
            json={
                "facility_id": "court-001",
                "customer_id": "customer-001",
                "start_time": "2024-01-15T10:00:00Z",
                "duration_minutes": 60,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        # Validate response matches OpenAPI schema
        with open("apps/backend/src/openapi.yaml") as f:
            spec = yaml.safe_load(f)

        schema = spec["components"]["schemas"]["BookingResponse"]
        validate(instance=data, schema=schema)

    def test_booking_list_response_matches_schema(self, client, auth_headers):
        """Contract: GET /bookings returns correct schema."""
        response = client.get(
            "/api/v1/bookings",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Validate paginated response schema
        with open("apps/backend/src/openapi.yaml") as f:
            spec = yaml.safe_load(f)

        schema = spec["components"]["schemas"]["BookingListResponse"]
        validate(instance=data, schema=schema)
```

---

## Consumer-Driven Contract Tests (Pact)

### Pact Setup

```bash
pip install pact-python
```

### Consumer Test

```python
# apps/frontend/tests/contracts/test_payment_contract.py
import pytest
from pact import Consumer, Provider


class TestPaymentServiceContract:
    """Pact tests for payment service integration."""

    @pytest.fixture
    def pact(self):
        """Set up Pact mock server."""
        consumer = Consumer("customer-pwa")
        provider = Provider("payment-service")
        return consumer.with_pact_specification(
            specification_version="2.0.0"
        ).has_pact_with(provider)

    def test_charge_card_returns_success(self, pact):
        """Consumer: successfully charges valid card."""
        pact.given("a valid payment method")
        pact.upon_receiving("a charge request for £40")
            .with_request(
                method="POST",
                path="/api/v1/charges",
                headers={"Content-Type": "application/json"},
                body={
                    "amount": 4000,
                    "currency": "gbp",
                    "payment_method": "pm_card_visa",
                    "customer_id": "cus_123",
                },
            )
            .will_respond_with(
                status=200,
                headers={"Content-Type": "application/json"},
                body={
                    "id": "ch_abc123",
                    "amount": 4000,
                    "currency": "gbp",
                    "status": "succeeded",
                },
            )

        with pact:
            # Call the actual service
            from payments import PaymentService
            service = PaymentService(base_url=pact.uri)
            result = service.charge(
                amount=4000,
                currency="gbp",
                payment_method="pm_card_visa",
                customer_id="cus_123",
            )

        # Verify interaction occurred
        pact.verify()
        assert result["status"] == "succeeded"

    def test_charge_card_handles_decline(self, pact):
        """Consumer: handles card decline gracefully."""
        pact.given("a declined payment method")
        pact.upon_receiving("a charge request for declined card")
            .with_request(
                method="POST",
                path="/api/v1/charges",
                body={"amount": 4000, "payment_method": "pm_card_declined"},
            )
            .will_respond_with(
                status=402,
                headers={"Content-Type": "application/json"},
                body={
                    "error": {
                        "type": "card_error",
                        "code": "card_declined",
                        "message": "Your card was declined",
                    }
                },
            )

        with pact:
            from payments import PaymentService
            from payments.exceptions import CardDeclinedError

            service = PaymentService(base_url=pact.uri)
            with pytest.raises(CardDeclinedError):
                service.charge(
                    amount=4000,
                    payment_method="pm_card_declined",
                )
```

### Provider Verification

```python
# apps/payment-service/tests/contracts/test_pact_verification.py
import pytest
from pact import Provider


class TestPaymentServiceProvider:
    """Verify payment service satisfies consumer contracts."""

    @pytest.fixture
    def verifier(self):
        return Provider("http://payment-service:8000")

    def test_verifies_booking_consumer_contract(self, verifier):
        """Provider: booking service contract is satisfied."""
        verifier.verify_file(
            "apps/booking-service/tests/contracts/pacts/booking-service-payment-service.json"
        )
```

---

## Event Schema Validation

### Domain Event Schemas

```python
# apps/backend/tests/contracts/test_event_schemas.py
import pytest
import json
from jsonschema import validate, ValidationError


EVENT_SCHEMAS = {
    "booking.created": {
        "type": "object",
        "required": ["event_id", "tenant_id", "booking_id", "timestamp"],
        "properties": {
            "event_id": {"type": "string", "format": "uuid"},
            "tenant_id": {"type": "string"},
            "booking_id": {"type": "string"},
            "customer_id": {"type": "string"},
            "facility_id": {"type": "string"},
            "start_time": {"type": "string", "format": "date-time"},
            "status": {"type": "string", "enum": ["pending", "confirmed", "cancelled"]},
            "timestamp": {"type": "string", "format": "date-time"},
        },
    },
    "booking.cancelled": {
        "type": "object",
        "required": ["event_id", "tenant_id", "booking_id", "timestamp"],
        "properties": {
            "event_id": {"type": "string", "format": "uuid"},
            "tenant_id": {"type": "string"},
            "booking_id": {"type": "string"},
            "cancelled_by": {"type": "string"},
            "reason": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
        },
    },
    "membership.renewed": {
        "type": "object",
        "required": ["event_id", "tenant_id", "member_id", "timestamp"],
        "properties": {
            "event_id": {"type": "string", "format": "uuid"},
            "tenant_id": {"type": "string"},
            "member_id": {"type": "string"},
            "plan_id": {"type": "string"},
            "new_expiry": {"type": "string", "format": "date-time"},
            "timestamp": {"type": "string", "format": "date-time"},
        },
    },
}


class TestEventSchemas:
    """Validate all domain events conform to schemas."""

    @pytest.mark.parametrize("event_type", list(EVENT_SCHEMAS.keys()))
    def test_event_schema_is_valid(self, event_type):
        """Contract: event schema is valid JSON Schema."""
        schema = EVENT_SCHEMAS[event_type]
        # Basic schema validation
        assert "type" in schema
        assert "properties" in schema

    def test_booking_created_validates_against_schema(self):
        """Contract: booking.created event matches schema."""
        event = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "tenant-001",
            "booking_id": "booking-123",
            "customer_id": "customer-456",
            "facility_id": "court-001",
            "start_time": "2024-01-15T10:00:00Z",
            "status": "confirmed",
            "timestamp": "2024-01-14T15:30:00Z",
        }

        validate(instance=event, schema=EVENT_SCHEMAS["booking.created"])

    def test_booking_created_rejects_invalid_status(self):
        """Contract: invalid status is rejected."""
        event = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id": "tenant-001",
            "booking_id": "booking-123",
            "start_time": "2024-01-15T10:00:00Z",
            "status": "invalid_status",  # Not in enum
            "timestamp": "2024-01-14T15:30:00Z",
        }

        with pytest.raises(ValidationError):
            validate(instance=event, schema=EVENT_SCHEMAS["booking.created"])
```

### Event Publisher Validation

```python
# apps/backend/tests/contracts/test_event_publishing.py
import pytest
from unittest.mock import MagicMock


class TestEventPublishing:
    """Validate events are published with correct schema."""

    def test_booking_created_event_published(self):
        """Contract: booking.created event matches schema."""
        from events.publisher import EventPublisher

        mock_stream = MagicMock()
        publisher = EventPublisher(stream=mock_stream)

        # Publish event
        publisher.publish_booking_created(
            tenant_id="tenant-001",
            booking_id="booking-123",
            customer_id="customer-456",
            facility_id="court-001",
        )

        # Verify event was published
        mock_stream.publish.assert_called_once()

        # Extract published event
        published_event = mock_stream.publish.call_args[0][0]

        # Validate against schema
        validate(instance=published_event, schema=EVENT_SCHEMAS["booking.created"])
```

---

## CI Gates for Contract Drift

### GitHub Actions Workflow

```yaml
# .github/workflows/contract-tests.yml
name: Contract Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install pytest pact-python jsonschema openapi-schema-validator pyyaml

      - name: Run OpenAPI validation
        run: pytest apps/backend/tests/contracts/test_openapi_contract.py -v

      - name: Run response schema tests
        run: pytest apps/backend/tests/contracts/test_response_schemas.py -v

      - name: Run event schema tests
        run: pytest apps/backend/tests/contracts/test_event_schemas.py -v

      - name: Run Pact consumer tests
        run: pytest apps/frontend/tests/contracts/ -v

      - name: Publish Pact contracts
        if: github.ref == 'refs/heads/main'
        run: |
          pact-broker publish \
            --pact-dir=apps/frontend/tests/contracts/pacts \
            --consumer-app-version=${{ github.sha }}
```

### Pact Broker Integration

```yaml
# Trigger provider verification after contract published
provider-verification:
  needs: contract-tests
  runs-on: ubuntu-latest
  steps:
    - name: Verify provider contracts
      run: |
        pact-verifier publish-verification-results \
          --provider-url=http://payment-service:8000 \
          --pact-url=${{ secrets.PACT_BROKER_URL }}/pacts/..."
```

---

## Contract Test Checklist

- [ ] OpenAPI spec validates all endpoints
- [ ] Response schemas match consumer expectations
- [ ] Event schemas are versioned and validated
- [ ] Pact contracts defined for external services
- [ ] Consumer tests verify error handling
- [ ] Provider verification runs in CI
- [ ] Contract changes require version bump

---

## Anti-patterns

### 1. No Contract Tests

> **Anti-pattern** — "We test it end-to-end, so we don't need contracts." E2E tests are too slow to catch contract drift early. Contracts catch issues in seconds.

### 2. Overly Strict Contracts

```python
# BAD: Contract so strict it breaks on minor changes
"properties": {
    "name": {"type": "string", "minLength": 1, "maxLength": 50}
    # Adding maxLength=51 breaks existing consumers
}
```

> **Anti-pattern** — Contracts should be as loose as possible while maintaining correctness. Test for minimum requirements, not exact values.

### 3. Skipping Provider Verification

> **Anti-pattern** — Only testing consumer side. Providers can break consumers without verification.

---

## Summary

| Aspect | Tool | Rule |
|--------|------|------|
| API schemas | OpenAPI + jsonschema | Validate all responses |
| Consumer contracts | Pact | Test external integrations |
| Provider verification | Pact Broker | Verify before deploy |
| Event schemas | jsonschema | Version and validate events |
| CI gate | GitHub Actions | Block on contract failure |

See also: [API Tests](api-tests.md), [Integration Tests](integration-tests.md), [Event Catalog](../07-events/event-catalog.md).
