import { zodResolver } from "@hookform/resolvers/zod";
import { Button, Card, CardContent, CardHeader, CardTitle, FormField, Input } from "@splashh/ui";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { useCreateFacility } from "./useAdminFacilities";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  slug: z
    .string()
    .min(1, "Slug is required")
    .regex(/^[a-z0-9-]+$/, "Lowercase letters, digits, hyphens only"),
  address_line1: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  postal_code: z.string().optional(),
  country: z.string().optional(),
  timezone: z.string().min(1, "Timezone is required"),
  phone: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

export function NewFacilityForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });
  const create = useCreateFacility();
  const navigate = useNavigate();

  const onSubmit = handleSubmit(async (data) => {
    const result = await create.mutateAsync(data as FormData & { timezone: string });
    navigate(`/admin/facilities/${result.id}`);
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">New facility</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <FormField label="Name" htmlFor="name" error={errors.name?.message}>
            <Input id="name" {...register("name")} />
          </FormField>
          <FormField label="Slug" htmlFor="slug" error={errors.slug?.message}>
            <Input id="slug" {...register("slug")} />
          </FormField>
          <FormField label="Address" htmlFor="address_line1">
            <Input id="address_line1" {...register("address_line1")} />
          </FormField>
          <div className="grid gap-4 sm:grid-cols-3">
            <FormField label="City" htmlFor="city">
              <Input id="city" {...register("city")} />
            </FormField>
            <FormField label="State" htmlFor="state">
              <Input id="state" {...register("state")} />
            </FormField>
            <FormField label="Postal code" htmlFor="postal_code">
              <Input id="postal_code" {...register("postal_code")} />
            </FormField>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Country" htmlFor="country">
              <Input id="country" {...register("country")} />
            </FormField>
            <FormField label="Timezone" htmlFor="timezone" error={errors.timezone?.message}>
              <Input id="timezone" placeholder="Australia/Sydney" {...register("timezone")} />
            </FormField>
          </div>
          <FormField label="Phone" htmlFor="phone">
            <Input id="phone" {...register("phone")} />
          </FormField>
          {create.error && (
            <p role="alert" className="text-sm text-destructive">
              {(create.error as Error).message}
            </p>
          )}
          <Button type="submit" disabled={isSubmitting || create.isPending}>
            {create.isPending ? "Creating…" : "Create facility"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
