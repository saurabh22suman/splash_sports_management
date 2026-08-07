import { useLocation } from "react-router-dom";
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
    <header className="h-14 bg-white border-b border-slate-200 flex items-center px-3 md:px-6 gap-3">
      <button
        type="button"
        aria-label="Toggle navigation"
        aria-expanded={mobileOpen}
        aria-controls="primary-nav"
        onClick={onToggleSidebar}
        className="md:hidden p-2 rounded hover:bg-slate-100"
      >
        ☰
      </button>
      <h2 className="text-base font-semibold text-slate-900 truncate">{title}</h2>
      <div className="ml-auto" />
    </header>
  );
}
