import { create } from 'zustand';
import { User } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
}

const STORAGE_KEY = 'certverify_auth';

const loadInitialState = (): { user: User | null; token: string | null; isAuthenticated: boolean } => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed.token && parsed.user) {
        return {
          user: parsed.user,
          token: parsed.token,
          isAuthenticated: true,
        };
      }
    }
  } catch {
    // Ignore JSON parse errors
  }
  return {
    user: null,
    token: null,
    isAuthenticated: false,
  };
};

export const useAuthStore = create<AuthState>((set) => ({
  ...loadInitialState(),
  setAuth: (token: string, user: User) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ token, user }));
    set({ token, user, isAuthenticated: true });
  },
  clearAuth: () => {
    localStorage.removeItem(STORAGE_KEY);
    set({ token: null, user: null, isAuthenticated: false });
  },
}));

