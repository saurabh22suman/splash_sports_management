import { useFacilities } from "@/features/facilities/useFacilities";
import {
  ArrowRight,
  Button,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  cn,
} from "@splashh/ui";
import { Link } from "react-router-dom";

export function FacilitiesPage() {
  const { data, isLoading, error, refetch } = useFacilities();

  return (
    <div className="container py-6">
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
          {data?.map((f, index) => (
            <li key={f.id}>
              <Card className={cn("h-full flex flex-col transition-shadow hover:shadow-volt-sm")}>
                <CardHeader className="pb-2">
                  <CardTitle as="h2" className="text-lg">
                    {f.name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 text-sm text-muted-foreground space-y-2">
                  <p>
                    {f.city}
                    {f.state && `, ${f.state}`}
                    {f.country && `, ${f.country}`}
                  </p>
                  <p className="text-xs text-muted-foreground/80">
                    Tap to view pools, courts and slots.
                  </p>
                </CardContent>
                <CardFooter>
                  <Button asChild variant={index === 0 ? "default" : "outline"} className="w-full">
                    <Link
                      to={`/book/facilities/${f.id}`}
                      className="flex items-center justify-center gap-2"
                    >
                      View details
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </Button>
                </CardFooter>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
