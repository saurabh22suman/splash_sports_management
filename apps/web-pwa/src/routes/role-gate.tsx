import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@splashh/api-client";
import { RoleMismatch } from "../components/RoleMismatch";

export function RoleGate({ roles }: { roles: string[] }) {
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const userRoles = useAuthStore((s) => s.roles);
  const location = useLocation();

  if (!isAuthed) return <Navigate to="/login" state={{ from: location }} replace />;
  if (!roles.some((r) => userRoles.includes(r))) return <RoleMismatch required={roles} />;
  return <Outlet />;
}
