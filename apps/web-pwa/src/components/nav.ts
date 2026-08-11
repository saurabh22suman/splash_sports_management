import type { NavItem } from "./Sidebar";
import { Waves, CalendarDays, Building2, Users, Receipt } from "@splashh/ui";

export const NAV_BY_ROLE: Record<string, NavItem[]> = {
  customer: [
    { to: "/book", label: "Browse", icon: "Waves" },
    { to: "/book/bookings", label: "My bookings", icon: "CalendarDays" },
  ],
  tenant_admin: [
    { to: "/admin", label: "Facilities", icon: "Building2" },
    { to: "/admin/users", label: "Users", icon: "Users" },
    { to: "/admin/invoices", label: "Invoices", icon: "Receipt" },
  ],
};

export function navForRoles(roles: string[]): NavItem[] {
  for (const r of roles) {
    if (NAV_BY_ROLE[r]) return NAV_BY_ROLE[r];
  }
  return [];
}
