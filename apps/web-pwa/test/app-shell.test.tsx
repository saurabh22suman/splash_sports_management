import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { post: vi.fn() } };
});

vi.mock("@/components/Sidebar", () => ({
  Sidebar: ({ items, mobileOpen, onClose }: any) => (
    <div data-testid="sidebar" data-mobile-open={mobileOpen ? "true" : "false"}>
      {items.map((it: any) => (
        <a key={it.to} href={it.to} onClick={onClose}>
          {it.label}
        </a>
      ))}
    </div>
  ),
}));

vi.mock("@/components/TopBar", () => ({
  TopBar: ({ mobileOpen, onToggleSidebar }: any) => (
    <div>
      <button data-testid="hamburger" aria-expanded={mobileOpen} onClick={onToggleSidebar}>
        ☰
      </button>
    </div>
  ),
}));

vi.mock("@/components/UserMenu", () => ({ UserMenu: () => <div data-testid="user-menu" /> }));

import { AppShell } from "@/components/AppShell";
import { NAV_BY_ROLE, navForRoles } from "@/components/nav";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useAuthStore } from "@splashh/api-client";

const renderShell = (path: string, roles: string[]) => {
  useAuthStore.setState({ roles, isAuthenticated: true });
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <AppShell>
          <div data-testid="content">Page content</div>
        </AppShell>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("navForRoles", () => {
  it("returns customer nav for the customer role", () => {
    expect(navForRoles(["customer"])).toEqual(NAV_BY_ROLE.customer);
  });
  it("returns admin nav for the tenant_admin role", () => {
    expect(navForRoles(["tenant_admin"])).toEqual(NAV_BY_ROLE.tenant_admin);
  });
  it("returns an empty array for an unknown role", () => {
    expect(navForRoles(["unknown"])).toEqual([]);
  });
});

describe("AppShell", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null,
      userId: null,
      tenantId: null,
      roles: [],
      isAuthenticated: false,
    });
  });

  it("renders the Sidebar and TopBar with the children content", () => {
    renderShell("/book", ["customer"]);
    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("hamburger")).toBeInTheDocument();
    expect(screen.getByTestId("content")).toBeInTheDocument();
  });

  it("shows customer nav items when the user is a customer", () => {
    renderShell("/book", ["customer"]);
    expect(screen.getByRole("link", { name: "Browse" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "My bookings" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
  });

  it("shows admin nav items when the user is a tenant_admin", () => {
    renderShell("/admin", ["tenant_admin"]);
    expect(screen.getByRole("link", { name: "Facilities" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Users" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Browse" })).not.toBeInTheDocument();
  });

  it("renders a Skip to main content link as the first focusable element", () => {
    renderShell("/book", ["customer"]);
    const skip = screen.getByRole("link", { name: /skip to main content/i });
    expect(skip).toHaveAttribute("href", "#main");
  });

  it("opens the mobile sidebar when the hamburger is clicked", async () => {
    renderShell("/book", ["customer"]);
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar).toHaveAttribute("data-mobile-open", "false");
    await userEvent.click(screen.getByTestId("hamburger"));
    expect(sidebar).toHaveAttribute("data-mobile-open", "true");
  });

  it("renders a <main id='main'> landmark for the children", () => {
    renderShell("/book", ["customer"]);
    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "main");
    expect(main).toContainElement(screen.getByTestId("content"));
  });
});
