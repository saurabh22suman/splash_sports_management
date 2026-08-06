import { api } from "@splashh/api-client";

export interface User {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  is_active: boolean;
  created_at: string;
}

export interface CreateUserInput {
  email: string;
  full_name: string;
  password: string;
  roles: Array<"customer" | "staff">;
}

export const usersApi = {
  list: () => api.get<{ data: User[] }>("/auth/users").then((r) => r.data.data),
  create: (input: CreateUserInput) => api.post<User>("/auth/users", input).then((r) => r.data),
};
