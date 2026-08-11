import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, Waves, ChevronLeft } from "@splashh/ui";
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
        "flex-1 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-all duration-250 ease-swim " +
        (selected
          ? "border-primary text-primary bg-primary/5"
          : "border-transparent text-muted-foreground hover:text-foreground hover:bg-secondary/40")
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
    <main className="relative min-h-screen flex flex-col items-center justify-center p-4 overflow-hidden">
      {/* Pool-blue orb top-right, faint warm orb bottom-left — keeps the brand mood on a non-gradient base */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "radial-gradient(60% 50% at 85% 0%, hsl(199 73% 42% / 0.12), transparent 60%)," +
            "radial-gradient(40% 40% at 10% 100%, hsl(25 95% 47% / 0.06), transparent 70%)",
        }}
      />
      {/* Faint horizontal lane-lines, very low contrast — visual cue without stripe noise */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-24 opacity-[0.04]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, hsl(199 73% 42%) 0 1px, transparent 1px 14px)",
        }}
      />

      <Link
        to="/"
        className="relative mb-4 inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors duration-250 hover:text-foreground animate-rise-up motion-reduce:animate-none"
      >
        <ChevronLeft className="h-3.5 w-3.5" /> Back to home
      </Link>

      <div className="relative mb-6 flex flex-col items-center text-center animate-rise-up motion-reduce:animate-none">
        <Waves
          aria-hidden="true"
          className="w-9 h-9 text-primary animate-swim-bob motion-reduce:animate-none"
        />
        <div className="mt-2 font-display text-3xl font-bold uppercase tracking-tight text-foreground">Splashh</div>
        <div className="mt-1 text-xs font-semibold uppercase tracking-[0.18em] text-volt">
          Sports club management
        </div>
        <div className="mt-3 max-w-sm text-sm text-muted-foreground">
          Pools, courts, members, and money in one place. Run your club, not your spreadsheet.
        </div>
      </div>

      <Card className="relative w-full max-w-sm rounded-none shadow-md animate-rise-up motion-reduce:animate-none [animation-delay:80ms]">
        <CardHeader className="p-0">
          <div role="tablist" aria-label="Login type" className="flex border-b border-border">
            <Tab id="customer" selected={mode === "customer"} onSelect={() => setMode("customer")}>
              Customer
            </Tab>
            <Tab id="staff" selected={mode === "staff"} onSelect={() => setMode("staff")}>
              Staff
            </Tab>
          </div>
        </CardHeader>
        <CardContent>
          <div
            id="login-panel"
            role="tabpanel"
            aria-labelledby={`tab-${mode}`}
            key={mode}
            className="animate-rise-up motion-reduce:animate-none"
          >
            <LoginForm
              mode={mode}
              headingLevel="h2"
              emailRef={emailRef}
              onSuccess={(roles) => navigate(homeForRoles(roles), { replace: true })}
            />
          </div>
        </CardContent>
      </Card>
      <p className="relative mt-6 text-xs text-muted-foreground animate-rise-up motion-reduce:animate-none [animation-delay:160ms]">
        Need help? Contact your club.
      </p>
    </main>
  );
}
