import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api } from "@splashh/api-client";
import { FacilitiesPage } from "@/pages/book/FacilitiesPage";

describe("FacilitiesPage", () => {
  it("links each facility to the customer detail route /book/facilities/:id", async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { data: [{ id: "fac-123", name: "Sydney Aquatic Centre", city: "Sydney", state: "NSW" }] },
    });

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <FacilitiesPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const link = await waitFor(() =>
      screen.getByRole("link", { name: /view details/i }),
    );
    expect(link).toHaveAttribute("href", "/book/facilities/fac-123");
  });
});
