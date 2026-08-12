import { useAuthStore } from "@splashh/api-client";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { homeForRoles } from "../lib/role-routing";

export function RoleBasedRedirect() {
  const navigate = useNavigate();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);

  useEffect(() => {
    if (isAuthed) {
      navigate(homeForRoles(roles), { replace: true });
    }
  }, [isAuthed, roles, navigate]);

  return null;
}
