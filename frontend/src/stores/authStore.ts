// Authentication store
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User, Tenant, Workspace } from '@/types';
import { setToken, clearAuthTokens } from '@/utils/token';

interface AuthState {
  user: User | null;
  token: string | null;
  currentTenant: Tenant | null;
  currentWorkspace: Workspace | null;
  workspaces: Workspace[];
  isAuthenticated: boolean;

  // Actions
  setAuth: (user: User, token: string, tenant?: Tenant, workspace?: Workspace) => void;
  setUser: (user: User) => void;
  setTenant: (tenant: Tenant) => void;
  setWorkspace: (workspace: Workspace) => void;
  setWorkspaces: (workspaces: Workspace[]) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      currentTenant: null,
      currentWorkspace: null,
      workspaces: [],
      isAuthenticated: false,

      setAuth: (user, token, tenant, workspace) => {
        setToken(token);
        set({
          user,
          token,
          currentTenant: tenant || { id: user.tenant_id || '', name: user.tenant_id || '' },
          currentWorkspace: workspace || null,
          isAuthenticated: true,
        });
      },

      setUser: (user) => {
        set({ user });
      },

      setTenant: (tenant) => {
        set({ currentTenant: tenant });
      },

      setWorkspace: (workspace) => {
        set({ currentWorkspace: workspace });
      },

      setWorkspaces: (workspaces) => {
        set({ workspaces });
      },

      clearAuth: () => {
        clearAuthTokens();
        set({
          user: null,
          token: null,
          currentTenant: null,
          currentWorkspace: null,
          workspaces: [],
          isAuthenticated: false,
        });
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        currentTenant: state.currentTenant,
        currentWorkspace: state.currentWorkspace,
        workspaces: state.workspaces,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
