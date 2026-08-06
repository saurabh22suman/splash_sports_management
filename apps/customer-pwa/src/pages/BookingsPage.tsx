import { Button, Card, CardContent, CardHeader, CardTitle } from "@splashh/ui";
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
      Cancel
    </Button>
  );
}

export function BookingsPage() {
  const userId = useAuthStore((s) => s.userId);
  const { data, isLoading, error } = useBookingsByCustomer(userId);
  if (isLoading) return <div className="p-6">Loading…</div>;
  if (error) return <div className="p-6 text-destructive">Failed to load bookings.</div>;
  return (
    <main className="container py-6">
      <h1 className="mb-4 text-2xl font-semibold">My bookings</h1>
      {data?.length === 0 && <p className="text-muted-foreground">No bookings yet.</p>}
      <ul className="space-y-3">
        {data?.map((b) => (
          <li key={b.id}>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{new Date(b.start_at).toLocaleString()}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Status: {b.status} · {b.price_cents / 100} {b.currency}
              </CardContent>
              <CardContent>{b.status === "confirmed" && <CancelButton id={b.id} />}</CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </main>
  );
}
