import { useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader } from "@splashh/ui";
import { LoginForm } from "@/features/auth/LoginForm";
import { useAuthStore } from "@splashh/api-client";
import { homeForRoles } from "@/lib/role-routing";

type Mode = "customer" | "staff";

function Tab({
  id,
  selected,
  onSelect,
  children,
}: {
  id: string;
  selected: boolean;
  onSelect: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      id={`tab-${id}`}
      aria-selected={selected}
      aria-controls="login-panel"
      onClick={onSelect}
      className={
        "flex-1 px-3 py-2 text-sm font-medium border-b-2 -mb-px " +
        (selected
          ? "border-sky-500 text-sky-700 bg-sky-50"
          : "border-transparent text-slate-500 hover:text-slate-700")
      }
    >
      {children}
    </button>
  );
}

export function LoginPage() {
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);
  const initialMode: Mode = search.get("role") === "staff" ? "staff" : "customer";
  const [mode, setMode] = useState<Mode>(initialMode);
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isAuthed) navigate(homeForRoles(roles), { replace: true });
  }, [isAuthed, roles, navigate]);

  useEffect(() => {
    emailRef.current?.focus();
  }, [mode]);

  return (
    <main
      className="min-h-screen flex flex-col items-center justify-center p-4"
      style={{ background: "linear-gradient(180deg, rgb(224 242 254) 0%, white 60%)" }}
    >
      <div className="mb-6 text-center">
        <div className="text-3xl font-bold text-sky-900">Splashh</div>
        <div className="text-sm text-slate-500">Book your club in seconds</div>
      </div>
      <Card className="w-full max-w-sm rounded-2xl shadow-md">
        <CardHeader className="p-0">
          <div role="tablist" aria-label="Login type" className="flex border-b border-slate-200">
            <Tab id="customer" selected={mode === "customer"} onSelect={() => setMode("customer")}>
              Customer
            </Tab>
            <Tab id="staff" selected={mode === "staff"} onSelect={() => setMode("staff")}>
              Staff
            </Tab>
          </div>
        </CardHeader>
        <CardContent>
          <div id="login-panel" role="tabpanel" aria-labelledby={`tab-${mode}`}>
            <LoginForm
              mode={mode}
              headingLevel="h2"
              emailRef={emailRef}
              onSuccess={(roles) => navigate(homeForRoles(roles), { replace: true })}
            />
          </div>
        </CardContent>
      </Card>
      <p className="mt-6 text-xs text-slate-500">Need help? Contact your club.</p>
    </main>
  );
}
