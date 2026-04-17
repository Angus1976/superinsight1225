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
import { keysToSnakeDeep } from '@/utils/jsonCase';

const norm = <T>(data: unknown): T => keysToSnakeDeep(data) as T;
const snakeBody = (data: unknown) => keysToSnakeDeep(data);

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
  async create(data: TenantCreateRequest): Promise<Tenant> {
    const r = await api.post<Tenant>('/api/v1/tenants', snakeBody(data));
    return norm<Tenant>(r.data);
  },

  async list(params?: { status?: TenantStatus; skip?: number; limit?: number }): Promise<Tenant[]> {
    const r = await api.get<Tenant[]>('/api/v1/tenants', { params });
    return norm<Tenant[]>(r.data);
  },

  async get(tenantId: string): Promise<Tenant> {
    const r = await api.get<Tenant>(`/api/v1/tenants/${tenantId}`);
    return norm<Tenant>(r.data);
  },

  async update(tenantId: string, data: TenantUpdateRequest): Promise<Tenant> {
    const r = await api.put<Tenant>(`/api/v1/tenants/${tenantId}`, snakeBody(data));
    return norm<Tenant>(r.data);
  },

  async setStatus(tenantId: string, status: TenantStatus): Promise<Tenant> {
    const r = await api.put<Tenant>(`/api/v1/tenants/${tenantId}/status`, null, { params: { new_status: status } });
    return norm<Tenant>(r.data);
  },

  async delete(tenantId: string): Promise<void> {
    await api.delete(`/api/v1/tenants/${tenantId}`);
  },
};

// ============================================================================
// Workspace API
// ============================================================================

export const workspaceApi = {
  async create(data: WorkspaceCreateRequest): Promise<Workspace> {
    const r = await api.post<Workspace>('/api/v1/workspaces', snakeBody(data));
    return norm<Workspace>(r.data);
  },

  async list(params?: { tenant_id?: string; status?: WorkspaceStatus; skip?: number; limit?: number }): Promise<Workspace[]> {
    const r = await api.get<Workspace[]>('/api/v1/workspaces', { params });
    return norm<Workspace[]>(r.data);
  },

  async getHierarchy(tenantId?: string): Promise<WorkspaceNode[]> {
    const r = await api.get<WorkspaceNode[]>('/api/v1/workspaces/hierarchy', { params: { tenant_id: tenantId } });
    return norm<WorkspaceNode[]>(r.data);
  },

  async get(workspaceId: string): Promise<Workspace> {
    const r = await api.get<Workspace>(`/api/v1/workspaces/${workspaceId}`);
    return norm<Workspace>(r.data);
  },

  async update(workspaceId: string, data: WorkspaceUpdateRequest): Promise<Workspace> {
    const r = await api.put<Workspace>(`/api/v1/workspaces/${workspaceId}`, snakeBody(data));
    return norm<Workspace>(r.data);
  },

  async archive(workspaceId: string): Promise<Workspace> {
    const r = await api.post<Workspace>(`/api/v1/workspaces/${workspaceId}/archive`);
    return norm<Workspace>(r.data);
  },

  async restore(workspaceId: string): Promise<Workspace> {
    const r = await api.post<Workspace>(`/api/v1/workspaces/${workspaceId}/restore`);
    return norm<Workspace>(r.data);
  },

  async move(workspaceId: string, newParentId?: string): Promise<Workspace> {
    const r = await api.put<Workspace>(`/api/v1/workspaces/${workspaceId}/move`, null, { params: { new_parent_id: newParentId } });
    return norm<Workspace>(r.data);
  },

  async delete(workspaceId: string): Promise<void> {
    await api.delete(`/api/v1/workspaces/${workspaceId}`);
  },
};

// ============================================================================
// Member API
// ============================================================================

export const memberApi = {
  async invite(workspaceId: string, data: InvitationConfig): Promise<Invitation> {
    const r = await api.post<Invitation>(`/api/v1/workspaces/${workspaceId}/members/invite`, snakeBody(data));
    return norm<Invitation>(r.data);
  },

  async add(workspaceId: string, data: MemberAddRequest): Promise<WorkspaceMember> {
    const r = await api.post<WorkspaceMember>(`/api/v1/workspaces/${workspaceId}/members`, snakeBody(data));
    return norm<WorkspaceMember>(r.data);
  },

  async list(workspaceId: string, params?: { skip?: number; limit?: number }): Promise<WorkspaceMember[]> {
    const r = await api.get<WorkspaceMember[]>(`/api/v1/workspaces/${workspaceId}/members`, { params });
    return norm<WorkspaceMember[]>(r.data);
  },

  async updateRole(workspaceId: string, userId: string, role: MemberRole): Promise<WorkspaceMember> {
    const r = await api.put<WorkspaceMember>(`/api/v1/workspaces/${workspaceId}/members/${userId}/role`, null, { params: { role } });
    return norm<WorkspaceMember>(r.data);
  },

  async remove(workspaceId: string, userId: string): Promise<void> {
    await api.delete(`/api/v1/workspaces/${workspaceId}/members/${userId}`);
  },

  async batchAdd(workspaceId: string, members: MemberAddRequest[]): Promise<WorkspaceMember[]> {
    const r = await api.post<WorkspaceMember[]>(`/api/v1/workspaces/${workspaceId}/members/batch`, snakeBody({ members }));
    return norm<WorkspaceMember[]>(r.data);
  },

  async createCustomRole(workspaceId: string, data: CustomRoleConfig): Promise<CustomRole> {
    const r = await api.post<CustomRole>(`/api/v1/workspaces/${workspaceId}/roles`, snakeBody(data));
    return norm<CustomRole>(r.data);
  },
};

// ============================================================================
// Quota API
// ============================================================================

export const quotaApi = {
  async get(entityType: EntityType, entityId: string): Promise<QuotaResponse> {
    const r = await api.get<QuotaResponse>(`/api/v1/quotas/${entityType}/${entityId}`);
    return norm<QuotaResponse>(r.data);
  },

  async set(entityType: EntityType, entityId: string, data: QuotaConfig): Promise<QuotaResponse> {
    const r = await api.put<QuotaResponse>(`/api/v1/quotas/${entityType}/${entityId}`, snakeBody(data));
    return norm<QuotaResponse>(r.data);
  },

  async getUsage(entityType: EntityType, entityId: string): Promise<QuotaUsage> {
    const r = await api.get<QuotaUsage>(`/api/v1/quotas/${entityType}/${entityId}/usage`);
    return norm<QuotaUsage>(r.data);
  },

  async check(
    entityType: EntityType,
    entityId: string,
    resourceType: ResourceType,
    amount?: number,
  ): Promise<QuotaCheckResult> {
    const r = await api.post<QuotaCheckResult>(`/api/v1/quotas/${entityType}/${entityId}/check`, null, {
      params: { resource_type: resourceType, amount },
    });
    return norm<QuotaCheckResult>(r.data);
  },
};

// ============================================================================
// Share API (Cross-Tenant Collaboration)
// ============================================================================

export const shareApi = {
  async create(data: CreateShareRequest): Promise<ShareLink> {
    const r = await api.post<ShareLink>('/api/v1/shares', snakeBody(data));
    return norm<ShareLink>(r.data);
  },

  async access(token: string): Promise<unknown> {
    const r = await api.get<unknown>(`/api/v1/shares/${token}`);
    return norm(r.data);
  },

  async revoke(shareId: string): Promise<void> {
    await api.delete(`/api/v1/shares/${shareId}`);
  },

  async list(params?: { skip?: number; limit?: number }): Promise<ShareLink[]> {
    const r = await api.get<ShareLink[]>('/api/v1/shares', { params });
    return norm<ShareLink[]>(r.data);
  },

  async setWhitelist(tenantId: string, data: WhitelistConfig): Promise<void> {
    await api.put(`/api/v1/tenants/${tenantId}/whitelist`, snakeBody(data));
  },

  async getWhitelist(tenantId: string): Promise<WhitelistConfig> {
    const r = await api.get<WhitelistConfig>(`/api/v1/tenants/${tenantId}/whitelist`);
    return norm<WhitelistConfig>(r.data);
  },
};

// ============================================================================
// Admin API
// ============================================================================

export const adminApi = {
  async getDashboard(): Promise<AdminDashboard> {
    const r = await api.get<AdminDashboard>('/api/v1/admin/dashboard');
    return norm<AdminDashboard>(r.data);
  },

  async getServices(): Promise<ServiceStatus[]> {
    const r = await api.get<ServiceStatus[]>('/api/v1/admin/services');
    return norm<ServiceStatus[]>(r.data);
  },

  async getConfig(): Promise<SystemConfig> {
    const r = await api.get<SystemConfig>('/api/v1/admin/config');
    return norm<SystemConfig>(r.data);
  },

  async updateConfig(data: SystemConfigRequest): Promise<SystemConfig> {
    const r = await api.put<SystemConfig>('/api/v1/admin/config', snakeBody(data));
    return norm<SystemConfig>(r.data);
  },

  async getAuditLogs(params?: {
    tenant_id?: string;
    user_id?: string;
    action?: string;
    resource_type?: string;
    start_date?: string;
    end_date?: string;
    skip?: number;
    limit?: number;
  }): Promise<AuditLogEntry[]> {
    const r = await api.get<AuditLogEntry[]>('/api/v1/admin/audit-logs', { params });
    return norm<AuditLogEntry[]>(r.data);
  },
};

export default {
  tenant: tenantApi,
  workspace: workspaceApi,
  member: memberApi,
  quota: quotaApi,
  share: shareApi,
  admin: adminApi,
};
