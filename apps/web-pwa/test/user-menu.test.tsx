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

import { UserMenu } from "@/components/UserMenu";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useAuthStore } from "@splashh/api-client";

const setup = () => {
  const qc = new QueryClient();
  useAuthStore.setState({ userId: "alex-123", accessToken: "t", isAuthenticated: true });
  return {
    qc,
    rerender: () => undefined as undefined,
  };
};

const renderMenu = () => {
  setup();
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <UserMenu />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("UserMenu", () => {
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

  it("renders an avatar button with the user's first initial", () => {
    useAuthStore.setState({ userId: "alex-123" });
    renderMenu();
    expect(screen.getByRole("button", { name: /open account menu/i })).toBeInTheDocument();
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("falls back to ? when no userId is set", () => {
    // Do NOT call renderMenu() - it sets userId via setup().
    // Store is already reset to { userId: null } by beforeEach.
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <UserMenu />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByText("?")).toBeInTheDocument();
  });

  it("does not show the menu items until the avatar is clicked", () => {
    useAuthStore.setState({ userId: "alex-123" });
    renderMenu();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: /log out/i })).not.toBeInTheDocument();
  });

  it("opens the menu and shows Log out after clicking the avatar", async () => {
    useAuthStore.setState({ userId: "alex-123" });
    renderMenu();
    await userEvent.click(screen.getByRole("button", { name: /open account menu/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /log out/i })).toBeInTheDocument();
  });

  it("closes the menu when the avatar is clicked a second time", async () => {
    useAuthStore.setState({ userId: "alex-123" });
    renderMenu();
    const trigger = screen.getByRole("button", { name: /open account menu/i });
    await userEvent.click(trigger);
    expect(screen.getByRole("menu")).toBeInTheDocument();
    await userEvent.click(trigger);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes the menu on Escape", async () => {
    useAuthStore.setState({ userId: "alex-123" });
    renderMenu();
    await userEvent.click(screen.getByRole("button", { name: /open account menu/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
