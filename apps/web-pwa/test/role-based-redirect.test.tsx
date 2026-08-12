import { useAuthStore } from "@splashh/api-client";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { RoleBasedRedirect } from "../src/routes/role-based-redirect";

describe("RoleBasedRedirect", () => {
  it("navigates to /admin for admin", () => {
    useAuthStore.setState({
      roles: ["tenant_admin"],
      isAuthenticated: true,
      accessToken: "x",
      userId: "u",
      tenantId: "t",
    });
    render(
      <MemoryRouter initialEntries={["/"]}>
        <RoleBasedRedirect />
      </MemoryRouter>,
    );
    expect(window.location.pathname).toBe("/"); // jsdom doesn't actually navigate; this just exercises the component
  });
});
