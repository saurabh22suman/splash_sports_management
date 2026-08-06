# Folder Structure

> The source layout for admin-pwa and customer-pwa. Feature-based vertical slicing with clear boundaries.

This document defines the folder structure for both PWA applications. The structure follows **feature-based vertical slicing** — each feature is a self-contained unit containing everything it needs. This maximizes colocation, minimizes cross-feature imports, and enables easier code splitting.

---

## Root Layout

```
apps/
  admin-pwa/
    src/
      features/          # Feature modules (vertical slices)
      components/        # Shared, generic components
      hooks/             # Shared custom hooks
      lib/               # Utilities, SDKs, configurations
      routes/            # Route definitions and guards
      pages/             # Page-level components
      styles/            # Global styles
      types/             # Global TypeScript types
      App.tsx
      main.tsx
    index.html
    vite.config.ts
    tsconfig.json
    public/
      manifest.json
      sw.js
  customer-pwa/
    src/
      features/
      components/
      hooks/
      lib/
      routes/
      pages/
      styles/
      types/
      App.tsx
      main.tsx
    index.html
    vite.config.ts
```

---

## Features Directory

Each feature is a **vertical slice** containing:

```
features/
  booking/
    components/          # Feature-specific components
      BookingCard.tsx
      BookingCalendar.tsx
      BookingForm.tsx
    hooks/               # Feature-specific hooks
      useBooking.ts
      useCreateBooking.ts
    types/               # Feature-specific types
      booking.types.ts
    schemas/              # Zod schemas
      booking.schema.ts
    api/                 # API client wrappers
      booking.api.ts
    index.ts             # Public exports
    routes.tsx           # Feature routes (optional)
  membership/
    components/
    hooks/
    types/
    schemas/
    api/
    index.ts
  facility/
  auth/
  dashboard/
  payments/
  profile/
  admin/                 # Admin-only features (customer-pwa)
```

> **Rule** — Features must not import from each other. If feature A needs something from feature B, either move it to a shared location or propose moving it to `components/` if truly generic.

> **Why** — Vertical slicing reduces the blast radius of changes. When we modify booking logic, we modify one folder, not scattered files across the codebase.

---

## Components Directory

Generic, reusable components that any feature may use:

```
components/
  ui/                     # shadcn/ui components
    Button/
    Input/
    Dialog/
    Card/
    ...
  layout/
    AppShell.tsx
    Sidebar.tsx
    Header.tsx
    Footer.tsx
  data/
    DataTable.tsx
    DataGrid.tsx
  forms/
    FormField.tsx
    DatePicker.tsx
    Select.tsx
  feedback/
    Toast.tsx
    Alert.tsx
    Spinner.tsx
  accessibility/
    SkipLink.tsx
    LiveRegion.tsx
```

> **Guideline** — Before creating a new component in `components/`, verify it cannot be composed from existing shadcn/ui primitives. Custom components should be truly reusable, not one-off implementations.

---

## Hooks Directory

Shared custom hooks:

```
hooks/
  useAuth.ts
  useTenant.ts
  useTheme.ts
  useLocalStorage.ts
  useDebounce.ts
  useMediaQuery.ts
  useOffline.ts
  usePWAInstall.ts
```

> **Rule** — Hooks must follow React's Rules of Hooks. No conditional calls, no use inside loops or early returns before all hooks run.

---

## Lib Directory

Utilities and SDK configurations:

```
lib/
  api/                    # Axios/fetch client, interceptors
    client.ts
    interceptors.ts
  auth/                   # Auth utilities
    token.ts
    permissions.ts
  utils/
    cn.ts                 # classnames helper
    formatters.ts
    validators.ts
  constants.ts
  config.ts               # Runtime config
```

---

## Routes Directory

Route definitions with guards:

```
routes/
  index.tsx               # Route tree
  protected.routes.tsx    # Guarded route wrapper
  public.routes.tsx
  admin.routes.tsx
```

---

## Pages Directory

Page-level components (thin wrappers around features):

```
pages/
  HomePage.tsx
  LoginPage.tsx
  NotFoundPage.tsx
  AdminPage.tsx
```

> **Guideline** — Pages should be minimal. If a page grows beyond 30 lines, extract to a feature component.

---

## Styles Directory

Global styles and Tailwind directives:

```
styles/
  globals.css
  themes.css              # CSS custom properties
  utilities.css           # Custom utilities
```

---

## Types Directory

Global TypeScript types:

```
types/
  global.d.ts
  env.d.ts
  react-query.d.ts
```

---

## Tests Co-location

Tests live alongside the code they test:

```
features/
  booking/
    components/
      BookingCard.tsx
      BookingCard.test.tsx
    hooks/
      useBooking.test.ts
    index.ts
```

> **Rule** — Test files use `.test.tsx` for React component tests, `.test.ts` for utility/hook tests.

---

## Import Conventions

```typescript
// Feature internal import
import { useCreateBooking } from '@/features/booking';

// Shared component import
import { Button } from '@/components/ui/Button';

// Shared hook import
import { useAuth } from '@/hooks/useAuth';

// Utility import
import { cn } from '@/lib/utils';
```

> **Rule** — Use path aliases (`@/`) defined in `tsconfig.json`. No relative imports beyond one level (`../`).

---

## Code Organization Rules

| Rule | Rationale |
|------|-----------|
| Features own their data | Each feature manages its own API, types, schemas, and state |
| No cross-feature imports | Prevents coupling, enables independent code splitting |
| Shared code in `components/`, `hooks/`, `lib/` | Single source of truth for reusable code |
| Tests co-located | Easier to find tests, clearer ownership |
| Path aliases everywhere | Refactoring is safer; no broken relative paths |
| Pages are thin wrappers | Pages are routing glue; features hold the logic |

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| Feature-based slicing | Clear ownership, easy code splitting, self-contained features | Possible duplication if not careful |
| Co-located tests | Test discovery, single responsibility | Larger file count per feature |
| Path aliases | Cleaner imports, easier refactoring | Slight IDE setup complexity |

---

## Related Documents

- [Component Design](component-design.md) — Component composition patterns
- [Hooks](hooks.md) — Custom hook conventions
- [Code Splitting](code-splitting.md) — Vite chunk configuration
- [Lazy Loading](lazy-loading.md) — Route and component lazy loading
