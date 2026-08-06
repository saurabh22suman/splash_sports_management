# Caching

> TanStack Query as the cache. Stale-while-revalidate. Cache time vs. stale time. Invalidation patterns. Optimistic updates.

This document establishes caching strategies for the Splashh Sports Platform using **TanStack Query** (formerly React Query). TanStack Query handles server state — the data that lives on the server and changes over time.

---

## Core Concepts

### Stale-While-Revalidate

TanStack Query uses a stale-while-revalidate strategy:

1. **Data returned immediately** from cache (if available)
2. **Background refetch** triggers to get fresh data
3. **UI stays responsive** while data refreshes

```typescript
const { data, isLoading, isStale } = useQuery({
  queryKey: ['bookings'],
  queryFn: fetchBookings,
  staleTime: 30 * 1000,   // Data considered fresh for 30s
  cacheTime: 5 * 60 * 1000, // Cache garbage collected after 5 min
});
```

### Cache Time vs. Stale Time

| Setting | Purpose | When to change |
|---------|---------|----------------|
| `staleTime` | How long data is "fresh" before refetch | Longer for rarely changing data |
| `cacheTime` | How long inactive cache is retained | Longer for expensive fetches |
| `gcTime` | Alias for cacheTime | - |

```typescript
// Frequently changing data - short staleTime
const { data: notifications } = useQuery({
  queryKey: ['notifications'],
  queryFn: fetchNotifications,
  staleTime: 10 * 1000, // Refetch after 10s
});

// Rarely changing data - long staleTime
const { data: facilityList } = useQuery({
  queryKey: ['facilities'],
  queryFn: fetchFacilities,
  staleTime: 60 * 60 * 1000, // 1 hour
});
```

---

## Basic Query Patterns

```typescript
// features/booking/hooks/useBookings.ts

// Standard query with caching
export function useBookings(filters?: BookingFilters) {
  return useQuery({
    queryKey: ['bookings', filters],
    queryFn: () => bookingApi.list(filters),
    staleTime: 30 * 1000,
  });
}

// Query with dependent fetching
export function useFacilityDetails(facilityId: string | undefined) {
  return useQuery({
    queryKey: ['facility', facilityId],
    queryFn: () => facilityApi.get(facilityId!),
    enabled: !!facilityId, // Only fetch when facilityId exists
  });
}

// Query with background refetching
export function useUpcomingBookings() {
  return useQuery({
    queryKey: ['bookings', 'upcoming'],
    queryFn: () => bookingApi.getUpcoming(),
    refetchInterval: 60 * 1000, // Refetch every minute
    staleTime: 10 * 1000,
  });
}
```

---

## Invalidation Patterns

### Invalidate All Queries in a Key

```typescript
// After creating a booking, invalidate the bookings list
const createBooking = useMutation({
  mutationFn: createBookingApi,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['bookings'] });
  },
});
```

### Invalidate with Partial Matching

```typescript
// Invalidate all bookings queries (any filters)
queryClient.invalidateQueries({
  queryKey: ['bookings'],
});

// Invalidate only facility-related queries
queryClient.invalidateQueries({
  queryKey: ['facilities'],
});
```

### Invalidate Using Predicates

```typescript
// Invalidate only queries where the facilityId matches
queryClient.invalidateQueries({
  queryKey: ['bookings'],
  predicate: (query) => {
    const filters = query.queryKey[1] as BookingFilters | undefined;
    return filters?.facilityId === updatedFacilityId;
  },
});
```

### Refetch After Invalidation

```typescript
// Optionally trigger immediate refetch
await queryClient.invalidateQueries({ queryKey: ['bookings'] });

// Or manually refetch
queryClient.refetchQueries({ queryKey: ['bookings'] });
```

---

## Optimistic Updates

For immediate UI feedback with rollback on error:

```typescript
// features/booking/hooks/useCancelBooking.ts
export function useCancelBooking() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: cancelBookingApi,

    // Called before mutation
    onMutate: async (bookingId) => {
      // 1. Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['bookings'] });

      // 2. Snapshot previous value
      const previousBookings = queryClient.getQueryData(['bookings']);

      // 3. Optimistically update
      queryClient.setQueriesData(['bookings'], (old: Booking[] | undefined) => {
        return old?.map((booking) =>
          booking.id === bookingId
            ? { ...booking, status: 'cancelled' as const }
            : booking
        );
      });

      // Return context for rollback
      return { previousBookings };
    },

    // Called on error
    onError: (err, bookingId, context) => {
      // Rollback to previous value
      if (context?.previousBookings) {
        queryClient.setQueryData(['bookings'], context.previousBookings);
      }
      toast.error('Failed to cancel booking');
    },

    // Always refetch after error or success
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['bookings'] });
    },
  });
}
```

---

## Cache Persistence

Persist cache to localStorage for app restart:

```typescript
// main.tsx
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';

const persister = createSyncStoragePersister({
  storage: window.localStorage,
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <PersistQueryClientProvider
    client={queryClient}
    persistOptions={{ persister }}
  >
    <App />
  </PersistQueryClientProvider>
);
```

> **Pitfall** — Don't persist sensitive data. Clear auth tokens separately.

---

## Prefetching

Load data before it's needed:

```typescript
// Prefetch on hover
function BookingListItem({ booking }) {
  const queryClient = useQueryClient();

  const handleHover = () => {
    queryClient.prefetchQuery({
      queryKey: ['booking', booking.id],
      queryFn: () => fetchBooking(booking.id),
    });
  };

  return (
    <div onMouseEnter={handleHover}>
      <BookingCard booking={booking} />
    </div>
  );
}

// Prefetch on app mount
function App() {
  const queryClient = useQueryClient();

  useEffect(() => {
    // Prefetch commonly needed data
    queryClient.prefetchQuery({
      queryKey: ['facilities'],
      queryFn: fetchFacilities,
    });
    queryClient.prefetchQuery({
      queryKey: ['user'],
      queryFn: fetchCurrentUser,
    });
  }, [queryClient]);

  return <Outlet />;
}
```

---

## Pagination & Infinite Scroll

```typescript
// Infinite scroll for bookings
export function useInfiniteBookings() {
  return useInfiniteQuery({
    queryKey: ['bookings', 'infinite'],
    queryFn: ({ pageParam = 0 }) =>
      bookingApi.list({ cursor: pageParam, limit: 20 }),
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    initialPageParam: undefined,
  });
}

function BookingList() {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteBookings();

  return (
    <>
      {data?.pages.map((page) =>
        page.items.map((booking) => (
          <BookingCard key={booking.id} booking={booking} />
        ))
      )}

      <Button
        onClick={() => fetchNextPage()}
        disabled={!hasNextPage || isFetchingNextPage}
      >
        {isFetchingNextPage ? 'Loading...' : 'Load More'}
      </Button>
    </>
  );
}
```

---

## Cache Keys Strategy

| Key Pattern | Example | When to Invalidate |
|-------------|---------|-------------------|
| `[entity]` | `['bookings']` | Any booking change |
| `[entity, id]` | `['booking', '123']` | Specific booking changes |
| `[entity, filters]` | `['bookings', { status: 'pending' }]` | Filtered list changes |
| `[entity, 'list']` | `['bookings', 'list']` | List-specific changes |

---

## Performance Considerations

### Query Keys Include Dependencies

```typescript
// Good: Include all query dependencies in key
const { data: user } = useQuery({ queryKey: ['user'], ... });
const { data: bookings } = useQuery({
  queryKey: ['bookings', user?.id], // Include user dependency
  queryFn: () => fetchUserBookings(user!.id),
  enabled: !!user,
});
```

### Avoid Over-Fetching

```typescript
// Bad: Refetching too often
const { data } = useQuery({
  queryKey: ['bookings'],
  queryFn: fetchBookings,
  refetchInterval: 1000, // Every second - too aggressive
});

// Good: Reasonable refetch interval
const { data } = useQuery({
  queryKey: ['bookings'],
  queryFn: fetchBookings,
  staleTime: 30 * 1000,
  refetchInterval: 60 * 1000, // Once per minute
});
```

---

## Trade-offs

| Decision | What we gain | What we give up |
|----------|--------------|-----------------|
| Long staleTime | Fewer network requests, faster UI | Stale data possible |
| Short staleTime | Always fresh data | More network requests |
| Optimistic updates | Instant feedback | Complexity, rollback handling |
| Cache persistence | Faster app restart | Memory usage, stale data |

---

## Related Documents

- [Offline Support](offline-support.md) — Offline queue integration
- [State Management](state-management.md) — Server vs. client state
- [TanStack Query](https://tanstack.com/query/latest) — Full documentation
