/**
 * RBAC API Service for SuperInsight Platform
 * 
 * Provides API client functions for Role-Based Access Control management.
 */

import apiClient from './api/client';

// ============================================================================
// Types
// ============================================================================

export interface Permission {
  resource: string;
  action: string;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  permissions: Permission[];
  parent_role_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface UserRoleAssignment {
  id: string;
  user_id: string;
  role_id: string;
  role_name: string;
  granted_by?: string;
  granted_at: string;
  expires_at?: string;
}

export interface CreateRoleRequest {
  name: string;
  description?: string;
  permissions: Permission[];
  parent_role_id?: string;
}

export interface UpdateRoleRequest {
  name?: string;
  description?: string;
  permissions?: Permission[];
  parent_role_id?: string;
}

export interface AssignRoleRequest {
  role_id: string;
  expires_at?: string;
}

export interface CheckPermissionRequest {
  user_id: string;
  resource: string;
  action: string;
  ip_address?: string;
  attributes?: Record<string, unknown>;
}

export interface PermissionCheckResponse {
  allowed: boolean;
  reason?: string;
  checked_at: string;
}

export interface UserPermissions {
  user_id: string;
  permissions: Permission[];
  total_count: number;
}

// ============================================================================
// API Functions
// ============================================================================

const BASE_URL = '/api/v1/rbac';

export const rbacApi = {
  // Role Management
  async createRole(data: CreateRoleRequest): Promise<Role> {
    const response = await apiClient.post<Role>(`${BASE_URL}/roles`, data);
    return response.data;
  },

  async listRoles(params?: {
    skip?: number;
    limit?: number;
    search?: string;
  }): Promise<Role[]> {
    const response = await apiClient.get<Role[]>(`${BASE_URL}/roles`, { params });
    return response.data;
  },

  async getRole(roleId: string): Promise<Role> {
    const response = await apiClient.get<Role>(`${BASE_URL}/roles/${roleId}`);
    return response.data;
  },

  async updateRole(roleId: string, data: UpdateRoleRequest): Promise<Role> {
    const response = await apiClient.put<Role>(`${BASE_URL}/roles/${roleId}`, data);
    return response.data;
  },

  async deleteRole(roleId: string): Promise<void> {
    await apiClient.delete(`${BASE_URL}/roles/${roleId}`);
  },

  // User Role Assignment
  async assignRoleToUser(userId: string, data: AssignRoleRequest): Promise<UserRoleAssignment> {
    const response = await apiClient.post<UserRoleAssignment>(
      `${BASE_URL}/users/${userId}/roles`,
      data
    );
    return response.data;
  },

  async getUserRoles(userId: string): Promise<UserRoleAssignment[]> {
    const response = await apiClient.get<UserRoleAssignment[]>(
      `${BASE_URL}/users/${userId}/roles`
    );
    return response.data;
  },

  async revokeRoleFromUser(userId: string, roleId: string): Promise<void> {
    await apiClient.delete(`${BASE_URL}/users/${userId}/roles/${roleId}`);
  },

  // Permission Checking
  async checkPermission(data: CheckPermissionRequest): Promise<PermissionCheckResponse> {
    const response = await apiClient.post<PermissionCheckResponse>(
      `${BASE_URL}/check`,
      data
    );
    return response.data;
  },

  async checkPermissionsBulk(
    userId: string,
    checks: Array<{ resource: string; action: string }>
  ): Promise<{ results: PermissionCheckResponse[] }> {
    const response = await apiClient.post<{ results: PermissionCheckResponse[] }>(
      `${BASE_URL}/check/bulk`,
      { user_id: userId, checks }
    );
    return response.data;
  },

  async getUserPermissions(userId: string): Promise<UserPermissions> {
    const response = await apiClient.get<UserPermissions>(
      `${BASE_URL}/users/${userId}/permissions`
    );
    return response.data;
  },
};

export default rbacApi;
