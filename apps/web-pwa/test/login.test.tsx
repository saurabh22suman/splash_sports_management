import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { LoginForm } from "@/features/auth/LoginForm";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { post: vi.fn() } };
});

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api } from "@splashh/api-client";

const renderForm = () => {
  const qc = new QueryClient();
  const onSuccess = vi.fn();
  render(
    <QueryClientProvider client={qc}>
      <LoginForm onSuccess={onSuccess} />
    </QueryClientProvider>,
  );
  return { onSuccess };
};

describe("LoginForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows validation error for empty fields", async () => {
    const { onSuccess } = renderForm();
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    expect(await screen.findByText(/enter a valid email/i)).toBeInTheDocument();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("submits when fields are valid", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: { access_token: "t", user_id: "u1", tenant_id: "t1" },
    });
    const { onSuccess } = renderForm();
    await userEvent.type(screen.getByLabelText(/email/i), "u@example.com");
    await userEvent.type(screen.getByLabelText(/password/i), "password123");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });
});
