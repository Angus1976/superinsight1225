// Authentication service
import apiClient from './api/client';
import { API_ENDPOINTS } from '@/constants';
import { apiRequestToSnake, apiResponseToSnake } from '@/utils/jsonCase';
import type { LoginCredentials, LoginResponse, User, Tenant, Workspace } from '@/types';

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  tenant_name?: string;
  invite_code?: string;
}

export interface SwitchWorkspaceResponse {
  success: boolean;
  workspace: Workspace;
  message?: string;
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    // Backend expects 'email' field, but frontend uses 'username'
    // Convert username to email for login request
    const loginPayload = {
      email: credentials.username, // Use username as email for login
      password: credentials.password,
    };
    const response = await apiClient.post<LoginResponse>(
      API_ENDPOINTS.AUTH.LOGIN,
      apiRequestToSnake(loginPayload)
    );
    return apiResponseToSnake<LoginResponse>(response.data);
  },

  async register(payload: RegisterPayload): Promise<void> {
    await apiClient.post(API_ENDPOINTS.AUTH.REGISTER, apiRequestToSnake(payload));
  },

  async logout(): Promise<void> {
    await apiClient.post(API_ENDPOINTS.AUTH.LOGOUT);
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>(API_ENDPOINTS.AUTH.CURRENT_USER);
    return apiResponseToSnake<User>(response.data);
  },

  async getTenants(): Promise<Tenant[]> {
    const response = await apiClient.get<Tenant[]>(API_ENDPOINTS.ADMIN.TENANTS);
    return apiResponseToSnake<Tenant[]>(response.data);
  },

  async switchTenant(tenantId: string): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>(
      API_ENDPOINTS.AUTH.SWITCH_TENANT,
      apiRequestToSnake({ tenant_id: tenantId })
    );
    return apiResponseToSnake<LoginResponse>(response.data);
  },

  // Workspace operations
  async getWorkspaces(): Promise<Workspace[]> {
    const response = await apiClient.get<Workspace[]>(API_ENDPOINTS.WORKSPACES.MY_WORKSPACES);
    return apiResponseToSnake<Workspace[]>(response.data);
  },

  async getWorkspaceById(workspaceId: string): Promise<Workspace> {
    const response = await apiClient.get<Workspace>(API_ENDPOINTS.WORKSPACES.BY_ID(workspaceId));
    return apiResponseToSnake<Workspace>(response.data);
  },

  async switchWorkspace(workspaceId: string): Promise<SwitchWorkspaceResponse> {
    const response = await apiClient.post<SwitchWorkspaceResponse>(
      API_ENDPOINTS.WORKSPACES.SWITCH,
      apiRequestToSnake({ workspace_id: workspaceId })
    );
    return apiResponseToSnake<SwitchWorkspaceResponse>(response.data);
  },

  async createWorkspace(data: { name: string; description?: string }): Promise<Workspace> {
    const response = await apiClient.post<Workspace>(
      API_ENDPOINTS.WORKSPACES.BASE,
      apiRequestToSnake(data)
    );
    return apiResponseToSnake<Workspace>(response.data);
  },

  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>(
      API_ENDPOINTS.AUTH.REFRESH,
      apiRequestToSnake({ refresh_token: refreshToken })
    );
    return apiResponseToSnake<LoginResponse>(response.data);
  },

  async requestPasswordReset(email: string): Promise<void> {
    await apiClient.post(API_ENDPOINTS.AUTH.FORGOT_PASSWORD, apiRequestToSnake({ email }));
  },

  async resetPassword(data: { token: string; email: string; password: string }): Promise<void> {
    await apiClient.post(API_ENDPOINTS.AUTH.RESET_PASSWORD, apiRequestToSnake(data));
  },
};
