# Hooks

> Custom hook conventions. Rules of hooks compliance. Hook composition. useQuery/useMutation wrappers. Avoiding stale closures.

This document establishes patterns for writing custom hooks in the Splashh Sports Platform. Hooks are our primary mechanism for extracting and sharing stateful logic.

---

## Rules of Hooks

> **Rule** — Hooks must follow the Rules of Hooks. Violations will cause runtime errors and unpredictable behavior.

1. **Only call hooks at the top level** — not inside loops, conditions, or nested functions
2. **Only call hooks from React functions** — components or other hooks
3. **Name hooks with `use` prefix** — enables the linter to enforce rules

```typescript
// Anti-pattern: Conditional hook call
function Component({ showData }: { showData: boolean }) {
  if (showData) {
    const data = useFetchData(); // Violates rule #1
  }
  return <div />;
}

// Anti-pattern: Hook in regular function
function regularFunction() {
  const [state, setState] = useState(0); // Violates rule #2
}

// Good: Top-level hook calls
function Component() {
  const [query, setQuery] = useState('');

  // This is fine - conditional logic affects what happens AFTER the hook
  const { data } = useQuery({
    queryKey: ['search', query],
    queryFn: () => searchAPI(query),
    enabled: query.length > 0, // Enabled is a query option, not a conditional call
  });

  return <div>{data?.length}</div>;
}
```

---

## Custom Hook Conventions

### Naming

```typescript
// Good: Descriptive names with use prefix
export function useAuth();
export function useBooking(id: string);
export function useBookings(filters: BookingFilters);
export function useCreateBooking();

// Bad: No use prefix
export function Auth();           // Not a hook
export function getBooking(id);    // Sounds like a function
```

### Single Responsibility

```typescript
// Good: Focused hooks
export function useAuth() {
  const { data: session } = useQuery({
    queryKey: ['session'],
    queryFn: getSession,
  });

  return {
    user: session?.user,
    isAuthenticated: !!session,
    login: /* ... */,
    logout: /* ... */,
  };
}

export function useBooking(id: string) {
  return useQuery({
    queryKey: ['booking', id],
    queryFn: () => fetchBooking(id),
  });
}

// Bad: Combined god hook
export function useAuthAndBookingAndUserData() {
  // 500 lines handling auth, bookings, user profile, settings, notifications
}
```

---

## Hook Composition

Compose hooks from other hooks:

```typescript
// useBookings.ts - Wraps useQuery with business logic
export function useBookings(filters?: BookingFilters) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['bookings', filters],
    queryFn: () => bookingApi.list(filters),
    staleTime: 30 * 1000, // 30 seconds
  });

  const invalidateBookings = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['bookings'] });
  }, [queryClient]);

  return {
    ...query,
    invalidateBookings,
  };
}

// useMyBookings.ts - Composes useBookings
export function useMyBookings() {
  const { data: session } = useAuth();

  return useBookings({
    userId: session?.id,
  });
}

// useUpcomingBookings.ts - Further composition
export function useUpcomingBookings() {
  const { data: bookings, ...rest } = useMyBookings();

  const upcoming = useMemo(() => {
    if (!bookings) return [];
    return bookings.filter(isFutureBooking);
  }, [bookings]);

  return { ...rest, data: upcoming };
}
```

---

## TanStack Query Wrappers

> **Rule** — Wrap useQuery/useMutation in custom hooks. Never use them directly in components.

```typescript
// features/booking/api/booking.hooks.ts

// Query hook with typed keys
export function useBooking(id: string) {
  return useQuery({
    queryKey: ['booking', id] as const,
    queryFn: () => bookingApi.get(id),
    enabled: !!id,
  });
}

export function useBookings(filters?: BookingFilters) {
  return useQuery({
    queryKey: ['bookings', filters] as const,
    queryFn: () => bookingApi.list(filters),
  });
}

// Mutation hook with optimistic update
export function useCancelBooking() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: bookingApi.cancel,
    onMutate: async (bookingId) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['bookings'] });

      // Snapshot previous value
      const previousBookings = queryClient.getQueryData<Bookings[]>(['bookings']);

      // Optimistically update
      queryClient.setQueriesData<Bookings[]>(
        { queryKey: ['bookings'] },
        (old) => old?.map((b) =>
          b.id === bookingId ? { ...b, status: 'cancelled' as const } : b
        )
      );

      return { previousBookings };
    },
    onError: (err, id, context) => {
      // Rollback on error
      if (context?.previousBookings) {
        queryClient.setQueryData(['bookings'], context.previousBookings);
      }
      toast.error('Failed to cancel booking');
    },
    onSettled: () => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['bookings'] });
    },
  });
}

// Mutation hook with loading state helpers
export function useCreateBooking() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: bookingApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookings'] });
      toast.success('Booking created successfully');
    },
  });
}
```

---

## Avoiding Stale Closures

Stale closures occur when a closure captures stale state. Common in event handlers and timers.

### Problem

```typescript
// Anti-pattern: Stale closure
function Component() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      console.log('Count is:', count); // Always logs 0!
    }, 1000);
    return () => clearInterval(interval);
  }, []); // Empty deps = stale count

  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

### Solution: Use Refs or Functional Updates

```typescript
// Solution 1: Functional state updates
function Component() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCount((c) => c + 1); // Always gets current value
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return <div>{count}</div>;
}

// Solution 2: Use ref for mutable value
function Component() {
  const [count, setCount] = useState(0);
  const countRef = useRef(count);

  useEffect(() => {
    countRef.current = count;
  }, [count]);

  useEffect(() => {
    const interval = setInterval(() => {
      console.log('Count is:', countRef.current); // Always fresh
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

### With Event Handlers

```typescript
// Problem: Handler uses stale value
function BookingList() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: bookings } = useBookings();

  const handleCancel = useCallback((id: string) => {
    // selectedId is stale if not in deps
    if (selectedId === id) {
      setSelectedId(null);
    }
  }, []); // Missing selectedId dependency

  return (
    <ul>
      {bookings?.map((b) => (
        <li key={b.id}>
          {b.name}
          <button onClick={() => {
            setSelectedId(b.id);
            handleCancel(b.id);
          }}>
            Cancel
          </button>
        </li>
      ))}
    </ul>
  );
}

// Solution: Include dependencies or use functional pattern
const handleCancel = useCallback((id: string) => {
  setSelectedId((current) => (current === id ? null : current));
}, []);
```

---

## Hook Testing

```typescript
// useBookings.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useBookings } from './useBookings';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('useBookings', () => {
  it('fetches bookings', async () => {
    const { result } = renderHook(() => useBookings(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(3);
  });

  it('handles errors', async () => {
    server.use(mockError('Failed to fetch bookings'));

    const { result } = renderHook(() => useBookings(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeDefined();
  });
});
```

---

## Common Hook Patterns

### useLocalStorage

```typescript
export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') return initialValue;

    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback(
    (value: T | ((val: T) => T)) => {
      try {
        const valueToStore = value instanceof Function ? value(storedValue) : value;
        setStoredValue(valueToStore);
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      } catch (error) {
        console.error('Failed to save to localStorage:', error);
      }
    },
    [key, storedValue]
  );

  return [storedValue, setValue] as const;
}
```

### useDebounce

```typescript
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
```

### useMediaQuery

```typescript
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    if (media.matches !== matches) {
      setMatches(media.matches);
    }

    const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
    media.addEventListener('change', listener);

    return () => media.removeEventListener('change', listener);
  }, [matches, query]);

  return matches;
}
```

---

## Trade-offs

| Pattern | When to use | When to avoid |
|---------|-------------|---------------|
| Custom hooks | Extract stateful logic, compose queries | When simple function suffices |
| Query hooks | Data fetching with caching | Static data, simple computations |
| Mutation hooks | Write operations | Read-only operations |
| Optimistic updates | User-facing speed, reversible actions | Irreversible operations, financial transactions |

---

## Related Documents

- [Caching](caching.md) — TanStack Query caching strategy
- [State Management](state-management.md) — Server vs. client state
- [Component Design](component-design.md) — Composition patterns
