import { useLocation } from "react-router-dom";
import { cn, Menu, Waves } from "@splashh/ui";
import { titleForPath } from "@/lib/page-titles";

export function TopBar({
  mobileOpen,
  onToggleSidebar,
}: {
  mobileOpen: boolean;
  onToggleSidebar: () => void;
}) {
  const { pathname } = useLocation();
  const title = titleForPath(pathname);
  return (
    <header
      className={cn(
        "h-14 bg-card border-b border-border flex items-center px-3 md:px-6 gap-3",
        "transition-colors duration-250 ease-swim",
        mobileOpen ? "relative z-30" : "relative",
      )}
    >
      <button
        type="button"
        aria-label="Toggle navigation"
        aria-expanded={mobileOpen}
        aria-controls="primary-nav"
        onClick={onToggleSidebar}
        className={cn(
          "md:hidden p-2 rounded-none transition-all duration-250 ease-swim",
          "hover:bg-secondary active:scale-95",
        )}
      >
        <Menu className="w-5 h-5 text-foreground" />
      </button>
      <h2
        key={pathname}
        className="text-base font-semibold text-foreground truncate animate-rise-up motion-reduce:animate-none"
      >
        {title}
      </h2>
      <div className="ml-auto flex items-center gap-2">
        <Waves
          aria-hidden="true"
          className="hidden md:block w-4 h-4 text-primary/40 animate-wave-drift motion-reduce:animate-none"
        />
      </div>
    </header>
  );
}
