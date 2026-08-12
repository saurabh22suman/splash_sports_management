import type { CreateUserInput } from "@/features/admin/users/api";
import { useCreateUser, useUsers } from "@/features/admin/users/useUsers";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  FormField,
  Input,
} from "@splashh/ui";
import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

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
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { role_customer: true, role_staff: false },
  });
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
              Something went wrong. Please try again, or contact your club if the problem continues.
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

function getRoleBadgeVariant(role: string): "accent" | "default" | "muted" {
  if (role === "tenant_admin") return "accent";
  if (role === "customer") return "muted";
  return "default";
}

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(dateString));
}

export function AdminUsersPage() {
  const { data, isLoading, error } = useUsers();
  const [adding, setAdding] = useState(false);
  const [search, setSearch] = useState("");

  const filteredUsers = useMemo(() => {
    if (!data) return [];
    if (!search.trim()) return data;
    const q = search.toLowerCase();
    return data.filter(
      (u) => u.email.toLowerCase().includes(q) || u.full_name.toLowerCase().includes(q),
    );
  }, [data, search]);

  return (
    <div className="container py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Users</h1>
        <Button onClick={() => setAdding((s) => !s)}>{adding ? "Close" : "+ Add user"}</Button>
      </div>
      {adding && (
        <div className="mb-4">
          <AddUserForm onCreated={() => setAdding(false)} />
        </div>
      )}
      {isLoading && <p>Loading...</p>}
      {error && <p className="text-destructive">Failed to load users.</p>}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-end">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search by email or name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-64 pl-9"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {data && (
            <p className="text-sm text-muted-foreground mb-3">
              Showing {filteredUsers.length} of {data.length} users
            </p>
          )}
          {filteredUsers.length === 0 && search && (
            <p className="text-sm text-muted-foreground py-4">No users match your search.</p>
          )}
          {filteredUsers.length === 0 && !search && (
            <p className="text-sm text-muted-foreground">No users yet.</p>
          )}
          {filteredUsers.length > 0 && (
            <table className="w-full">
              <thead>
                <tr className="border-b text-left text-sm text-muted-foreground">
                  <th className="pb-2 font-medium">Email</th>
                  <th className="pb-2 font-medium">Full Name</th>
                  <th className="pb-2 font-medium">Role</th>
                  <th className="pb-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => (
                  <tr key={u.id} className="border-b last:border-0">
                    <td className="py-3 text-sm">{u.email}</td>
                    <td className="py-3 text-sm">{u.full_name}</td>
                    <td className="py-3">
                      <div className="flex gap-1 flex-wrap">
                        {u.roles.map((role) => (
                          <Badge key={role} variant={getRoleBadgeVariant(role)}>
                            {role}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 text-sm text-muted-foreground">
                      {formatDate(u.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
