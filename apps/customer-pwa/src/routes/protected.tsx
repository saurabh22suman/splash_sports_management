import { useAuthStore } from "@splashh/api-client";
import { Navigate, Outlet, useLocation } from "react-router-dom";

export function ProtectedRoute() {
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const location = useLocation();
  if (!isAuthed) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <Outlet />;
}
