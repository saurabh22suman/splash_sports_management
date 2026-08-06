import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { AuthBootstrap } from "@/features/auth/AuthBootstrap";
import { AdminLoginPage } from "@/pages/AdminLoginPage";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { ProtectedRoute } from "./protected";
import { RoleGate } from "./role-gate";
import { RoleBasedRedirect } from "./role-based-redirect";

const FacilitiesPage = lazy(() => import("@/pages/book/FacilitiesPage").then((m) => ({ default: m.FacilitiesPage })));
const FacilityDetailPage = lazy(() => import("@/pages/book/FacilityDetailPage").then((m) => ({ default: m.FacilityDetailPage })));
const BookingsPage = lazy(() => import("@/pages/book/BookingsPage").then((m) => ({ default: m.BookingsPage })));
const AdminFacilitiesPage = lazy(() => import("@/pages/admin/AdminFacilitiesPage").then((m) => ({ default: m.AdminFacilitiesPage })));
const AdminFacilityNewPage = lazy(() => import("@/pages/admin/AdminFacilityNewPage").then((m) => ({ default: m.AdminFacilityNewPage })));
const AdminFacilityDetailPage = lazy(() => import("@/pages/admin/AdminFacilityDetailPage").then((m) => ({ default: m.AdminFacilityDetailPage })));
const AdminUsersPage = lazy(() => import("@/pages/AdminUsersPage").then((m) => ({ default: m.AdminUsersPage })));

export function AppRouter() {
  return (
    <AuthBootstrap>
      <Suspense fallback={<div className="p-8 text-center text-muted-foreground">Loading…</div>}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/redirect" element={<RoleBasedRedirect />} />
            <Route element={<RoleGate roles={["customer"]} />}>
              <Route path="/book" element={<FacilitiesPage />} />
              <Route path="/book/facilities/:id" element={<FacilityDetailPage />} />
              <Route path="/book/bookings" element={<BookingsPage />} />
            </Route>
            <Route element={<RoleGate roles={["tenant_admin"]} />}>
              <Route path="/admin" element={<AdminFacilitiesPage />} />
              <Route path="/admin/facilities/new" element={<AdminFacilityNewPage />} />
              <Route path="/admin/facilities/:id" element={<AdminFacilityDetailPage />} />
              <Route path="/admin/users" element={<AdminUsersPage />} />
            </Route>
          </Route>
          <Route path="*" element={<HomePage />} />
        </Routes>
      </Suspense>
    </AuthBootstrap>
  );
}
