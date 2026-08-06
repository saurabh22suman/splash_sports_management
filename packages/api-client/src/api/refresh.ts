import { useAuthStore } from "../auth/store.js";

let inflight: Promise<string> | null = null;

export async function silentRefresh(): Promise<string> {
  if (inflight) return inflight;
  inflight = doRefresh().finally(() => {
    inflight = null;
  });
  return inflight;
}

async function doRefresh(): Promise<string> {
  const res = await fetch("/v1/auth/refresh", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    useAuthStore.getState().clear();
    throw new Error(`refresh failed: ${res.status}`);
  }
  const data = (await res.json()) as {
    access_token: string;
    user_id?: string;
    tenant_id?: string;
    roles?: string[];
  };
  useAuthStore.getState().setSession({
    accessToken: data.access_token,
    userId: data.user_id ?? useAuthStore.getState().userId ?? "",
    tenantId: data.tenant_id ?? useAuthStore.getState().tenantId ?? "",
    roles: data.roles ?? useAuthStore.getState().roles,
  });
  return data.access_token;
}
