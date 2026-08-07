import { Button, Card, CardContent, CardHeader, CardTitle, EmptyState, ErrorState, LoadingSkeleton } from "@splashh/ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@splashh/api-client";
import { bookingsApi } from "@/features/bookings/api";
import { useBookingsByCustomer } from "@/features/bookings/useBookings";

function CancelButton({ id }: { id: string }) {
  const qc = useQueryClient();
  const cancel = useMutation({
    mutationFn: () => bookingsApi.cancel(id, "customer_request"),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["bookings"] });
    },
  });
  return (
    <Button size="sm" variant="destructive" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
      {cancel.isPending ? "Cancelling..." : "Cancel"}
    </Button>
  );
}

export function BookingsPage() {
  const userId = useAuthStore((s) => s.userId);
  const { data, isLoading, error, refetch } = useBookingsByCustomer(userId);

  return (
    <div className="container py-6">
      <h1 className="mb-4 text-2xl font-semibold">My bookings</h1>
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
                  <CardTitle as="h2" className="text-base">
                    {new Date(b.start_at).toLocaleString()}
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Status: {b.status} · {b.price_cents / 100} {b.currency}
                </CardContent>
                {b.status === "confirmed" && (
                  <CardContent>
                    <CancelButton id={b.id} />
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
