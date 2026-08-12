import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EditFacilityForm } from "@/features/admin/facilities/EditFacilityForm";
import { EditResourceForm } from "@/features/admin/facilities/EditResourceForm";
import { NewResourceForm } from "@/features/admin/facilities/NewResourceForm";
import {
  useAdminFacility,
  useAdminResources,
  useDeactivateFacility,
  useDeactivateResource,
} from "@/features/admin/facilities/useAdminFacilities";
import type { Resource } from "@splashh/api-client";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
} from "@splashh/ui";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

type Tab = "info" | "resources";

export function AdminFacilityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const facility = useAdminFacility(id);
  const resources = useAdminResources(id);
  const [tab, setTab] = useState<Tab>("info");
  const [editMode, setEditMode] = useState(false);
  const [addResource, setAddResource] = useState(false);
  const [editingResourceId, setEditingResourceId] = useState<string | null>(null);

  const [confirmDeleteFacility, setConfirmDeleteFacility] = useState(false);
  const [confirmDeleteResource, setConfirmDeleteResource] = useState<{
    id: string;
    name: string;
  } | null>(null);

  const deactivateFacility = useDeactivateFacility();
  const deactivateResource = useDeactivateResource(id!);

  if (facility.isLoading)
    return (
      <div className="container py-6">
        <LoadingSkeleton withCard lines={3} />
      </div>
    );
  if (facility.error || !facility.data) {
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
  const f = facility.data;

  const onDeleteFacility = async () => {
    await deactivateFacility.mutateAsync(f.id);
    setConfirmDeleteFacility(false);
    navigate("/admin");
  };

  const onDeleteResource = async (resourceId: string) => {
    await deactivateResource.mutateAsync(resourceId);
    setConfirmDeleteResource(null);
  };

  return (
    <div className="container py-6">
      <Link
        to="/admin"
        className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors duration-200 hover:text-foreground"
      >
        ← All facilities
      </Link>
      <header className="mt-2 mb-6 border-b-2 border-border pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-display text-[10px] uppercase tracking-[0.18em] text-volt">
              Facility
            </p>
            <h1 className="font-display text-3xl font-bold uppercase tracking-tight">{f.name}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {f.address_line1 ?? ""}
              {f.city ? `, ${f.city}` : ""} {f.state ?? ""} · {f.timezone}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              <span>Slug: {f.slug}</span>
              <span>·</span>
              <span>Status: {f.status}</span>
              {f.phone && (
                <>
                  <span>·</span>
                  <span>Tel: {f.phone}</span>
                </>
              )}
            </div>
          </div>
          {!editMode && tab === "info" && (
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button variant="outline" size="sm" onClick={() => setEditMode(true)}>
                Edit facility
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setConfirmDeleteFacility(true)}
              >
                Deactivate
              </Button>
            </div>
          )}
        </div>
      </header>

      <div role="tablist" aria-label="Facility sections" className="flex border-b-2 border-border">
        {(["info", "resources"] as Tab[]).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => {
              setTab(t);
              setEditMode(false);
              setAddResource(false);
              setEditingResourceId(null);
            }}
            className={`px-4 py-2 text-sm font-semibold uppercase tracking-[0.06em] transition-all duration-200 ease-out ${
              tab === t
                ? "border-b-2 -mb-0.5 border-volt text-volt"
                : "text-muted-foreground hover:text-foreground"
            }`}
            type="button"
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      <section className="mt-6">
        {tab === "info" &&
          (editMode ? (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Edit facility</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setEditMode(false)}>
                    Cancel
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <EditFacilityForm facility={f} onSaved={() => setEditMode(false)} />
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Facility info</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2 sm:grid-cols-2 text-sm">
                <p>
                  <span className="text-muted-foreground">Address 1:</span> {f.address_line1 ?? "—"}
                </p>
                <p>
                  <span className="text-muted-foreground">Address 2:</span> {f.address_line2 ?? "—"}
                </p>
                <p>
                  <span className="text-muted-foreground">City / State:</span> {f.city}, {f.state}
                </p>
                <p>
                  <span className="text-muted-foreground">Postal:</span> {f.postal_code}
                </p>
                <p>
                  <span className="text-muted-foreground">Country:</span> {f.country}
                </p>
                <p>
                  <span className="text-muted-foreground">Timezone:</span> {f.timezone}
                </p>
                <p>
                  <span className="text-muted-foreground">Phone:</span> {f.phone ?? "—"}
                </p>
                <p>
                  <span className="text-muted-foreground">Status:</span> {f.status}
                </p>
              </CardContent>
            </Card>
          ))}

        {tab === "resources" && (
          <div className="space-y-4">
            {!addResource && (
              <div className="flex justify-end">
                <Button onClick={() => setAddResource(true)}>+ Add resource</Button>
              </div>
            )}
            {addResource && (
              <NewResourceForm facilityId={f.id} onCreated={() => setAddResource(false)} />
            )}

            {resources.isLoading && <LoadingSkeleton withCard lines={3} />}
            {resources.error && (
              <ErrorState title="Could not load resources" onRetry={() => resources.refetch()} />
            )}
            {!resources.isLoading &&
              !resources.error &&
              resources.data?.length === 0 &&
              !addResource && (
                <EmptyState
                  title="No resources yet"
                  description="Add the lanes, courts, or rooms your club books."
                  action={{ label: "Add resource", onClick: () => setAddResource(true) }}
                />
              )}
            {!resources.isLoading && !resources.error && (resources.data?.length ?? 0) > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">
                    Resources
                    <span className="ml-2 font-mono text-xs text-muted-foreground">
                      ({resources.data?.length})
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="divide-y-2 divide-border">
                    {resources.data?.map((r: Resource) => {
                      const isEditing = editingResourceId === r.id;
                      return (
                        <li key={r.id} className="py-3 first:pt-0 last:pb-0">
                          {!isEditing ? (
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div>
                                <p className="font-display text-base font-bold uppercase tracking-tight">
                                  {r.name}
                                </p>
                                <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                                  {r.resource_type} · capacity {r.capacity} · {r.status}
                                </p>
                              </div>
                              <div className="flex gap-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => setEditingResourceId(r.id)}
                                >
                                  Edit
                                </Button>
                                <Button
                                  variant="destructive"
                                  size="sm"
                                  onClick={() =>
                                    setConfirmDeleteResource({ id: r.id, name: r.name })
                                  }
                                >
                                  Deactivate
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <div className="border-2 border-border bg-charcoal-900 p-4">
                              <div className="mb-3 flex items-center justify-between">
                                <p className="font-display text-[10px] uppercase tracking-[0.18em] text-volt">
                                  Editing resource
                                </p>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setEditingResourceId(null)}
                                >
                                  Cancel
                                </Button>
                              </div>
                              <EditResourceForm
                                facilityId={f.id}
                                resource={r}
                                onSaved={() => setEditingResourceId(null)}
                              />
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </section>

      <ConfirmDialog
        open={confirmDeleteFacility}
        title="Deactivate facility?"
        description={`${f.name} will be hidden from booking flows. You can reactivate it later from the database.`}
        confirmLabel="Deactivate facility"
        destructive
        isPending={deactivateFacility.isPending}
        onClose={() => setConfirmDeleteFacility(false)}
        onConfirm={onDeleteFacility}
      />

      <ConfirmDialog
        open={!!confirmDeleteResource}
        title="Deactivate resource?"
        description={`${confirmDeleteResource?.name ?? ""} will stop accepting new bookings.`}
        confirmLabel="Deactivate resource"
        destructive
        isPending={deactivateResource.isPending}
        onClose={() => setConfirmDeleteResource(null)}
        onConfirm={() => confirmDeleteResource && onDeleteResource(confirmDeleteResource.id)}
      />
    </div>
  );
}
