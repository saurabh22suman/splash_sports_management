import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, useAuthStore } from "@splashh/api-client";

export function useLogout() {
  const navigate = useNavigate();
  return useMutation({
    mutationFn: async () => {
      try {
        await api.post("/auth/logout");
      } catch {
        // swallow: local logout still proceeds
      }
    },
    onSettled: () => {
      useAuthStore.getState().clear();
      navigate("/", { replace: true });
    },
  });
}
