import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@splashh/ui";
import { useFacility, useResources } from "@/features/facilities/useFacilities";
import { BookingDialog } from "@/features/bookings/BookingDialog";

export function FacilityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const facility = useFacility(id);
  const resources = useResources(id);
  const [bookingResource, setBookingResource] = useState<string | null>(null);

  if (facility.isLoading) return <div className="p-6">Loading…</div>;
  if (facility.error) return <div className="p-6 text-destructive">Failed to load facility.</div>;
  const f = facility.data!;
  return (
    <main className="container py-6">
      <h1 className="text-2xl font-semibold">{f.name}</h1>
      <p className="text-sm text-muted-foreground">
        {f.address_line1}, {f.city} {f.state}
      </p>
      <h2 className="mt-6 text-lg font-medium">Resources</h2>
      <ul className="mt-2 grid gap-3 sm:grid-cols-2">
        {resources.data?.map((r) => (
          <li key={r.id}>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{r.name}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Type: {r.resource_type} · Capacity: {r.capacity}
              </CardContent>
              <CardContent>
                <Button onClick={() => setBookingResource(r.id)}>Book</Button>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
      {bookingResource && (
        <BookingDialog resourceId={bookingResource} onClose={() => setBookingResource(null)} />
      )}
    </main>
  );
}
