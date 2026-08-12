import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { post: vi.fn() } };
});

import { useCreateBooking } from "@/features/bookings/useCreateBooking";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api } from "@splashh/api-client";

function Probe() {
  const create = useCreateBooking();
  return (
    <button
      onClick={() =>
        create.mutate({
          customer_id: "c1",
          resource_id: "r1",
          start_at: "2026-12-01T10:00:00Z",
          end_at: "2026-12-01T11:00:00Z",
        })
      }
    >
      create
    </button>
  );
}

describe("useCreateBooking", () => {
  it("POSTs to /booking and returns the new booking", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { id: "b1", status: "confirmed" },
    });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <Probe />
      </QueryClientProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "create" }));
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        "/booking",
        expect.objectContaining({ resource_id: "r1" }),
      );
    });
  });
});
