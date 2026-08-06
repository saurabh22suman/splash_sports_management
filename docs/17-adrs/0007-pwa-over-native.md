# ADR-0007: PWA Over Native Mobile

> Mobile application strategy.

## Status
Accepted

## Context
We need mobile apps for:
- Members booking facilities
- Staff managing operations
- Limited budget and timeline
- Need both iOS and Android

## Decision
We will build **Progressive Web Apps (PWA)** for both member-facing and staff-facing applications:
- Single React codebase
- Service workers for offline
- Installable (add to home screen)
- Push notifications (Android only initially)
- Responsive design for all screen sizes

## Consequences

### Positive
- **Single codebase** — One team, one code
- **Faster development** — No platform-specific code
- **Instant deployment** — No app store review
- **Offline-capable** — Service workers
- **Lower cost** — No platform-specific developers

### Negative
- **iOS push** — Limited support (web push not available)
- **Native features** — Limited access to device APIs
- **App store presence** — Not in app stores
- **Perceived quality** — Some users prefer "real" apps

### Neutral
- PWA support improving across browsers
- Can add native wrappers later if needed (Capacitor)

## Alternatives Considered

### Alternative 1: React Native
Rejected because:
- Two codebases (iOS/Android) or bridge complexity
- Requires mobile-specific expertise
- Higher development cost
- Still needs web for desktop

### Alternative 2: Flutter
Rejected because:
- Team lacks Dart expertise
- Less React integration
- Similar trade-offs to React Native

### Alternative 3: Native (Swift/Kotlin)
Rejected because:
- Double the development cost
- Longer timeline
- Overkill for our requirements
- Team doesn't have native expertise

## Implementation

```javascript
// Service worker registration
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => console.log('SW registered'))
      .catch(err => console.log('SW failed', err));
  });
}

// Web app manifest
{
  "name": "Splashh",
  "short_name": "Splashh",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#0066cc",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

## References
- [PWA Strategy](../05-frontend/pwa-strategy.md)
- [Offline Support](../05-frontend/offline-support.md)
- [Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest)
