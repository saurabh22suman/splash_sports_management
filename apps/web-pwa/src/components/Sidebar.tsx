import { cn } from "@splashh/ui";
import { NavLink } from "react-router-dom";
import { UserMenu } from "./UserMenu";

export interface NavItem {
  to: string;
  label: string;
  icon: string;
}

export function Sidebar({
  items,
  mobileOpen,
  onClose,
}: {
  items: NavItem[];
  mobileOpen: boolean;
  onClose: () => void;
}) {
  return (
    <aside
      aria-label="Primary"
      id="primary-nav"
      className={cn(
        "fixed md:static inset-y-0 left-0 z-40 w-60 bg-white border-r border-slate-200 shadow-sm",
        "transform transition-transform duration-200 ease-out md:transform-none",
        mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
      )}
    >
      <div className="px-4 py-4 font-bold text-sky-900">Splashh</div>
      <nav aria-label="Primary">
        <ul role="list" className="px-2 space-y-1">
          {items.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                onClick={onClose}
                end={item.to === "/admin" || item.to === "/book"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 px-3 py-2 rounded-lg text-sm",
                    isActive
                      ? "bg-sky-50 text-sky-700 border-l-2 border-sky-500"
                      : "text-slate-700 hover:bg-slate-50",
                  )
                }
              >
                <span aria-hidden="true">{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="absolute bottom-0 left-0 right-0 p-2 border-t border-slate-200">
        <UserMenu />
      </div>
    </aside>
  );
}
