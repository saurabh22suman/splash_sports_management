import { AppShell } from "@/components/AppShell";
import { AuthBootstrap } from "@/features/auth/AuthBootstrap";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { titleForPath } from "@/lib/page-titles";
import { AdminLoginPage } from "@/pages/AdminLoginPage";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { Suspense, lazy } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { ProtectedRoute } from "./protected";
import { RoleBasedRedirect } from "./role-based-redirect";
import { RoleGate } from "./role-gate";

const FacilitiesPage = lazy(() =>
  import("@/pages/book/FacilitiesPage").then((m) => ({ default: m.FacilitiesPage })),
);
const FacilityDetailPage = lazy(() =>
  import("@/pages/book/FacilityDetailPage").then((m) => ({ default: m.FacilityDetailPage })),
);
const BookingsPage = lazy(() =>
  import("@/pages/book/BookingsPage").then((m) => ({ default: m.BookingsPage })),
);
const AdminFacilitiesPage = lazy(() =>
  import("@/pages/admin/AdminFacilitiesPage").then((m) => ({ default: m.AdminFacilitiesPage })),
);
const AdminFacilityNewPage = lazy(() =>
  import("@/pages/admin/AdminFacilityNewPage").then((m) => ({ default: m.AdminFacilityNewPage })),
);
const AdminFacilityDetailPage = lazy(() =>
  import("@/pages/admin/AdminFacilityDetailPage").then((m) => ({
    default: m.AdminFacilityDetailPage,
  })),
);
const AdminUsersPage = lazy(() =>
  import("@/pages/AdminUsersPage").then((m) => ({ default: m.AdminUsersPage })),
);
const InvoicesPage = lazy(() =>
  import("@/pages/admin/InvoicesPage").then((m) => ({ default: m.InvoicesPage })),
);
const InvoiceDetailPage = lazy(() =>
  import("@/pages/admin/InvoiceDetailPage").then((m) => ({ default: m.InvoiceDetailPage })),
);
const PayInvoicePage = lazy(() =>
  import("@/pages/book/PayInvoicePage").then((m) => ({ default: m.PayInvoicePage })),
);
const PayInvoiceReturnPage = lazy(() =>
  import("@/pages/book/PayInvoiceReturnPage").then((m) => ({ default: m.PayInvoiceReturnPage })),
);

export function AppRouter() {
  const location = useLocation();
  useDocumentTitle(titleForPath(location.pathname));
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
              <Route
                path="/book"
                element={
                  <AppShell>
                    <FacilitiesPage />
                  </AppShell>
                }
              />
              <Route
                path="/book/facilities/:id"
                element={
                  <AppShell>
                    <FacilityDetailPage />
                  </AppShell>
                }
              />
              <Route
                path="/book/bookings"
                element={
                  <AppShell>
                    <BookingsPage />
                  </AppShell>
                }
              />
              <Route
                path="/book/pay/:id"
                element={
                  <AppShell>
                    <PayInvoicePage />
                  </AppShell>
                }
              />
              <Route
                path="/book/pay/:id/return"
                element={
                  <AppShell>
                    <PayInvoiceReturnPage />
                  </AppShell>
                }
              />
            </Route>
            <Route element={<RoleGate roles={["tenant_admin"]} />}>
              <Route
                path="/admin/users"
                element={
                  <AppShell>
                    <AdminUsersPage />
                  </AppShell>
                }
              />
              <Route
                path="/admin/facilities/new"
                element={
                  <AppShell>
                    <AdminFacilityNewPage />
                  </AppShell>
                }
              />
              <Route
                path="/admin/facilities/:id"
                element={
                  <AppShell>
                    <AdminFacilityDetailPage />
                  </AppShell>
                }
              />
              <Route
                path="/admin/invoices"
                element={
                  <AppShell>
                    <InvoicesPage />
                  </AppShell>
                }
              />
              <Route
                path="/admin/invoices/:id"
                element={
                  <AppShell>
                    <InvoiceDetailPage />
                  </AppShell>
                }
              />
              <Route
                path="/admin"
                element={
                  <AppShell>
                    <AdminFacilitiesPage />
                  </AppShell>
                }
              />
            </Route>
          </Route>
          <Route path="*" element={<HomePage />} />
        </Routes>
      </Suspense>
    </AuthBootstrap>
  );
}
