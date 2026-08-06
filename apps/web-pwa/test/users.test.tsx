import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api } from "@splashh/api-client";
import { useCreateUser } from "../src/features/admin/users/useUsers";

function Probe() {
  const create = useCreateUser();
  return (
    <button
      onClick={() =>
        create.mutate({
          email: "new@example.com",
          full_name: "New User",
          password: "verysecurepassword123",
          roles: ["customer"],
        })
      }
    >
      create
    </button>
  );
}

it("posts to /auth/users and returns the new user", async () => {
  (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
    data: { id: "u1", email: "new@example.com", full_name: "New User", roles: ["customer"] },
  });
  render(
    <QueryClientProvider client={new QueryClient()}>
      <Probe />
    </QueryClientProvider>,
  );
  await userEvent.click(screen.getByRole("button", { name: "create" }));
  await waitFor(() => {
    expect(api.post).toHaveBeenCalledWith(
      "/auth/users",
      expect.objectContaining({ email: "new@example.com", roles: ["customer"] }),
    );
  });
});
