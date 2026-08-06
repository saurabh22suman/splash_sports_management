import { api, useAuthStore } from "@splashh/api-client";

export async function loginRequest(email: string, password: string): Promise<void> {
  const res = await api.post("/auth/login", { email, password });
  const data = res.data as {
    access_token: string;
    user_id: string;
    tenant_id: string;
  };
  useAuthStore.getState().setSession({
    accessToken: data.access_token,
    userId: data.user_id,
    tenantId: data.tenant_id,
    roles: [],
  });
}
