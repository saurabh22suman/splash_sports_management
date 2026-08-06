import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usersApi, type CreateUserInput } from "./api";

export const userKeys = {
  all: ["users"] as const,
  list: (tenantId: string) => ["users", "list", tenantId] as const,
};

export function useUsers() {
  return useQuery({ queryKey: userKeys.all, queryFn: usersApi.list });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateUserInput) => usersApi.create(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}
