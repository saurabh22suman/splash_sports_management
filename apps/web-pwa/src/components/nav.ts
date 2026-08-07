import type { NavItem } from "./Sidebar";

export const NAV_BY_ROLE: Record<string, NavItem[]> = {
  customer: [
    { to: "/book", label: "Browse", icon: "🏊" },
    { to: "/book/bookings", label: "My bookings", icon: "📅" },
  ],
  tenant_admin: [
    { to: "/admin", label: "Facilities", icon: "🏢" },
    { to: "/admin/users", label: "Users", icon: "👥" },
  ],
};

export function navForRoles(roles: string[]): NavItem[] {
  for (const r of roles) {
    if (NAV_BY_ROLE[r]) return NAV_BY_ROLE[r];
  }
  return [];
}
