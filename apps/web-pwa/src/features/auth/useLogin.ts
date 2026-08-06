import { useMutation } from "@tanstack/react-query";
import { loginRequest } from "./api";

export function useLogin() {
  return useMutation({
    mutationFn: (input: { email: string; password: string }) =>
      loginRequest(input.email, input.password),
  });
}
