import { Card, CardContent, CardFooter, CardHeader, CardTitle, EmptyState, ErrorState, LoadingSkeleton } from "@splashh/ui";
import { Link } from "react-router-dom";
import { useFacilities } from "@/features/facilities/useFacilities";

export function FacilitiesPage() {
  const { data, isLoading, error, refetch } = useFacilities();

  return (
    <main className="container py-6">
      <h1 className="mb-4 text-2xl font-semibold">Facilities</h1>
      {isLoading && <LoadingSkeleton withCard lines={3} />}
      {error && (
        <ErrorState
          title="Could not load facilities"
          description="Try again in a moment."
          onRetry={() => refetch()}
        />
      )}
      {!isLoading && !error && data?.length === 0 && (
        <EmptyState
          title="No facilities yet"
          description="When your club adds facilities, they'll show up here."
        />
      )}
      {!isLoading && !error && (data?.length ?? 0) > 0 && (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data!.map((f) => (
            <li key={f.id}>
              <Card className="h-full">
                <CardHeader>
                  <CardTitle as="h2" className="text-lg">{f.name}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {f.city}, {f.state}
                </CardContent>
                <CardFooter>
                  <Link
                    to={`/book/facilities/${f.id}`}
                    className="text-sm text-primary hover:underline"
                  >
                    View details →
                  </Link>
                </CardFooter>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
