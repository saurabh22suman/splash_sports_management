import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { AuthBootstrap } from "@/features/auth/AuthBootstrap";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { ProtectedRoute } from "./protected";

const FacilitiesPage = lazy(() =>
  import("@/pages/FacilitiesPage").then((m) => ({ default: m.FacilitiesPage })),
);
const FacilityDetailPage = lazy(() =>
  import("@/pages/FacilityDetailPage").then((m) => ({ default: m.FacilityDetailPage })),
);
const BookingsPage = lazy(() =>
  import("@/pages/BookingsPage").then((m) => ({ default: m.BookingsPage })),
);

export function AppRouter() {
  return (
    <AuthBootstrap>
      <Suspense fallback={<div className="p-8 text-center text-muted-foreground">Loading…</div>}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/facilities" element={<FacilitiesPage />} />
            <Route path="/facilities/:id" element={<FacilityDetailPage />} />
            <Route path="/bookings" element={<BookingsPage />} />
          </Route>
          <Route path="*" element={<HomePage />} />
        </Routes>
      </Suspense>
    </AuthBootstrap>
  );
}
