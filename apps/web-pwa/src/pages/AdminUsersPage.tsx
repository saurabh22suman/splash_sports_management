import { useState, useEffect } from "react";
import { Button, Card, CardContent, CardHeader, CardTitle, FormField, Input } from "@splashh/ui";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useUsers, useCreateUser } from "@/features/admin/users/useUsers";
import type { CreateUserInput } from "@/features/admin/users/api";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  full_name: z.string().min(1, "Name is required"),
  password: z.string().min(12, "At least 12 characters"),
  role_customer: z.boolean().default(false),
  role_staff: z.boolean().default(false),
});
type FormData = z.infer<typeof schema>;

function AddUserForm({ onCreated }: { onCreated: () => void }) {
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { role_customer: true, role_staff: false } });
  const create = useCreateUser();
  const [roleError, setRoleError] = useState<string | null>(null);

  const roleValues = watch(["role_customer", "role_staff"]);

  useEffect(() => {
    if (roleValues[0] || roleValues[1]) {
      setRoleError(null);
    }
  }, [roleValues]);

  const onSubmit = handleSubmit(async (data) => {
    const roles: CreateUserInput["roles"] = [];
    if (data.role_customer) roles.push("customer");
    if (data.role_staff) roles.push("staff");
    if (roles.length === 0) {
      setRoleError("Select at least one role");
      return;
    }
    try {
      await create.mutateAsync({
        email: data.email,
        full_name: data.full_name,
        password: data.password,
        roles,
      });
      reset();
      onCreated();
    } catch {
      /* surfaced via mutation state */
    }
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Add user</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-3">
          <FormField label="Email" htmlFor="u-email" error={errors.email?.message}>
            <Input id="u-email" type="email" {...register("email")} />
          </FormField>
          <FormField label="Full name" htmlFor="u-name" error={errors.full_name?.message}>
            <Input id="u-name" {...register("full_name")} />
          </FormField>
          <FormField label="Temporary password" htmlFor="u-pw" error={errors.password?.message}>
            <Input id="u-pw" type="password" {...register("password")} />
          </FormField>
          <fieldset className="space-y-1">
            <legend className="text-sm font-medium">Roles</legend>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" {...register("role_customer")} /> Customer
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" {...register("role_staff")} /> Staff
            </label>
            {roleError && (
              <p role="alert" className="text-sm text-destructive">
                {roleError}
              </p>
            )}
          </fieldset>
          {create.error && (
            <p role="alert" className="text-sm text-destructive">
              {(create.error as Error).message}
            </p>
          )}
          <Button type="submit" size="sm" disabled={isSubmitting || create.isPending}>
            {create.isPending ? "Adding..." : "Add user"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export function AdminUsersPage() {
  const { data, isLoading, error } = useUsers();
  const [adding, setAdding] = useState(false);

  return (
    <div className="container py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Users</h1>
        <Button onClick={() => setAdding((s) => !s)}>{adding ? "Close" : "+ Add user"}</Button>
      </div>
      {adding && <div className="mb-4"><AddUserForm onCreated={() => setAdding(false)} /></div>}
      {isLoading && <p>Loading...</p>}
      {error && <p className="text-destructive">Failed to load users.</p>}
      <Card>
        <CardHeader><CardTitle className="text-base">All users</CardTitle></CardHeader>
        <CardContent>
          {data?.length === 0 && <p className="text-sm text-muted-foreground">No users yet.</p>}
          <ul className="divide-y">
            {data?.map((u) => (
              <li key={u.id} className="flex items-center justify-between py-2 text-sm">
                <span>
                  {u.email} · {u.full_name}
                </span>
                <span className="text-muted-foreground">{u.roles.join(", ")}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
