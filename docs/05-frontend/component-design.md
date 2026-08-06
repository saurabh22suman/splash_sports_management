# Component Design

> Composition over configuration. Props as contracts. Narrow interfaces. Children over render props where possible.

This document establishes the principles for building React components in the Splashh Sports Platform. We prioritize **composability** — small, focused components that combine to form complex UIs — over configuration — massive components with dozens of props.

---

## Composition Over Configuration

> **Rule** — Build small, composable components. Avoid "god components" with 10+ props.

### Bad: God Component

```typescript
// Anti-pattern: A component with too many props and responsibilities
interface BookingWidgetProps {
  title: string;
  showCalendar: boolean;
  showTimeSlots: boolean;
  showPricing: boolean;
  showPayment: boolean;
  enableRecurring: boolean;
  allowGuestBooking: boolean;
  defaultSport?: string;
  defaultFacility?: string;
  onBookingComplete?: (booking: Booking) => void;
  onError?: (error: Error) => void;
  theme?: 'light' | 'dark';
  locale?: string;
  // ... 20 more props
}

export function BookingWidget(props: BookingWidgetProps) {
  // 500+ lines of logic handling everything
}
```

### Good: Composed Components

```typescript
// Each component has a single responsibility
import { BookingProvider } from '@/features/booking';
import { SportSelector } from '@/features/booking/components/SportSelector';
import { FacilityCalendar } from '@/features/booking/components/FacilityCalendar';
import { TimeSlotPicker } from '@/features/booking/components/TimeSlotPicker';
import { BookingSummary } from '@/features/booking/components/BookingSummary';
import { PaymentForm } from '@/features/payments/components/PaymentForm';

export function BookingWidget() {
  return (
    <BookingProvider>
      <SportSelector />
      <FacilityCalendar>
        <TimeSlotPicker />
        <BookingSummary />
        <PaymentForm />
      </FacilityCalendar>
    </BookingProvider>
  );
}
```

---

## Container / Presentational Split

Separate components that manage **state** (containers) from components that render **UI** (presentational).

```typescript
// Presentational component — only accepts data via props, renders UI
interface BookingCardProps {
  booking: Booking;
  onCancel: (id: string) => void;
  isCancelling?: boolean;
}

export function BookingCard({ booking, onCancel, isCancelling }: BookingCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{booking.facility.name}</CardTitle>
        <CardDescription>
          {formatDate(booking.date)} at {booking.startTime}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Badge variant={booking.status === 'confirmed' ? 'default' : 'secondary'}>
          {booking.status}
        </Badge>
      </CardContent>
      <CardFooter>
        <Button
          variant="destructive"
          onClick={() => onCancel(booking.id)}
          disabled={isCancelling}
        >
          {isCancelling ? 'Cancelling...' : 'Cancel'}
        </Button>
      </CardFooter>
    </Card>
  );
}

// Container component — manages state and data fetching
export function BookingCardContainer({ bookingId }: { bookingId: string }) {
  const { data: booking, isLoading } = useQuery({
    queryKey: ['booking', bookingId],
    queryFn: () => fetchBooking(bookingId),
  });

  const cancelMutation = useMutation({
    mutationFn: cancelBooking,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookings'] });
    },
  });

  if (isLoading) return <Skeleton />;

  return (
    <BookingCard
      booking={booking}
      onCancel={(id) => cancelMutation.mutate(id)}
      isCancelling={cancelMutation.isPending}
    />
  );
}
```

> **Why** — Presentational components are trivially testable (just pass props, check render output). Container components contain the complex logic and can be mocked during testing.

---

## Props as a Contract

Define explicit interfaces. Avoid `any`. Use narrow types.

```typescript
// Good: Explicit, narrow interface
interface UserAvatarProps {
  userId: string;
  size?: 'sm' | 'md' | 'lg';
  showStatus?: boolean;
}

// Bad: Too broad
interface UserAvatarProps {
  user: any;           // Avoid any
  options?: object;    // Avoid object
}
```

### Union Types for Finite Options

```typescript
// Use union types for finite options
type ButtonVariant = 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
type BookingStatus = 'pending' | 'confirmed' | 'cancelled' | 'completed';

interface BadgeProps {
  variant: ButtonVariant;
}
```

---

## Children Over Render Props

> **Rule** — Prefer `children` prop over render prop callbacks when possible.

```typescript
// Good: children pattern
function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('rounded-lg border', className)}>{children}</div>;
}

<Card>
  <CardHeader>Title</CardHeader>
  <CardContent>Content</CardContent>
</Card>

// Acceptable: render props when needed for conditional rendering
function DataList<T>({
  items,
  renderItem,
}: {
  items: T[];
  renderItem: (item: T, index: number) => ReactNode;
}) {
  return <ul>{items.map(renderItem)}</ul>;
}
```

> **Why** — `children` is idiomatic React, easier to type, and composes naturally. Render props are appropriate when the consumer needs to control rendering logic (e.g., virtualization, complex conditionals).

---

## State Colocation

> **Rule** — Keep state as close as possible to where it's used. Lift state only when truly shared.

```typescript
// Bad: Lifting state too early
function BookingPage() {
  const [selectedSport, setSelectedSport] = useState<string | null>(null);
  const [selectedFacility, setSelectedFacility] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  return (
    <div>
      <SportSelector value={selectedSport} onChange={setSelectedSport} />
      <FacilitySelector value={selectedFacility} onChange={setSelectedFacility} />
      <DateSelector value={selectedDate} onChange={setSelectedDate} />
    </div>
  );
}

// Good: Colocated state with useReducer for complex state
function BookingWidget() {
  const [state, dispatch] = useReducer(bookingReducer, initialState);

  return (
    <BookingContext.Provider value={{ state, dispatch }}>
      <SportSelector />
      <FacilitySelector />
      <DateSelector />
    </BookingContext.Provider>
  );
}
```

---

## Anti-Patterns

### Prop Drilling

```typescript
// Anti-pattern: Passing props through many levels
function App() {
  const [user, setUser] = useState<User>(null);
  return <Parent user={user} />;
}

function Parent({ user }: { user: User }) {
  return <Child user={user} />;
}

function Child({ user }: { user: User }) {
  return <GrandChild user={user} />;
}

function GrandChild({ user }: { user: User }) {
  return <div>{user.name}</div>;
}

// Solution: Use context
function App() {
  return (
    <UserProvider>
      <GrandChild />
    </UserProvider>
  );
}
```

### God Components

```typescript
// Anti-pattern: Single component doing everything
function AdminDashboard() {
  // 2000 lines, manages:
  // - User list state
  // - Booking list state
  // - Analytics data
  // - Filter states
  // - Export functionality
  // - 15 event handlers
}

// Solution: Break into smaller components
function AdminDashboard() {
  return (
    <DashboardLayout>
      <UserStatsWidget />
      <BookingTableWidget />
      <AnalyticsWidget />
      <ExportWidget />
    </DashboardLayout>
  );
}
```

---

## Component Testing Strategy

```typescript
// BookingCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { BookingCard } from './BookingCard';

describe('BookingCard', () => {
  const mockBooking = {
    id: '123',
    facility: { name: 'Tennis Court A' },
    date: '2024-01-15',
    startTime: '10:00',
    status: 'confirmed' as const,
  };

  it('renders booking details', () => {
    render(<BookingCard booking={mockBooking} onCancel={jest.fn()} />);

    expect(screen.getByText('Tennis Court A')).toBeInTheDocument();
    expect(screen.getByText('10:00')).toBeInTheDocument();
    expect(screen.getByText('confirmed')).toBeInTheDocument();
  });

  it('calls onCancel when cancel button clicked', () => {
    const onCancel = jest.fn();
    render(<BookingCard booking={mockBooking} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));

    expect(onCancel).toHaveBeenCalledWith('123');
  });
});
```

---

## Accessibility in Components

Every component must be accessible:

```typescript
// Button component with proper accessibility
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export function Button({
  children,
  variant = 'default',
  size = 'default',
  loading = false,
  disabled,
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading}
      {...props}
    >
      {loading && <Spinner className="mr-2 h-4 w-4" />}
      {children}
    </button>
  );
}
```

---

## Related Documents

- [Hooks](hooks.md) — Custom hook patterns
- [Accessibility](accessibility.md) — WCAG compliance
- [State Management](state-management.md) — Server vs. client state
