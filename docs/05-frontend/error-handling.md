# Error Handling

> Error boundaries per route. Fallback UI. Retry via Query. Global error reporter. User-friendly messages.

This document establishes error handling patterns for the Splashh Sports Platform. We aim for graceful degradation — when errors occur, users see helpful messages, and we gather diagnostic information.

---

## Error Boundaries

React Error Boundaries catch JavaScript errors in component trees:

```typescript
// components/error-boundary/ErrorBoundary.tsx
import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);

    // Report to Sentry
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    } else {
      captureException(error, { extra: { errorInfo } });
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[400px] items-center justify-center">
          <Card className="max-w-md">
            <CardHeader>
              <CardTitle>Something went wrong</CardTitle>
              <CardDescription>
                An unexpected error occurred. Please try again.
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button onClick={() => this.setState({ hasError: false })}>
                Try again
              </Button>
            </CardFooter>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
```

---

## Route-Level Error Boundaries

```typescript
// routes/ErrorBoundary.tsx - Per-route wrapper
import { ErrorBoundary as SentryErrorBoundary } from '@sentry/react';

export function RouteErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <SentryErrorBoundary
      fallback={({ error, resetError }) => (
        <ErrorDisplay
          error={error}
          onRetry={resetError}
        />
      )}
    >
      {children}
    </SentryErrorBoundary>
  );
}

// App.tsx - Apply to routes
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route
            index
            element={
              <ErrorBoundary>
                <HomePage />
              </ErrorBoundary>
            }
          />
          <Route
            path="bookings/*"
            element={
              <ErrorBoundary>
                <BookingsPage />
              </ErrorBoundary>
            }
          />
        </Route>
      </Routes>
    </Router>
  );
}
```

---

## Query Error Handling

TanStack Query provides error states for failed queries:

```typescript
// hooks/useBookings.ts with retry
export function useBookings(filters?: BookingFilters) {
  return useQuery({
    queryKey: ['bookings', filters],
    queryFn: () => bookingApi.list(filters),
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}

// Component with error UI
function BookingsPage() {
  const { data, isLoading, isError, error, refetch } = useBookings();

  if (isLoading) return <Skeleton />;

  if (isError) {
    return (
      <ErrorDisplay
        title="Failed to load bookings"
        message={error instanceof Error ? error.message : 'Unknown error'}
        onRetry={refetch}
      />
    );
  }

  return <BookingList bookings={data} />;
}
```

---

## Global Error Reporter

```typescript
// lib/error-reporting/sentry.ts
import * as Sentry from '@sentry/react';

export function initSentry() {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration(),
    ],
    tracesSampleRate: 0.1, // 10% of transactions
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  });
}

export function captureException(error: unknown, context?: Record<string, unknown>) {
  Sentry.captureException(error, {
    extra: context,
  });
}

export function captureMessage(message: string, level: Sentry.SeverityLevel = 'info') {
  Sentry.captureMessage(message, level);
}
```

---

## User-Friendly Error Messages

```typescript
// lib/error-messages.ts
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'NETWORK_ERROR':
        return 'Unable to connect. Check your internet connection.';
      case 'UNAUTHORIZED':
        return 'Your session has expired. Please log in again.';
      case 'FORBIDDEN':
        return "You don't have permission to perform this action.";
      case 'NOT_FOUND':
        return 'The requested resource was not found.';
      case 'VALIDATION_ERROR':
        return 'Please check your input and try again.';
      case 'RATE_LIMITED':
        return 'Too many requests. Please wait a moment.';
      default:
        return 'An error occurred. Please try again.';
    }
  }

  if (error instanceof TypeError && error.message === 'Failed to fetch') {
    return 'Unable to connect. Check your internet connection.';
  }

  return 'An unexpected error occurred. Please try again.';
}

class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
```

---

## Error Display Component

```typescript
// components/ui/ErrorDisplay.tsx
interface ErrorDisplayProps {
  title?: string;
  message: string;
  error?: Error;
  onRetry?: () => void;
  onReport?: () => void;
}

export function ErrorDisplay({
  title = 'Something went wrong',
  message,
  error,
  onRetry,
  onReport,
}: ErrorDisplayProps) {
  return (
    <Card className="max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-destructive" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{message}</p>

        {import.meta.env.DEV && error && (
          <pre className="mt-4 max-h-32 overflow-auto rounded bg-muted p-2 text-xs">
            {error.stack}
          </pre>
        )}
      </CardContent>
      <CardFooter className="gap-2">
        {onRetry && (
          <Button onClick={onRetry} variant="default">
            Try again
          </Button>
        )}
        {onReport && (
          <Button onClick={onReport} variant="outline">
            Report issue
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
```

---

## Form Error Handling

See [Forms](forms.md) for form-specific error patterns.

---

## Network Error Handling

```typescript
// lib/api/client.ts with interceptors
import { AxiosError } from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (!error.response) {
      // Network error
      throw new ApiError('NETWORK_ERROR', 'Network error', 0);
    }

    const { status, data } = error.response;

    if (status === 401) {
      // Handle unauthorized - redirect to login
      window.location.href = '/login';
    }

    if (status === 429) {
      throw new ApiError('RATE_LIMITED', 'Too many requests', status);
    }

    // Extract error message from response
    const message = extractErrorMessage(data);
    throw new ApiError('API_ERROR', message, status);
  }
);

function extractErrorMessage(data: unknown): string {
  if (typeof data === 'object' && data !== null && 'message' in data) {
    return String(data.message);
  }
  return 'An error occurred';
}
```

---

## Trade-offs

| Approach | What we gain | What we give up |
|----------|--------------|-----------------|
| Error boundaries | Catch React errors gracefully | Only class components in older React |
| Route-level boundaries | Isolated failures | More boundaries to manage |
| Sentry | Detailed error tracking | Cost at scale |
| Retry logic | Automatic recovery | Delayed error feedback |

---

## Related Documents

- [Caching](caching.md) — Query retry configuration
- [Offline Support](offline-support.md) — Offline error handling
- [Sentry Documentation](https://docs.sentry.io) — Full reference
