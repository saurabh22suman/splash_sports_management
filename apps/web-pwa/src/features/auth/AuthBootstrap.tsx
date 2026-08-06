import { silentRefresh, useAuthStore } from "@splashh/api-client";
import { useEffect } from "react";
import { homeForRoles } from "@/lib/role-routing";

export function AuthBootstrap({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (!useAuthStore.getState().isAuthenticated) {
      silentRefresh()
        .then(() => {
          if (window.location.pathname === "/") {
            const roles = useAuthStore.getState().roles;
            window.location.replace(homeForRoles(roles));
          }
        })
        .catch(() => undefined);
    }
  }, []);
  return <>{children}</>;
}
