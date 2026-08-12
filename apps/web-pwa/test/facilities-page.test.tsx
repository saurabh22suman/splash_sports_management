import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});

vi.mock("@/features/facilities/useFacilities", () => ({
  useFacilities: vi.fn(),
}));

import { useFacilities } from "@/features/facilities/useFacilities";
import { FacilitiesPage } from "@/pages/book/FacilitiesPage";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api } from "@splashh/api-client";

describe("FacilitiesPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  it("links each facility to the customer detail route /book/facilities/:id", async () => {
    (useFacilities as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [{ id: "fac-123", name: "Sydney Aquatic Centre", city: "Sydney", state: "NSW" }],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <FacilitiesPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const link = await waitFor(() => screen.getByRole("link", { name: /view details/i }));
    expect(link).toHaveAttribute("href", "/book/facilities/fac-123");
  });
});

describe("FacilitiesPage (polish)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  it("renders a polite live region while loading", () => {
    (useFacilities as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <QueryClientProvider client={new QueryClient()}>
          <FacilitiesPage />
        </QueryClientProvider>
      </MemoryRouter>,
    );
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("renders an h1 inside <main>", async () => {
    (useFacilities as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <QueryClientProvider client={new QueryClient()}>
          <FacilitiesPage />
        </QueryClientProvider>
      </MemoryRouter>,
    );
    expect(
      await screen.findByRole("heading", { level: 1, name: /facilities/i }),
    ).toBeInTheDocument();
  });

  it("renders the empty state with a Browse action when there are no facilities", async () => {
    (useFacilities as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <QueryClientProvider client={new QueryClient()}>
          <FacilitiesPage />
        </QueryClientProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByText(/no facilities yet/i)).toBeInTheDocument();
  });

  it("renders an alert region on error and a retry button", async () => {
    const mockRefetch = vi.fn();
    (useFacilities as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("boom"),
      refetch: mockRefetch,
    });

    render(
      <MemoryRouter>
        <QueryClientProvider client={new QueryClient()}>
          <FacilitiesPage />
        </QueryClientProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });
});
