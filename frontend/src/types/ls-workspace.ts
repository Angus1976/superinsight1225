/**
 * Label Studio Workspace Types
 *
 * Type definitions for Label Studio Enterprise Workspace extension.
 * These types ensure type safety for workspace management operations.
 */

// ============================================================================
// Workspace Role Types
// ============================================================================

/** Workspace member roles in order of increasing permissions */
export type WorkspaceMemberRole = 'annotator' | 'reviewer' | 'manager' | 'admin' | 'owner';

/** Role hierarchy for comparison */
export const ROLE_HIERARCHY: readonly WorkspaceMemberRole[] = [
  'annotator',
  'reviewer',
  'manager',
  'admin',
  'owner',
] as const;

// ============================================================================
// Workspace Types
// ============================================================================

/** Label Studio Workspace */
export interface LSWorkspace {
  /** Workspace UUID */
  id: string;
  /** Workspace name */
  name: string;
  /** Workspace description */
  description?: string;
  /** Owner user ID */
  owner_id: string;
  /** Workspace settings */
  settings: Record<string, unknown>;
  /** Whether workspace is active */
  is_active: boolean;
  /** Whether workspace is deleted (soft delete) */
  is_deleted: boolean;
  /** Created timestamp */
  created_at?: string;
  /** Updated timestamp */
  updated_at?: string;
  /** Member count */
  member_count: number;
  /** Project count */
  project_count: number;
}

/** Workspace list response */
export interface LSWorkspaceListResponse {
  /** List of workspaces */
  items: LSWorkspace[];
  /** Total count */
  total: number;
}

// ============================================================================
// Workspace Member Types
// ============================================================================

/** Workspace member */
export interface LSWorkspaceMember {
  /** Member record UUID */
  id: string;
  /** Workspace UUID */
  workspace_id: string;
  /** User UUID */
  user_id: string;
  /** Member role */
  role: WorkspaceMemberRole;
  /** Whether member is active */
  is_active: boolean;
  /** Joined timestamp */
  joined_at?: string;
  /** User email */
  user_email?: string;
  /** User display name */
  user_name?: string;
}

/** Member list response */
export interface LSWorkspaceMemberListResponse {
  /** List of members */
  items: LSWorkspaceMember[];
  /** Total count */
  total: number;
}

// ============================================================================
// Workspace Project Types
// ============================================================================

/** Workspace project association */
export interface LSWorkspaceProject {
  /** Association record UUID */
  id: string;
  /** Workspace UUID */
  workspace_id: string;
  /** Label Studio project ID */
  label_studio_project_id: string;
  /** SuperInsight project UUID (optional) */
  superinsight_project_id?: string;
  /** Metadata */
  metadata: Record<string, unknown>;
  /** Created timestamp */
  created_at?: string;
  /** Updated timestamp */
  updated_at?: string;
  /** Project title (from Label Studio) */
  project_title?: string;
  /** Project description (from Label Studio) */
  project_description?: string;
}

/** Project list response */
export interface LSWorkspaceProjectListResponse {
  /** List of projects */
  items: LSWorkspaceProject[];
  /** Total count */
  total: number;
}

// ============================================================================
// Workspace Permission Types
// ============================================================================

/** Permission enum values */
export type WorkspacePermission =
  | 'workspace:view'
  | 'workspace:edit'
  | 'workspace:delete'
  | 'workspace:manage_members'
  | 'project:view'
  | 'project:create'
  | 'project:edit'
  | 'project:delete'
  | 'project:manage_members'
  | 'task:view'
  | 'task:annotate'
  | 'task:review'
  | 'task:assign'
  | 'data:export'
  | 'data:import';

/** User permissions response */
export interface LSUserPermissions {
  /** Workspace UUID */
  workspace_id: string;
  /** User UUID */
  user_id: string;
  /** User role in workspace */
  role: WorkspaceMemberRole;
  /** List of permission strings */
  permissions: WorkspacePermission[];
}

// ============================================================================
// Request Types
// ============================================================================

/** Create workspace request */
export interface CreateLSWorkspaceRequest {
  /** Workspace name */
  name: string;
  /** Workspace description */
  description?: string;
  /** Workspace settings */
  settings?: Record<string, unknown>;
}

/** Update workspace request */
export interface UpdateLSWorkspaceRequest {
  /** Workspace name */
  name?: string;
  /** Workspace description */
  description?: string;
  /** Workspace settings */
  settings?: Record<string, unknown>;
  /** Whether workspace is active */
  is_active?: boolean;
}

/** Add member request */
export interface AddLSWorkspaceMemberRequest {
  /** User UUID to add */
  user_id: string;
  /** Role to assign */
  role?: WorkspaceMemberRole;
}

/** Update member role request */
export interface UpdateLSWorkspaceMemberRequest {
  /** New role */
  role: WorkspaceMemberRole;
}

/** Associate project request */
export interface AssociateLSProjectRequest {
  /** Label Studio project ID */
  label_studio_project_id: string;
  /** SuperInsight project UUID (optional) */
  superinsight_project_id?: string;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
}

// ============================================================================
// Workspace Context Type
// ============================================================================

/** Workspace context for components */
export interface LSWorkspaceContext {
  /** Current workspace */
  workspace: LSWorkspace | null;
  /** Current user's role in workspace */
  userRole: WorkspaceMemberRole | null;
  /** Current user's permissions */
  permissions: WorkspacePermission[];
  /** Whether user can perform action */
  can: (permission: WorkspacePermission) => boolean;
  /** Whether context is loading */
  isLoading: boolean;
  /** Error if any */
  error: Error | null;
}

// ============================================================================
// Type Guards
// ============================================================================

/** Check if value is a valid LSWorkspace */
export const isLSWorkspace = (value: unknown): value is LSWorkspace => {
  if (!value || typeof value !== 'object') return false;
  const ws = value as Record<string, unknown>;
  return (
    typeof ws.id === 'string' &&
    typeof ws.name === 'string' &&
    typeof ws.owner_id === 'string'
  );
};

/** Check if value is a valid WorkspaceMemberRole */
export const isWorkspaceMemberRole = (value: unknown): value is WorkspaceMemberRole => {
  return ROLE_HIERARCHY.includes(value as WorkspaceMemberRole);
};

/** Check if role1 is higher than role2 */
export const isHigherRole = (
  role1: WorkspaceMemberRole,
  role2: WorkspaceMemberRole
): boolean => {
  return ROLE_HIERARCHY.indexOf(role1) > ROLE_HIERARCHY.indexOf(role2);
};

/** Check if role can manage another role */
export const canManageRole = (
  managerRole: WorkspaceMemberRole,
  targetRole: WorkspaceMemberRole
): boolean => {
  if (managerRole === 'owner') return true;
  if (managerRole === 'admin') {
    return targetRole !== 'owner' && targetRole !== 'admin';
  }
  return false;
};
