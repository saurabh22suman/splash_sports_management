import { api, useAuthStore } from "@splashh/api-client";

interface LoginResponse {
  access_token: string;
  user_id: string;
  customer_id: string;
  tenant_id: string;
  roles: string[];
}

export async function loginRequest(
  email: string,
  password: string,
  mode?: "customer" | "staff",
): Promise<string[]> {
  const res = await api.post<LoginResponse>("/auth/login", { email, password, mode });
  useAuthStore.getState().setSession({
    accessToken: res.data.access_token,
    userId: res.data.user_id,
    customerId: res.data.customer_id,
    tenantId: res.data.tenant_id,
    roles: res.data.roles ?? [],
  });
  return res.data.roles ?? [];
}
