import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@splashh/api-client";
import { homeForRoles } from "@/lib/role-routing";
import { LandingPage } from "./LandingPage";

export function HomePage() {
  const navigate = useNavigate();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);

  useEffect(() => {
    if (isAuthed) {
      navigate(homeForRoles(roles), { replace: true });
    }
  }, [isAuthed, roles, navigate]);

  // If not authenticated, render the landing page
  // The AuthBootstrap component handles silent refresh in the background
  // and will redirect if the user turns out to be logged in
  if (isAuthed) {
    return null;
  }

  return <LandingPage />;
}
