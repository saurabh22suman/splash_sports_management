# Lazy Loading

> Route-level via React.lazy + Suspense. Component-level for heavy widgets. Preload on hover.

This document establishes lazy loading patterns for the Splashh Sports Platform. We use code splitting to reduce initial bundle size and improve time-to-interactive.

---

## Route-Level Lazy Loading

```typescript
// routes/index.tsx
import { Suspense, lazy } from 'react';
import { createBrowserRouter } from 'react-router-dom';
import { Skeleton } from '@/components/ui/Skeleton';

// Lazy load pages
const DashboardPage = lazy(() => import('@/pages/DashboardPage'));
const BookingsPage = lazy(() => import('@/pages/BookingsPage'));
const BookingDetailPage = lazy(() => import('@/pages/BookingDetailPage'));
const FacilitiesPage = lazy(() => import('@/pages/FacilitiesPage'));
const ProfilePage = lazy(() => import('@/pages/ProfilePage'));
const AdminPage = lazy(() => import('@/pages/AdminPage'));

// Loading fallback component
function PageLoader() {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-8 w-1/3" />
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-8 w-1/2" />
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <Suspense fallback={<PageLoader />}>
        <DashboardPage />
      </Suspense>
    ),
  },
  {
    path: '/bookings',
    element: (
      <Suspense fallback={<PageLoader />}>
        <BookingsPage />
      </Suspense>
    ),
    children: [
      {
        path: ':id',
        element: (
          <Suspense fallback={<PageLoader />}>
            <BookingDetailPage />
          </Suspense>
        ),
      },
    ],
  },
  {
    path: '/facilities',
    element: (
      <Suspense fallback={<PageLoader />}>
        <FacilitiesPage />
      </Suspense>
    ),
  },
  {
    path: '/profile',
    element: (
      <Suspense fallback={<PageLoader />}>
        <ProfilePage />
      </Suspense>
    ),
  },
  {
    path: '/admin',
    element: (
      <Suspense fallback={<PageLoader />}>
        <AdminPage />
      </Suspense>
    ),
  },
]);
```

---

## Component-Level Lazy Loading

For heavy components that aren't needed immediately:

```typescript
// Lazy load heavy components
const BookingCalendar = lazy(() => import('@/features/booking/components/BookingCalendar'));
const RevenueChart = lazy(() => import('@/features/analytics/components/RevenueChart'));
const MemberImport = lazy(() => import('@/features/admin/components/MemberImport'));
const PhotoUploader = lazy(() => import('@/features/photos/components/Uploader'));

// Usage
function BookingPage() {
  const [showCalendar, setShowCalendar] = useState(false);

  return (
    <div>
      <Button onClick={() => setShowCalendar(true)}>
        Open Calendar
      </Button>

      {showCalendar && (
        <Suspense fallback={<CalendarSkeleton />}>
          <BookingCalendar />
        </Suspense>
      )}
    </div>
  );
}

function AnalyticsDashboard() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Suspense fallback={<ChartSkeleton />}>
        <RevenueChart />
      </Suspense>
      <Suspense fallback={<ChartSkeleton />}>
        <MemberGrowthChart />
      </Suspense>
    </div>
  );
}
```

---

## Preload on Hover

Preload routes when user hovers over navigation links:

```typescript
// components/NavLink.tsx
import { Link, useNavigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';

function NavLink({ to, children }: { to: string; children: ReactNode }) {
  const navigate = useNavigate();

  const handleMouseEnter = () => {
    // Preload the route's chunk
    const preload = lazy(() => import(/* @vite-ignore */ to));
  };

  return (
    <Link
      to={to}
      onMouseEnter={handleMouseEnter}
      onMouseDown={() => navigate(to)}
    >
      {children}
    </Link>
  );
}
```

---

## Preloading in Layout

```typescript
// App.tsx - Preload common routes on app load
function App() {
  const router = useRouter();

  useEffect(() => {
    // Preload common routes after initial render
    const timer = setTimeout(() => {
      // Preload bookings page
      router.preload('/bookings');
      router.preload('/facilities');
    }, 2000);

    return () => clearTimeout(timer);
  }, [router]);

  return <RouterProvider router={router} />;
}
```

---

## Lazy Loading Pattern for Features

```typescript
// features/booking/index.ts
import { lazy, Suspense } from 'react';

// Export lazy-loaded component
export const LazyBookingWidget = lazy(() => import('./components/BookingWidget'));

// Export loading state
export function BookingWidgetSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-8 w-1/3 bg-muted rounded" />
      <div className="h-64 bg-muted rounded" />
      <div className="h-10 w-full bg-muted rounded" />
    </div>
  );
}

// Usage in parent
function BookingSection() {
  return (
    <Suspense fallback={<BookingWidgetSkeleton />}>
      <LazyBookingWidget />
    </Suspense>
  );
}
```

---

## Dynamic Imports

For non-component lazy loading:

```typescript
// Dynamic import for utilities
async function loadExportUtils() {
  const { exportToCSV, exportToPDF } = await import('@/lib/export');
  return { exportToCSV, exportToPDF };
}

// Usage in handler
async function handleExport(format: 'csv' | 'pdf') {
  const { exportToCSV, exportToPDF } = await loadExportUtils();

  if (format === 'csv') {
    exportToCSV(data);
  } else {
    exportToPDF(data);
  }
}

// Dynamic import for heavy libraries
async function handleImageUpload(file: File) {
  // Only load image processing library when needed
  const { processImage } = await import('image-processor');
  const result = await processImage(file);
  // ...
}
```

---

## Intersection Observer for Advanced Lazy Loading

```typescript
// Lazy load when element enters viewport
function LazyOnViewport({
  children,
  threshold = 0.1,
}: {
  children: ReactNode;
  threshold?: number;
}) {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { threshold }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [threshold]);

  return (
    <div ref={ref}>
      {isVisible ? children : <Placeholder />}
    </div>
  );
}

// Usage
function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>
      <LazyOnViewport>
        <HeavyAnalyticsWidget />
      </LazyOnViewport>
    </div>
  );
}
```

---

## Trade-offs

| Approach | What we gain | What we give up |
|----------|--------------|-----------------|
| Route-level splitting | Faster initial load | Slight delay on navigation |
| Component-level splitting | Smaller bundles | Complexity |
| Preload on hover | Instant navigation | Network requests |
| Intersection observer | On-demand loading | JS overhead |

---

## Related Documents

- [Code Splitting](code-splitting.md) — Vite chunk configuration
- [Performance](performance.md) — Bundle budgets
- [React.lazy](https://react.dev/reference/react/lazy) — Full reference
