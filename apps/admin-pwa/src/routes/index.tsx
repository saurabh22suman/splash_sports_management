import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { AuthBootstrap } from "@/features/auth/AuthBootstrap";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { ProtectedRoute } from "./protected";

const AdminFacilitiesPage = lazy(() =>
  import("@/pages/AdminFacilitiesPage").then((m) => ({ default: m.AdminFacilitiesPage })),
);
const AdminFacilityNewPage = lazy(() =>
  import("@/pages/AdminFacilityNewPage").then((m) => ({ default: m.AdminFacilityNewPage })),
);
const AdminFacilityDetailPage = lazy(() =>
  import("@/pages/AdminFacilityDetailPage").then((m) => ({ default: m.AdminFacilityDetailPage })),
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
            <Route path="/admin/facilities" element={<AdminFacilitiesPage />} />
            <Route path="/admin/facilities/new" element={<AdminFacilityNewPage />} />
            <Route path="/admin/facilities/:id" element={<AdminFacilityDetailPage />} />
            <Route path="/bookings" element={<BookingsPage />} />
          </Route>
          <Route path="*" element={<HomePage />} />
        </Routes>
      </Suspense>
    </AuthBootstrap>
  );
}
