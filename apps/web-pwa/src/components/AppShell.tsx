import { useMemo, useState } from "react";
import { useAuthStore } from "@splashh/api-client";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { navForRoles } from "./nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const roles = useAuthStore((s) => s.roles);
  const items = useMemo(() => navForRoles(roles), [roles]);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-card focus:px-3 focus:py-2 focus:rounded focus:shadow"
      >
        Skip to main content
      </a>
      <Sidebar items={items} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      )}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar
          mobileOpen={mobileOpen}
          onToggleSidebar={() => setMobileOpen((v) => !v)}
        />
        <main id="main" className="flex-1 p-4 md:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
