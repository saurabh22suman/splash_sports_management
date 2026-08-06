import { Button, Card, CardContent, CardHeader, CardTitle, FormField, Input } from "@splashh/ui";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useLogin } from "./useLogin";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormData = z.infer<typeof schema>;

export function LoginForm({ onSuccess }: { onSuccess: () => void }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });
  const login = useLogin();

  const onSubmit = handleSubmit(async (data) => {
    try {
      await login.mutateAsync(data);
      onSuccess();
    } catch {
      /* error surfaced via mutation */
    }
  });

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle className="text-xl">Admin log in</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <FormField label="Email" htmlFor="email" error={errors.email?.message}>
            <Input id="email" type="email" autoComplete="email" {...register("email")} />
          </FormField>
          <FormField label="Password" htmlFor="password" error={errors.password?.message}>
            <Input id="password" type="password" autoComplete="current-password" {...register("password")} />
          </FormField>
          {login.error && <p role="alert" className="text-sm text-destructive">{(login.error as Error).message || "Login failed"}</p>}
          <Button type="submit" disabled={isSubmitting || login.isPending} className="w-full">
            {login.isPending ? "Logging in…" : "Log in"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
