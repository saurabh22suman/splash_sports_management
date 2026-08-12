import { zodResolver } from "@hookform/resolvers/zod";
import type { Resource } from "@splashh/api-client";
import { Button, FormField, Input } from "@splashh/ui";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useUpdateResource } from "./useAdminFacilities";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  capacity: z.coerce.number().int().min(1, "At least 1"),
  attributes: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

function attributesToText(a: Record<string, unknown> | undefined): string {
  if (!a || Object.keys(a).length === 0) return "";
  return JSON.stringify(a, null, 2);
}

export function EditResourceForm({
  facilityId,
  resource,
  onSaved,
}: {
  facilityId: string;
  resource: Resource;
  onSaved?: () => void;
}) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: resource.name,
      capacity: resource.capacity,
      attributes: attributesToText(resource.attributes as Record<string, unknown>),
    },
  });
  const update = useUpdateResource(facilityId);

  useEffect(() => {
    reset({
      name: resource.name,
      capacity: resource.capacity,
      attributes: attributesToText(resource.attributes as Record<string, unknown>),
    });
  }, [resource, reset]);

  const onSubmit = handleSubmit(async (data) => {
    let attributes: Record<string, unknown> | undefined;
    const trimmed = data.attributes?.trim();
    if (trimmed) {
      try {
        attributes = JSON.parse(trimmed);
      } catch {
        attributes = { raw: trimmed };
      }
    } else {
      attributes = {};
    }
    await update.mutateAsync({
      id: resource.id,
      input: {
        name: data.name,
        capacity: data.capacity,
        attributes,
      },
    });
    onSaved?.();
  });

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="Name" htmlFor={`er-name-${resource.id}`} error={errors.name?.message}>
          <Input id={`er-name-${resource.id}`} {...register("name")} />
        </FormField>
        <FormField
          label="Capacity"
          htmlFor={`er-cap-${resource.id}`}
          error={errors.capacity?.message}
        >
          <Input id={`er-cap-${resource.id}`} type="number" min={1} {...register("capacity")} />
        </FormField>
      </div>
      <FormField
        label="Attributes (JSON)"
        htmlFor={`er-attr-${resource.id}`}
        error={errors.attributes?.message}
      >
        <Input
          id={`er-attr-${resource.id}`}
          placeholder='{"surface":"clay"}'
          {...register("attributes")}
        />
      </FormField>
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        Slug: {resource.slug} · Type: {resource.resource_type} · Status: {resource.status}
      </p>

      {update.error && (
        <p
          role="alert"
          className="border-2 border-destructive bg-destructive/10 p-3 text-sm text-destructive"
        >
          {(update.error as Error).message}
        </p>
      )}

      <div className="flex justify-end border-t-2 border-border pt-3">
        <Button type="submit" disabled={isSubmitting || update.isPending || !isDirty}>
          {update.isPending ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </form>
  );
}
