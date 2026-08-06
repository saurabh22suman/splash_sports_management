# Code Splitting

> Vite manual chunks. Vendor splitting. Per-route chunks. Dynamic imports for admin-only features.

This document establishes code splitting strategies for the Splashh Sports Platform. Code splitting reduces initial bundle size by separating code into smaller chunks that load on demand.

---

## Vite Chunk Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        // Manual chunks for vendor splitting
        manualChunks: {
          // React core
          'vendor-react': [
            'react',
            'react-dom',
            'react-router-dom',
            'react/jsx-runtime',
          ],

          // TanStack Query
          'vendor-query': [
            '@tanstack/react-query',
            '@tanstack/react-query-devtools',
          ],

          // Radix UI (shadcn/ui base)
          'vendor-radix': [
            '@radix-ui/react-dialog',
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-select',
            '@radix-ui/react-tabs',
            '@radix-ui/react-toast',
            '@radix-ui/react-popover',
            '@radix-ui/react-accordion',
            '@radix-ui/react-alert-dialog',
            '@radix-ui/react-avatar',
            '@radix-ui/react-checkbox',
            '@radix-ui/react-collapsible',
            '@radix-ui/react-context-menu',
            '@radix-ui/react-label',
            '@radix-ui/react-menu',
            '@radix-ui/react-navigation-menu',
            '@radix-ui/react-progress',
            '@radix-ui/react-radio-group',
            '@radix-ui/react-scroll-area',
            '@radix-ui/react-separator',
            '@radix-ui/react-slider',
            '@radix-ui/react-switch',
            '@radix-ui/react-tabs',
            '@radix-ui/react-tooltip',
          ],

          // Charting library
          'vendor-charts': ['recharts', 'chart.js'],

          // Date handling
          'vendor-date': ['date-fns', 'dayjs'],

          // Forms
          'vendor-forms': [
            'react-hook-form',
            '@hookform/resolvers',
            'zod',
          ],
        },
      },
    },
    // Warning limits
    chunkSizeWarningLimit: 500,
  },
});
```

---

## Per-Route Chunks

Each route gets its own chunk via React.lazy:

```typescript
// routes/index.tsx - Creates separate chunks per route
import { lazy, Suspense } from 'react';

// Each import creates a separate chunk
const DashboardPage = lazy(() => import(/* webpackChunkName: "dashboard" */ '@/pages/DashboardPage'));
const BookingsPage = lazy(() => import(/* webpackChunkName: "bookings" */ '@/pages/BookingsPage'));
const FacilitiesPage = lazy(() => import(/* webpackChunkName: "facilities" */ '@/pages/FacilitiesPage'));
const SettingsPage = lazy(() => import(/* webpackChunkName: "settings" */ '@/pages/SettingsPage'));
const AdminPage = lazy(() => import(/* webpackChunkName: "admin" */ '@/pages/AdminPage'));

// Route tree creates natural chunk boundaries
const router = createBrowserRouter([
  { path: '/', element: <DashboardPage /> },
  { path: '/bookings/*', element: <BookingsPage /> },
  { path: '/facilities', element: <FacilitiesPage /> },
  { path: '/settings', element: <SettingsPage /> },
  { path: '/admin/*', element: <AdminPage /> },
]);
```

---

## Admin-Only Feature Splitting

Admin features are only loaded for admin users:

```typescript
// routes/AdminRoutes.tsx - Only load admin code for admin users
import { lazy, Suspense } from 'react';
import { useAuth } from '@/hooks/useAuth';

const AdminDashboard = lazy(() => import('@/features/admin/components/Dashboard'));
const UserManagement = lazy(() => import('@/features/admin/components/UserManagement'));
const ReportsPanel = lazy(() => import('@/features/admin/components/Reports'));
const SystemSettings = lazy(() => import('@/features/admin/components/SystemSettings'));

function AdminRoutes() {
  const { user } = useAuth();

  // Only render admin routes if user is admin
  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  return (
    <Routes>
      <Route path="dashboard" element={<AdminDashboard />} />
      <Route path="users" element={<UserManagement />} />
      <Route path="reports" element={<ReportsPanel />} />
      <Route path="settings" element={<SystemSettings />} />
    </Routes>
  );
}
```

---

## Dynamic Imports for Conditional Features

```typescript
// Heavy features loaded conditionally
function BookingPage() {
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  // Only load when needed
  const AdvancedFilters = useMemo(
    () => lazy(() => import('@/features/booking/components/AdvancedFilters')),
    []
  );

  return (
    <div>
      <Button onClick={() => setShowAdvancedFilters(true)}>
        Advanced Filters
      </Button>

      {showAdvancedFilters && (
        <Suspense fallback={<Skeleton />}>
          <AdvancedFilters />
        </Suspense>
      )}
    </div>
  );
}

// Conditional feature based on user role
function ExportButton({ format }: { format: 'csv' | 'pdf' | 'excel' }) {
  const { user } = useAuth();

  // Only load PDF library for PDF export
  const PDFExporter = useMemo(
    () => format === 'pdf'
      ? lazy(() => import('@/lib/export/pdf'))
      : null,
    [format]
  );

  const handleExport = async () => {
    if (PDFExporter) {
      return <PDFExporter data={data} />;
    }
    // CSV/Excel don't need heavy libraries
  };
}
```

---

## Analyzing Bundles

```bash
# Install bundle analyzer
npm install -D rollup-plugin-visualizer

# Run with analysis
npm run build -- --visualize
```

```typescript
// vite.config.ts - Add visualizer
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    visualizer({
      filename: 'dist/stats.html',
      open: true,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
});
```

---

## Chunk Naming

```typescript
// vite.config.ts - Meaningful chunk names
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        // Function for dynamic chunk names
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId || '';
          if (facadeModuleId.includes('/features/')) {
            const feature = facadeModuleId.split('/features/')[1].split('/')[0];
            return `js/features-${feature}-[hash].js`;
          }
          return `js/[name]-[hash].js`;
        },
        entryFileNames: 'js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const name = assetInfo.name || '';
          if (name.endsWith('.css')) {
            return 'css/[name]-[hash][extname]';
          }
          return 'assets/[name]-[hash][extname]';
        },
      },
    },
  },
});
```

---

## Bundle Size Monitoring

```json
// .size-limit.js
module.exports = [
  {
    name: 'Initial bundle',
    limit: '200 kB',
    path: 'dist/assets/index-*.js',
  },
  {
    name: 'Vendor chunk',
    limit: '300 kB',
    path: 'dist/assets/vendor-*.js',
  },
  {
    name: 'Admin bundle (admin users only)',
    limit: '150 kB',
    path: 'dist/assets/admin-*.js',
  },
];
```

---

## Preload and Prefetch

```typescript
// index.html - Preload critical assets
<head>
  <link rel="preload" href="/fonts/inter-var.woff2" as="font" type="font/woff2" crossorigin />
  <link rel="preload" href="/js/app.js" as="script" />

  <!-- Prefetch likely navigation targets -->
  <link rel="prefetch" href="/js/bookings.js" />
  <link rel="prefetch" href="/js/dashboard.js" />
</head>
```

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| Manual chunks | Control over splitting | Manual maintenance |
| Vendor splitting | Shared caching | Larger vendor bundles |
| Per-route chunks | Fast initial load | Multiple network requests |
| Dynamic imports | Conditional loading | Code complexity |

---

## Related Documents

- [Lazy Loading](lazy-loading.md) — Route and component lazy loading
- [Performance](performance.md) — Bundle budgets
- [Vite Build Options](https://vitejs.dev/config/build-options.html) — Full reference
