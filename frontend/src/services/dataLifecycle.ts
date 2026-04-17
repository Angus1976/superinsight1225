// Data Lifecycle Management API client
import apiClient from './api/client';
import { apiRequestToSnake, apiResponseToSnake } from '@/utils/jsonCase';
import { API_ENDPOINTS } from '@/constants';

// ============================================================================
// Types
// ============================================================================

// Temp Data Types
export interface TempData {
  id: string;
  name: string;
  content: Record<string, unknown>;
  state: string;
  uploaded_by: string;
  uploaded_at: string;
  updated_at?: string;
  metadata?: Record<string, unknown>;
}

export interface CreateTempDataPayload {
  name: string;
  content: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface UpdateTempDataPayload {
  name?: string;
  content?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface TempDataListParams {
  page?: number;
  page_size?: number;
  state?: string;
  uploaded_by?: string;
}

export interface TempDataListResponse {
  items: TempData[];
  total: number;
  page: number;
  page_size: number;
}

// Sample Library Types
export interface Sample {
  id: string;
  name: string;
  description?: string;
  data_type: string;
  quality_score: number;
  usage_count: number;
  created_by: string;
  created_at: string;
  updated_at?: string;
  metadata?: Record<string, unknown>;
}

export interface CreateSamplePayload {
  name: string;
  description?: string;
  data_type: string;
  content: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface SampleListParams {
  page?: number;
  page_size?: number;
  search?: string;
  data_type?: string;
  min_quality_score?: number;
}

export interface SampleListResponse {
  items: Sample[];
  total: number;
  page: number;
  page_size: number;
}

// Review Types
export interface Review {
  id: string;
  target_type: string;
  target_id: string;
  requester: string;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  submitted_at: string;
  reviewed_at?: string;
  reviewer?: string;
  rejection_reason?: string;
  metadata?: Record<string, unknown>;
}

export interface ReviewListParams {
  page?: number;
  page_size?: number;
  status?: string;
  requester?: string;
  reviewer?: string;
}

export interface ReviewListResponse {
  items: Review[];
  total: number;
  page: number;
  page_size: number;
}

// Annotation Task Types
export interface AnnotationTask {
  id: string;
  name: string;
  description?: string;
  status: 'created' | 'in_progress' | 'completed' | 'cancelled';
  annotation_type: 'classification' | 'entity_recognition' | 'relation_extraction' | 'sentiment_analysis' | 'custom';
  sample_ids: string[];
  instructions: string;
  assigned_to?: string[];
  deadline?: string;
  progress: number;
  created_by: string;
  created_at: string;
  updated_at?: string;
  metadata?: Record<string, unknown>;
}

export interface CreateAnnotationTaskPayload {
  name: string;
  description?: string;
  sample_ids: string[];
  annotation_type: 'classification' | 'entity_recognition' | 'relation_extraction' | 'sentiment_analysis' | 'custom';
  instructions: string;
  created_by: string;
  deadline?: string;
  assigned_to?: string[];
}

export interface UpdateAnnotationTaskPayload {
  name?: string;
  description?: string;
  instructions?: string;
  assigned_to?: string[];
  deadline?: string;
  status?: 'created' | 'in_progress' | 'completed' | 'cancelled';
}

export interface AnnotationTaskListParams {
  page?: number;
  page_size?: number;
  status?: string;
  priority?: string;
  assignee?: string;
}

export interface AnnotationTaskListResponse {
  items: AnnotationTask[];
  total: number;
  page: number;
  page_size: number;
}

// Enhancement Types
export interface EnhancementJob {
  id: string;
  data_id: string;
  enhancement_type: 'data_augmentation' | 'quality_improvement' | 'noise_reduction' | 'feature_extraction' | 'normalization';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused';
  progress: number;
  current_version: number;
  target_quality?: number;
  created_by: string;
  created_at: string;
  completed_at?: string;
  metadata?: Record<string, unknown>;
}

export interface CreateEnhancementPayload {
  data_id: string;
  enhancement_type: 'data_augmentation' | 'quality_improvement' | 'noise_reduction' | 'feature_extraction' | 'normalization';
  created_by: string;
  parameters?: Record<string, unknown>;
  target_quality?: number;
}

export interface EnhancementListParams {
  page?: number;
  page_size?: number;
  status?: string;
  type?: string;
}

export interface EnhancementListResponse {
  items: EnhancementJob[];
  total: number;
  page: number;
  page_size: number;
}

// AI Trial Types
export interface AITrial {
  id: string;
  name: string;
  model: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  trial_count: number;
  success_rate: number;
  avg_score: number;
  created_by: string;
  created_at: string;
  completed_at?: string;
  metadata?: Record<string, unknown>;
}

export interface CreateAITrialPayload {
  name: string;
  model: string;
  target_data_id: string;
  config?: Record<string, unknown>;
  trial_count?: number;
}

export interface AITrialListParams {
  page?: number;
  page_size?: number;
  status?: string;
  model?: string;
}

export interface AITrialListResponse {
  items: AITrial[];
  total: number;
  page: number;
  page_size: number;
}

// ============================================================================
// API Client
// ============================================================================

export const dataLifecycleApi = {
  // -------------------------------------------------------------------------
  // Temp Data API
  // -------------------------------------------------------------------------
  async listTempData(params?: TempDataListParams): Promise<TempDataListResponse> {
    const response = await apiClient.get<TempDataListResponse>(
      '/api/temp-data',
      { params }
    );
    return apiResponseToSnake(response.data);
  },

  async getTempData(id: string): Promise<TempData> {
    const response = await apiClient.get<TempData>(`/api/temp-data/${id}`);
    return apiResponseToSnake(response.data);
  },

  async createTempData(payload: CreateTempDataPayload): Promise<TempData> {
    const response = await apiClient.post<TempData>('/api/temp-data', apiRequestToSnake(payload));
    return apiResponseToSnake(response.data);
  },

  async updateTempData(id: string, payload: UpdateTempDataPayload): Promise<TempData> {
    const response = await apiClient.put<TempData>(`/api/temp-data/${id}`, apiRequestToSnake(payload));
    return apiResponseToSnake(response.data);
  },

  async deleteTempData(id: string): Promise<void> {
    await apiClient.delete(`/api/temp-data/${id}`);
  },

  async archiveTempData(id: string): Promise<TempData> {
    const response = await apiClient.post<TempData>(`/api/temp-data/${id}/archive`);
    return apiResponseToSnake(response.data);
  },

  async restoreTempData(id: string): Promise<TempData> {
    const response = await apiClient.post<TempData>(`/api/temp-data/${id}/restore`);
    return apiResponseToSnake(response.data);
  },

  // -------------------------------------------------------------------------
  // Sample Library API
  // -------------------------------------------------------------------------
  async listSamples(params?: SampleListParams): Promise<SampleListResponse> {
    const response = await apiClient.get<SampleListResponse>(
      '/api/samples',
      { params }
    );
    return apiResponseToSnake(response.data);
  },

  async getSample(id: string): Promise<Sample> {
    const response = await apiClient.get<Sample>(`/api/samples/${id}`);
    return apiResponseToSnake(response.data);
  },

  async createSample(payload: CreateSamplePayload): Promise<Sample> {
    const response = await apiClient.post<Sample>('/api/samples', apiRequestToSnake(payload));
    return apiResponseToSnake(response.data);
  },

  async deleteSample(id: string): Promise<void> {
    await apiClient.delete(`/api/samples/${id}`);
  },

  async addToLibrary(dataId: string): Promise<Sample> {
    const response = await apiClient.post<Sample>(`/api/samples/add-from-data/${dataId}`);
    return apiResponseToSnake(response.data);
  },

  async removeFromLibrary(id: string): Promise<void> {
    await apiClient.delete(`/api/samples/${id}/remove-from-library`);
  },

  async exportSample(id: string): Promise<Blob> {
    const response = await apiClient.get(`/api/samples/${id}/export`, {
      responseType: 'blob'
    });
    return apiResponseToSnake(response.data);
  },

  // -------------------------------------------------------------------------
  // Review API
  // -------------------------------------------------------------------------
  async listReviews(params?: ReviewListParams): Promise<ReviewListResponse> {
    const response = await apiClient.get<ReviewListResponse>(
      '/api/reviews',
      { params }
    );
    return apiResponseToSnake(response.data);
  },

  async getReview(id: string): Promise<Review> {
    const response = await apiClient.get<Review>(`/api/reviews/${id}`);
    return apiResponseToSnake(response.data);
  },

  async submitForReview(targetType: string, targetId: string): Promise<Review> {
    const response = await apiClient.post<Review>(
      '/api/reviews',
      apiRequestToSnake({
        target_type: targetType,
        target_id: targetId,
      })
    );
    return apiResponseToSnake(response.data);
  },

  async approveReview(id: string): Promise<Review> {
    const response = await apiClient.post<Review>(`/api/reviews/${id}/approve`);
    return apiResponseToSnake(response.data);
  },

  async rejectReview(id: string, reason: string): Promise<Review> {
    const response = await apiClient.post<Review>(
      `/api/reviews/${id}/reject`,
      apiRequestToSnake({ reason })
    );
    return apiResponseToSnake(response.data);
  },

  async cancelReview(id: string): Promise<Review> {
    const response = await apiClient.post<Review>(`/api/reviews/${id}/cancel`);
    return apiResponseToSnake(response.data);
  },

  // -------------------------------------------------------------------------
  // Annotation Task API
  // -------------------------------------------------------------------------
  async listAnnotationTasks(params?: AnnotationTaskListParams): Promise<AnnotationTaskListResponse> {
    const response = await apiClient.get<AnnotationTaskListResponse>(
      '/api/annotation-tasks',
      { params }
    );
    return apiResponseToSnake(response.data);
  },

  async getAnnotationTask(id: string): Promise<AnnotationTask> {
    const response = await apiClient.get<AnnotationTask>(`/api/annotation-tasks/${id}`);
    return apiResponseToSnake(response.data);
  },

  async createAnnotationTask(payload: CreateAnnotationTaskPayload): Promise<AnnotationTask> {
    const response = await apiClient.post<AnnotationTask>(
      '/api/annotation-tasks',
      apiRequestToSnake(payload)
    );
    return apiResponseToSnake(response.data);
  },

  async updateAnnotationTask(id: string, payload: UpdateAnnotationTaskPayload): Promise<AnnotationTask> {
    const response = await apiClient.put<AnnotationTask>(
      `/api/annotation-tasks/${id}`,
      apiRequestToSnake(payload)
    );
    return apiResponseToSnake(response.data);
  },

  async startAnnotationTask(id: string): Promise<AnnotationTask> {
    const response = await apiClient.post<AnnotationTask>(`/api/annotation-tasks/${id}/start`);
    return apiResponseToSnake(response.data);
  },

  async completeAnnotationTask(id: string): Promise<AnnotationTask> {
    const response = await apiClient.post<AnnotationTask>(`/api/annotation-tasks/${id}/complete`);
    return apiResponseToSnake(response.data);
  },

  async cancelAnnotationTask(id: string): Promise<AnnotationTask> {
    const response = await apiClient.post<AnnotationTask>(`/api/annotation-tasks/${id}/cancel`);
    return apiResponseToSnake(response.data);
  },

  async assignAnnotationTask(id: string, assignee: string): Promise<AnnotationTask> {
    const response = await apiClient.post<AnnotationTask>(
      `/api/annotation-tasks/${id}/assign`,
      apiRequestToSnake({ assignee })
    );
    return apiResponseToSnake(response.data);
  },

  // -------------------------------------------------------------------------
  // Enhancement API
  // -------------------------------------------------------------------------
  async listEnhancements(params?: EnhancementListParams): Promise<EnhancementListResponse> {
    const response = await apiClient.get<EnhancementListResponse>(
      '/api/enhancements',
      { params }
    );
    return apiResponseToSnake(response.data);
  },

  async getEnhancement(id: string): Promise<EnhancementJob> {
    const response = await apiClient.get<EnhancementJob>(`/api/enhancements/${id}`);
    return apiResponseToSnake(response.data);
  },

  async createEnhancement(payload: CreateEnhancementPayload): Promise<EnhancementJob> {
    const response = await apiClient.post<EnhancementJob>('/api/enhancements', apiRequestToSnake(payload));
    return apiResponseToSnake(response.data);
  },

  async startEnhancement(id: string): Promise<EnhancementJob> {
    const response = await apiClient.post<EnhancementJob>(`/api/enhancements/${id}/start`);
    return apiResponseToSnake(response.data);
  },

  async pauseEnhancement(id: string): Promise<EnhancementJob> {
    const response = await apiClient.post<EnhancementJob>(`/api/enhancements/${id}/pause`);
    return apiResponseToSnake(response.data);
  },

  async resumeEnhancement(id: string): Promise<EnhancementJob> {
    const response = await apiClient.post<EnhancementJob>(`/api/enhancements/${id}/resume`);
    return apiResponseToSnake(response.data);
  },

  async cancelEnhancement(id: string): Promise<EnhancementJob> {
    const response = await apiClient.post<EnhancementJob>(`/api/enhancements/${id}/cancel`);
    return apiResponseToSnake(response.data);
  },

  async rollbackEnhancement(id: string, version: number): Promise<EnhancementJob> {
    const response = await apiClient.post<EnhancementJob>(
      `/api/enhancements/${id}/rollback`,
      apiRequestToSnake({ version })
    );
    return apiResponseToSnake(response.data);
  },

  async getEnhancementHistory(id: string): Promise<Array<{ version: number; timestamp: string; changes: Record<string, unknown> }>> {
    const response = await apiClient.get(`/api/enhancements/${id}/history`);
    return apiResponseToSnake(response.data);
  },

  async addEnhancementToLibrary(id: string): Promise<Sample> {
    const response = await apiClient.post<Sample>(`/api/enhancements/${id}/add-to-library`);
    return apiResponseToSnake(response.data);
  },

  // -------------------------------------------------------------------------
  // AI Trial API
  // -------------------------------------------------------------------------
  async listAITrials(params?: AITrialListParams): Promise<AITrialListResponse> {
    const response = await apiClient.get<AITrialListResponse>(
      '/api/ai-trials',
      { params }
    );
    return apiResponseToSnake(response.data);
  },

  async getAITrial(id: string): Promise<AITrial> {
    const response = await apiClient.get<AITrial>(`/api/ai-trials/${id}`);
    return apiResponseToSnake(response.data);
  },

  async createAITrial(payload: CreateAITrialPayload): Promise<AITrial> {
    const response = await apiClient.post<AITrial>('/api/ai-trials', apiRequestToSnake(payload));
    return apiResponseToSnake(response.data);
  },

  async startAITrial(id: string): Promise<AITrial> {
    const response = await apiClient.post<AITrial>(`/api/ai-trials/${id}/start`);
    return apiResponseToSnake(response.data);
  },

  async stopAITrial(id: string): Promise<AITrial> {
    const response = await apiClient.post<AITrial>(`/api/ai-trials/${id}/stop`);
    return apiResponseToSnake(response.data);
  },

  async getAITrialResults(id: string): Promise<{
    trials: Array<{
      trial_id: string;
      success: boolean;
      score: number;
      duration: number;
      error?: string;
    }>;
    summary: {
      total: number;
      successful: number;
      failed: number;
      success_rate: number;
      avg_score: number;
      avg_duration: number;
    };
  }> {
    const response = await apiClient.get(`/api/ai-trials/${id}/results`);
    return apiResponseToSnake(response.data);
  },

  async exportAITrialResults(id: string): Promise<Blob> {
    const response = await apiClient.get(`/api/ai-trials/${id}/export`, {
      responseType: 'blob'
    });
    return apiResponseToSnake(response.data);
  },

  async compareAITrials(ids: string[]): Promise<{
    trials: AITrial[];
    comparison: {
      success_rate: Record<string, number>;
      avg_score: Record<string, number>;
      avg_duration: Record<string, number>;
    };
  }> {
    const response = await apiClient.post('/api/ai-trials/compare', apiRequestToSnake({ ids }));
    return apiResponseToSnake(response.data);
  },
};

export default dataLifecycleApi;