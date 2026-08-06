# Accessibility

> WCAG 2.2 AA compliance. Semantic HTML first. ARIA only when needed. Keyboard navigation. Focus management.

This document establishes accessibility requirements for the Splashh Sports Platform. We target **WCAG 2.2 Level AA** compliance. Accessibility is not a feature — it is a fundamental requirement for a public-facing application.

---

## Core Principles

1. **Semantic HTML first** — Use proper HTML elements before reaching for ARIA
2. **Keyboard accessible** — All functionality available via keyboard
3. **Screen reader compatible** — Proper labels, live regions, and structure
4. **Color contrast** — Minimum 4.5:1 for normal text, 3:1 for large text
5. **Focus visible** — Clear focus indicators on all interactive elements
6. **No reliance on color alone** — Convey information through multiple senses

> **Rule** — Every new component must pass accessibility review before merge.

---

## Semantic HTML

```typescript
// Good: Proper semantic elements
<header>
  <nav aria-label="Main navigation">
    <ul>
      <li><a href="/">Home</a></li>
      <li><a href="/bookings">Bookings</a></li>
    </ul>
  </nav>
</header>

<main>
  <h1>My Bookings</h1>
  <article>
    <h2>Tennis Court A</h2>
    <p>Date: January 15, 2024</p>
    <p>Time: 10:00 AM</p>
  </article>
</main>

<footer>
  <p>&copy; 2024 Splashh Sports</p>
</footer>

// Anti-pattern: Non-semantic structure
<div>
  <div class="header">
    <div class="nav">
      <div>Home</div>
      <div>Bookings</div>
    </div>
  </div>
  <div class="content">
    <div class="title">My Bookings</div>
    <div class="card">
      <div class="card-title">Tennis Court A</div>
    </div>
  </div>
</div>
```

---

## Headings Hierarchy

```typescript
// Good: Proper heading hierarchy
function BookingsPage() {
  return (
    <main>
      <h1>My Bookings</h1>           {/* Page title */}
      <section aria-labelledby="upcoming-heading">
        <h2 id="upcoming-heading">Upcoming</h2>  {/* Section */}
        <BookingList />
      </section>
      <section aria-labelledby="past-heading">
        <h2 id="past-heading">Past</h2>
        <PastBookingList />
      </section>
    </main>
  );
}

// Anti-pattern: Skipped levels
function BadPage() {
  return (
    <main>
      <h1>Page Title</h1>
      <h3>This is wrong (h2 is missing)</h3>
    </main>
  );
}
```

---

## Form Labels

```typescript
// Good: Explicit labels
<form>
  <label htmlFor="email">Email address</label>
  <input id="email" type="email" name="email" />

  <label htmlFor="password">Password</label>
  <input id="password" type="password" name="password" />
</form>

// Good: Implicit labels
<label>
  Email address
  <input type="email" name="email" />
</label>

// Anti-pattern: No label
<input type="email" placeholder="Enter email" />

// Anti-pattern: Placeholder as label
<label className="sr-only">Search</label>
<input type="search" placeholder="Search bookings..." />
```

---

## ARIA: When Needed

> **Rule** — Use ARIA only when semantic HTML cannot express the semantics. ARIA is a repair mechanism, not a primary tool.

### When to Use ARIA

| Scenario | Solution |
|----------|----------|
| Custom interactive component | `role`, `aria-*` attributes |
| Live region for dynamic updates | `aria-live` |
| Complex widget state | `aria-expanded`, `aria-selected`, `aria-checked` |
| Hidden content from screen readers | `aria-hidden` |
| Required fields | `aria-required` |
| Invalid fields | `aria-invalid`, `aria-errormessage` |

### Example: Custom Toggle

```typescript
// ToggleButton.tsx
interface ToggleButtonProps {
  isOn: boolean;
  onToggle: () => void;
  label: string;
}

export function ToggleButton({ isOn, onToggle, label }: ToggleButtonProps) {
  return (
    <button
      role="switch"
      aria-checked={isOn}
      aria-label={label}
      onClick={onToggle}
      className={cn(
        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
        isOn ? 'bg-primary' : 'bg-gray-200'
      )}
    >
      <span
        className={cn(
          'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
          isOn ? 'translate-x-6' : 'translate-x-1'
        )}
      />
    </button>
  );
}
```

---

## Keyboard Navigation

### Focus Order

```typescript
// Ensure logical tab order
<>
  {/* Good: Logical order */}
  <a href="/">Home</a>
  <a href="/about">About</a>
  <button>Menu</button>

  {/* Anti-pattern: Random order breaks keyboard flow */}
  <button>Menu</button>
  <a href="/">Home</a>
  <a href="/about">About</a>
```

### Focus Management

```typescript
// Modal focus management
function Modal({ isOpen, onClose, title, children }) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      // Focus the modal when opened
      modalRef.current?.focus();
      // Trap focus inside modal
      trapFocus(modalRef.current);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      ref={modalRef}
      tabIndex={-1}
    >
      <h2 id="modal-title">{title}</h2>
      <button aria-label="Close" onClick={onClose}>
        <XIcon />
      </button>
      {children}
    </div>
  );
}

// Focus return after navigation
function BookingPage() {
  const navigate = useNavigate();
  const titleRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    // Return focus to page title after navigation
    titleRef.current?.focus();
  }, []);

  return <h1 ref={titleRef} tabIndex={-1}>Booking Details</h1>;
}
```

---

## Skip Links

```typescript
// App.tsx - Skip link for keyboard users
export function App() {
  return (
    <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground">
      Skip to main content
    </a>

    <Header />

    <main id="main-content">
      <Outlet />
    </main>

    <Footer />
  </a>
);
```

---

## Live Regions

For dynamic content updates:

```typescript
// Toast notifications
function ToastContainer() {
  return (
    <div aria-live="polite" aria-atomic="true" className="fixed top-4 right-4">
      {toasts.map((toast) => (
        <div key={toast.id} role="alert">
          {toast.message}
        </div>
      ))}
    </div>
  );
}

// Status updates
function BookingStatus({ status }) {
  return (
    <div aria-live="polite" className="sr-only">
      Booking status: {status}
    </div>
  );
}
```

> **Pitfall** — Avoid `aria-live="assertive"` unless the update is critical and time-sensitive (e.g., form validation errors).

---

## Color Contrast

```css
/* tailwind.config.ts - Ensuring sufficient contrast */
export default {
  theme: {
    extend: {
      colors: {
        /* Primary: WCAG AA compliant */
        primary: {
          DEFAULT: '#0066CC',      /* 7.3:1 on white - passes AAA */
          foreground: '#FFFFFF',
        },
        /* Text colors */
        foreground: {
          primary: '#1A1A1A',     /* 16.3:1 - passes AAA */
          secondary: '#4A4A4A',   /* 7.5:1 - passes AA */
          muted: '#6B6B6B',       /* 4.6:1 - passes AA */
        },
      },
    },
  },
};

/* Anti-pattern: Low contrast colors */
.colors-that-fail {
  color: #999;       /* 2.9:1 - FAILS */
  background: #eee; /* 1.2:1 - FAILS */
}
```

---

## Focus Indicators

```css
/* Global focus styles */
*:focus-visible {
  outline: 2px solid oklch(0.6 0.2 250);
  outline-offset: 2px;
}

/* Remove default focus for mouse users */
*:focus:not(:focus-visible) {
  outline: none;
}
```

---

## Screen Reader Testing

> **Guideline** — Test with actual screen readers regularly.

### Testing Checklist

| Tool | Platform | How to test |
|------|----------|-------------|
| NVDA | Windows | Navigate with Tab, Arrow keys, Screen reader shortcuts |
| JAWS | Windows | Use virtual cursor to read page |
| VoiceOver | macOS/iOS | Rotor navigation, VoiceOver rotor |
| Orca | Linux | Review mode |

### Testing Commands

```bash
# VoiceOver (macOS)
Cmd + F5          # Toggle VoiceOver
Ctrl + Option + Arrows  # Navigate
Ctrl + Option + U      # Open rotor

# NVDA (Windows)
NVDA + Arrow       # Read
NVDA + Tab         # Move to next form field
```

---

## Accessibility Testing in CI

```typescript
// .eslintrc.js - eslint-plugin-jsx-a11y
module.exports = {
  plugins: ['jsx-a11y'],
  rules: {
    'jsx-a11y/alt-text': 'error',
    'jsx-a1/anchor-valid': 'error',
    'jsx-a11y/label-has-associated-control': 'error',
    'jsx-a11y/no-autofocus': 'warn',
    'jsx-a11y/role-has-required-aria-props': 'error',
  },
};

// playwright.config.ts - Automated a11y testing
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('page has no accessibility violations', async ({ page }) => {
  const accessibilityScanResults = await new AxeBuilder({ page }).analyze();

  expect(accessibilityScanResults.violations).toEqual([]);
});
```

---

## Common Accessibility Issues

| Issue | Solution |
|-------|----------|
| Missing form labels | Add `<label>` or `aria-label` |
| Images without alt text | Add meaningful alt or `alt=""` for decorative |
| Low color contrast | Use WCAG-compliant colors |
| Missing focus indicators | Add visible focus styles |
| No skip link | Add skip to main content link |
| Missing page regions | Use `<header>`, `<main>`, `<footer>` |
| Dynamic content not announced | Use `aria-live` regions |
| Invalid ARIA | Validate ARIA usage |

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| WCAG 2.2 AA | Legal compliance, wider audience, better SEO | Slightly more development time |
| Semantic HTML | Built-in accessibility, SEO | Less styling flexibility |
| ARIA repair | Accessible custom widgets | Learning curve |

---

## Related Documents

- [Component Design](component-design.md) — Accessible components
- [Responsive Design](responsive-design.md) — Mobile accessibility
- [WCAG 2.2 Guidelines](https://www.w3.org/WAI/WCAG22/quickref/) — Full reference
