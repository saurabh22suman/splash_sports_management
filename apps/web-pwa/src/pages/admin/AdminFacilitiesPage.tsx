import { ConfirmDialog } from "@/components/ConfirmDialog";
import {
  useAdminFacilities,
  useDeactivateFacility,
} from "@/features/admin/facilities/useAdminFacilities";
import type { Facility } from "@splashh/api-client";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Clock,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  MapPin,
} from "@splashh/ui";
import { useState } from "react";
import { Link } from "react-router-dom";

export function AdminFacilitiesPage() {
  const { data, isLoading, error } = useAdminFacilities();
  const deactivate = useDeactivateFacility();
  const [confirmDelete, setConfirmDelete] = useState<Facility | null>(null);

  return (
    <div className="container py-6">
      <header className="mb-6 flex items-end justify-between gap-3 border-b-2 border-border pb-3">
        <div>
          <p className="font-display text-[10px] uppercase tracking-[0.18em] text-volt">Manage</p>
          <h1 className="font-display text-3xl font-bold uppercase tracking-tight">Facilities</h1>
        </div>
        <Button asChild>
          <Link to="/admin/facilities/new">+ New facility</Link>
        </Button>
      </header>

      {isLoading && <LoadingSkeleton withCard lines={3} />}
      {error && (
        <ErrorState title="Could not load facilities" description="Try again in a moment." />
      )}
      {!isLoading && !error && data?.length === 0 && (
        <EmptyState
          title="No facilities yet"
          description="Add your first facility to start accepting bookings."
          action={{ label: "Create facility", to: "/admin/facilities/new" }}
        />
      )}
      {!isLoading && !error && (data?.length ?? 0) > 0 && (
        <ul className="grid gap-3 md:grid-cols-2">
          {data?.map((f, idx) => (
            <li
              key={f.id}
              className="animate-rise-up motion-reduce:animate-none"
              style={{ animationDelay: `${Math.min(idx * 80, 480)}ms` }}
            >
              <Card className="group h-full transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-volt-md hover:border-primary/40">
                <CardHeader>
                  <CardTitle className="text-lg">
                    <Link
                      to={`/admin/facilities/${f.id}`}
                      className="inline-flex items-center gap-2 transition-colors duration-200 group-hover:text-primary"
                    >
                      <span className="lane-underline">{f.name}</span>
                    </Link>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-muted-foreground">
                  <p className="inline-flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5 text-primary/60" aria-hidden="true" />
                    {f.city}, {f.state}
                  </p>
                  <p className="inline-flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5 text-primary/60" aria-hidden="true" />
                    {f.timezone}
                  </p>
                  <p className="font-mono text-[10px] uppercase tracking-widest">
                    Slug: {f.slug} · Status: {f.status}
                  </p>
                </CardContent>
                <CardContent className="flex justify-end gap-2">
                  <Button variant="outline" size="sm" asChild>
                    <Link to={`/admin/facilities/${f.id}`}>Manage</Link>
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setConfirmDelete(f)}
                    disabled={f.status === "inactive"}
                  >
                    Deactivate
                  </Button>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={!!confirmDelete}
        title="Deactivate facility?"
        description={`${confirmDelete?.name ?? ""} will be hidden from booking flows.`}
        confirmLabel="Deactivate facility"
        destructive
        isPending={deactivate.isPending}
        onClose={() => setConfirmDelete(null)}
        onConfirm={async () => {
          if (confirmDelete) {
            await deactivate.mutateAsync(confirmDelete.id);
            setConfirmDelete(null);
          }
        }}
      />
    </div>
  );
}
