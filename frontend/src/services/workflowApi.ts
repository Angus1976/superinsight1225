/**
 * Quality Workflow API Service - 质量工作流 API 服务
 * 对应后端 API: quality_workflow.py
 */

import apiClient from './api/client';

// Types
export interface QualityIssue {
  rule_id: string;
  rule_name: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  field?: string;
}

export interface ImprovementTask {
  id: string;
  annotation_id: string;
  project_id: string;
  issues: QualityIssue[];
  assignee_id: string;
  assignee_name?: string;
  status: 'pending' | 'in_progress' | 'submitted' | 'approved' | 'rejected';
  priority: number;
  improved_data?: Record<string, unknown>;
  reviewer_id?: string;
  reviewer_name?: string;
  review_comments?: string;
  created_at: string;
  submitted_at?: string;
  reviewed_at?: string;
}

export interface ImprovementHistory {
  id: string;
  task_id: string;
  action: string;
  actor_id: string;
  actor_name?: string;
  details?: Record<string, unknown>;
  created_at: string;
}

export interface QualityWorkflow {
  id: string;
  project_id: string;
  stages: string[];
  auto_create_task: boolean;
  escalation_rules: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ImprovementEffectReport {
  project_id: string;
  period: string;
  total_tasks: number;
  completed_tasks: number;
  average_improvement_score: number;
  improvement_by_dimension: Record<string, number>;
}

// Request types
export interface WorkflowConfigRequest {
  project_id: string;
  stages?: string[];
  auto_create_task?: boolean;
  escalation_rules?: Record<string, unknown>;
}

export interface CreateTaskRequest {
  annotation_id: string;
  issues: QualityIssue[];
  assignee_id?: string;
}

export interface SubmitImprovementRequest {
  improved_data: Record<string, unknown>;
}

export interface ReviewImprovementRequest {
  approved: boolean;
  comments?: string;
}

export interface TaskListParams {
  project_id?: string;
  assignee_id?: string;
  status?: string;
  priority?: number;
  page?: number;
  page_size?: number;
}

export interface TaskListResponse {
  items: ImprovementTask[];
  total: number;
  page: number;
  page_size: number;
}

// API Service
export const workflowApi = {
  // Workflow Configuration
  async configureWorkflow(request: WorkflowConfigRequest): Promise<QualityWorkflow> {
    const response = await apiClient.post<QualityWorkflow>('/api/v1/quality-workflow/configure', request);
    return response.data;
  },

  async getWorkflowConfig(projectId: string): Promise<QualityWorkflow> {
    const response = await apiClient.get<QualityWorkflow>(`/api/v1/quality-workflow/config/${projectId}`);
    return response.data;
  },

  // Improvement Tasks
  async createTask(request: CreateTaskRequest): Promise<ImprovementTask> {
    const response = await apiClient.post<ImprovementTask>('/api/v1/quality-workflow/tasks', request);
    return response.data;
  },

  async listTasks(params?: TaskListParams): Promise<TaskListResponse> {
    const response = await apiClient.get<TaskListResponse>('/api/v1/quality-workflow/tasks', { params });
    return response.data;
  },

  async getTask(taskId: string): Promise<ImprovementTask> {
    const response = await apiClient.get<ImprovementTask>(`/api/v1/quality-workflow/tasks/${taskId}`);
    return response.data;
  },

  async submitImprovement(taskId: string, request: SubmitImprovementRequest): Promise<ImprovementTask> {
    const response = await apiClient.post<ImprovementTask>(
      `/api/v1/quality-workflow/tasks/${taskId}/submit`,
      request
    );
    return response.data;
  },

  async reviewImprovement(taskId: string, request: ReviewImprovementRequest): Promise<ImprovementTask> {
    const response = await apiClient.post<ImprovementTask>(
      `/api/v1/quality-workflow/tasks/${taskId}/review`,
      request
    );
    return response.data;
  },

  async getTaskHistory(taskId: string): Promise<ImprovementHistory[]> {
    const response = await apiClient.get<ImprovementHistory[]>(
      `/api/v1/quality-workflow/tasks/${taskId}/history`
    );
    return response.data;
  },

  // Effect Evaluation
  async evaluateEffect(projectId: string, period?: string): Promise<ImprovementEffectReport> {
    const response = await apiClient.get<ImprovementEffectReport>(
      `/api/v1/quality-workflow/effect/${projectId}`,
      { params: { period } }
    );
    return response.data;
  },

  // Batch Operations
  async batchAssign(taskIds: string[], assigneeId: string): Promise<ImprovementTask[]> {
    const response = await apiClient.post<ImprovementTask[]>('/api/v1/quality-workflow/tasks/batch-assign', {
      task_ids: taskIds,
      assignee_id: assigneeId,
    });
    return response.data;
  },

  async batchReview(
    taskIds: string[],
    approved: boolean,
    comments?: string
  ): Promise<ImprovementTask[]> {
    const response = await apiClient.post<ImprovementTask[]>('/api/v1/quality-workflow/tasks/batch-review', {
      task_ids: taskIds,
      approved,
      comments,
    });
    return response.data;
  },
};

export default workflowApi;
