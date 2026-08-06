# BDD (Behavior-Driven Development)

> BDD uses Gherkin scenarios (Given-When-Then) as executable specifications. It adds value when cross-team alignment is needed (product, engineering, QA) but adds overhead for internal APIs where engineers already share language.

This document covers when BDD adds value, feature file structure, pytest-bdd usage, and when to avoid BDD overhead.

---

## What is BDD

BDD uses natural language scenarios:

```gherkin
Feature: Booking Cancellation
  As a member
  I want to cancel my booking
  So that I can get a refund if I cancel in time

  Scenario: Cancel booking within cancellation window
    Given I have a confirmed booking for tomorrow at 10:00
    When I cancel the booking 24 hours before start time
    Then I should receive a 100% refund

  Scenario: Cancel booking outside cancellation window
    Given I have a confirmed booking starting in 2 hours
    When I cancel the booking
    Then I should receive no refund
    And the booking status should be "cancelled_no_refund"
```

---

## When BDD Adds Value

### Cross-Team Requirements

```gherkin
Feature: Membership Pricing
  As a Product Manager
  I want member pricing tiers
  So that I can offer discounts to loyal members

  Scenario: Premium member gets 20% discount
    Given a customer with "premium" membership
    When they book a court priced at £40/hour
    Then the total should be £32
```

**When BDD helps:**
- Product defines requirements in Gherkin
- Engineers implement to match
- QA validates against scenarios
- Living documentation for stakeholders

### Customer-Facing Features

```gherkin
Feature: Online Booking
  As a club member
  I want to book facilities online
  So that I don't have to call the club
```

---

## When to Avoid BDD

### Internal APIs

```gherkin
# AVOID: Internal API contracts
Feature: Booking Repository
  Scenario: Save booking
    Given a valid Booking object
    When save() is called
    Then the booking should be persisted
```

> **Anti-pattern** — BDD adds overhead for internal APIs where:
> - Engineers share the domain language
> - Tests are for developers, not stakeholders
> - Unit/integration tests are faster

### Rapid Development

> **Anti-pattern** — BDD slows down early-stage development when requirements change frequently.

---

## pytest-bdd Setup

### Installation

```bash
pip install pytest-bdd
```

### Structure

```
tests/
├── features/
│   ├── booking_cancellation.feature
│   └── membership_pricing.feature
└── steps/
    ├── test_booking_cancellation.py
    └── test_membership_pricing.py
```

### Feature File

```gherkin
# tests/features/booking_cancellation.feature
Feature: Booking Cancellation
  Cancel bookings and calculate refunds

  Scenario: Cancel within 24 hours - full refund
    Given a confirmed booking for tomorrow at 10:00
    And the booking amount is £40
    When I cancel the booking
    Then the refund should be £40
    And the booking status should be "cancelled"

  Scenario: Cancel within 12-24 hours - 50% refund
    Given a confirmed booking for 18 hours from now
    And the booking amount is £40
    When I cancel the booking
    Then the refund should be £20
    And the booking status should be "cancelled"

  Scenario: Cancel less than 12 hours before - no refund
    Given a confirmed booking for 6 hours from now
    And the booking amount is £40
    When I cancel the booking
    Then the refund should be £0
    And the booking status should be "cancelled_no_refund"
```

### Step Implementation

```python
# tests/steps/test_booking_cancellation.py
from pytest_bdd import scenario, given, when, then
import pytest
from datetime import datetime, timedelta


@given("a confirmed booking for tomorrow at 10:00")
def confirmed_booking_tomorrow():
    return {
        "id": "booking-123",
        "start_time": datetime.utcnow() + timedelta(days=1, hours=10 - datetime.utcnow().hour),
        "amount": 40.00,
        "status": "confirmed",
    }


@given("the booking amount is £40")
def booking_amount(confirmed_booking_tomorrow):
    confirmed_booking_tomorrow["amount"] = 40.00


@given("a confirmed booking for 18 hours from now")
def booking_in_18_hours():
    return {
        "id": "booking-124",
        "start_time": datetime.utcnow() + timedelta(hours=18),
        "amount": 40.00,
        "status": "confirmed",
    }


@when("I cancel the booking")
def cancel_booking(confirmed_booking_tomorrow):
    from booking.service import BookingService

    service = BookingService(repository=MagicMock())
    result = service.cancel_booking(confirmed_booking_tomorrow["id"])
    return result


@then("the refund should be £40")
def assert_full_refund(cancel_booking):
    assert cancel_booking["refund_amount"] == 40.00


@then("the booking status should be cancelled")
def assert_cancelled(cancel_booking):
    assert cancel_booking["status"] == "cancelled"
```

---

## Running BDD Tests

```bash
# Run all BDD tests
pytest tests/features/ -v

# Run specific feature
pytest tests/features/booking_cancellation.feature -v

# Run specific scenario
pytest tests/features/booking_cancellation.feature::Scenario:\ Cancel\ within\ 24\ hours -v
```

---

## Living Documentation

### Generate HTML Report

```bash
# Generate behavior-driven documentation
pytest tests/features/ \
  --tb=short \
  --junit-xml=results.xml \
  -v

# Or use pytest-bdd-selenium for HTML report
pytest-bdd report tests/features/ --format html --output docs/bdd-report.html
```

### Example Output

```text
Feature: Booking Cancellation  # tests/features/booking_cancellation.feature

  Scenario: Cancel within 24 hours - full refund  [3 examples]
    ✓ Given a confirmed booking for tomorrow at 10:00
    ✓ And the booking amount is £40
    ✓ When I cancel the booking
    ✓ Then the refund should be £40
    ✓ And the booking status should be cancelled

  Scenario: Cancel within 12-24 hours - 50% refund
    ✓ ...

  Scenario: Cancel less than 12 hours before - no refund
    ✓ ...
```

---

## BDD Anti-patterns

### 1. BDD for Everything

```gherkin
# BAD: BDD for simple internal logic
Feature: Add Numbers
  Scenario: Add 2 + 2
    Given x = 2
    When I add 2
    Then result is 4
```

> **Anti-pattern** — Unit tests are faster and clearer for internal logic.

### 2. Duplicate Tests

```python
# BAD: BDD + unit tests for same thing
@pytest.mark.unit
def test_cancel_booking_full_refund():
    ...

# AND

@then("the refund should be £40")
def same_test():
    ...
```

> **Anti-pattern** — Don't duplicate coverage.

### 3. Complex Step Definitions

```python
# BAD: Giant step with too much logic
@given("I have a complex booking setup")
def setup_everything():
    # 200 lines of setup
    # Hard to maintain
```

> **Anti-pattern** — Steps should be simple and composable.

---

## Summary

| Use BDD | Avoid BDD |
|---------|-----------|
| Cross-team requirements | Internal APIs |
| Customer-facing features | Rapid prototyping |
| Living documentation | Simple unit tests |
| Stakeholder communication | Performance-critical code |

---

## See Also

- [TDD Handbook](tdd-handbook.md)
- [Unit Tests](unit-tests.md)
- [Integration Tests](integration-tests.md)
