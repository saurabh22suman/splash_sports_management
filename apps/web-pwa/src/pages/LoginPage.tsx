import { useNavigate } from "react-router-dom";
import { useEffect, useRef } from "react";
import { LoginForm } from "@/features/auth/LoginForm";
import { useAuthStore } from "@splashh/api-client";
import { homeForRoles } from "@/lib/role-routing";

export function LoginPage() {
  const navigate = useNavigate();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isAuthed) navigate(homeForRoles(roles), { replace: true });
  }, [isAuthed, roles, navigate]);

  useEffect(() => {
    emailRef.current?.focus();
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center p-4 pb-[env(safe-area-inset-bottom)]">
      <LoginForm
        mode="customer"
        headingLevel="h1"
        emailRef={emailRef}
        onSuccess={(roles) => navigate(homeForRoles(roles), { replace: true })}
      />
    </main>
  );
}
