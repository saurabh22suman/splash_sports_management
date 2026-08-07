import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";

vi.mock("@/features/facilities/api", () => ({
  facilitiesApi: {
    get: vi.fn(),
    listResources: vi.fn(),
  },
}));

import { facilitiesApi } from "@/features/facilities/api";
import { FacilityDetailPage } from "@/pages/book/FacilityDetailPage";

// Create a QueryClient with retries disabled to speed up error handling
const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

function renderAt(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/book/facilities/${id}`]}>
      <QueryClientProvider client={createQueryClient()}>
        <Routes>
          <Route path="/book/facilities/:id" element={<FacilityDetailPage />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("FacilityDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a polite live region while loading", () => {
    // Mock the API to delay forever, simulating loading
    (facilitiesApi.get as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}), // never resolves
    );
    (facilitiesApi.listResources as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}),
    );
    renderAt("fac-123");
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("renders the facility name as h1 inside <main>", async () => {
    (facilitiesApi.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      id: "fac-123",
      name: "Sydney Aquatic Centre",
      address_line1: "1 Driver Ave",
      city: "Sydney",
      state: "NSW",
      slug: "sydney-aquatic-centre",
      postal_code: null,
      country: null,
      timezone: "Australia/Sydney",
      status: "active",
    });
    (facilitiesApi.listResources as ReturnType<typeof vi.fn>).mockResolvedValueOnce([]);
    renderAt("fac-123");
    expect(
      await screen.findByRole("heading", { level: 1, name: /sydney aquatic centre/i }),
    ).toBeInTheDocument();
  });

  it("renders a 404 empty state when the facility is not found", async () => {
    (facilitiesApi.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce(null);
    (facilitiesApi.listResources as ReturnType<typeof vi.fn>).mockResolvedValueOnce([]);
    renderAt("missing");
    expect(await screen.findByText(/not found/i)).toBeInTheDocument();
  });

  it("renders an alert region on error with a retry button", async () => {
    // Use Promise.reject to trigger the error state
    (facilitiesApi.get as ReturnType<typeof vi.fn>).mockReturnValueOnce(
      Promise.reject(new Error("Network error")),
    );
    renderAt("fac-123");
    // Wait for the error to propagate to React Query
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});
