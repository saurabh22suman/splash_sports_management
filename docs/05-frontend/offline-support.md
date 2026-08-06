# Offline Support

> Service worker (Vite PWA plugin). IndexedDB for offline queue. Background sync. Conflict resolution strategies.

This document establishes offline support patterns for the Splashh Sports Platform. Our PWAs must remain functional during network interruptions, providing a reliable experience for users in areas with poor connectivity.

---

## Service Worker Strategy

We use the **Vite PWA plugin** for service worker management:

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'robots.txt', 'apple-touch-icon.png'],
      manifest: {
        name: 'Splashh Sports',
        short_name: 'Splashh',
        description: 'Book sports facilities',
        theme_color: '#0066CC',
        background_color: '#FFFFFF',
        display: 'standalone',
        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\./,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24, // 24 hours
              },
              networkTimeoutSeconds: 10,
            },
          },
          {
            urlPattern: /\.(?:png|jpg|jpeg|svg|webp|avif)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'image-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
              },
            },
          },
        ],
      },
    }),
  ],
});
```

---

## Offline Detection

```typescript
// hooks/useOffline.ts
import { useState, useEffect } from 'react';

export function useOffline() {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOffline;
}

// Usage
function BookingPage() {
  const isOffline = useOffline();

  if (isOffline) {
    return (
      <Alert>
        <AlertTitle>You're offline</AlertTitle>
        <AlertDescription>
          Some features may be limited. Changes will sync when reconnected.
        </AlertDescription>
      </Alert>
    );
  }

  return <BookingContent />;
}
```

---

## IndexedDB Offline Queue

For offline-capable mutations (bookings, updates), we queue operations in IndexedDB:

```typescript
// lib/offline/queue.ts
import { openDB, type IDBPDatabase } from 'idb';

interface QueuedOperation {
  id: string;
  type: 'CREATE' | 'UPDATE' | 'DELETE';
  entity: 'booking' | 'profile' | 'membership';
  payload: unknown;
  timestamp: number;
  retryCount: number;
}

const DB_NAME = 'splashh-offline';
const STORE_NAME = 'operation-queue';

async function getDB(): Promise<IDBPDatabase> {
  return openDB(DB_NAME, 1, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, {
          keyPath: 'id',
        });
        store.createIndex('entity', 'entity');
        store.createIndex('timestamp', 'timestamp');
      }
    },
  });
}

export async function enqueueOperation(operation: Omit<QueuedOperation, 'id' | 'timestamp' | 'retryCount'>): Promise<string> {
  const db = await getDB();
  const id = crypto.randomUUID();

  await db.add(STORE_NAME, {
    ...operation,
    id,
    timestamp: Date.now(),
    retryCount: 0,
  });

  // Try to sync immediately if online
  if (navigator.onLine) {
    await syncQueue();
  }

  return id;
}

export async function dequeueOperation(id: string): Promise<void> {
  const db = await getDB();
  await db.delete(STORE_NAME, id);
}

export async function getQueuedOperations(): Promise<QueuedOperation[]> {
  const db = await getDB();
  return db.getAllFromIndex(STORE_NAME, 'timestamp');
}

export async function syncQueue(): Promise<{ success: number; failed: number }> {
  const operations = await getQueuedOperations();
  let success = 0;
  let failed = 0;

  for (const op of operations) {
    try {
      await processOperation(op);
      await dequeueOperation(op.id);
      success++;
    } catch (error) {
      // Increment retry count
      const db = await getDB();
      await db.put(STORE_NAME, {
        ...op,
        retryCount: op.retryCount + 1,
      });
      failed++;

      // Remove after 3 retries
      if (op.retryCount >= 3) {
        await dequeueOperation(op.id);
        console.error('Operation failed after 3 retries:', op);
      }
    }
  }

  return { success, failed };
}

async function processOperation(op: QueuedOperation): Promise<void> {
  const { type, entity, payload } = op;
  const endpoint = `/${entity}s`;

  switch (type) {
    case 'CREATE':
      await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      break;
    case 'UPDATE':
      await fetch(`${endpoint}/${(payload as { id: string }).id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      break;
    case 'DELETE':
      await fetch(`${endpoint}/${(payload as { id: string }).id}`, {
        method: 'DELETE',
      });
      break;
  }
}
```

---

## Background Sync

```typescript
// Register for background sync when online
if ('serviceWorker' in navigator && 'sync' in window.SyncManager) {
  // Request sync when page loads
  window.addEventListener('online', async () => {
    const registration = await navigator.serviceWorker.ready;
    await registration.sync.register('sync-bookings');
  });
}

// In service worker (public/sw.js)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-bookings') {
    event.waitUntil(syncQueue());
  }
});

async function syncQueue() {
  const db = await openDB();
  const operations = await db.getAll('operation-queue');

  for (const op of operations) {
    try {
      await processOperation(op);
      await db.delete('operation-queue', op.id);
    } catch (e) {
      console.error('Sync failed:', e);
      throw e; // Will retry later
    }
  }
}
```

---

## Conflict Resolution

### Last-Write-Wins (Non-Critical Data)

For profile settings, preferences:

```typescript
// lib/offline/conflict-resolution.ts
export function resolveConflict<T>(local: T, server: T): T {
  // Simple last-write-wins based on timestamp
  // In production, use vector clocks or CRDTs
  return local;
}
```

### Server-Wins (Bookings)

For bookings where server state is authoritative:

```typescript
// hooks/useBooking.ts - Force refetch after reconnect
export function useBooking(id: string) {
  const isOffline = useOffline();

  return useQuery({
    queryKey: ['booking', id],
    queryFn: () => fetchBooking(id),
    // When coming back online, refetch immediately
    staleTime: isOffline ? Infinity : 30 * 1000,
  });
}
```

### Optimistic with Server Check (Dual-Approach)

For facilities availability:

```typescript
// Offline booking with availability check on reconnect
async function createBooking(data: BookingFormData): Promise<BookingResult> {
  if (navigator.onLine) {
    // Online: Direct API call
    return api.createBooking(data);
  }

  // Offline: Queue and return optimistic result
  const tempId = crypto.randomUUID();
  await enqueueOperation({
    type: 'CREATE',
    entity: 'booking',
    payload: { ...data, tempId },
  });

  return { success: true, tempId, requiresSync: true };
}

// On reconnect, validate availability
window.addEventListener('online', async () => {
  const result = await syncQueue();

  if (result.failed > 0) {
    // Show notification about conflicts
    toast.error('Some bookings could not be confirmed. Please review.');
  }
});
```

---

## Offline Booking Queue UI

```typescript
// features/booking/components/OfflineBookingQueue.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getQueuedOperations, syncQueue } from '@/lib/offline/queue';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export function OfflineBookingQueue() {
  const queryClient = useQueryClient();

  const { data: queue } = useQuery({
    queryKey: ['offline-queue'],
    queryFn: getQueuedOperations,
    refetchInterval: 5000,
  });

  const syncMutation = useMutation({
    mutationFn: syncQueue,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['offline-queue'] });
    },
  });

  if (!queue?.length) return null;

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Pending Changes
          <Badge variant="secondary">{queue.length}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {queue.map((op) => (
            <li key={op.id} className="flex items-center justify-between text-sm">
              <span>
                {op.type} {op.entity}
              </span>
              <Badge variant="outline">
                {new Date(op.timestamp).toLocaleTimeString()}
              </Badge>
            </li>
          ))}
        </ul>
      </CardContent>
      <CardFooter>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Now'}
        </Button>
      </CardFooter>
    </Card>
  );
}
```

---

## Service Worker Update Flow

```typescript
// App.tsx - Handle service worker updates
import { useRegisterSW } from 'virtual:pwa-register/react';

export function ReloadPrompt() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onNeedRefresh() {
      // Show prompt to user
      setShowRefresh(true);
    },
    onOfflineReady() {
      console.log('App ready to work offline');
    },
  });

  const handleRefresh = async () => {
    await updateServiceWorker(true);
    window.location.reload();
  };

  if (!needRefresh) return null;

  return (
    <Alert>
      <AlertTitle>Update available</AlertTitle>
      <AlertDescription>
        New version available. Refresh to update.
      </AlertDescription>
      <Button onClick={handleRefresh}>Refresh</Button>
    </Alert>
  );
}
```

---

## Trade-offs

| Approach | When to use | Trade-offs |
|----------|-------------|------------|
| NetworkFirst API | Most API calls | Slight latency on first request |
| CacheFirst assets | Static assets, images | Potential stale content |
| IndexedDB queue | Create/update/delete mutations | Complex conflict resolution |
| Last-write-wins | Non-critical data | Possible data loss |
| Server-wins | Authoritative data | User may lose work |

---

## Related Documents

- [PWA Strategy](pwa-strategy.md) — PWA installation and push
- [Caching](caching.md) — TanStack Query caching
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) — Full reference
