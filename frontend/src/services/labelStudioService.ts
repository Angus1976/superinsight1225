/**
 * Label Studio API Service
 * 
 * Provides API functions for Label Studio integration including:
 * - Project validation
 * - Project creation/ensuring
 * - Task import
 * - Authenticated URL generation
 * - Automatic project creation with annotation templates
 */

import apiClient from './api/client';
import { API_ENDPOINTS } from '@/constants';
import { 
  getAnnotationTemplate, 
  generateClassificationTemplate, 
  generateNERTemplate, 
  generateSentimentTemplate 
} from '@/constants/annotationTemplates';
import type { LabelStudioProject } from '@/types/label-studio';
import type { AnnotationType } from '@/types/task';

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

/** Sync annotations response */
export interface SyncAnnotationsResponse {
  /** Whether the sync was successful */
  success: boolean;
  /** Number of annotations synced */
  synced_count: number;
  /** Total annotations in the project */
  total_annotations: number;
  /** Error messages if any */
  errors: string[];
  /** Timestamp of the sync */
  synced_at?: string;
}

/** Annotation template configuration */
export interface AnnotationTemplateConfig {
  /** Categories for text classification */
  categories?: string[];
  /** Whether to allow multi-label classification */
  multiLabel?: boolean;
  /** Entity types for NER */
  entityTypes?: string[];
  /** Sentiment scale type */
  sentimentScale?: 'binary' | 'ternary' | 'five_point';
}

/** Create project with template request */
export interface CreateProjectWithTemplateRequest {
  /** SuperInsight task ID */
  task_id: string;
  /** Task name for project title */
  task_name: string;
  /** Task description */
  task_description?: string;
  /** Annotation type */
  annotation_type: AnnotationType;
  /** Template configuration */
  template_config?: AnnotationTemplateConfig;
  /** Initial data to import */
  initial_data?: Array<{ text: string; [key: string]: unknown }>;
  /** Assignee user IDs for permissions */
  assignee_ids?: string[];
}

/** Create project with template response */
export interface CreateProjectWithTemplateResponse {
  /** Label Studio project ID */
  project_id: string;
  /** Whether the project was newly created */
  created: boolean;
  /** Project status */
  status: 'ready' | 'creating' | 'error';
  /** Number of tasks imported */
  task_count: number;
  /** Label config used */
  label_config: string;
  /** Message */
  message?: string;
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

  /**
   * Generate label config based on annotation type and configuration
   * @param annotationType - Annotation type
   * @param config - Template configuration
   * @returns Label config XML string
   */
  generateLabelConfig(
    annotationType: AnnotationType,
    config?: AnnotationTemplateConfig
  ): string {
    if (!config) {
      return getAnnotationTemplate(annotationType);
    }

    switch (annotationType) {
      case 'text_classification':
        if (config.categories && config.categories.length > 0) {
          return generateClassificationTemplate(config.categories, config.multiLabel);
        }
        return getAnnotationTemplate(annotationType);

      case 'ner':
        if (config.entityTypes && config.entityTypes.length > 0) {
          return generateNERTemplate(config.entityTypes);
        }
        return getAnnotationTemplate(annotationType);

      case 'sentiment':
        if (config.sentimentScale) {
          return generateSentimentTemplate(config.sentimentScale);
        }
        return getAnnotationTemplate(annotationType);

      default:
        return getAnnotationTemplate(annotationType);
    }
  },

  /**
   * Create Label Studio project with template configuration
   * This is the main method for automatic project creation when creating a task
   * @param request - Create project request with template config
   * @returns Created project response
   */
  async createProjectWithTemplate(
    request: CreateProjectWithTemplateRequest
  ): Promise<CreateProjectWithTemplateResponse> {
    // Generate label config based on annotation type and config
    const labelConfig = this.generateLabelConfig(
      request.annotation_type,
      request.template_config
    );

    try {
      // First, ensure the project exists
      const ensureResponse = await this.ensureProject({
        task_id: request.task_id,
        task_name: request.task_name,
        annotation_type: request.annotation_type,
      });

      let taskCount = ensureResponse.task_count || 0;

      // If initial data is provided, import it
      if (request.initial_data && request.initial_data.length > 0 && ensureResponse.project_id) {
        try {
          const importResponse = await this.importTasks(
            ensureResponse.project_id,
            request.task_id
          );
          taskCount = importResponse.imported_count;
        } catch (importError) {
          console.warn('Failed to import initial data:', importError);
          // Continue even if import fails
        }
      }

      return {
        project_id: ensureResponse.project_id,
        created: ensureResponse.created,
        status: ensureResponse.status,
        task_count: taskCount,
        label_config: labelConfig,
        message: ensureResponse.message,
      };
    } catch (error) {
      console.error('Failed to create project with template:', error);
      throw error;
    }
  },

  /**
   * Create project and link to task (convenience method for TaskCreateModal)
   * @param taskId - SuperInsight task ID
   * @param taskName - Task name
   * @param annotationType - Annotation type
   * @param templateConfig - Optional template configuration
   * @returns Project ID if successful
   */
  async createAndLinkProject(
    taskId: string,
    taskName: string,
    annotationType: AnnotationType,
    templateConfig?: AnnotationTemplateConfig
  ): Promise<string | null> {
    try {
      const response = await this.createProjectWithTemplate({
        task_id: taskId,
        task_name: taskName,
        annotation_type: annotationType,
        template_config: templateConfig,
      });

      return response.project_id;
    } catch (error) {
      console.error('Failed to create and link project:', error);
      return null;
    }
  },

  /**
   * Sync annotations from Label Studio back to SuperInsight
   * @param projectId - Label Studio project ID
   * @returns Sync result with counts and errors
   */
  async syncAnnotations(projectId: string): Promise<SyncAnnotationsResponse> {
    const response = await apiClient.post<SyncAnnotationsResponse>(
      API_ENDPOINTS.LABEL_STUDIO.SYNC_ANNOTATIONS(projectId)
    );
    return response.data;
  },
};

export default labelStudioService;
