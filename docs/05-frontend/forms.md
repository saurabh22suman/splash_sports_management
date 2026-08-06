# Forms

> React Hook Form + Zod. Single source of truth schema. Performance optimization. Multi-step forms. Async validation.

This document establishes patterns for building forms in the Splashh Sports Platform. We use **React Hook Form** for form state management and **Zod** for schema validation.

---

## Schema as Single Source of Truth

> **Rule** — Define form schemas in Zod. Use them for both client validation and API contract.

```typescript
// features/booking/schemas/booking.schema.ts
import { z } from 'zod';

export const bookingSchema = z.object({
  facilityId: z.string().uuid('Invalid facility'),
  date: z.string().refine((d) => !isNaN(Date.parse(d)), 'Invalid date'),
  startTime: z.string().regex(/^\d{2}:\d{2}$/, 'Invalid time format'),
  duration: z.number().min(30).max(240), // 30min - 4 hours
  sportId: z.string().uuid('Select a sport'),
  notes: z.string().max(500).optional(),
  guests: z.array(guestSchema).max(10).optional(),
});

// TypeScript inference
export type BookingFormData = z.infer<typeof bookingSchema>;

// API validation (reusing the same schema)
export async function createBooking(data: BookingFormData) {
  // Zod validation happens on server too
  const result = bookingSchema.safeParse(data);
  if (!result.success) {
    throw new ValidationError(result.error);
  }
  return api.post('/bookings', data);
}
```

---

## Basic Form Implementation

```typescript
// features/booking/components/BookingForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { bookingSchema, type BookingFormData } from '../schemas/booking.schema';
import { useCreateBooking } from '../hooks/useBooking';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/Form';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';

export function BookingForm({ facilityId }: { facilityId: string }) {
  const createBooking = useCreateBooking();

  const form = useForm<BookingFormData>({
    resolver: zodResolver(bookingSchema),
    defaultValues: {
      facilityId,
      date: '',
      startTime: '',
      duration: 60,
      sportId: '',
      notes: '',
    },
  });

  const onSubmit = (data: BookingFormData) => {
    createBooking.mutate(data, {
      onSuccess: () => {
        form.reset();
      },
    });
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="date"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Date</FormLabel>
              <FormControl>
                <Input type="date" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="startTime"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Time</FormLabel>
              <FormControl>
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select time" />
                  </SelectTrigger>
                  <SelectContent>
                    {timeSlots.map((slot) => (
                      <SelectItem key={slot} value={slot}>
                        {slot}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="sportId"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Sport</FormLabel>
              <FormControl>
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select sport" />
                  </SelectTrigger>
                  <SelectContent>
                    {sports.map((sport) => (
                      <SelectItem key={sport.id} value={sport.id}>
                        {sport.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="duration"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Duration (minutes)</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  min={30}
                  max={240}
                  step={30}
                  {...field}
                  onChange={(e) => field.onChange(Number(e.target.value))}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button
          type="submit"
          disabled={createBooking.isPending}
        >
          {createBooking.isPending ? 'Creating...' : 'Create Booking'}
        </Button>
      </form>
    </Form>
  );
}
```

---

## Performance: No Re-render on Every Keystroke

> **Rule** — Use controlled inputs with RHF. Avoid component-level re-renders.

React Hook Form uses uncontrolled components by default, but our shadcn/ui integration uses controlled components. Use `mode: 'onBlur'` or debounce for expensive operations:

```typescript
const form = useForm<BookingFormData>({
  resolver: zodResolver(bookingSchema),
  mode: 'onBlur',        // Validate on blur, not every keystroke
  reValidateMode: 'onChange', // Re-validate on change after first submit
});
```

### Debounced Fields

For fields requiring expensive validation (e.g., availability checks):

```typescript
// hooks/useDebouncedFormField.ts
export function useDebouncedField<T extends FieldValues>(
  control: UseFormReturn<T>['control'],
  name: FieldPath<T>,
  delay: number = 300
) {
  const [debouncedValue, setDebouncedValue] = useState('');

  // Watch the field value
  const value = useWatch({ control, name });

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(String(value || ''));
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Usage in form
function CheckAvailability() {
  const form = useFormContext();
  const debouncedDate = useDebouncedField(form.control, 'date');

  const { data: availability } = useQuery({
    queryKey: ['availability', debouncedDate],
    queryFn: () => checkAvailability(debouncedDate),
    enabled: debouncedDate.length > 0,
  });

  return <div>Available slots: {availability?.slots.length}</div>;
}
```

---

## Field Arrays

```typescript
// Booking with guests
const bookingWithGuestsSchema = bookingSchema.extend({
  guests: z.array(
    z.object({
      name: z.string().min(2, 'Name required'),
      email: z.string().email('Invalid email'),
      phone: z.string().optional(),
    })
  ).max(10, 'Maximum 10 guests'),
});

type BookingWithGuests = z.infer<typeof bookingWithGuestsSchema>;

function BookingWithGuestsForm() {
  const form = useForm<BookingWithGuests>({
    resolver: zodResolver(bookingWithGuestsSchema),
    defaultValues: {
      guests: [{ name: '', email: '', phone: '' }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'guests',
  });

  return (
    <>
      {fields.map((field, index) => (
        <div key={field.id} className="flex gap-2">
          <FormField
            control={form.control}
            name={`guests.${index}.name` as const}
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <Input placeholder="Guest name" {...field} />
                </Control>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name={`guests.${index}.email` as const}
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <Input placeholder="Email" type="email" {...field} />
                </Control>
              </FormItem>
            )}
          />
          <Button type="button" variant="destructive" onClick={() => remove(index)}>
            Remove
          </Button>
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        onClick={() => append({ name: '', email: '', phone: '' })}
      >
        Add Guest
      </Button>
    </>
  );
}
```

---

## Multi-Step Forms

```typescript
// components/BookingWizard.tsx
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { bookingSchema, type BookingFormData } from '../schemas/booking.schema';

type Step = 'facility' | 'datetime' | 'details' | 'review';

const STEPS: Step[] = ['facility', 'datetime', 'details', 'review'];

export function BookingWizard() {
  const [currentStep, setCurrentStep] = useState<Step>('facility');

  const form = useForm<BookingFormData>({
    resolver: zodResolver(bookingSchema),
    mode: 'onBlur',
  });

  const currentStepIndex = STEPS.indexOf(currentStep);

  const next = async () => {
    const fields = getFieldsForStep(currentStep);
    const isValid = await form.trigger(fields);

    if (isValid) {
      setCurrentStep(STEPS[currentStepIndex + 1]);
    }
  };

  const back = () => {
    setCurrentStep(STEPS[currentStepIndex - 1]);
  };

  return (
    <div>
      <StepIndicator current={currentStep} steps={STEPS} />

      {currentStep === 'facility' && <FacilityStep form={form} />}
      {currentStep === 'datetime' && <DateTimeStep form={form} />}
      {currentStep === 'details' && <DetailsStep form={form} />}
      {currentStep === 'review' && <ReviewStep form={form} />}

      <div className="flex gap-4">
        {currentStepIndex > 0 && <Button onClick={back}>Back</Button>}
        {currentStepIndex < STEPS.length - 1 && (
          <Button onClick={next}>Next</Button>
        )}
        {currentStepIndex === STEPS.length - 1 && (
          <Button type="submit">Complete Booking</Button>
        )}
      </div>
    </div>
  );
}

function getFieldsForStep(step: Step): (keyof BookingFormData)[] {
  switch (step) {
    case 'facility':
      return ['facilityId', 'sportId'];
    case 'datetime':
      return ['date', 'startTime', 'duration'];
    case 'details':
      return ['notes'];
    default:
      return [];
  }
}
```

---

## Async Validation

```typescript
// Custom async validator for facility availability
const facilityAvailableSchema = bookingSchema.extend({
  facilityId: z.string().uuid().refine(
    async (facilityId, ctx) => {
      const { date, startTime, duration } = ctx.parent;
      if (!date || !startTime) return true; // Let required validation handle this

      const isAvailable = await checkFacilityAvailability({
        facilityId,
        date,
        startTime,
        duration,
      });

      return isAvailable || 'This time slot is no longer available';
    },
    { message: 'Time slot not available' }
  ),
});
```

---

## Server Error Mapping

Map API errors back to form fields:

```typescript
function BookingForm() {
  const createBooking = useCreateBooking();

  const form = useForm<BookingFormData>({
    resolver: zodResolver(bookingSchema),
  });

  const onSubmit = async (data: BookingFormData) => {
    try {
      await createBooking.mutateAsync(data);
    } catch (error) {
      if (error instanceof ApiError && error.response?.status === 422) {
        // Map server errors to form fields
        const fieldErrors = error.response.data.detail;

        // Example: { field_errors: { date: 'Date must be in the future' } }
        if (fieldErrors) {
          Object.entries(fieldErrors).forEach(([field, message]) => {
            form.setError(field as keyof BookingFormData, {
              type: 'server',
              message: message as string,
            });
          });
        }
      }
    }
  };

  return <Form {...form}>...</Form>;
}
```

---

## Testing Forms

```typescript
// BookingForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BookingForm } from './BookingForm';

describe('BookingForm', () => {
  it('shows validation errors for invalid input', async () => {
    render(<BookingForm facilityId="123" />);

    fireEvent.submit(screen.getByRole('form'));

    await waitFor(() => {
      expect(screen.getByText('Invalid date')).toBeInTheDocument();
    });
  });

  it('calls createBooking on valid submit', async () => {
    const mockCreate = jest.fn();
    jest.mocked(useCreateBooking).mockReturnValue({
      mutate: mockCreate,
      isPending: false,
    });

    render(<BookingForm facilityId="123" />);

    fireEvent.change(screen.getByLabelText(/date/i), {
      target: { value: '2024-12-01' },
    });
    fireEvent.change(screen.getByLabelText(/time/i), {
      target: { value: '10:00' },
    });
    fireEvent.change(screen.getByLabelText(/sport/i), {
      target: { value: 'tennis-id' },
    });

    fireEvent.submit(screen.getByRole('form'));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          facilityId: '123',
          date: '2024-12-01',
          startTime: '10:00',
          sportId: 'tennis-id',
        })
      );
    });
  });
});
```

---

## Trade-offs

| Approach | When to use | Trade-offs |
|----------|-------------|------------|
| Uncontrolled | Simple forms, max performance | Hard to integrate with UI libraries |
| Controlled + onBlur | Most forms | Slight re-render overhead |
| Controlled + debounce | Expensive validation | Added complexity |
| Multi-step | Complex flows | More state management |
| Field arrays | Dynamic fields | Complex validation |

---

## Related Documents

- [Hooks](hooks.md) — Custom hook patterns
- [Zod Integration](https://zod.dev) — Zod schema reference
- [React Hook Form](https://react-hook-form.com) — RHF documentation
