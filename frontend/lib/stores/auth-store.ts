"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type UserRole = "basic" | "advanced";

interface AuthState {
  token: string | null;
  username: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  setAuth: (token: string, username: string, role: UserRole) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      username: null,
      role: null,
      isAuthenticated: false,

      setAuth: (token, username, role) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("accessToken", token);
          // Set cookies for middleware access (httpOnly not possible from JS, but enough for route guard)
          document.cookie = `access_token=${token}; path=/; max-age=${8 * 3600}; SameSite=Lax`;
          document.cookie = `user_role=${role}; path=/; max-age=${8 * 3600}; SameSite=Lax`;
        }
        set({ token, username, role, isAuthenticated: true });
      },

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("accessToken");
          document.cookie = "access_token=; path=/; max-age=0";
          document.cookie = "user_role=; path=/; max-age=0";
        }
        set({ token: null, username: null, role: null, isAuthenticated: false });
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        token: state.token,
        username: state.username,
        role: state.role,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
