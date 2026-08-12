import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/lib/page-titles", () => ({
  titleForPath: (p: string) => (p.startsWith("/admin") ? "Admin" : "Browse"),
}));

vi.mock("@/features/auth/useLogout", () => ({
  useLogout: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { TopBar } from "@/components/TopBar";

const renderBar = (pathname: string, mobileOpen = false) => {
  const onToggle = vi.fn();
  const result = render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[pathname]}>
        <TopBar mobileOpen={mobileOpen} onToggleSidebar={onToggle} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { onToggle, ...result };
};

describe("TopBar", () => {
  beforeEach(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((q: string) => ({
        matches: false,
        media: q,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it("renders the page title from the current route", () => {
    renderBar("/book");
    expect(screen.getByRole("heading", { level: 2, name: "Browse" })).toBeInTheDocument();
  });

  it("renders the hamburger button with aria-label", () => {
    renderBar("/book");
    expect(screen.getByRole("button", { name: /toggle navigation/i })).toBeInTheDocument();
  });

  it("calls onToggleSidebar when the hamburger is clicked", async () => {
    const { onToggle } = renderBar("/book");
    await userEvent.click(screen.getByRole("button", { name: /toggle navigation/i }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("reflects the mobileOpen prop in aria-expanded", () => {
    renderBar("/book", true);
    expect(screen.getByRole("button", { name: /toggle navigation/i })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });
});
