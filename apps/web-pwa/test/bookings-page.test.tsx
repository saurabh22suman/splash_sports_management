import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>(
    "@splashh/api-client",
  );
  return { ...actual, useAuthStore: vi.fn(() => ({ userId: "u1" })) };
});

vi.mock("@/features/bookings/useBookings", () => ({
  useBookingsByCustomer: vi.fn(),
}));

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { useAuthStore } from "@splashh/api-client";
import { useBookingsByCustomer } from "@/features/bookings/useBookings";
import { BookingsPage } from "@/pages/book/BookingsPage";

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <BookingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("BookingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a polite live region while loading", () => {
    (useBookingsByCustomer as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });
    renderPage();
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("renders an alert region on error with a retry button", async () => {
    (useBookingsByCustomer as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed to load"),
      refetch: vi.fn(),
    });
    renderPage();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("renders an h1 and an empty state when there are no bookings", async () => {
    (useBookingsByCustomer as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    renderPage();
    expect(await screen.findByRole("heading", { level: 1, name: /my bookings/i })).toBeInTheDocument();
    expect(screen.getByText(/no bookings yet/i)).toBeInTheDocument();
  });
});
