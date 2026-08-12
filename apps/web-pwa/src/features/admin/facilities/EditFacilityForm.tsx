import { zodResolver } from "@hookform/resolvers/zod";
import type { Facility } from "@splashh/api-client";
import { Button, FormField, Input } from "@splashh/ui";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useUpdateFacility } from "./useAdminFacilities";

const schema = z.object({
  name: z.string().min(2, "Name is required (2+ chars)"),
  address_line1: z.string().optional(),
  address_line2: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  postal_code: z.string().optional(),
  country: z.string().optional(),
  timezone: z.string().min(1, "Timezone is required"),
  phone: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

export function EditFacilityForm({
  facility,
  onSaved,
}: {
  facility: Facility;
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
      name: facility.name,
      address_line1: facility.address_line1 ?? "",
      address_line2: facility.address_line2 ?? "",
      city: facility.city ?? "",
      state: facility.state ?? "",
      postal_code: facility.postal_code ?? "",
      country: facility.country ?? "",
      timezone: facility.timezone ?? "Asia/Kolkata",
      phone: facility.phone ?? "",
    },
  });
  const update = useUpdateFacility();

  // Re-seed the form if the facility prop changes (e.g. after a refresh).
  useEffect(() => {
    reset({
      name: facility.name,
      address_line1: facility.address_line1 ?? "",
      address_line2: facility.address_line2 ?? "",
      city: facility.city ?? "",
      state: facility.state ?? "",
      postal_code: facility.postal_code ?? "",
      country: facility.country ?? "",
      timezone: facility.timezone ?? "Asia/Kolkata",
      phone: facility.phone ?? "",
    });
  }, [facility, reset]);

  const onSubmit = handleSubmit(async (data) => {
    await update.mutateAsync({
      id: facility.id,
      input: {
        name: data.name,
        address_line1: data.address_line1 || undefined,
        address_line2: data.address_line2 || null,
        city: data.city || undefined,
        state: data.state || undefined,
        postal_code: data.postal_code || undefined,
        country: data.country || undefined,
        timezone: data.timezone,
        phone: data.phone || null,
      },
    });
    onSaved?.();
  });

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <FormField label="Name" htmlFor="edit-name" error={errors.name?.message}>
        <Input id="edit-name" {...register("name")} />
      </FormField>
      <FormField label="Address line 1" htmlFor="edit-address1">
        <Input id="edit-address1" {...register("address_line1")} />
      </FormField>
      <FormField label="Address line 2" htmlFor="edit-address2">
        <Input id="edit-address2" {...register("address_line2")} />
      </FormField>
      <div className="grid gap-4 sm:grid-cols-3">
        <FormField label="City" htmlFor="edit-city">
          <Input id="edit-city" {...register("city")} />
        </FormField>
        <FormField label="State" htmlFor="edit-state">
          <Input id="edit-state" {...register("state")} />
        </FormField>
        <FormField label="Postal code" htmlFor="edit-postal">
          <Input id="edit-postal" {...register("postal_code")} />
        </FormField>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <FormField label="Country (ISO)" htmlFor="edit-country">
          <Input id="edit-country" placeholder="AU" maxLength={2} {...register("country")} />
        </FormField>
        <FormField label="Timezone" htmlFor="edit-timezone" error={errors.timezone?.message}>
          <Input id="edit-timezone" placeholder="Australia/Sydney" {...register("timezone")} />
        </FormField>
        <FormField label="Phone" htmlFor="edit-phone">
          <Input id="edit-phone" {...register("phone")} />
        </FormField>
      </div>
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        Slug: {facility.slug} · Status: {facility.status}
      </p>

      {update.error && (
        <p
          role="alert"
          className="border-2 border-destructive bg-destructive/10 p-3 text-sm text-destructive"
        >
          {(update.error as Error).message}
        </p>
      )}

      <div className="flex justify-end gap-2 border-t-2 border-border pt-4">
        <Button type="submit" disabled={isSubmitting || update.isPending || !isDirty}>
          {update.isPending ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </form>
  );
}
