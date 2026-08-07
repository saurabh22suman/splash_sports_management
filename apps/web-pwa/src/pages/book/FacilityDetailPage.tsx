import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, EmptyState, ErrorState, LoadingSkeleton } from "@splashh/ui";
import { useFacility, useResources } from "@/features/facilities/useFacilities";
import { BookingDialog } from "@/features/bookings/BookingDialog";

export function FacilityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const facility = useFacility(id);
  const resources = useResources(id);
  const [bookingResource, setBookingResource] = useState<string | null>(null);

  if (facility.isLoading) {
    return (
      <div className="container py-6">
        <LoadingSkeleton withCard lines={3} />
      </div>
    );
  }

  if (facility.error) {
    return (
      <div className="container py-6">
        <ErrorState
          title="Could not load facility"
          description="Try again in a moment."
          onRetry={() => facility.refetch()}
        />
      </div>
    );
  }

  if (!facility.data) {
    return (
      <div className="container py-6">
        <EmptyState
          title="Facility not found"
          description="It may have been removed. Try browsing all facilities."
          action={{ label: "Browse facilities", to: "/book" }}
        />
      </div>
    );
  }

  const f = facility.data;
  return (
    <div className="container py-6">
      <h1 className="text-2xl font-semibold">{f.name}</h1>
      <p className="text-sm text-muted-foreground">
        {f.address_line1}, {f.city} {f.state}
      </p>
      <h2 className="mt-6 text-lg font-medium">Resources</h2>
      {resources.isLoading && <LoadingSkeleton />}
      {resources.error && (
        <ErrorState
          title="Could not load resources"
          onRetry={() => resources.refetch()}
        />
      )}
      {!resources.isLoading && !resources.error && resources.data?.length === 0 && (
        <EmptyState title="No resources yet" description="This facility has no bookable resources." />
      )}
      {!resources.isLoading && !resources.error && (resources.data?.length ?? 0) > 0 && (
        <ul className="mt-2 grid gap-3 sm:grid-cols-2">
          {resources.data!.map((r) => (
            <li key={r.id}>
              <Card>
                <CardHeader>
                  <CardTitle as="h3" className="text-base">{r.name}</CardTitle>
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
      )}
      {bookingResource && (
        <BookingDialog resourceId={bookingResource} onClose={() => setBookingResource(null)} />
      )}
    </div>
  );
}
