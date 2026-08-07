import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/components/UserMenu", () => ({ UserMenu: () => <div data-testid="user-menu" /> }));

import { Sidebar } from "@/components/Sidebar";

const items = [
  { to: "/book", label: "Browse", icon: "🏊" },
  { to: "/book/bookings", label: "My bookings", icon: "📅" },
];

const renderSidebar = (path: string = "/book") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Sidebar items={items} mobileOpen={false} onClose={vi.fn()} />
    </MemoryRouter>,
  );

describe("Sidebar", () => {
  it("renders the Splashh wordmark", () => {
    renderSidebar();
    expect(screen.getByText("Splashh")).toBeInTheDocument();
  });

  it("renders a nav element with aria-label='Primary'", () => {
    renderSidebar();
    expect(screen.getByRole("navigation", { name: /primary/i })).toBeInTheDocument();
  });

  it("renders a NavLink for each item with the label and icon", () => {
    renderSidebar();
    expect(screen.getByRole("link", { name: /🏊.*Browse/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /📅.*My bookings/ })).toBeInTheDocument();
  });

  it("marks the current route's link as active (sky-50 background)", () => {
    renderSidebar("/book");
    const browse = screen.getByRole("link", { name: /🏊.*Browse/ });
    expect(browse.className).toMatch(/bg-sky-50/);
  });

  it("renders the UserMenu in the footer", () => {
    renderSidebar();
    expect(screen.getByTestId("user-menu")).toBeInTheDocument();
  });

  it("calls onClose when a nav item is clicked", async () => {
    const onClose = vi.fn();
    render(
      <MemoryRouter>
        <Sidebar items={items} mobileOpen={true} onClose={onClose} />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole("link", { name: /Browse/ }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
