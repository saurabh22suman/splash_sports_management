# UI Tests

> UI tests verify the frontend experience: component behavior, user flows, visual correctness, and cross-browser compatibility. We use Playwright for component and E2E tests, with visual regression via Percy or Chromatic.

This document covers our UI testing strategy: Playwright setup, component tests for isolated UI logic, E2E tests for critical flows (booking, payment, login), Page Object Model pattern, and visual regression testing. These tests verify what users actually see and interact with.

---

## What is a UI Test

UI tests verify:
- **Component behavior** — Does the booking form validate correctly?
- **User flows** — Can a user complete a booking from start to finish?
- **Visual correctness** — Does the UI look right across breakpoints?
- **Cross-browser** — Does it work in Chrome, Firefox, Safari?

> **Rule** — UI tests are expensive. We prioritize critical user journeys and use unit/integration tests for everything else.

---

## Playwright Setup

### Installation

```bash
pip install playwright pytest-playwright
playwright install chromium firefox webkit
```

### Configuration

```python
# apps/frontend/tests/conftest.py
import pytest
from playwright.sync_api import sync_playwright, Page, Browser


@pytest.fixture(scope="session")
def browser():
    """Launch browser for test session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Create new page for each test."""
    page = browser.new_page()
    yield page
    page.close()


@pytest.fixture
def logged_in_page(page):
    """Page with authenticated session."""
    page.goto("http://localhost:3000/login")
    page.fill('input[name="email"]', "test@example.com")
    page.fill('input[name="password"]', "password123")
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard")
    return page
```

---

## Component Tests

### Testing React Components

```python
# apps/frontend/tests/components/test_booking_form.py
import pytest


class TestBookingForm:
    """Component tests for BookingForm."""

    def test_validates_empty_facility_selection(self, page):
        """Validation: must select a facility."""
        page.goto("http://localhost:3000/bookings/new")

        # Try to submit without selecting facility
        page.click('button[type="submit"]')

        # Assert error message appears
        error = page.locator('[data-testid="facility-error"]')
        assert error.is_visible()
        assert "required" in error.text_content().lower()

    def test_validates_future_time_only(self, page):
        """Validation: cannot book in the past."""
        page.goto("http://localhost:3000/bookings/new")

        # Enter past date
        page.fill('input[name="start_time"]', "2020-01-01T10:00")

        # Try to submit
        page.click('button[type="submit"]')

        # Assert error
        error = page.locator('[data-testid="time-error"]')
        assert error.is_visible()

    def test_shows_available_slots(self, page):
        """UI: displays available time slots."""
        page.goto("http://localhost:3000/bookings/new")

        # Select facility
        page.select_option('select[name="facility_id"]', "court-001")

        # Assert slots appear
        slots = page.locator('[data-testid="time-slot"]')
        assert slots.count() > 0

    def test_calculates_total_price(self, page):
        """UI: price updates when duration changes."""
        page.goto("http://localhost:3000/bookings/new")

        # Select facility with known price
        page.select_option('select[name="facility_id"]', "court-001")
        page.select_option('select[name="duration"]', "60")

        # Assert price displays correctly
        price = page.locator('[data-testid="total-price"]')
        assert "£40.00" in price.text_content()
```

### Storybook Integration

```python
# Test components in Storybook isolation
def test_button_component_in_storybook(self, page):
    """Component: Button renders correctly in Storybook."""
    page.goto("http://localhost:6006/?path=/story/components-button--primary")

    button = page.locator('button[data-testid="btn-primary"]')
    assert button.is_visible()
    assert button.text_content() == "Click me"
    assert button.is_enabled()
```

---

## E2E Tests: Critical Flows

### Login Flow

```python
# apps/frontend/tests/e2e/test_login.py
import pytest


class TestLoginFlow:
    """E2E tests for authentication flow."""

    def test_successful_login_redirects_to_dashboard(self, page):
        """Happy path: valid credentials redirect to dashboard."""
        page.goto("http://localhost:3000/login")

        page.fill('input[name="email"]', "member@example.com")
        page.fill('input[name="password"]', "password123")
        page.click('button[type="submit"]')

        # Assert redirect
        page.wait_for_url("**/dashboard", timeout=5000)

        # Assert user sees dashboard
        assert page.locator('[data-testid="dashboard"]').is_visible()

    def test_invalid_credentials_shows_error(self, page):
        """Error: invalid credentials show error message."""
        page.goto("http://localhost:3000/login")

        page.fill('input[name="email"]', "wrong@example.com")
        page.fill('input[name="password"]', "wrongpassword")
        page.click('button[type="submit"]')

        # Assert error appears
        error = page.locator('[data-testid="login-error"]')
        assert error.is_visible()
        assert "invalid" in error.text_content().lower()

    def test_logout_redirects_to_login(self, page):
        """Flow: logout returns to login page."""
        # ARRANGE: Logged in state
        page.goto("http://localhost:3000/dashboard")

        # ACT: Click logout
        page.click('[data-testid="user-menu"]')
        page.click('[data-testid="logout-button"]')

        # ASSERT
        page.wait_for_url("**/login")
        assert "login" in page.url
```

### Booking Flow

```python
# apps/frontend/tests/e2e/test_booking.py
class TestBookingFlow:
    """E2E tests for complete booking journey."""

    @pytest.fixture(autouse=True)
    def setup(self, logged_in_page):
        """Each test starts logged in."""
        self.page = logged_in_page

    def test_complete_booking_flow(self):
        """Happy path: user completes full booking."""
        # 1. Navigate to booking page
        self.page.goto("http://localhost:3000/bookings/new")

        # 2. Select facility
        self.page.select_option('select[name="facility_id"]', "court-001")
        self.page.wait_for_selector('[data-testid="available-slots"]')

        # 3. Select time slot
        self.page.click('[data-testid="slot-10:00"]')

        # 4. Select duration
        self.page.select_option('select[name="duration"]', "60")

        # 5. Verify price
        price = self.page.locator('[data-testid="total-price"]')
        assert "£40.00" in price.text_content()

        # 6. Submit booking
        self.page.click('button[type="submit"]')

        # 7. Verify success
        success = self.page.locator('[data-testid="booking-success"]')
        assert success.is_visible()
        assert "confirmed" in success.text_content().lower()

    def test_booking_conflict_shows_error(self):
        """Error: slot already taken shows conflict message."""
        # ARRANGE: Create booking in this slot via API
        create_booking_in_db(facility_id="court-001", start_time="14:00")

        # ACT: Try to book same slot
        self.page.goto("http://localhost:3000/bookings/new")
        self.page.select_option('select[name="facility_id"]', "court-001")
        self.page.click('[data-testid="slot-14:00"]')
        self.page.click('button[type="submit"]')

        # ASSERT: Error appears
        error = self.page.locator('[data-testid="booking-error"]')
        assert error.is_visible()
        assert "not available" in error.text_content().lower()

    def test_booking_cancellation(self):
        """Flow: user can cancel a booking."""
        # ARRANGE: Existing booking
        booking_id = create_booking_in_db(customer_id=get_logged_in_customer_id())

        # ACT: Navigate to my bookings
        self.page.goto("http://localhost:3000/bookings")

        # Click cancel on the booking
        self.page.click(f'[data-booking-id="{booking_id}"] [data-testid="cancel-button"]')

        # Confirm cancellation
        self.page.click('[data-testid="confirm-cancel"]')

        # ASSERT: Booking shows as cancelled
        status = self.page.locator(f'[data-booking-id="{booking_id}"] [data-testid="status"]')
        assert "cancelled" in status.text_content().lower()
```

### Payment Flow

```python
# apps/frontend/tests/e2e/test_payment.py
class TestPaymentFlow:
    """E2E tests for payment processing."""

    def test_successful_payment(self, logged_in_page):
        """Happy path: payment succeeds and booking is confirmed."""
        page = logged_in_page

        # ARRANGE: Add item to cart
        page.goto("http://localhost:3000/cart")
        page.click('[data-testid="add-membership-basic"]')

        # ACT: Proceed to payment
        page.click('[data-testid="checkout-button"]')

        # Enter payment details (use Stripe test card)
        page.fill('input[name="card_number"]', "4242424242424242")
        page.fill('input[name="expiry"]', "12/28")
        page.fill('input[name="cvc"]', "123")
        page.fill('input[name="postal"]', "SW1A 1AA")

        page.click('[data-testid="pay-button"]')

        # ASSERT: Payment success
        page.wait_for_selector('[data-testid="payment-success"]', timeout=10000)
        assert "success" in page.locator('[data-testid="payment-success"]').text_content().lower()

    def test_payment_failure_shows_error(self, logged_in_page):
        """Error: declined card shows error message."""
        page = logged_in_page

        # ARRANGE: Go to payment with cart
        page.goto("http://localhost:3000/cart")
        page.click('[data-testid="checkout-button"]')

        # ACT: Use declined card
        page.fill('input[name="card_number"]', "4000000000000002")  # Stripe decline
        page.fill('input[name="expiry"]', "12/28")
        page.fill('input[name="cvc"]', "123")
        page.click('[data-testid="pay-button"]')

        # ASSERT: Error appears
        error = page.locator('[data-testid="payment-error"]')
        assert error.is_visible()
        assert "declined" in error.text_content().lower()
```

---

## Page Object Model

### POM Structure

```python
# apps/frontend/tests/pages/booking_page.py
from playwright.sync_api import Page


class BookingPage:
    """Page Object for booking page."""

    def __init__(self, page: Page):
        self.page = page

    @property
    def facility_select(self):
        return self.page.locator('select[name="facility_id"]')

    @property
    def submit_button(self):
        return self.page.locator('button[type="submit"]')

    @property
    def error_message(self):
        return self.page.locator('[data-testid="error-message"]')

    @property
    def success_message(self):
        return self.page.locator('[data-testid="success-message"]')

    def select_facility(self, facility_id: str):
        self.facility_select.select_option(facility_id)
        self.page.wait_for_timeout(500)  # Wait for slots to load

    def select_slot(self, time: str):
        self.page.click(f'[data-testid="slot-{time}"]')

    def select_duration(self, minutes: int):
        self.page.select_option('select[name="duration"]', str(minutes))

    def submit(self):
        self.submit_button.click()

    def get_total_price(self) -> str:
        return self.page.locator('[data-testid="total-price"]').text_content()

    def get_error(self) -> str:
        return self.error_message.text_content()
```

### Using POM in Tests

```python
from tests.pages.booking_page import BookingPage


def test_complete_booking_using_pom(logged_in_page):
    """E2E: booking flow using Page Object Model."""
    page = logged_in_page
    booking_page = BookingPage(page)

    page.goto("http://localhost:3000/bookings/new")

    booking_page.select_facility("court-001")
    booking_page.select_slot("10:00")
    booking_page.select_duration(60)

    assert "£40.00" in booking_page.get_total_price()

    booking_page.submit()

    assert booking_page.success_message.is_visible()
```

---

## Visual Regression Testing

### Percy Integration

```python
# apps/frontend/tests/visual/test_components.py
import pytest
from percy import percy_snapshot


class TestVisualRegression:
    """Visual regression tests using Percy."""

    def test_booking_form_visual(self, page):
        """Visual: booking form matches baseline."""
        page.goto("http://localhost:3000/bookings/new")
        percy_snapshot(page, "booking-form")

    def test_dashboard_visual(self, logged_in_page):
        """Visual: dashboard matches baseline."""
        percy_snapshot(logged_in_page, "dashboard")

    def test_login_page_visual(self, page):
        """Visual: login page across viewports."""
        page.goto("http://localhost:3000/login")
        percy_snapshot(page, "login-page-desktop")

        # Test tablet
        page.set_viewport_size({"width": 768, "height": 1024})
        percy_snapshot(page, "login-page-tablet")

        # Test mobile
        page.set_viewport_size({"width": 375, "height": 667})
        percy_snapshot(page, "login-page-mobile")
```

### Chromatic Alternative

```yaml
# .github/workflows/chromatic.yml
- name: Chromatic
  uses: chromaui/action@v1
  with:
    projectToken: ${{ secrets.CHROMATIC_PROJECT_TOKEN }}
    buildScriptName: "build-storybook"
    autoAcceptChanges: "main"
```

---

## Cross-Browser Testing

```python
# conftest.py - run tests across browsers
import pytest


@pytest.fixture(params=["chromium", "firefox", "webkit"])
def browser_context(browser_type_launcher, request):
    """Run tests across all browsers."""
    browser = browser_type_launcher.launch()
    context = browser.new_context()
    yield context
    context.close()
    browser.close()
```

---

## Test Execution

### Running UI Tests

```bash
# Run all E2E tests
pytest apps/frontend/tests/e2e/ -v

# Run specific test
pytest apps/frontend/tests/e2e/test_booking.py::TestBookingFlow::test_complete_booking_flow -v

# Run in headed mode (debug)
pytest apps/frontend/tests/e2e/ --headed

# Run with UI (interact)
pytest apps/frontend/tests/e2e/ --ui

# Run visual tests
percy exec -- pytest apps/frontend/tests/visual/
```

### CI Configuration

```yaml
# .github/workflows/ui-tests.yml
- name: UI Tests
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: 20
    - run: npm ci
    - run: npm run build
    - name: Install Playwright Browsers
      run: npx playwright install --with-deps
    - name: Run E2E Tests
      run: pytest apps/frontend/tests/e2e/ -v
    - name: Run Visual Tests
      run: percy exec -- pytest apps/frontend/tests/visual/
```

---

## UI Test Checklist

- [ ] Critical user flows covered (login, booking, payment)
- [ ] Page Object Model used for maintainability
- [ ] Visual regression tests for key pages
- [ ] Cross-browser testing (Chrome, Firefox, Safari)
- [ ] Mobile viewport testing
- [ ] Error states tested
- [ ] Loading states tested
- [ ] Accessibility basics (can navigate with keyboard)

---

## Anti-patterns

### 1. Too Many E2E Tests

```python
# BAD: Testing everything in E2E
def test_calculator_addition(self):
    # This belongs in unit tests!
    page.goto("/calculator")
    page.fill("input:first", "1")
    page.fill("input:last", "2")
    page.click("#add")
    assert page.text_content("#result") == "3"
```

> **Anti-pattern** — E2E tests are slow and brittle. Unit tests catch calculation errors faster.

### 2. No POM

```python
# BAD: Scattered selectors
def test_booking(self, page):
    page.goto("/bookings/new")
    page.click('select[name="facility_id"]')  # Repeated everywhere
    page.click('[data-testid="slot-10:00"]')
    # If selector changes, many tests break
```

> **Anti-pattern** — No POM leads to brittle tests that break on every UI change.

### 3. Skipping Visual Tests

> **Anti-pattern** — "Unit tests cover it." Visual bugs still reach production without visual regression.

---

## Summary

| Aspect | Rule |
|--------|------|
| Tool | Playwright |
| Scope | Critical user journeys only |
| Pattern | Page Object Model |
| Visual | Percy or Chromatic |
| Browsers | Chrome, Firefox, Safari |
| Viewports | Desktop, tablet, mobile |
| Speed | <5 min for full suite |

See also: [Unit Tests](unit-tests.md), [Integration Tests](integration-tests.md), [API Tests](api-tests.md), [Testing Pyramid](testing-pyramid.md), [Testing Diamond](testing-diamond.md).
