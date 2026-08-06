import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/auth/store";
import { silentRefresh } from "./refresh";

const baseURL = "/v1";

export const api: AxiosInstance = axios.create({ baseURL, withCredentials: true });

// Request: attach Bearer
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

// Response: silent refresh on 401
type RetryConfig = InternalAxiosRequestConfig & { _retried?: boolean };

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config as RetryConfig | undefined;
    const status = error.response?.status;
    if (status === 401 && original && !original._retried) {
      original._retried = true;
      try {
        const token = await silentRefresh();
        original.headers?.set("Authorization", `Bearer ${token}`);
        return api.request(original);
      } catch {
        useAuthStore.getState().clear();
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  },
);
