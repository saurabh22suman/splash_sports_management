import { create } from "zustand";

export interface Session {
  accessToken: string;
  userId: string;
  customerId: string;
  tenantId: string;
  roles: string[];
}

interface AuthState {
  accessToken: string | null;
  userId: string | null;
  customerId: string | null;
  tenantId: string | null;
  roles: string[];
  isAuthenticated: boolean;
  setSession: (s: Session) => void;
  setAccessToken: (token: string) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  userId: null,
  customerId: null,
  tenantId: null,
  roles: [],
  isAuthenticated: false,
  setSession: (s) =>
    set({
      accessToken: s.accessToken,
      userId: s.userId,
      customerId: s.customerId,
      tenantId: s.tenantId,
      roles: s.roles,
      isAuthenticated: true,
    }),
  setAccessToken: (token) => set({ accessToken: token, isAuthenticated: true }),
  clear: () => set({ accessToken: null, userId: null, customerId: null, tenantId: null, roles: [], isAuthenticated: false }),
}));
