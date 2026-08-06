import { Button, Card, CardContent, CardHeader, CardTitle } from "@splashh/ui";
import { Link } from "react-router-dom";
import { useAdminFacilities } from "@/features/admin/facilities/useAdminFacilities";

export function AdminFacilitiesPage() {
  const { data, isLoading, error } = useAdminFacilities();
  return (
    <main className="container py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Facilities</h1>
        <Button asChild>
          <Link to="/admin/facilities/new">+ New facility</Link>
        </Button>
      </div>
      {isLoading && <p>Loading…</p>}
      {error && <p className="text-destructive">Failed to load facilities.</p>}
      <ul className="space-y-3">
        {data?.map((f) => (
          <li key={f.id}>
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">
                  <Link to={`/admin/facilities/${f.id}`} className="hover:underline">
                    {f.name}
                  </Link>
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {f.city}, {f.state} · {f.timezone}
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </main>
  );
}
