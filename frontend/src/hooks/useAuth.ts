// Authentication hook
import { useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/auth';
import { ROUTES } from '@/constants';
import type { LoginCredentials, Workspace } from '@/types';

export function useAuth() {
  const navigate = useNavigate();
  const { 
    user, 
    token, 
    currentTenant, 
    currentWorkspace,
    workspaces,
    isAuthenticated, 
    setAuth, 
    setWorkspace,
    setWorkspaces,
    clearAuth 
  } = useAuthStore();

  // Load workspaces when user is authenticated
  useEffect(() => {
    const loadWorkspaces = async () => {
      if (isAuthenticated && user) {
        try {
          const workspaceList = await authService.getWorkspaces();
          setWorkspaces(workspaceList);
          
          // Set default workspace if not already set
          if (!currentWorkspace && workspaceList.length > 0) {
            const defaultWorkspace = workspaceList.find(w => w.is_default) || workspaceList[0];
            setWorkspace(defaultWorkspace);
          }
        } catch (error) {
          console.error('Failed to load workspaces:', error);
        }
      }
    };

    loadWorkspaces();
  }, [isAuthenticated, user, currentWorkspace, setWorkspaces, setWorkspace]);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      try {
        const response = await authService.login(credentials);
        
        // Use user info from response
        const user = response.user || {
          id: '',
          username: credentials.username,
          email: '',
          role: '',
          tenant_id: '',
        };
        
        // Ensure user has all required fields
        const fullUser: typeof user = {
          id: user.id || '',
          username: user.username || credentials.username,
          email: user.email || '',
          full_name: user.full_name || '',
          role: user.role || '',
          tenant_id: user.tenant_id || credentials.tenant_id || '',
          is_active: user.is_active !== false,
          last_login: user.last_login,
        };
        
        // Save authentication info
        setAuth(
          fullUser,
          response.access_token,
          {
            id: fullUser.tenant_id || 'default_tenant',
            name: fullUser.tenant_id || 'Default Tenant',
          }
        );

        message.success('登录成功');
        navigate(ROUTES.DASHBOARD);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '登录失败，请检查用户名和密码';
        message.error(errorMessage);
        throw error;
      }
    },
    [navigate, setAuth]
  );

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } catch {
      // Ignore logout errors
    } finally {
      clearAuth();
      navigate(ROUTES.LOGIN);
      message.success('已退出登录');
    }
  }, [navigate, clearAuth]);

  const checkAuth = useCallback(async () => {
    if (!token) {
      return false;
    }
    try {
      const userInfo = await authService.getCurrentUser();
      setAuth(userInfo, token, currentTenant || undefined, currentWorkspace || undefined);
      return true;
    } catch {
      clearAuth();
      return false;
    }
  }, [token, currentTenant, currentWorkspace, setAuth, clearAuth]);

  const switchTenant = useCallback(
    async (tenantId: string) => {
      try {
        const response = await authService.switchTenant(tenantId);
        
        // Update auth state with new tenant context
        const updatedUser = { ...user!, tenant_id: tenantId };
        const newTenant = { id: tenantId, name: tenantId };
        
        setAuth(updatedUser, response.access_token, newTenant);
        
        return true;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to switch tenant';
        message.error(errorMessage);
        throw error;
      }
    },
    [user, setAuth]
  );

  const switchWorkspace = useCallback(
    async (workspaceId: string): Promise<boolean> => {
      try {
        const response = await authService.switchWorkspace(workspaceId);
        
        if (response.success) {
          setWorkspace(response.workspace);
          message.success(`已切换到工作空间: ${response.workspace.name}`);
          return true;
        }
        
        return false;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '切换工作空间失败';
        message.error(errorMessage);
        throw error;
      }
    },
    [setWorkspace]
  );

  const refreshWorkspaces = useCallback(async (): Promise<Workspace[]> => {
    try {
      const workspaceList = await authService.getWorkspaces();
      setWorkspaces(workspaceList);
      return workspaceList;
    } catch (error) {
      console.error('Failed to refresh workspaces:', error);
      return [];
    }
  }, [setWorkspaces]);

  const createWorkspace = useCallback(
    async (data: { name: string; description?: string }): Promise<Workspace | null> => {
      try {
        const newWorkspace = await authService.createWorkspace(data);
        
        // Refresh workspace list
        await refreshWorkspaces();
        
        message.success(`工作空间 "${newWorkspace.name}" 创建成功`);
        return newWorkspace;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '创建工作空间失败';
        message.error(errorMessage);
        return null;
      }
    },
    [refreshWorkspaces]
  );

  return {
    user,
    token,
    currentTenant,
    currentWorkspace,
    workspaces,
    isAuthenticated,
    login,
    logout,
    checkAuth,
    switchTenant,
    switchWorkspace,
    refreshWorkspaces,
    createWorkspace,
  };
}
