# PWA Strategy

> Install prompt. App shell caching. Runtime caching strategies. Push notifications. Update flow.

This document establishes Progressive Web App (PWA) patterns for the Splashh Sports Platform. Our PWAs must be installable, work offline-capable, and provide a native-like experience.

---

## Installation Prompt

```typescript
// components/PWAInstallPrompt.tsx
import { useState, useEffect } from 'react';
import { BeforeInstallPromptEvent } from '@/types/pwa';

export function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setIsInstalled(true);
      return;
    }

    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setIsVisible(true);
    };

    const handleAppInstalled = () => {
      setIsInstalled(true);
      setIsVisible(false);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;

    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;

    if (outcome === 'accepted') {
      setIsInstalled(true);
    }

    setDeferredPrompt(null);
    setIsVisible(false);
  };

  if (isInstalled || !isVisible) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:w-80">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Install Splashh</CardTitle>
          <CardDescription className="text-sm">
            Add to your home screen for the best experience
          </CardDescription>
        </CardHeader>
        <CardFooter className="gap-2">
          <Button size="sm" onClick={handleInstall}>
            Install
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setIsVisible(false)}>
            Not now
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
```

---

## App Shell Caching

The app shell (HTML, CSS, JS, fonts) is cached for instant load:

```typescript
// vite.config.ts
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    VitePWA({
      workbox: {
        // Cache app shell
        globPatterns: [
          '**/*.{js,css,html,ico,png,svg,woff2}',
          'manifest.json',
        ],
        // App shell strategy
        runtimeCaching: [
          {
            // App shell assets - Cache First
            urlPattern: /^\/.*\.(js|css|woff2)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'app-shell',
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

## Runtime Caching Strategies

| Strategy | Use Case | Implementation |
|----------|----------|----------------|
| CacheFirst | Static assets, images | Serve from cache, fallback to network |
| NetworkFirst | API calls | Try network, fallback to cache |
| StaleWhileRevalidate | Frequently updated data | Serve cache, update in background |
| NetworkOnly | Real-time data | Never cache |

```typescript
// vite.config.ts - Full caching strategy
VitePWA({
  workbox: {
    runtimeCaching: [
      // API calls - Network First
      {
        urlPattern: /^https:\/\/api\./,
        handler: 'NetworkFirst',
        options: {
          cacheName: 'api-cache',
          networkTimeoutSeconds: 10,
          expiration: {
            maxEntries: 100,
            maxAgeSeconds: 60 * 60 * 24, // 24 hours
          },
          cacheableResponse: {
            statuses: [0, 200],
          },
        },
      },
      // Images - Cache First
      {
        urlPattern: /\.(?:png|jpg|jpeg|svg|webp|avif|gif)$/,
        handler: 'CacheFirst',
        options: {
          cacheName: 'image-cache',
          expiration: {
            maxEntries: 200,
            maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
          },
        },
      },
      // Fonts - Cache First with longer expiry
      {
        urlPattern: /\/fonts\/.*\.woff2$/,
        handler: 'CacheFirst',
        options: {
          cacheName: 'font-cache',
          expiration: {
            maxEntries: 20,
            maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
          },
        },
      },
    ],
  },
});
```

---

## Push Notifications

### Web Push API Integration

```typescript
// lib/notifications/push.ts
export async function requestNotificationPermission(): Promise<NotificationPermission> {
  if (!('Notification' in window)) {
    throw new Error('Notifications not supported');
  }

  const permission = await Notification.requestPermission();
  return permission;
}

export async function subscribeToPush(): Promise<PushSubscription | null> {
  const permission = await requestNotificationPermission();
  if (permission !== 'granted') {
    return null;
  }

  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(
      import.meta.env.VITE_VAPID_PUBLIC_KEY
    ),
  });

  // Send subscription to server
  await api.post('/push/subscribe', subscription.toJSON());

  return subscription;
}

// Service worker: Handle push events
// public/sw.js
self.addEventListener('push', (event) => {
  const data = event.data?.json() || {};

  const options = {
    body: data.body,
    icon: '/icons/icon-192.png',
    badge: '/icons/badge-72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/',
      dateOfArrival: Date.now(),
    },
    actions: data.actions || [
      { action: 'view', title: 'View' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'Splashh Sports', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'dismiss') return;

  const url = event.notification.data?.url || '/';
  event.waitUntil(clients.openWindow(url));
});
```

---

## Update Flow

```typescript
// App.tsx - Handle service worker updates
import { useRegisterSW } from 'virtual:pwa-register/react';

function UpdatePrompt() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onNeedRefresh() {
      // Show update banner
      setShowUpdate(true);
    },
    onOfflineReady() {
      console.log('App ready to work offline');
    },
  });

  const handleUpdate = async () => {
    await updateServiceWorker(true); // Reload page after update
  };

  if (!needRefresh) return null;

  return (
    <Alert className="fixed bottom-4 left-4 right-4 md:left-auto md:w-96">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Update available</AlertTitle>
      <AlertDescription>
        A new version is available. Refresh to update.
      </AlertDescription>
      <AlertAction onClick={handleUpdate}>Refresh</AlertAction>
    </Alert>
  );
}
```

---

## PWA Manifest

```json
// public/manifest.json
{
  "name": "Splashh Sports",
  "short_name": "Splashh",
  "description": "Book sports facilities at your club",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#0066CC",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/icons/icon-72.png",
      "sizes": "72x72",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-96.png",
      "sizes": "96x96",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-128.png",
      "sizes": "128x128",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-144.png",
      "sizes": "144x144",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-152.png",
      "sizes": "152x152",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-384.png",
      "sizes": "384x384",
      "type": "image/png",
      "purpose": "maskable any"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable any"
    }
  ],
  "categories": ["sports", "lifestyle"],
  "shortcuts": [
    {
      "name": "My Bookings",
      "short_name": "Bookings",
      "url": "/bookings",
      "icons": [{ "src": "/icons/shortcut-bookings.png", "sizes": "96x96" }]
    },
    {
      "name": "New Booking",
      "short_name": "Book",
      "url": "/bookings/new",
      "icons": [{ "src": "/icons/shortcut-new.png", "sizes": "96x96" }]
    }
  ]
}
```

---

## Testing PWA

### Lighthouse PWA Audit

```bash
# Run in Chrome DevTools
# 1. Open DevTools (F12)
# 2. Go to Lighthouse tab
# 3. Select "Progressive Web App"
# 4. Run audit
```

### Required Criteria

| Criterion | Target |
|-----------|--------|
| HTTPS | Enabled |
| Redirects | HTTP to HTTPS |
| Start URL | Valid and accessible |
| Favicon | 192x192 and 512x512 |
| HTML | Has `<meta name="viewport">` |
| Manifest | Valid, accessible, has icons |
| Service Worker | Registered |
| Offline | 200 response for offline |

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| CacheFirst images | Fast image loads | Potential stale images |
| NetworkFirst API | Fresh data when online | Slight latency |
| Push notifications | Re-engagement | Permission prompts |
| Install prompt | Native-like experience | Extra UI complexity |

---

## Related Documents

- [Offline Support](offline-support.md) — Offline data handling
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API) — Full reference
- [Web Push API](https://developer.mozilla.org/en-US/docs/Web/API/Push_API) — Push notifications
