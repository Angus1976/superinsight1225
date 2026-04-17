// Task API service with pagination support
import apiClient from './api/client';
import { API_ENDPOINTS } from '@/constants';
import { apiRequestToSnake, apiResponseToSnake } from '@/utils/jsonCase';
import type {
  Task,
  TaskListParams,
  TaskListResponse,
  CreateTaskPayload,
  UpdateTaskPayload,
  TaskStats,
} from '@/types';

// Default pagination settings
const DEFAULT_PAGE_SIZE = 10;

export const taskService = {
  // Get task list with pagination and filters
  async getList(params: TaskListParams = {}): Promise<TaskListResponse> {
    const { status, page_size, ...rest } = params;
    // Map frontend param names to backend query param names
    const paginatedParams: Record<string, unknown> = {
      ...rest,
      page: params.page || 1,
      size: page_size || DEFAULT_PAGE_SIZE,
    };
    if (status) paginatedParams.status_filter = status;
    const response = await apiClient.get<TaskListResponse>(API_ENDPOINTS.TASKS.BASE, { 
      params: paginatedParams 
    });
    return apiResponseToSnake<TaskListResponse>(response.data);
  },

  // Get single task by ID
  async getById(id: string): Promise<Task> {
    const response = await apiClient.get<Task>(API_ENDPOINTS.TASKS.BY_ID(id));
    return apiResponseToSnake<Task>(response.data);
  },

  // Create a new task
  async create(payload: CreateTaskPayload): Promise<Task> {
    const response = await apiClient.post<Task>(API_ENDPOINTS.TASKS.BASE, apiRequestToSnake(payload));
    return apiResponseToSnake<Task>(response.data);
  },

  // Update an existing task
  async update(id: string, payload: UpdateTaskPayload): Promise<Task> {
    const response = await apiClient.patch<Task>(
      API_ENDPOINTS.TASKS.BY_ID(id),
      apiRequestToSnake(payload)
    );
    return apiResponseToSnake<Task>(response.data);
  },

  // Delete a task
  async delete(id: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.TASKS.BY_ID(id));
  },

  // Get task statistics
  async getStats(): Promise<TaskStats> {
    const response = await apiClient.get<TaskStats>(API_ENDPOINTS.TASKS.STATS);
    return apiResponseToSnake<TaskStats>(response.data);
  },

  // Assign task to user
  async assign(id: string, userId: string): Promise<Task> {
    const response = await apiClient.post<Task>(
      API_ENDPOINTS.TASKS.ASSIGN(id),
      apiRequestToSnake({ assignee_id: userId })
    );
    return apiResponseToSnake<Task>(response.data);
  },

  // Batch operations
  async batchDelete(ids: string[]): Promise<void> {
    await apiClient.post(API_ENDPOINTS.TASKS.BATCH, apiRequestToSnake({ action: 'delete', ids }));
  },

  async batchUpdateStatus(ids: string[], status: string): Promise<void> {
    await apiClient.post(
      API_ENDPOINTS.TASKS.BATCH,
      apiRequestToSnake({ action: 'update_status', ids, status })
    );
  },
};
