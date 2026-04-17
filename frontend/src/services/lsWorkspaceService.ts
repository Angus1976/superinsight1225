/**
 * Label Studio Workspace Service
 *
 * Provides API functions for Label Studio Enterprise Workspace management:
 * - Workspace CRUD operations
 * - Member management
 * - Project association
 * - Permission checking
 */

import apiClient from './api/client';
import { API_ENDPOINTS } from '@/constants';
import { apiRequestToSnake, apiResponseToSnake } from '@/utils/jsonCase';
import type {
  LSWorkspace,
  LSWorkspaceListResponse,
  LSWorkspaceMember,
  LSWorkspaceMemberListResponse,
  LSWorkspaceProject,
  LSWorkspaceProjectListResponse,
  LSUserPermissions,
  CreateLSWorkspaceRequest,
  UpdateLSWorkspaceRequest,
  AddLSWorkspaceMemberRequest,
  UpdateLSWorkspaceMemberRequest,
  AssociateLSProjectRequest,
} from '@/types/ls-workspace';

// ============================================================================
// Workspace Service
// ============================================================================

export const lsWorkspaceService = {
  // ==========================================================================
  // Workspace CRUD
  // ==========================================================================

  /**
   * List workspaces the current user has access to
   * @param includeInactive - Include inactive workspaces
   * @returns List of workspaces
   */
  async listWorkspaces(includeInactive = false): Promise<LSWorkspaceListResponse> {
    const response = await apiClient.get<LSWorkspaceListResponse>(
      API_ENDPOINTS.LS_WORKSPACES.BASE,
      { params: { include_inactive: includeInactive } }
    );
    return apiResponseToSnake(response.data);
  },

  /**
   * Get workspace by ID
   * @param workspaceId - Workspace UUID
   * @returns Workspace details
   */
  async getWorkspace(workspaceId: string): Promise<LSWorkspace> {
    const response = await apiClient.get<LSWorkspace>(
      API_ENDPOINTS.LS_WORKSPACES.BY_ID(workspaceId)
    );
    return apiResponseToSnake(response.data);
  },

  /**
   * Create a new workspace
   * @param request - Create workspace request
   * @returns Created workspace
   */
  async createWorkspace(request: CreateLSWorkspaceRequest): Promise<LSWorkspace> {
    const response = await apiClient.post<LSWorkspace>(
      API_ENDPOINTS.LS_WORKSPACES.BASE,
      apiRequestToSnake(request)
    );
    return apiResponseToSnake(response.data);
  },

  /**
   * Update workspace
   * @param workspaceId - Workspace UUID
   * @param request - Update workspace request
   * @returns Updated workspace
   */
  async updateWorkspace(
    workspaceId: string,
    request: UpdateLSWorkspaceRequest
  ): Promise<LSWorkspace> {
    const response = await apiClient.put<LSWorkspace>(
      API_ENDPOINTS.LS_WORKSPACES.BY_ID(workspaceId),
      apiRequestToSnake(request)
    );
    return apiResponseToSnake(response.data);
  },

  /**
   * Delete workspace (soft delete by default)
   * @param workspaceId - Workspace UUID
   * @param hardDelete - Permanently delete workspace
   */
  async deleteWorkspace(workspaceId: string, hardDelete = false): Promise<void> {
    await apiClient.delete(
      API_ENDPOINTS.LS_WORKSPACES.BY_ID(workspaceId),
      { params: { hard_delete: hardDelete } }
    );
  },

  // ==========================================================================
  // Member Management
  // ==========================================================================

  /**
   * List workspace members
   * @param workspaceId - Workspace UUID
   * @param includeInactive - Include inactive members
   * @returns List of members
   */
  async listMembers(
    workspaceId: string,
    includeInactive = false
  ): Promise<LSWorkspaceMemberListResponse> {
    const response = await apiClient.get<LSWorkspaceMemberListResponse>(
      API_ENDPOINTS.LS_WORKSPACES.MEMBERS(workspaceId),
      { params: { include_inactive: includeInactive } }
    );
    return apiResponseToSnake(response.data);
  },

  /**
   * Add member to workspace
   * @param workspaceId - Workspace UUID
   * @param request - Add member request
   * @returns Added member
   */
  async addMember(
    workspaceId: string,
    request: AddLSWorkspaceMemberRequest
  ): Promise<LSWorkspaceMember> {
    const response = await apiClient.post<LSWorkspaceMember>(
      API_ENDPOINTS.LS_WORKSPACES.MEMBERS(workspaceId),
      apiRequestToSnake(request)
    );
    return apiResponseToSnake(response.data);
  },

  /**
   * Update member role
   * @param workspaceId - Workspace UUID
   * @param userId - User UUID
   * @param request - Update member request
   * @returns Updated member
   */
  async updateMemberRole(
    workspaceId: string,
    userId: string,
    request: UpdateLSWorkspaceMemberRequest
  ): Promise<LSWorkspaceMember> {
    const response = await apiClient.put<LSWorkspaceMember>(
      API_ENDPOINTS.LS_WORKSPACES.MEMBER_BY_ID(workspaceId, userId),
      apiRequestToSnake(request)
    );
    return apiResponseToSnake(response.data);
  },

  /**
   * Remove member from workspace
   * @param workspaceId - Workspace UUID
   * @param userId - User UUID
   */
  async removeMember(workspaceId: string, userId: string): Promise<void> {
    await apiClient.delete(
      API_ENDPOINTS.LS_WORKSPACES.MEMBER_BY_ID(workspaceId, userId)
    );
  },

  // ==========================================================================
  // Permissions
  // ==========================================================================

  /**
   * Get current user's permissions in workspace
   * @param workspaceId - Workspace UUID
   * @returns User permissions
   */
  async getMyPermissions(workspaceId: string): Promise<LSUserPermissions> {
    const response = await apiClient.get<LSUserPermissions>(
      API_ENDPOINTS.LS_WORKSPACES.PERMISSIONS(workspaceId)
    );
    return apiResponseToSnake(response.data);
  },

  // ==========================================================================
  // Project Association
  // ==========================================================================

  /**
   * List projects in workspace
   * @param workspaceId - Workspace UUID
   * @returns List of projects
   */
  async listProjects(workspaceId: string): Promise<LSWorkspaceProjectListResponse> {
    const response = await apiClient.get<LSWorkspaceProjectListResponse>(
      API_ENDPOINTS.LS_WORKSPACES.PROJECTS(workspaceId)
    );
    return apiResponseToSnake(response.data);
  },

  /**
   * Get project in workspace
   * @param workspaceId - Workspace UUID
   * @param projectId - Label Studio project ID
   * @returns Project details
   */
  async getProject(workspaceId: string, projectId: string): Promise<LSWorkspaceProject> {
    const response = await apiClient.get<LSWorkspaceProject>(
      API_ENDPOINTS.LS_WORKSPACES.PROJECT_BY_ID(workspaceId, projectId)
    );
    return apiResponseToSnake(response.data);
  },

  /**
   * Associate project with workspace
   * @param workspaceId - Workspace UUID
   * @param request - Associate project request
   * @returns Created association
   */
  async associateProject(
    workspaceId: string,
    request: AssociateLSProjectRequest
  ): Promise<LSWorkspaceProject> {
    const response = await apiClient.post<LSWorkspaceProject>(
      API_ENDPOINTS.LS_WORKSPACES.PROJECTS(workspaceId),
      apiRequestToSnake(request)
    );
    return apiResponseToSnake(response.data);
  },

  /**
   * Remove project association
   * @param workspaceId - Workspace UUID
   * @param projectId - Label Studio project ID
   */
  async removeProjectAssociation(workspaceId: string, projectId: string): Promise<void> {
    await apiClient.delete(
      API_ENDPOINTS.LS_WORKSPACES.PROJECT_BY_ID(workspaceId, projectId)
    );
  },
};

export default lsWorkspaceService;
