import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/auth/store";
import { silentRefresh } from "@/api/refresh";

describe("silentRefresh", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("stores the new access token on success", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: "new-tok" }), { status: 200 }),
    );
    const token = await silentRefresh();
    expect(token).toBe("new-tok");
    expect(useAuthStore.getState().accessToken).toBe("new-tok");
  });

  it("clears the store on failure", async () => {
    useAuthStore.getState().setAccessToken("old");
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("", { status: 401 }));
    await expect(silentRefresh()).rejects.toBeTruthy();
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it("is single-flight: concurrent calls share one request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ access_token: "shared" }), { status: 200 }),
    );
    const [a, b] = await Promise.all([silentRefresh(), silentRefresh()]);
    expect(a).toBe("shared");
    expect(b).toBe("shared");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
