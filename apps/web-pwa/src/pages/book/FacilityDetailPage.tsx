import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Card, CardContent, CardHeader, CardTitle, EmptyState, ErrorState, LoadingSkeleton, MapPin } from "@splashh/ui";
import { useFacility, useResources } from "@/features/facilities/useFacilities";
import { BookingDialog } from "@/features/bookings/BookingDialog";

// Helper to format resource attributes for display
function formatAttributes(attributes: Record<string, unknown> | null): string[] {
  if (!attributes) return [];
  return Object.entries(attributes)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => {
      // Convert snake_case to Title Case with spaces
      const label = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      return `${label}: ${value}`;
    });
}

export function FacilityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const facility = useFacility(id);
  const resources = useResources(id);
  const [bookingTarget, setBookingTarget] = useState<
    { id: string; name: string } | null
  >(null);

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
      <p className="flex items-center gap-1.5 text-sm text-muted-foreground mt-1">
        <MapPin className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
        <span>
          {f.address_line1}{f.address_line1 && f.city && ", "}{f.city} {f.state} {f.postal_code}
        </span>
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
          {resources.data!.map((r) => {
            const attrList = formatAttributes(r.attributes);
            return (
              <li key={r.id}>
                <Card>
                  <CardHeader>
                    <CardTitle as="h3" className="text-base">{r.name}</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground space-y-1">
                    <p>Type: {r.resource_type} · Capacity: {r.capacity}</p>
                    {attrList.length > 0 && (
                      <ul className="text-xs space-y-0.5 mt-2">
                        {attrList.slice(0, 4).map((attr, i) => (
                          <li key={i}>{attr}</li>
                        ))}
                        {attrList.length > 4 && (
                          <li className="text-muted-foreground/70">+{attrList.length - 4} more</li>
                        )}
                      </ul>
                    )}
                  </CardContent>
                  <CardContent>
                    <Button variant="default" onClick={() => setBookingTarget({ id: r.id, name: r.name })}>
                      Book
                    </Button>
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
      {bookingTarget && (
        <BookingDialog
          resourceId={bookingTarget.id}
          resourceName={bookingTarget.name}
          facilityName={f.name}
          onClose={() => setBookingTarget(null)}
        />
      )}
    </div>
  );
}
