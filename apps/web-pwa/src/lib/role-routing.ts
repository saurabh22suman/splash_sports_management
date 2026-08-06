const ROLE_PRIORITY = ["tenant_admin", "staff", "customer"] as const;

const ROLE_HOMES: Record<string, string> = {
  tenant_admin: "/admin",
  customer: "/book",
  staff: "/staff",
};

export const homeForRoles = (roles: readonly string[]): string => {
  // Check roles in priority order
  for (const role of ROLE_PRIORITY) {
    if (roles.includes(role)) {
      return ROLE_HOMES[role] ?? "/";
    }
  }
  return "/";
};
