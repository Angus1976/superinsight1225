/**
 * Multi-Tenant Workspace API Service
 * 
 * Provides API functions for:
 * - Tenant management
 * - Workspace management
 * - Member management
 * - Quota management
 * - Cross-tenant collaboration
 * - Admin console
 */

import { api } from './api';

// ============================================================================
// Types
// ============================================================================

export type TenantStatus = 'active' | 'suspended' | 'disabled';
export type WorkspaceStatus = 'active' | 'archived' | 'deleted';
export type MemberRole = 'owner' | 'admin' | 'member' | 'guest';
export type SharePermission = 'read_only' | 'edit';
export type EntityType = 'tenant' | 'workspace';
export type ResourceType = 'storage_bytes' | 'project_count' | 'user_count' | 'api_call_count';

export interface TenantConfig {
  features: Record<string, boolean>;
  security: Record<string, any>;
  workspace_defaults: Record<string, any>;
  custom_settings: Record<string, any>;
}

export interface Tenant {
  id: string;
  name: string;
  description?: string;
  status: TenantStatus;
  admin_email: string;
  plan: string;
  config: TenantConfig;
  created_at: string;
  updated_at: string;
}

export interface TenantCreateRequest {
  name: string;
  description?: string;
  admin_email: string;
  plan?: string;
  config?: Partial<TenantConfig>;
}

export interface TenantUpdateRequest {
  name?: string;
  description?: string;
  admin_email?: string;
  plan?: string;
  config?: Partial<TenantConfig>;
}

export interface Workspace {
  id: string;
  tenant_id: string;
  parent_id?: string;
  name: string;
  description?: string;
  status: WorkspaceStatus;
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceNode extends Workspace {
  children: WorkspaceNode[];
}

export interface WorkspaceCreateRequest {
  name: string;
  description?: string;
  parent_id?: string;
  template_id?: string;
  config?: Record<string, any>;
}

export interface WorkspaceUpdateRequest {
  name?: string;
  description?: string;
  config?: Record<string, any>;
}

export interface WorkspaceMember {
  id: string;
  user_id: string;
  workspace_id: string;
  role: MemberRole;
  custom_role_id?: string;
  joined_at: string;
  last_active_at?: string;
}

export interface MemberAddRequest {
  user_id: string;
  role: MemberRole;
  custom_role_id?: string;
}

export interface InvitationConfig {
  email: string;
  role: MemberRole;
  message?: string;
  expires_in_days?: number;
}

export interface Invitation {
  id: string;
  workspace_id: string;
  email: string;
  role: MemberRole;
  token: string;
  expires_at: string;
  created_at: string;
}

export interface CustomRole {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  permissions: string[];
  created_at: string;
}

export interface CustomRoleConfig {
  name: string;
  description?: string;
  permissions: string[];
}

export interface QuotaConfig {
  storage_bytes: number;
  project_count: number;
  user_count: number;
  api_call_count: number;
}

export interface QuotaUsage {
  storage_bytes: number;
  project_count: number;
  user_count: number;
  api_call_count: number;
  last_updated: string;
}

export interface QuotaResponse {
  entity_id: string;
  entity_type: EntityType;
  storage_bytes: number;
  project_count: number;
  user_count: number;
  api_call_count: number;
  created_at: string;
  updated_at: string;
}

export interface QuotaCheckResult {
  allowed: boolean;
  percentage: number;
  reason?: string;
  warning?: string;
}

export interface ShareLink {
  id: string;
  resource_id: string;
  resource_type: string;
  permission: SharePermission;
  token: string;
  owner_tenant_id: string;
  expires_at: string;
  created_at: string;
  revoked: boolean;
}

export interface CreateShareRequest {
  resource_id: string;
  resource_type: string;
  permission?: SharePermission;
  expires_in_days?: number;
}

export interface WhitelistConfig {
  allowed_tenant_ids: string[];
}

export interface AdminDashboard {
  tenant_stats: {
    total_tenants: number;
    active_tenants: number;
    suspended_tenants: number;
    disabled_tenants: number;
  };
  workspace_stats: {
    total_workspaces: number;
    active_workspaces: number;
    archived_workspaces: number;
  };
  user_stats: {
    total_users: number;
    active_users_today: number;
    active_users_week: number;
  };
  system_health: {
    database: string;
    cache: string;
    storage: string;
    overall: string;
  };
  last_updated: string;
}

export interface ServiceStatus {
  name: string;
  status: string;
  version?: string;
  uptime?: string;
  last_check: string;
}

export interface SystemConfig {
  max_tenants: number;
  max_workspaces_per_tenant: number;
  max_users_per_workspace: number;
  default_storage_quota_gb: number;
  enable_cross_tenant_sharing: boolean;
  audit_log_retention_days: number;
}

export interface SystemConfigRequest {
  max_tenants?: number;
  max_workspaces_per_tenant?: number;
  max_users_per_workspace?: number;
  default_storage_quota_gb?: number;
  enable_cross_tenant_sharing?: boolean;
  audit_log_retention_days?: number;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user_id?: string;
  tenant_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
}

// ============================================================================
// Tenant API
// ============================================================================

export const tenantApi = {
  create: (data: TenantCreateRequest) => 
    api.post<Tenant>('/api/v1/tenants', data),
  
  list: (params?: { status?: TenantStatus; skip?: number; limit?: number }) =>
    api.get<Tenant[]>('/api/v1/tenants', { params }),
  
  get: (tenantId: string) =>
    api.get<Tenant>(`/api/v1/tenants/${tenantId}`),
  
  update: (tenantId: string, data: TenantUpdateRequest) =>
    api.put<Tenant>(`/api/v1/tenants/${tenantId}`, data),
  
  setStatus: (tenantId: string, status: TenantStatus) =>
    api.put<Tenant>(`/api/v1/tenants/${tenantId}/status`, null, { params: { new_status: status } }),
  
  delete: (tenantId: string) =>
    api.delete(`/api/v1/tenants/${tenantId}`),
};

// ============================================================================
// Workspace API
// ============================================================================

export const workspaceApi = {
  create: (data: WorkspaceCreateRequest) =>
    api.post<Workspace>('/api/v1/workspaces', data),
  
  list: (params?: { tenant_id?: string; status?: WorkspaceStatus; skip?: number; limit?: number }) =>
    api.get<Workspace[]>('/api/v1/workspaces', { params }),
  
  getHierarchy: (tenantId?: string) =>
    api.get<WorkspaceNode[]>('/api/v1/workspaces/hierarchy', { params: { tenant_id: tenantId } }),
  
  get: (workspaceId: string) =>
    api.get<Workspace>(`/api/v1/workspaces/${workspaceId}`),
  
  update: (workspaceId: string, data: WorkspaceUpdateRequest) =>
    api.put<Workspace>(`/api/v1/workspaces/${workspaceId}`, data),
  
  archive: (workspaceId: string) =>
    api.post<Workspace>(`/api/v1/workspaces/${workspaceId}/archive`),
  
  restore: (workspaceId: string) =>
    api.post<Workspace>(`/api/v1/workspaces/${workspaceId}/restore`),
  
  move: (workspaceId: string, newParentId?: string) =>
    api.put<Workspace>(`/api/v1/workspaces/${workspaceId}/move`, null, { params: { new_parent_id: newParentId } }),
  
  delete: (workspaceId: string) =>
    api.delete(`/api/v1/workspaces/${workspaceId}`),
};

// ============================================================================
// Member API
// ============================================================================

export const memberApi = {
  invite: (workspaceId: string, data: InvitationConfig) =>
    api.post<Invitation>(`/api/v1/workspaces/${workspaceId}/members/invite`, data),
  
  add: (workspaceId: string, data: MemberAddRequest) =>
    api.post<WorkspaceMember>(`/api/v1/workspaces/${workspaceId}/members`, data),
  
  list: (workspaceId: string, params?: { skip?: number; limit?: number }) =>
    api.get<WorkspaceMember[]>(`/api/v1/workspaces/${workspaceId}/members`, { params }),
  
  updateRole: (workspaceId: string, userId: string, role: MemberRole) =>
    api.put<WorkspaceMember>(`/api/v1/workspaces/${workspaceId}/members/${userId}/role`, null, { params: { role } }),
  
  remove: (workspaceId: string, userId: string) =>
    api.delete(`/api/v1/workspaces/${workspaceId}/members/${userId}`),
  
  batchAdd: (workspaceId: string, members: MemberAddRequest[]) =>
    api.post<WorkspaceMember[]>(`/api/v1/workspaces/${workspaceId}/members/batch`, { members }),
  
  createCustomRole: (workspaceId: string, data: CustomRoleConfig) =>
    api.post<CustomRole>(`/api/v1/workspaces/${workspaceId}/roles`, data),
};

// ============================================================================
// Quota API
// ============================================================================

export const quotaApi = {
  get: (entityType: EntityType, entityId: string) =>
    api.get<QuotaResponse>(`/api/v1/quotas/${entityType}/${entityId}`),
  
  set: (entityType: EntityType, entityId: string, data: QuotaConfig) =>
    api.put<QuotaResponse>(`/api/v1/quotas/${entityType}/${entityId}`, data),
  
  getUsage: (entityType: EntityType, entityId: string) =>
    api.get<QuotaUsage>(`/api/v1/quotas/${entityType}/${entityId}/usage`),
  
  check: (entityType: EntityType, entityId: string, resourceType: ResourceType, amount?: number) =>
    api.post<QuotaCheckResult>(`/api/v1/quotas/${entityType}/${entityId}/check`, null, {
      params: { resource_type: resourceType, amount },
    }),
};

// ============================================================================
// Share API (Cross-Tenant Collaboration)
// ============================================================================

export const shareApi = {
  create: (data: CreateShareRequest) =>
    api.post<ShareLink>('/api/v1/shares', data),
  
  access: (token: string) =>
    api.get<any>(`/api/v1/shares/${token}`),
  
  revoke: (shareId: string) =>
    api.delete(`/api/v1/shares/${shareId}`),
  
  list: (params?: { skip?: number; limit?: number }) =>
    api.get<ShareLink[]>('/api/v1/shares', { params }),
  
  setWhitelist: (tenantId: string, data: WhitelistConfig) =>
    api.put(`/api/v1/tenants/${tenantId}/whitelist`, data),
  
  getWhitelist: (tenantId: string) =>
    api.get<WhitelistConfig>(`/api/v1/tenants/${tenantId}/whitelist`),
};

// ============================================================================
// Admin API
// ============================================================================

export const adminApi = {
  getDashboard: () =>
    api.get<AdminDashboard>('/api/v1/admin/dashboard'),
  
  getServices: () =>
    api.get<ServiceStatus[]>('/api/v1/admin/services'),
  
  getConfig: () =>
    api.get<SystemConfig>('/api/v1/admin/config'),
  
  updateConfig: (data: SystemConfigRequest) =>
    api.put<SystemConfig>('/api/v1/admin/config', data),
  
  getAuditLogs: (params?: {
    tenant_id?: string;
    user_id?: string;
    action?: string;
    resource_type?: string;
    start_date?: string;
    end_date?: string;
    skip?: number;
    limit?: number;
  }) =>
    api.get<AuditLogEntry[]>('/api/v1/admin/audit-logs', { params }),
};

export default {
  tenant: tenantApi,
  workspace: workspaceApi,
  member: memberApi,
  quota: quotaApi,
  share: shareApi,
  admin: adminApi,
};
