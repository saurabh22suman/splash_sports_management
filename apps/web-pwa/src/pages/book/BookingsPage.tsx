import { useRef, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  StatusPill,
} from "@splashh/ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@splashh/api-client";
import { bookingsApi } from "@/features/bookings/api";
import { useBookingsByCustomer } from "@/features/bookings/useBookings";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

function CancelConfirmDialog({
  bookingId,
  bookingLabel,
  open,
  onClose,
  onConfirm,
  isPending,
}: {
  bookingId: string;
  bookingLabel: string;
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isPending: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  // Sync open prop → native dialog state.
  if (open && ref.current && !ref.current.open) ref.current.showModal();
  if (!open && ref.current?.open) ref.current.close();

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-labelledby="cancel-title"
      className="m-auto max-w-md border-2 border-destructive bg-card p-6 shadow-volt-lg text-foreground backdrop:bg-black/60"
    >
      <h2 id="cancel-title" className="font-display text-2xl font-bold uppercase tracking-tight">
        Cancel booking?
      </h2>
      <p className="mt-3 text-sm text-muted-foreground">
        You're about to cancel <strong className="text-foreground">{bookingLabel}</strong>. This cannot be undone.
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <Button variant="ghost" type="button" onClick={onClose} disabled={isPending}>
          Keep booking
        </Button>
        <Button
          variant="destructive"
          type="button"
          onClick={onConfirm}
          disabled={isPending}
          data-booking-id={bookingId}
        >
          {isPending ? "Cancelling…" : "Cancel booking"}
        </Button>
      </div>
    </dialog>
  );
}

function CancelButton({ booking }: { booking: { id: string; facility_name?: string | null; resource_name?: string | null; start_at: string } }) {
  const qc = useQueryClient();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const cancel = useMutation({
    mutationFn: () => bookingsApi.cancel(booking.id, "customer_request"),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["bookings"] });
    },
  });
  const label = `${booking.facility_name ?? "Facility"} · ${booking.resource_name ?? "Slot"} · ${formatDateTime(booking.start_at)}`;
  return (
    <>
      <Button variant="destructive" size="sm" onClick={() => setConfirmOpen(true)}>
        Cancel
      </Button>
      {cancel.error && (
        <p role="alert" className="mt-1 text-xs text-destructive">
          Something went wrong. Please try again, or contact your club if the problem continues.
        </p>
      )}
      <CancelConfirmDialog
        bookingId={booking.id}
        bookingLabel={label}
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => {
          cancel.mutate();
          setConfirmOpen(false);
        }}
        isPending={cancel.isPending}
      />
    </>
  );
}

export function BookingsPage() {
  const customerId = useAuthStore((s) => s.customerId);
  const { data, isLoading, error, refetch } = useBookingsByCustomer(customerId);

  return (
    <div className="container py-6">
      <header className="mb-6 flex items-end justify-between gap-3 border-b-2 border-border pb-3">
        <div>
          <p className="font-display text-[10px] uppercase tracking-[0.18em] text-volt">Your bookings</p>
          <h1 className="font-display text-3xl font-bold uppercase tracking-tight">My bookings</h1>
        </div>
      </header>

      {isLoading && <LoadingSkeleton withCard lines={3} />}
      {error && (
        <ErrorState
          title="Could not load your bookings"
          description="Try again in a moment."
          onRetry={() => refetch()}
        />
      )}
      {!isLoading && !error && data?.length === 0 && (
        <EmptyState
          title="No bookings yet"
          description="Browse facilities and book your first slot."
          action={{ label: "Browse facilities", to: "/book" }}
        />
      )}
      {!isLoading && !error && (data?.length ?? 0) > 0 && (
        <ul className="space-y-3">
          {data!.map((b) => (
            <li key={b.id}>
              <Card>
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-display text-[10px] uppercase tracking-[0.18em] text-volt">
                        {b.facility_name ?? "Facility"}
                      </p>
                      <CardTitle as="h2" className="text-base">
                        {b.resource_name ?? "Resource"}
                      </CardTitle>
                      <p className="mt-1 font-mono text-xs text-muted-foreground">
                        {formatDateTime(b.start_at)}
                      </p>
                    </div>
                    <StatusPill status={b.status} />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {b.price_cents === 0 ? "Free booking" : new Intl.NumberFormat("en-US", { style: "currency", currency: b.currency }).format(b.price_cents / 100)}
                  </p>
                  {b.notes && <p className="mt-1 text-xs text-muted-foreground">{b.notes}</p>}
                </CardContent>
                {b.status === "confirmed" && (
                  <CardContent>
                    <CancelButton booking={b} />
                  </CardContent>
                )}
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
