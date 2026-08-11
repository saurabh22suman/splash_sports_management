import { cn, brand, Waves, CalendarDays, Building2, Users, Receipt, X } from "@splashh/ui";
import { NavLink } from "react-router-dom";
import { UserMenu } from "./UserMenu";

// Map icon name strings to actual icon components
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Waves,
  CalendarDays,
  Building2,
  Users,
  Receipt,
};

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
        "fixed md:static inset-y-0 left-0 z-40 w-60 bg-card border-r border-border shadow-sm",
        "transform transition-transform duration-350 ease-swim md:transform-none",
        mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
      )}
    >
      <div className="flex items-center justify-between px-4 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Waves className="w-6 h-6 text-primary animate-swim-bob motion-reduce:animate-none" aria-hidden="true" />
          <span className="font-bold text-lg text-foreground">{brand.name}</span>
        </div>
        <button
          type="button"
          aria-label="Close navigation"
          onClick={onClose}
          className="md:hidden p-1 text-muted-foreground hover:text-foreground transition-colors duration-250"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
      <nav aria-label="Primary">
        <ul role="list" className="px-2 py-3 space-y-1">
          {items.map((item, idx) => {
            const IconComponent = iconMap[item.icon];
            return (
              <li
                key={item.to}
                className="animate-slide-in-left motion-reduce:animate-none"
                style={{ animationDelay: `${Math.min(idx * 60, 360)}ms` }}
              >
                <NavLink
                  to={item.to}
                  onClick={onClose}
                  end={item.to === "/admin" || item.to === "/book"}
                  className={({ isActive }) =>
                    cn(
                      "group flex items-center gap-3 px-3 py-2.5 rounded-none text-sm transition-all duration-250 ease-swim",
                      "hover:translate-x-0.5",
                      isActive
                        ? "bg-primary/10 text-primary font-medium border-b-2 border-primary"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                    )
                  }
                >
                  {IconComponent && (
                    <IconComponent
                      className={cn(
                        "w-5 h-5 transition-transform duration-250 ease-swim",
                        "group-hover:scale-110 group-active:scale-95",
                      )}
                      aria-hidden="true"
                    />
                  )}
                  <span>{item.label}</span>
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="hidden md:block absolute bottom-0 left-0 right-0 p-2 border-t border-border bg-card">
        <UserMenu />
      </div>
    </aside>
  );
}
