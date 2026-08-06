import { Button, Card, CardContent, CardFooter, CardHeader, CardTitle } from "@splashh/ui";
import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const DISMISS_KEY = "pwa_install_dismissed_at";
const VISITS_KEY = "pwa_visits";
const SHOW_AFTER_MS = 7 * 24 * 60 * 60 * 1000;
const SHOW_AFTER_VISITS = 3;

export function PWAInstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    const newCount = Number(localStorage.getItem(VISITS_KEY) ?? "0") + 1;
    localStorage.setItem(VISITS_KEY, String(newCount));
    const dismissedAt = localStorage.getItem(DISMISS_KEY);
    if (dismissedAt && Date.now() - Number(dismissedAt) < SHOW_AFTER_MS) return;
    if (newCount < SHOW_AFTER_VISITS) return;
    if (window.matchMedia("(display-mode: standalone)").matches) return;

    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  if (!deferred) return null;

  const install = async () => {
    deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
  };
  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    setDeferred(null);
  };

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 md:left-auto md:w-80">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Install Splashh</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Add to your home screen for the best experience.
        </CardContent>
        <CardFooter className="gap-2">
          <Button size="sm" onClick={install}>
            Install
          </Button>
          <Button size="sm" variant="ghost" onClick={dismiss}>
            Not now
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
