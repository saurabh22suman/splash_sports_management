import { useAuthStore } from "@splashh/api-client";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { RoleGate } from "../src/routes/role-gate";

const renderWith = (roles: string[], path = "/admin") => {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    accessToken: "x",
    userId: "u",
    tenantId: "t",
  });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<RoleGate roles={["tenant_admin"]} />}>
          <Route path="/admin" element={<div>admin ok</div>} />
        </Route>
        <Route path="/book" element={<div>book</div>} />
      </Routes>
    </MemoryRouter>,
  );
};

describe("RoleGate", () => {
  it("renders Outlet when role matches", () => {
    renderWith(["tenant_admin"]);
    expect(screen.getByText("admin ok")).toBeInTheDocument();
  });
  it("renders 403 page when role missing", () => {
    renderWith(["customer"]);
    expect(screen.getByRole("heading", { name: /not authorized/i })).toBeInTheDocument();
  });
});
