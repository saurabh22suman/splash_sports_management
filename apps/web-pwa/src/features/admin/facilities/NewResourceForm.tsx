import { Button, Card, CardContent, CardHeader, CardTitle, FormField, Input } from "@splashh/ui";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useCreateResource } from "./useAdminFacilities";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  slug: z.string().min(1, "Slug is required").regex(/^[a-z0-9-]+$/, "Lowercase letters, digits, hyphens only"),
  resource_type: z.enum(["court", "lane", "pool", "field", "net", "studio", "gym_floor", "room"]),
  capacity: z.coerce.number().int().min(1, "At least 1"),
  attributes: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

export function NewResourceForm({
  facilityId,
  onCreated,
}: {
  facilityId: string;
  onCreated?: () => void;
}) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { resource_type: "court", capacity: 4 },
  });
  const create = useCreateResource(facilityId);

  const onSubmit = handleSubmit(async (data) => {
    let attributes: Record<string, unknown> | undefined;
    if (data.attributes && data.attributes.trim()) {
      try {
        attributes = JSON.parse(data.attributes);
      } catch {
        attributes = { raw: data.attributes };
      }
    }
    await create.mutateAsync({
      name: data.name,
      slug: data.slug,
      resource_type: data.resource_type,
      capacity: data.capacity,
      attributes,
    });
    reset();
    onCreated?.();
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Add resource</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Name" htmlFor="rname" error={errors.name?.message}>
              <Input id="rname" {...register("name")} />
            </FormField>
            <FormField label="Slug" htmlFor="rslug" error={errors.slug?.message}>
              <Input id="rslug" {...register("slug")} />
            </FormField>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Type" htmlFor="rtype" error={errors.resource_type?.message}>
              <select
                id="rtype"
                {...register("resource_type")}
                className="flex h-11 w-full border-2 border-border bg-input px-4 py-2 text-sm text-foreground transition-all duration-200 ease-out focus-visible:outline-none focus-visible:border-primary focus-visible:shadow-volt-sm"
              >
                <option value="court">Court</option>
                <option value="lane">Lane</option>
                <option value="pool">Pool</option>
                <option value="field">Field</option>
                <option value="net">Net</option>
                <option value="studio">Studio</option>
                <option value="gym_floor">Gym floor</option>
                <option value="room">Room</option>
              </select>
            </FormField>
            <FormField label="Capacity" htmlFor="rcapacity" error={errors.capacity?.message}>
              <Input id="rcapacity" type="number" min={1} {...register("capacity")} />
            </FormField>
          </div>
          <FormField label="Attributes (JSON, optional)" htmlFor="rattr" error={errors.attributes?.message}>
            <Input id="rattr" placeholder='{"surface":"clay"}' {...register("attributes")} />
          </FormField>
          {create.error && (
            <p role="alert" className="border-2 border-destructive bg-destructive/10 p-3 text-sm text-destructive">
              {(create.error as Error).message}
            </p>
          )}
          <div className="flex justify-end border-t-2 border-border pt-3">
            <Button type="submit" disabled={isSubmitting || create.isPending}>
              {create.isPending ? "Adding…" : "Add resource"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
