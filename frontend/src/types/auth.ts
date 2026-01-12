// Authentication types

export interface LoginCredentials {
  username: string;
  password: string;
  tenant_id?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  message?: string;
  user: {
    id: string;
    username: string;
    email: string;
    full_name: string;
    role: string;
    tenant_id: string;
    is_active: boolean;
    last_login?: string;
  };
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  full_name: string;
  tenant_id?: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  user: User | null;
  currentTenant: Tenant | null;
}

export interface User {
  id?: string;
  username: string;
  email: string;
  full_name?: string;
  role: string;
  tenant_id?: string;
  is_active?: boolean;
  last_login?: string;
  created_at?: string;
}

export type UserRole = 'admin' | 'manager' | 'annotator' | 'viewer';

export interface Tenant {
  id: string;
  name: string;
  logo?: string;
}

export interface Workspace {
  id: string;
  name: string;
  description?: string;
  tenant_id: string;
  is_default?: boolean;
  created_at?: string;
  updated_at?: string;
  member_count?: number;
  project_count?: number;
  settings?: WorkspaceSettings;
}

export interface WorkspaceSettings {
  default_language?: string;
  timezone?: string;
  notification_enabled?: boolean;
  auto_assign_tasks?: boolean;
}

export interface WorkspaceMember {
  id: string;
  user_id: string;
  workspace_id: string;
  role: WorkspaceRole;
  joined_at: string;
  user?: User;
}

export type WorkspaceRole = 'owner' | 'admin' | 'member' | 'viewer';

export interface Permission {
  id: string;
  user_id: string;
  project_id: string;
  permission_type: PermissionType;
}

export type PermissionType = 'read' | 'write' | 'admin' | 'quality_control';
