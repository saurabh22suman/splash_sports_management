import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { post: vi.fn() } };
});

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: vi.fn() };
});

import { AdminLoginPage } from "@/pages/AdminLoginPage";
import { LoginPage } from "@/pages/LoginPage";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api, useAuthStore } from "@splashh/api-client";
import { useNavigate } from "react-router-dom";

const renderLogin = (initialPath = "/login") => {
  const navigate = vi.fn();
  (useNavigate as ReturnType<typeof vi.fn>).mockReturnValue(navigate);
  return {
    navigate,
    ...render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/login?role=staff" element={<LoginPage />} />
            <Route path="/admin/login" element={<AdminLoginPage />} />
            <Route path="/admin" element={<div>admin home</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
};

describe("LoginPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAuthStore.setState({
      accessToken: null,
      userId: null,
      tenantId: null,
      roles: [],
      isAuthenticated: false,
    });
  });

  it("renders a Customer and Staff tab with Customer selected by default", () => {
    renderLogin("/login");
    const customer = screen.getByRole("tab", { name: "Customer" });
    const staff = screen.getByRole("tab", { name: "Staff" });
    expect(customer).toHaveAttribute("aria-selected", "true");
    expect(staff).toHaveAttribute("aria-selected", "false");
  });

  it("pre-selects the Staff tab when ?role=staff is in the URL", () => {
    renderLogin("/login?role=staff");
    expect(screen.getByRole("tab", { name: "Customer" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tab", { name: "Staff" })).toHaveAttribute("aria-selected", "true");
  });

  it("switches the active tab on click", async () => {
    renderLogin("/login");
    await userEvent.click(screen.getByRole("tab", { name: "Staff" }));
    expect(screen.getByRole("tab", { name: "Staff" })).toHaveAttribute("aria-selected", "true");
  });

  it("shows the Splashh wordmark and tagline above the card", () => {
    renderLogin();
    expect(screen.getByText("Splashh")).toBeInTheDocument();
    expect(screen.getByText(/sports club management/i)).toBeInTheDocument();
  });

  it("submits the Customer tab with mode='customer' on success", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { access_token: "t", user_id: "u1", tenant_id: "ten1" },
    });
    renderLogin("/login");
    await userEvent.type(screen.getByLabelText(/email/i), "alex@demo.splashh.dev");
    await userEvent.type(screen.getByLabelText(/password/i), "Customer!Demo1");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    expect(api.post).toHaveBeenCalledWith(
      "/auth/login",
      expect.objectContaining({ mode: "customer" }),
    );
  });

  it("submits the Staff tab with mode='staff'", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { access_token: "t", user_id: "u1", tenant_id: "ten1" },
    });
    renderLogin("/login?role=staff");
    await userEvent.type(screen.getByLabelText(/email/i), "admin@demo.splashh.dev");
    await userEvent.type(screen.getByLabelText(/password/i), "Admin!Demo2026");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    expect(api.post).toHaveBeenCalledWith(
      "/auth/login",
      expect.objectContaining({ mode: "staff" }),
    );
  });
});

describe("AdminLoginPage", () => {
  it("renders a Navigate that sends the user to /login?role=staff", () => {
    renderLogin("/admin/login");
    expect(screen.getByRole("heading", { name: /log in/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Staff" })).toHaveAttribute("aria-selected", "true");
  });
});
