import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("@splashh/api-client", async () => {
  const actual = await vi.importActual<typeof import("@splashh/api-client")>("@splashh/api-client");
  return { ...actual, api: { post: vi.fn() } };
});

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: vi.fn() };
});

// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { api, useAuthStore } from "@splashh/api-client";
import { useNavigate } from "react-router-dom";
import { useLogout } from "@/features/auth/useLogout";

const setup = () => {
  const qc = new QueryClient();
  const navigate = vi.fn();
  (useNavigate as ReturnType<typeof vi.fn>).mockReturnValue(navigate);
  useAuthStore.setState({
    accessToken: "t",
    userId: "u1",
    tenantId: "ten1",
    roles: ["customer"],
    isAuthenticated: true,
  });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  return { navigate, wrapper };
};

describe("useLogout", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAuthStore.setState({
      accessToken: null, userId: null, tenantId: null, roles: [], isAuthenticated: false,
    });
  });

  it("calls POST /auth/logout on mutate", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: {} });
    const { wrapper } = setup();
    useAuthStore.setState({ accessToken: "t", isAuthenticated: true });
    const { result } = renderHook(() => useLogout(), { wrapper });
    await act(async () => { result.current.mutate(); });
    expect(api.post).toHaveBeenCalledWith("/auth/logout");
  });

  it("clears the auth store and navigates to / on success", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: {} });
    const { navigate, wrapper } = setup();
    useAuthStore.setState({ accessToken: "t", isAuthenticated: true });
    const { result } = renderHook(() => useLogout(), { wrapper });
    await act(async () => { result.current.mutate(); });
    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(navigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });

  it("still clears and navigates on API error (graceful degradation)", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("network down"));
    const { navigate, wrapper } = setup();
    useAuthStore.setState({ accessToken: "t", isAuthenticated: true });
    const { result } = renderHook(() => useLogout(), { wrapper });
    await act(async () => { result.current.mutate(); });
    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(navigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });
});
