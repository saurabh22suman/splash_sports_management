# Performance

> Core Web Vitals targets. Bundle size budgets. Image optimization. Font loading.

This document establishes performance targets and optimization strategies for the Splashh Sports Platform. Performance is a feature — slow applications lose users.

---

## Core Web Vitals Targets

| Metric | Target | What it measures |
|--------|--------|------------------|
| LCP | < 2.5s | Largest contentful paint |
| INP | < 200ms | Interaction to next paint |
| CLS | < 0.1 | Cumulative layout shift |

### Measuring Web Vitals

```typescript
// lib/analytics/web-vitals.ts
import { onCLS, onINP, onLCP } from 'web-vitals';

function reportWebVitals({ name, value, id }: { name: string; value: number; id: string }) {
  // Send to analytics
  window.gtag?.('event', name, {
    event_category: 'Web Vitals',
    event_label: id,
    value: Math.round(name === 'CLS' ? value * 1000 : value),
  });
}

export function initWebVitals() {
  onCLS(reportWebVitals);
  onINP(reportWebVitals);
  onLCP(reportWebVitals);
}
```

---

## Bundle Size Budgets

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        // Manual chunks for vendor splitting
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-query': ['@tanstack/react-query', '@tanstack/react-query-devtools'],
          'vendor-ui': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
        },
      },
    },
    // Budget warnings
    chunkSizeWarningLimit: 500, // KB
  },
});
```

### Per-Route Budgets

| Route | Budget |
|-------|--------|
| Landing | 100KB |
| Dashboard | 200KB |
| Booking | 150KB |
| Admin | 300KB |

```json
// package.json
{
  "scripts": {
    "analyze": "vite-bundle-visualizer"
  }
}
```

---

## Image Optimization

### Using srcset and Modern Formats

```typescript
function FacilityImage({ src, alt }: { src: string; alt: string }) {
  return (
    <picture>
      <source
        srcSet={`${src}?fmt=avif&w=400 400w, ${src}?fmt=avif&w=800 800w`}
        type="image/avif"
      />
      <source
        srcSet={`${src}?fmt=webp&w=400 400w, ${src}?fmt=webp&w=800 800w`}
        type="image/webp"
      />
      <img
        src={`${src}?w=400`}
        alt={alt}
        loading="lazy"
        decoding="async"
        className="w-full h-48 object-cover"
      />
    </picture>
  );
}
```

### Image Component with Fallback

```typescript
function OptimizedImage({
  src,
  alt,
  width,
  height,
}: {
  src: string;
  alt: string;
  width?: number;
  height?: number;
}) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isError, setIsError] = useState(false);

  // Generate responsive srcSet
  const srcSet = useMemo(() => {
    const widths = [320, 640, 960, 1280];
    return widths
      .map((w) => `${cdnUrl}/resize/${w}/${src} ${w}w`)
      .join(', ');
  }, [src]);

  if (isError) {
    return (
      <div className="bg-muted flex items-center justify-center" style={{ aspectRatio: width && height ? `${width}/${height}` : undefined }}>
        <ImageIcon className="h-8 w-8 text-muted-foreground" />
      </div>
    );
  }

  return (
    <img
      src={`${cdnUrl}/resize/640/${src}`}
      srcSet={srcSet}
      sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
      alt={alt}
      width={width}
      height={height}
      loading="lazy"
      decoding="async"
      onLoad={() => setIsLoaded(true)}
      onError={() => setIsError(true)}
      className={cn(
        'transition-opacity duration-300',
        isLoaded ? 'opacity-100' : 'opacity-0'
      )}
    />
  );
}
```

---

## Font Loading

```css
/* styles/globals.css */

/* Font-display swap - text visible while font loads */
@font-face {
  font-family: 'Inter';
  src: url('/fonts/inter-var.woff2') format('woff2');
  font-display: swap;
  font-weight: 100 900;
}

/* Preload critical fonts */
<link
  rel="preload"
  href="/fonts/inter-var.woff2"
  as="font"
  type="font/woff2"
  crossorigin
/>
```

### Font Loading Strategy

```typescript
// Prevent FOIT (Flash of Invisible Text)
function FontLoader() {
  useEffect(() => {
    // Check if fonts are loaded
    if (document.fonts?.ready) {
      document.fonts.ready.then(() => {
        document.documentElement.classList.add('fonts-loaded');
      });
    }
  }, []);

  return null;
}
```

---

## Performance Budgets in CI

```yaml
# .github/workflows/performance.yml
name: Performance

on: [push, pull_request]

jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build
        run: npm run build

      - name: Serve
        run: npm run preview &

      - name: Lighthouse CI
        uses: treosh/lighthouse-ci-action@v10
        with:
          urls: |
            http://localhost:4173/
          budgetPath: ./lighthouse-budget.json
          uploadArtifacts: true
```

```json
// lighthouse-budget.json
{
  "ci": {
    "collect": {
      "staticDistDir": "./dist"
    },
    "assert": {
      "assertions": {
        "categories:performance": ["error", { "minScore": 0.9 }],
        "categories:accessibility": ["error", { "minScore": 0.9 }],
        "first-contentful-paint": ["warn", { "maxNumericValue": 1500 }],
        "largest-contentful-paint": ["error", { "maxNumericValue": 2500 }],
        "cumulative-layout-shift": ["error", { "maxNumericValue": 0.1 }],
        "interactive": ["error", { "maxNumericValue": 3000 }],
        "total-byte-weight": ["error", { "maxNumericValue": 500000 }]
      }
    }
  }
}
```

---

## Runtime Performance

### React Profiler

```typescript
// In development, wrap expensive components
import { Profiler } from 'react';

function onRender(id, phase, actualDuration) {
  if (actualDuration > 100) {
    console.warn(`Slow render: ${id} took ${actualDuration}ms in ${phase}`);
  }
}

<Profiler id="BookingPage" onRender={onRender}>
  <BookingPage />
</Profiler>
```

### useMemo and useCallback

```typescript
// Only use memoization when necessary
function BookingList({ bookings, filter }) {
  // Memoize expensive computations
  const filteredBookings = useMemo(
    () => bookings.filter((b) => matchesFilter(b, filter)),
    [bookings, filter]
  );

  // Memoize callback to prevent child re-renders
  const handleBookingClick = useCallback((id: string) => {
    navigate(`/bookings/${id}`);
  }, [navigate]);

  return (
    <ul>
      {filteredBookings.map((booking) => (
        <BookingItem
          key={booking.id}
          booking={booking}
          onClick={handleBookingClick}
        />
      ))}
    </ul>
  );
}
```

---

## Performance Monitoring

```typescript
// lib/analytics/performance.ts
export function reportPerformance() {
  // Navigation timing
  const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;

  if (navigation) {
    console.log({
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
      loadComplete: navigation.loadEventEnd - navigation.fetchStart,
      ttfb: navigation.responseStart - navigation.requestStart,
    });
  }

  // Long tasks
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.duration > 50) {
        console.warn('Long task detected:', entry.duration);
      }
    }
  });

  observer.observe({ type: 'longtask', buffered: true });
}
```

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| AVIF images | Smaller files, better quality | Browser support |
| Font swap | Visible text immediately | Potential layout shift |
| Lazy loading | Faster initial load | Delay when scrolling |
| Code splitting | Smaller initial bundle | Additional network requests |

---

## Related Documents

- [Lazy Loading](lazy-loading.md) — Route and component lazy loading
- [Code Splitting](code-splitting.md) — Vite chunk configuration
- [Core Web Vitals](https://web.dev/vitals/) — Full reference
