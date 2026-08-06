import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { LoginForm } from "@/features/auth/LoginForm";
import { useAuthStore } from "@splashh/api-client";
import { homeForRoles } from "@/lib/role-routing";

export function AdminLoginPage() {
  const navigate = useNavigate();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);

  useEffect(() => {
    document.title = "Splashh Admin";
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex";
    document.head.appendChild(meta);
    return () => {
      document.head.removeChild(meta);
    };
  }, []);

  useEffect(() => {
    if (isAuthed) navigate(homeForRoles(roles), { replace: true });
  }, [isAuthed, roles, navigate]);

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <LoginForm
        mode="staff"
        onSuccess={(roles) => navigate(homeForRoles(roles), { replace: true })}
      />
    </main>
  );
}
