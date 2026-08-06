# Responsive Design

> Mobile-first. Tailwind breakpoints. Container queries for component-level responsiveness. Touch targets >= 44x44px.

This document establishes responsive design patterns for the Splashh Sports Platform. We follow a **mobile-first** approach — design and develop for mobile first, then enhance for larger screens.

---

## Mobile-First Approach

> **Rule** — Write base styles for mobile. Use `min-width` media queries to add complexity for larger screens.

```css
/* Mobile first: Base styles apply to all */
.button {
  padding: 0.5rem 1rem;
  font-size: 1rem;
}

/* Enhanced for tablet */
@media (min-width: 768px) {
  .button {
    padding: 0.75rem 1.5rem;
    font-size: 1.125rem;
  }
}

/* Enhanced for desktop */
@media (min-width: 1024px) {
  .button {
    padding: 1rem 2rem;
    font-size: 1.25rem;
  }
}
```

```typescript
// Tailwind: Mobile-first classes
function BookingCard() {
  return (
    <div className="w-full p-4 md:w-1/2 md:p-6 lg:w-1/3 lg:p-8">
      {/* Mobile: full width */}
      {/* Tablet: 2 columns */}
      {/* Desktop: 3 columns */}
    </div>
  );
}
```

---

## Tailwind Breakpoints

| Breakpoint | Width | Usage |
|------------|-------|-------|
| `sm` | 640px | Small phones landscape |
| `md` | 768px | Tablets |
| `lg` | 1024px | Laptops |
| `xl` | 1280px | Desktops |
| `2xl` | 1536px | Large screens |

```typescript
// Using Tailwind breakpoints
function DashboardLayout() {
  return (
    <div className="flex">
      {/* Mobile: hidden, Desktop: visible */}
      <aside className="hidden lg:block lg:w-64">
        <Sidebar />
      </aside>

      {/* Mobile: full width, Desktop: with sidebar */}
      <main className="flex-1 p-4 lg:p-8">
        <Outlet />
      </main>
    </div>
  );
}
```

---

## Container Queries

For component-level responsiveness, use container queries:

```typescript
// tailwind.config.ts - Enable container queries
export default {
  theme: {
    extend: {
      container: {
        center: true,
        padding: '1rem',
        screens: {
          sm: '640px',
          md: '768px',
          lg: '1024px',
          xl: '1280px',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/container-queries'),
  ],
};

// Component with container queries
function BookingCard() {
  return (
    <div className="@container">
      <div className="@lg:flex @lg:items-center @lg:justify-between">
        {/* Mobile: stacked, Desktop: horizontal */}
        <div className="flex-1">
          <h3 className="font-bold @lg:text-lg">Tennis Court A</h3>
          <p className="text-sm text-muted-foreground @lg:text-base">
            10:00 AM - 11:00 AM
          </p>
        </div>
        <div className="mt-2 @lg:mt-0">
          <Button size="sm">Book</Button>
        </div>
      </div>
    </div>
  );
}
```

---

## Touch Targets

> **Rule** — All interactive elements must have a minimum touch target of 44x44 pixels.

```typescript
// Good: Adequate touch targets
<button className="min-h-[44px] min-w-[44px] px-4 py-2">
  Confirm
</button>

// Using Tailwind
<button className="h-11 px-4">  {/* h-11 = 44px */}
  Confirm
</button>

// Anti-pattern: Too small
<button className="h-6 w-6">  {/* 24px - fails touch target requirement */}
  X
</button>
```

### Touch Target Spacing

```typescript
// Mobile navigation with proper spacing
function MobileNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-background border-t">
      <ul className="flex justify-around">
        {navItems.map((item) => (
          <li key={item.href}>
            <a
              href={item.href}
              className="flex flex-col items-center gap-1 p-4 min-h-[44px] min-w-[44px]"
            >
              <item.icon className="h-6 w-6" />
              <span className="text-xs">{item.label}</span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
```

---

## Responsive Component Patterns

### Responsive Table

```typescript
// Mobile: Card view, Desktop: Table view
function BookingsTable({ bookings }) {
  return (
    <div className="overflow-x-auto">
      {/* Desktop table */}
      <table className="hidden md:table w-full">
        <thead>
          <tr>
            <th>Date</th>
            <th>Facility</th>
            <th>Time</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {bookings.map((booking) => (
            <tr key={booking.id}>
              <td>{booking.date}</td>
              <td>{booking.facility}</td>
              <td>{booking.time}</td>
              <td>
                <Badge>{booking.status}</Badge>
              </td>
              <td>
                <Button variant="ghost" size="sm">View</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Mobile cards */}
      <div className="md:hidden space-y-4">
        {bookings.map((booking) => (
          <Card key={booking.id}>
            <CardHeader>
              <CardTitle>{booking.facility}</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Date: {booking.date}</p>
              <p>Time: {booking.time}</p>
              <Badge>{booking.status}</Badge>
            </CardContent>
            <CardFooter>
              <Button className="w-full">View</Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

### Responsive Form

```typescript
// Form layout
function BookingForm() {
  return (
    <form className="space-y-4">
      {/* Mobile: stacked, Desktop: 2 columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <FormField
          name="date"
          label="Date"
          control={form.control}
        />
        <FormField
          name="time"
          label="Time"
          control={form.control}
        />
      </div>

      {/* Full width on mobile */}
      <FormField
        name="notes"
        label="Notes"
        control={form.control}
        className="md:col-span-2"
      />
    </form>
  );
}
```

---

## Test Matrix

> **Guideline** — Test on these form factors.

### Physical Devices

| Category | Device | Viewport |
|----------|--------|----------|
| Small mobile | iPhone SE | 375x667 |
| Mobile | iPhone 14 | 390x844 |
| Large mobile | Pixel 7 | 412x915 |
| Tablet | iPad Mini | 768x1024 |
| Tablet | iPad Pro | 1024x1366 |
| Laptop | MacBook Air | 1440x900 |
| Desktop | Desktop | 1920x1080 |

### Browser DevTools

```bash
# Chrome DevTools Device Mode
# - iPhone SE: 375 x 667
# - iPhone 12 Pro: 390 x 844
# - iPad Mini: 768 x 1024
# - iPad Pro: 1024 x 1366
# - Laptop: 1440 x 900
```

### Orientation Testing

- Portrait (default for mobile)
- Landscape (secondary for tablets)

---

## Responsive Images

```typescript
// Responsive images with srcset
function FacilityImage({ src, alt }) {
  return (
    <img
      src={`${src}?w=400`}
      srcSet={`
        ${src}?w=400 400w,
        ${src}?w=800 800w,
        ${src}?w=1200 1200w
      `}
      sizes="
        (max-width: 640px) 100vw,
        (max-width: 1024px) 50vw,
        33vw
      "
      alt={alt}
      className="w-full h-auto object-cover"
      loading="lazy"
    />
  );
}
```

---

## Responsive Typography

```typescript
// Fluid typography using clamp
function TypographyExample() {
  return (
    <>
      {/* Fluid text: scales between min and max based on viewport */}
      <h1 className="text-3xl md:text-4xl lg:text-5xl">
        Splashh Sports
      </h1>

      {/* Or use Tailwind's responsive utilities */}
      <p className="text-base md:text-lg">
        Book your favorite sports facilities
      </p>
    </>
  );
}
```

---

## Common Responsive Patterns

| Pattern | Mobile | Tablet | Desktop |
|---------|--------|--------|--------|
| Navigation | Hamburger menu | Top nav | Full sidebar |
| Content | Single column | 2 columns | 3-4 columns |
| Tables | Card view | Scrollable | Full table |
| Forms | Single column | 2 columns | 3 columns |
| Cards | Stack | 2 per row | 3-4 per row |
| Buttons | Full width | Auto | Auto |

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| Mobile-first | Faster mobile, progressive enhancement | Requires thinking about breakpoints |
| Container queries | Self-contained responsive components | Browser support (good in modern browsers) |
| Separate mobile/desktop components | Perfect optimization | More code to maintain |

---

## Related Documents

- [Accessibility](accessibility.md) — Mobile accessibility considerations
- [Performance](performance.md) — Responsive image optimization
- [Component Design](component-design.md) — Responsive component patterns
