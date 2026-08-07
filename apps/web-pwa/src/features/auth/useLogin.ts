import { useMutation } from "@tanstack/react-query";
import { loginRequest } from "./api";

export function useLogin() {
  return useMutation({
    mutationFn: (input: { email: string; password: string; mode?: "customer" | "staff" }) =>
      loginRequest(input.email, input.password, input.mode),
  });
}
