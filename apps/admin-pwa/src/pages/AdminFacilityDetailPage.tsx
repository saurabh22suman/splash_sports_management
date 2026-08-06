import { useState } from "react";
import { useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@splashh/ui";
import { useAdminFacility, useAdminResources } from "@/features/admin/facilities/useAdminFacilities";
import { NewResourceForm } from "@/features/admin/facilities/NewResourceForm";

type Tab = "info" | "resources" | "bookings";

export function AdminFacilityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const facility = useAdminFacility(id);
  const resources = useAdminResources(id);
  const [tab, setTab] = useState<Tab>("info");

  if (facility.isLoading) return <main className="container py-6">Loading…</main>;
  if (facility.error || !facility.data)
    return <main className="container py-6 text-destructive">Failed to load facility.</main>;
  const f = facility.data;

  return (
    <main className="container py-6">
      <h1 className="text-2xl font-semibold">{f.name}</h1>
      <p className="text-sm text-muted-foreground">
        {f.address_line1}, {f.city} {f.state} · {f.timezone}
      </p>
      <div className="mt-4 flex gap-2 border-b">
        {(["info", "resources", "bookings"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm font-medium ${
              tab === t ? "border-b-2 border-primary text-primary" : "text-muted-foreground"
            }`}
            type="button"
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      <div className="mt-6">
        {tab === "info" && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p>Slug: {f.slug}</p>
              <p>Status: {f.status}</p>
              <p>Timezone: {f.timezone}</p>
              <p>Phone: {f.phone ?? "—"}</p>
            </CardContent>
          </Card>
        )}
        {tab === "resources" && (
          <div className="space-y-4">
            <NewResourceForm facilityId={f.id} />
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Existing resources</CardTitle>
              </CardHeader>
              <CardContent>
                {resources.data?.length === 0 && <p className="text-sm text-muted-foreground">No resources yet.</p>}
                <ul className="space-y-2">
                  {resources.data?.map((r: import("@splashh/api-client").Resource) => (
                    <li key={r.id} className="flex items-center justify-between text-sm">
                      <span>
                        {r.name} · {r.resource_type} · capacity {r.capacity}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        )}
        {tab === "bookings" && <p className="text-sm text-muted-foreground">Bookings view coming soon.</p>}
      </div>
    </main>
  );
}
