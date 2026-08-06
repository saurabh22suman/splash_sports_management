# State Management

> Server state: TanStack Query. Client state: React context. URL state: search params. Form state: RHF. We avoid Redux unless justified.

This document establishes state management patterns for the Splashh Sports Platform. We follow the principle of **colocating state** with its consumers and using the right tool for each state type.

---

## State Categories

| Category | Tool | Examples |
|----------|------|----------|
| Server state | TanStack Query | API data, user profile, bookings |
| Client state (global) | React Context | Theme, auth, tenant |
| Client state (local) | useState/useReducer | Form inputs, UI toggles |
| URL state | React Router | Filters, pagination |
| Form state | React Hook Form | All form data |

---

## Server State: TanStack Query

> **Rule** — All server data goes through TanStack Query. No direct fetch calls in components.

```typescript
// features/booking/hooks/useBooking.ts
export function useBooking(id: string) {
  return useQuery({
    queryKey: ['booking', id],
    queryFn: () => fetchBooking(id),
  });
}

// Components use the hook, not fetch directly
function BookingDetail({ bookingId }: { bookingId: string }) {
  const { data: booking, isLoading } = useBooking(bookingId);

  if (isLoading) return <Skeleton />;

  return <BookingCard booking={booking} />;
}
```

---

## Client State: Global (React Context)

### Auth Context

```typescript
// lib/auth/AuthContext.tsx
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  useEffect(() => {
    // Check auth on mount
    checkAuth().then((user) => {
      setState({
        user,
        isAuthenticated: !!user,
        isLoading: false,
      });
    });
  }, []);

  const login = async (credentials: LoginCredentials) => {
    const { user } = await loginApi(credentials);
    setState({ user, isAuthenticated: true, isLoading: false });
  };

  const logout = async () => {
    await logoutApi();
    setState({ user: null, isAuthenticated: false, isLoading: false });
  };

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

### Theme Context

```typescript
// lib/theme/ThemeContext.tsx
type Theme = 'light' | 'dark' | 'system';

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useLocalStorage<Theme>('theme', 'system');

  useEffect(() => {
    const root = window.document.documentElement;

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
      root.classList.remove('light', 'dark');
      root.classList.add(systemTheme);
    } else {
      root.classList.remove('light', 'dark');
      root.classList.add(theme);
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
```

---

## Client State: Local

### useState for Simple State

```typescript
function BookingFilters() {
  const [showPast, setShowPast] = useState(false);
  const [sortBy, setSortBy] = useState<'date' | 'name'>('date');

  return (
    <div className="flex gap-4">
      <label>
        <input
          type="checkbox"
          checked={showPast}
          onChange={(e) => setShowPast(e.target.checked)}
        />
        Show past bookings
      </label>
      <select
        value={sortBy}
        onChange={(e) => setSortBy(e.target.value as 'date' | 'name')}
      >
        <option value="date">Sort by date</option>
        <option value="name">Sort by name</option>
      </select>
    </div>
  );
}
```

### useReducer for Complex State

```typescript
// Booking wizard state
type BookingState = {
  step: 'facility' | 'datetime' | 'details' | 'review';
  facilityId: string | null;
  date: string | null;
  time: string | null;
  duration: number;
  notes: string;
};

type BookingAction =
  | { type: 'SET_FACILITY'; payload: string }
  | { type: 'SET_DATETIME'; payload: { date: string; time: string } }
  | { type: 'SET_DURATION'; payload: number }
  | { type: 'SET_NOTES'; payload: string }
  | { type: 'NEXT_STEP' }
  | { type: 'PREV_STEP' };

function bookingReducer(state: BookingState, action: BookingAction): BookingState {
  switch (action.type) {
    case 'SET_FACILITY':
      return { ...state, facilityId: action.payload };
    case 'SET_DATETIME':
      return { ...state, date: action.payload.date, time: action.payload.time };
    case 'SET_DURATION':
      return { ...state, duration: action.payload };
    case 'SET_NOTES':
      return { ...state, notes: action.payload };
    case 'NEXT_STEP':
      return { ...state, step: nextStep(state.step) };
    case 'PREV_STEP':
      return { ...state, step: prevStep(state.step) };
    default:
      return state;
  }
}

function BookingWizard() {
  const [state, dispatch] = useReducer(bookingReducer, initialState);

  return <WizardUI state={state} dispatch={dispatch} />;
}
```

---

## URL State

### Search Params as State

```typescript
// Route with search params
import { useSearchParams } from 'react-router-dom';

function BookingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const status = searchParams.get('status') || 'all';
  const page = parseInt(searchParams.get('page') || '1', 10);

  const { data } = useBookings({ status, page });

  const setStatus = (newStatus: string) => {
    setSearchParams((prev) => {
      prev.set('status', newStatus);
      prev.set('page', '1');
      return prev;
    });
  };

  const setPage = (newPage: number) => {
    setSearchParams((prev) => {
      prev.set('page', String(newPage));
      return prev;
    });
  };

  return (
    <div>
      <FilterTabs active={status} onChange={setStatus} />
      <BookingList bookings={data?.items} />
      <Pagination page={page} onChange={setPage} />
    </div>
  );
}
```

---

## Form State: React Hook Form

See [Forms](forms.md) for detailed patterns.

---

## Why Not Redux?

> **Guideline** — Avoid Redux unless you have a demonstrated need that TanStack Query + Context cannot meet.

### When Redux Is Justified

- Complex client-only state shared across many unrelated components
- State that updates frequently (e.g., drag-and-drop, real-time collaboration)
- Complex undo/redo functionality
- DevTools required for debugging

### Our Approach

| Use Case | Solution |
|----------|----------|
| API data | TanStack Query |
| Auth | Context + Query |
| Theme | Context |
| Forms | React Hook Form |
| URL | React Router |
| Component state | useState/useReducer |
| Most other cases | Context when shared, local when isolated |

---

## State Co-location

> **Rule** — Keep state as close as possible to where it's used. Lift only when truly shared.

```typescript
// Bad: Lifting state too early
function Page() {
  const [count, setCount] = useState(0);
  return <Widget count={count} onIncrement={() => setCount(c => c + 1)} />;
}

function Widget({ count, onIncrement }) {
  return <button onClick={onIncrement}>{count}</button>;
}

// Good: Colocated state
function Widget() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

---

## Trade-offs

| Approach | What we gain | What we give up |
|----------|--------------|-----------------|
| TanStack Query | Caching, deduping, background refetch | Learning curve |
| Context | Simple global state | Re-renders if not careful |
| URL state | Shareable links, back button | Limited data types |
| Local state | Simplicity, no prop drilling | Hard to share |

---

## Related Documents

- [Caching](caching.md) — TanStack Query caching
- [Hooks](hooks.md) — Custom hook patterns
- [Forms](forms.md) — Form state management
- [Theme Strategy](theme-strategy.md) — Theme context
