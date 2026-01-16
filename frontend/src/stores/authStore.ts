// Authentication store
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User, Tenant, Workspace } from '@/types';
import { setToken, clearAuthTokens, isTokenExpired, getToken } from '@/utils/token';

interface AuthState {
  user: User | null;
  token: string | null;
  currentTenant: Tenant | null;
  currentWorkspace: Workspace | null;
  workspaces: Workspace[];
  isAuthenticated: boolean;
  _hasHydrated: boolean;

  // Actions
  setAuth: (user: User, token: string, tenant?: Tenant, workspace?: Workspace) => void;
  setUser: (user: User) => void;
  setTenant: (tenant: Tenant) => void;
  setWorkspace: (workspace: Workspace) => void;
  setWorkspaces: (workspaces: Workspace[]) => void;
  clearAuth: () => void;
  setHasHydrated: (state: boolean) => void;
  validateAndHydrate: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      currentTenant: null,
      currentWorkspace: null,
      workspaces: [],
      isAuthenticated: false,
      _hasHydrated: false,

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

      setHasHydrated: (state) => {
        set({ _hasHydrated: state });
      },

      validateAndHydrate: () => {
        const state = get();
        const { token, isAuthenticated } = state;
        
        // Check if we have a token and it's valid
        if (token && isAuthenticated) {
          if (isTokenExpired(token)) {
            // Token is expired, clear auth state
            console.log('[Auth] Token expired during validation, clearing auth state');
            clearAuthTokens();
            set({
              user: null,
              token: null,
              currentTenant: null,
              currentWorkspace: null,
              workspaces: [],
              isAuthenticated: false,
              _hasHydrated: true,
            });
            return;
          }
          // Token is valid, ensure it's also in localStorage
          const storedToken = getToken();
          if (!storedToken) {
            setToken(token);
          }
        }
        
        set({ _hasHydrated: true });
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
      onRehydrateStorage: () => (state) => {
        // Called after rehydration completes
        if (state) {
          // Use setTimeout to ensure state is fully restored before validation
          setTimeout(() => {
            state.validateAndHydrate();
          }, 0);
        }
      },
    }
  )
);

// Initialize hydration check for SSR/initial load scenarios
if (typeof window !== 'undefined') {
  // Ensure hydration happens even if onRehydrateStorage doesn't fire
  const checkHydration = () => {
    const state = useAuthStore.getState();
    if (!state._hasHydrated) {
      state.validateAndHydrate();
    }
  };
  
  // Check after a short delay to allow persist middleware to complete
  setTimeout(checkHydration, 50);
}
