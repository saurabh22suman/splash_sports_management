import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@splashh/ui";
import { Link } from "react-router-dom";
import { useFacilities } from "@/features/facilities/useFacilities";

export function FacilitiesPage() {
  const { data, isLoading, error } = useFacilities();
  if (isLoading) return <div className="p-6">Loading…</div>;
  if (error) return <div className="p-6 text-destructive">Failed to load facilities.</div>;
  return (
    <main className="container py-6">
      <h1 className="mb-4 text-2xl font-semibold">Facilities</h1>
      {data?.length === 0 && <p className="text-muted-foreground">No facilities yet.</p>}
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.map((f) => (
          <li key={f.id}>
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">{f.name}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {f.city}, {f.state}
              </CardContent>
              <CardFooter>
                <Link to={`/facilities/${f.id}`} className="text-sm text-primary hover:underline">
                  View details →
                </Link>
              </CardFooter>
            </Card>
          </li>
        ))}
      </ul>
    </main>
  );
}
