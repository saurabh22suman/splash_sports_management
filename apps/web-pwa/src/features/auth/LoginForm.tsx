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

export function LoginForm({
  onSuccess,
  mode = "customer",
  emailRef,
  headingLevel = "h3",
}: {
  onSuccess: (roles: string[]) => void;
  mode?: "customer" | "staff";
  emailRef?: React.Ref<HTMLInputElement>;
  headingLevel?: "h1" | "h2" | "h3";
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });
  const login = useLogin();

  const onSubmit = handleSubmit(async (data) => {
    try {
      const roles = await login.mutateAsync({ ...data, mode });
      onSuccess(roles);
    } catch {
      /* error surfaced via mutation */
    }
  });

  // Create email register without ref - we'll manually set up the ref
  const emailRegister = register("email");

  // Create a ref callback that also calls the register's ref
  const handleEmailRef = (el: HTMLInputElement | null) => {
    // Set the external ref
    if (typeof emailRef === "function") {
      emailRef(el);
    } else if (emailRef && "current" in emailRef) {
      (emailRef as React.MutableRefObject<HTMLInputElement | null>).current = el;
    }
    // Call the register's ref
    emailRegister.ref(el);
  };

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle as={headingLevel} className="text-xl">
          {mode === "staff" ? "Admin log in" : "Log in"}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <FormField label="Email" htmlFor="email" error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              ref={handleEmailRef}
              onChange={emailRegister.onChange}
              onBlur={emailRegister.onBlur}
              name={emailRegister.name}
              className="text-base"
              aria-invalid={errors.email ? "true" : "false"}
            />
          </FormField>
          <FormField label="Password" htmlFor="password" error={errors.password?.message}>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              className="text-base"
              aria-invalid={errors.password ? "true" : "false"}
              {...register("password")}
            />
          </FormField>
          {login.error && (
            <p role="alert" aria-live="assertive" className="text-sm text-destructive">
              {(login.error as Error).message || "Login failed"}
            </p>
          )}
          <Button type="submit" disabled={isSubmitting || login.isPending} className="w-full">
            {login.isPending ? "Logging in..." : "Log in"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
