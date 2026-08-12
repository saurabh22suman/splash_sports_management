import { useRegisterSW } from "virtual:pwa-register/react";
import { Button } from "@splashh/ui";

export function UpdateBanner() {
  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({ onRegisteredSW: () => undefined });

  if (!needRefresh) return null;
  return (
    <div role="alert" className="fixed inset-x-0 top-0 z-50 border-b bg-card p-3 shadow">
      <div className="container flex items-center justify-between gap-3">
        <p className="text-sm">A new version of Splashh is available.</p>
        <Button size="sm" onClick={() => updateServiceWorker(true)}>
          Refresh
        </Button>
      </div>
    </div>
  );
}
