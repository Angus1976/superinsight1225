/**
 * Label Studio Workspace Hooks
 *
 * TanStack Query hooks for Label Studio Enterprise Workspace management.
 * Provides data fetching, caching, and mutation hooks for:
 * - Workspace CRUD operations
 * - Member management
 * - Project association
 * - Permission checking
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { message } from 'antd';
import { useCallback, useMemo } from 'react';
import { lsWorkspaceService } from '@/services/lsWorkspaceService';
import type {
  LSWorkspace,
  LSWorkspaceMember,
  LSWorkspaceProject,
  LSUserPermissions,
  LSWorkspaceContext,
  CreateLSWorkspaceRequest,
  UpdateLSWorkspaceRequest,
  AddLSWorkspaceMemberRequest,
  UpdateLSWorkspaceMemberRequest,
  AssociateLSProjectRequest,
  WorkspacePermission,
} from '@/types/ls-workspace';

// ============================================================================
// Query Keys
// ============================================================================

export const LS_WORKSPACE_QUERY_KEYS = {
  workspaces: ['ls-workspaces'] as const,
  workspace: (id: string) => ['ls-workspaces', id] as const,
  members: (workspaceId: string) => ['ls-workspaces', workspaceId, 'members'] as const,
  permissions: (workspaceId: string) => ['ls-workspaces', workspaceId, 'permissions'] as const,
  projects: (workspaceId: string) => ['ls-workspaces', workspaceId, 'projects'] as const,
  project: (workspaceId: string, projectId: string) =>
    ['ls-workspaces', workspaceId, 'projects', projectId] as const,
};

// ============================================================================
// Workspace Hooks
// ============================================================================

/**
 * Hook to fetch list of workspaces
 */
export function useLSWorkspaces(includeInactive = false) {
  return useQuery({
    queryKey: [...LS_WORKSPACE_QUERY_KEYS.workspaces, { includeInactive }],
    queryFn: () => lsWorkspaceService.listWorkspaces(includeInactive),
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Hook to fetch a single workspace
 */
export function useLSWorkspace(workspaceId: string | null | undefined) {
  return useQuery({
    queryKey: workspaceId ? LS_WORKSPACE_QUERY_KEYS.workspace(workspaceId) : ['ls-workspaces', 'null'],
    queryFn: () => (workspaceId ? lsWorkspaceService.getWorkspace(workspaceId) : null),
    enabled: !!workspaceId,
    staleTime: 30000,
  });
}

/**
 * Hook to create a workspace
 */
export function useCreateLSWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateLSWorkspaceRequest) =>
      lsWorkspaceService.createWorkspace(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.workspaces });
      message.success('Workspace created successfully');
    },
    onError: () => {
      message.error('Failed to create workspace');
    },
  });
}

/**
 * Hook to update a workspace
 */
export function useUpdateLSWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      workspaceId,
      request,
    }: {
      workspaceId: string;
      request: UpdateLSWorkspaceRequest;
    }) => lsWorkspaceService.updateWorkspace(workspaceId, request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.workspaces });
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.workspace(data.id) });
      message.success('Workspace updated successfully');
    },
    onError: () => {
      message.error('Failed to update workspace');
    },
  });
}

/**
 * Hook to delete a workspace
 */
export function useDeleteLSWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      workspaceId,
      hardDelete = false,
    }: {
      workspaceId: string;
      hardDelete?: boolean;
    }) => lsWorkspaceService.deleteWorkspace(workspaceId, hardDelete),
    onSuccess: (_, { workspaceId }) => {
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.workspaces });
      queryClient.removeQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.workspace(workspaceId) });
      message.success('Workspace deleted successfully');
    },
    onError: () => {
      message.error('Failed to delete workspace');
    },
  });
}

// ============================================================================
// Member Hooks
// ============================================================================

/**
 * Hook to fetch workspace members
 */
export function useLSWorkspaceMembers(workspaceId: string | null | undefined, includeInactive = false) {
  return useQuery({
    queryKey: workspaceId
      ? [...LS_WORKSPACE_QUERY_KEYS.members(workspaceId), { includeInactive }]
      : ['ls-workspaces', 'null', 'members'],
    queryFn: () =>
      workspaceId ? lsWorkspaceService.listMembers(workspaceId, includeInactive) : null,
    enabled: !!workspaceId,
    staleTime: 30000,
  });
}

/**
 * Hook to add a member to workspace
 */
export function useAddLSWorkspaceMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      workspaceId,
      request,
    }: {
      workspaceId: string;
      request: AddLSWorkspaceMemberRequest;
    }) => lsWorkspaceService.addMember(workspaceId, request),
    onSuccess: (_, { workspaceId }) => {
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.members(workspaceId) });
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.workspace(workspaceId) });
      message.success('Member added successfully');
    },
    onError: () => {
      message.error('Failed to add member');
    },
  });
}

/**
 * Hook to update member role
 */
export function useUpdateLSWorkspaceMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      workspaceId,
      userId,
      request,
    }: {
      workspaceId: string;
      userId: string;
      request: UpdateLSWorkspaceMemberRequest;
    }) => lsWorkspaceService.updateMemberRole(workspaceId, userId, request),
    onSuccess: (_, { workspaceId }) => {
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.members(workspaceId) });
      message.success('Member role updated successfully');
    },
    onError: () => {
      message.error('Failed to update member role');
    },
  });
}

/**
 * Hook to remove member from workspace
 */
export function useRemoveLSWorkspaceMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ workspaceId, userId }: { workspaceId: string; userId: string }) =>
      lsWorkspaceService.removeMember(workspaceId, userId),
    onSuccess: (_, { workspaceId }) => {
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.members(workspaceId) });
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.workspace(workspaceId) });
      message.success('Member removed successfully');
    },
    onError: () => {
      message.error('Failed to remove member');
    },
  });
}

// ============================================================================
// Permission Hooks
// ============================================================================

/**
 * Hook to fetch current user's permissions in workspace
 */
export function useLSWorkspacePermissions(workspaceId: string | null | undefined) {
  return useQuery({
    queryKey: workspaceId
      ? LS_WORKSPACE_QUERY_KEYS.permissions(workspaceId)
      : ['ls-workspaces', 'null', 'permissions'],
    queryFn: () => (workspaceId ? lsWorkspaceService.getMyPermissions(workspaceId) : null),
    enabled: !!workspaceId,
    staleTime: 60000, // 1 minute
  });
}

// ============================================================================
// Project Hooks
// ============================================================================

/**
 * Hook to fetch workspace projects
 */
export function useLSWorkspaceProjects(workspaceId: string | null | undefined) {
  return useQuery({
    queryKey: workspaceId
      ? LS_WORKSPACE_QUERY_KEYS.projects(workspaceId)
      : ['ls-workspaces', 'null', 'projects'],
    queryFn: () => (workspaceId ? lsWorkspaceService.listProjects(workspaceId) : null),
    enabled: !!workspaceId,
    staleTime: 30000,
  });
}

/**
 * Hook to fetch a specific project in workspace
 */
export function useLSWorkspaceProject(
  workspaceId: string | null | undefined,
  projectId: string | null | undefined
) {
  return useQuery({
    queryKey:
      workspaceId && projectId
        ? LS_WORKSPACE_QUERY_KEYS.project(workspaceId, projectId)
        : ['ls-workspaces', 'null', 'projects', 'null'],
    queryFn: () =>
      workspaceId && projectId
        ? lsWorkspaceService.getProject(workspaceId, projectId)
        : null,
    enabled: !!workspaceId && !!projectId,
    staleTime: 30000,
  });
}

/**
 * Hook to associate project with workspace
 */
export function useAssociateLSProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      workspaceId,
      request,
    }: {
      workspaceId: string;
      request: AssociateLSProjectRequest;
    }) => lsWorkspaceService.associateProject(workspaceId, request),
    onSuccess: (_, { workspaceId }) => {
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.projects(workspaceId) });
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.workspace(workspaceId) });
      message.success('Project associated successfully');
    },
    onError: () => {
      message.error('Failed to associate project');
    },
  });
}

/**
 * Hook to remove project association
 */
export function useRemoveLSProjectAssociation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ workspaceId, projectId }: { workspaceId: string; projectId: string }) =>
      lsWorkspaceService.removeProjectAssociation(workspaceId, projectId),
    onSuccess: (_, { workspaceId }) => {
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.projects(workspaceId) });
      queryClient.invalidateQueries({ queryKey: LS_WORKSPACE_QUERY_KEYS.workspace(workspaceId) });
      message.success('Project association removed successfully');
    },
    onError: () => {
      message.error('Failed to remove project association');
    },
  });
}

// ============================================================================
// Context Hook
// ============================================================================

/**
 * Hook to get workspace context with permissions
 * Combines workspace, permissions, and provides helper methods
 */
export function useLSWorkspaceContext(workspaceId: string | null | undefined): LSWorkspaceContext {
  const { data: workspace, isLoading: workspaceLoading, error: workspaceError } = useLSWorkspace(workspaceId);
  const { data: permissionsData, isLoading: permissionsLoading, error: permissionsError } = useLSWorkspacePermissions(workspaceId);

  const can = useCallback(
    (permission: WorkspacePermission) => {
      if (!permissionsData) return false;
      return permissionsData.permissions.includes(permission);
    },
    [permissionsData]
  );

  return useMemo(
    () => ({
      workspace: workspace ?? null,
      userRole: permissionsData?.role ?? null,
      permissions: permissionsData?.permissions ?? [],
      can,
      isLoading: workspaceLoading || permissionsLoading,
      error: (workspaceError ?? permissionsError) as Error | null,
    }),
    [workspace, permissionsData, can, workspaceLoading, permissionsLoading, workspaceError, permissionsError]
  );
}

// ============================================================================
// Selector Hook
// ============================================================================

/**
 * Hook for workspace selector component
 * Provides workspace list with selection state management
 */
export function useLSWorkspaceSelector() {
  const { data, isLoading, error } = useLSWorkspaces();

  const workspaces = useMemo(() => data?.items ?? [], [data]);

  return {
    workspaces,
    isLoading,
    error: error as Error | null,
    total: data?.total ?? 0,
  };
}
