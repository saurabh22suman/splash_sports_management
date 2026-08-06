import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/auth/store";

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.getState().clear();
  });
  it("starts unauthenticated", () => {
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
  it("setSession populates token + user", () => {
    useAuthStore.getState().setSession({
      accessToken: "abc",
      userId: "u1",
      tenantId: "t1",
      roles: ["tenant_admin"],
    });
    expect(useAuthStore.getState().accessToken).toBe("abc");
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().roles).toEqual(["tenant_admin"]);
  });
  it("clear wipes state", () => {
    useAuthStore.getState().setSession({ accessToken: "abc", userId: "u1", tenantId: "t1", roles: [] });
    useAuthStore.getState().clear();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
