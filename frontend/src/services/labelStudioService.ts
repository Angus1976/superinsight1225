/**
 * Label Studio API Service
 * 
 * Provides API functions for Label Studio integration including:
 * - Project validation
 * - Project creation/ensuring
 * - Task import
 * - Authenticated URL generation
 */

import apiClient from './api/client';
import { API_ENDPOINTS } from '@/constants';
import type { LabelStudioProject } from '@/types/label-studio';

// ============================================================================
// Types for Label Studio API responses
// ============================================================================

/** Project validation result */
export interface ProjectValidationResult {
  /** Whether the project exists */
  exists: boolean;
  /** Whether the project is accessible */
  accessible: boolean;
  /** Number of tasks in the project */
  task_count: number;
  /** Number of annotations in the project */
  annotation_count: number;
  /** Project status */
  status: 'ready' | 'creating' | 'error' | 'not_found';
  /** Error message if any */
  error_message?: string;
}

/** Ensure project request */
export interface EnsureProjectRequest {
  /** SuperInsight task ID */
  task_id: string;
  /** Task name for project title */
  task_name: string;
  /** Annotation type */
  annotation_type: string;
}

/** Ensure project response */
export interface EnsureProjectResponse {
  /** Label Studio project ID */
  project_id: string;
  /** Whether the project was newly created */
  created: boolean;
  /** Project status */
  status: 'ready' | 'creating' | 'error';
  /** Number of tasks in the project */
  task_count?: number;
  /** Message */
  message?: string;
}

/** Import tasks request */
export interface ImportTasksRequest {
  /** SuperInsight task ID to import from */
  task_id: string;
}

/** Import tasks response */
export interface ImportTasksResponse {
  /** Number of tasks imported */
  imported_count: number;
  /** Number of tasks that failed to import */
  failed_count: number;
  /** Import status */
  status: 'success' | 'partial' | 'failed';
  /** Error messages if any */
  errors?: string[];
}

/** Authenticated URL response */
export interface AuthUrlResponse {
  /** Authenticated URL for Label Studio */
  url: string;
  /** URL expiration time */
  expires_at: string;
  /** Project ID */
  project_id: string;
}

// ============================================================================
// Label Studio Service
// ============================================================================

export const labelStudioService = {
  /**
   * Validate if a Label Studio project exists and is accessible
   * @param projectId - Label Studio project ID
   * @returns Project validation result
   */
  async validateProject(projectId: string): Promise<ProjectValidationResult> {
    try {
      const response = await apiClient.get<ProjectValidationResult>(
        API_ENDPOINTS.LABEL_STUDIO.VALIDATE_PROJECT(projectId)
      );
      return response.data;
    } catch (error: unknown) {
      // Handle 404 - project not found
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { status?: number } };
        if (axiosError.response?.status === 404) {
          return {
            exists: false,
            accessible: false,
            task_count: 0,
            annotation_count: 0,
            status: 'not_found',
            error_message: 'Project not found',
          };
        }
      }
      throw error;
    }
  },

  /**
   * Ensure a Label Studio project exists for a task
   * Creates the project if it doesn't exist
   * @param request - Ensure project request
   * @returns Ensure project response
   */
  async ensureProject(request: EnsureProjectRequest): Promise<EnsureProjectResponse> {
    const response = await apiClient.post<EnsureProjectResponse>(
      API_ENDPOINTS.LABEL_STUDIO.ENSURE_PROJECT,
      request
    );
    return response.data;
  },

  /**
   * Import tasks from SuperInsight to Label Studio project
   * @param projectId - Label Studio project ID
   * @param taskId - SuperInsight task ID
   * @returns Import result
   */
  async importTasks(projectId: string, taskId: string): Promise<ImportTasksResponse> {
    const response = await apiClient.post<ImportTasksResponse>(
      API_ENDPOINTS.LABEL_STUDIO.IMPORT_TASKS(projectId),
      { task_id: taskId }
    );
    return response.data;
  },

  /**
   * Get authenticated URL for Label Studio project
   * @param projectId - Label Studio project ID
   * @param language - User's language preference ('zh' or 'en')
   * @returns Authenticated URL response
   */
  async getAuthUrl(projectId: string, language: string = 'zh'): Promise<AuthUrlResponse> {
    const response = await apiClient.get<AuthUrlResponse>(
      API_ENDPOINTS.LABEL_STUDIO.AUTH_URL(projectId),
      { params: { language } }
    );
    return response.data;
  },

  /**
   * Get Label Studio project by ID
   * @param projectId - Label Studio project ID
   * @returns Label Studio project
   */
  async getProject(projectId: string): Promise<LabelStudioProject> {
    const response = await apiClient.get<LabelStudioProject>(
      API_ENDPOINTS.LABEL_STUDIO.PROJECT_BY_ID(projectId)
    );
    return response.data;
  },

  /**
   * Create a new Label Studio project
   * @param taskId - SuperInsight task ID
   * @param taskName - Task name for project title
   * @param annotationType - Annotation type
   * @returns Created project
   */
  async createProject(
    taskId: string,
    taskName: string,
    annotationType: string
  ): Promise<EnsureProjectResponse> {
    return this.ensureProject({
      task_id: taskId,
      task_name: taskName,
      annotation_type: annotationType,
    });
  },
};

export default labelStudioService;
