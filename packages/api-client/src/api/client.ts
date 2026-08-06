import axios, { type AxiosInstance } from "axios";
import { useAuthStore } from "@/auth/store";

const baseURL = "/v1";

export const api: AxiosInstance = axios.create({ baseURL, withCredentials: true });

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});
