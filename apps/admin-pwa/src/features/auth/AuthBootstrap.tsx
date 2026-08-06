import { silentRefresh, useAuthStore } from "@splashh/api-client";
import { useEffect } from "react";

export function AuthBootstrap({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (!useAuthStore.getState().isAuthenticated) {
      silentRefresh().catch(() => undefined);
    }
  }, []);
  return <>{children}</>;
}
