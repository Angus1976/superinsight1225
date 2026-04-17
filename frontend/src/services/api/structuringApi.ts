/**
 * Structuring API Service
 *
 * Typed API functions for the AI data structuring workflow.
 * Wraps apiClient calls for: job creation, status polling, schema confirmation,
 * extraction triggering, record fetching, and annotation task creation.
 */

import apiClient from './client';
import { apiRequestToSnake, apiResponseToSnake } from '@/utils/jsonCase';
import type {
  StructuringJob,
  InferredSchema,
  StructuredRecord,
} from '@/stores/structuringStore';

// ============================================================================
// API Response Types
// ============================================================================

export interface JobCreateResponse {
  job_id: string;
  status: string;
  file_name: string;
  file_type: string;
  created_at: string;
  message: string;
}

export interface SchemaConfirmResponse {
  job_id: string;
  confirmed_schema: InferredSchema;
  message: string;
}

export interface ExtractResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface RecordListResponse {
  items: StructuredRecord[];
  total: number;
  page: number;
  size: number;
}

export interface CreateTaskResponse {
  job_id: string;
  task: Record<string, unknown>;
  message: string;
}

// ============================================================================
// Constants
// ============================================================================

const API_BASE = '/api/structuring';

// ============================================================================
// API Functions
// ============================================================================

/** POST /api/structuring/jobs — upload file and create a structuring job. */
export async function createJob(file: File): Promise<JobCreateResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await apiClient.post<JobCreateResponse>(
    `${API_BASE}/jobs`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return apiResponseToSnake<JobCreateResponse>(data);
}

/** GET /api/structuring/jobs/{id} — fetch current job status and details. */
export async function getJob(jobId: string): Promise<StructuringJob> {
  const { data } = await apiClient.get<StructuringJob>(
    `${API_BASE}/jobs/${jobId}`,
  );
  return apiResponseToSnake<StructuringJob>(data);
}

/** PUT /api/structuring/jobs/{id}/schema — confirm or edit the inferred schema. */
export async function confirmSchema(
  jobId: string,
  schema: InferredSchema,
): Promise<SchemaConfirmResponse> {
  const { data } = await apiClient.put<SchemaConfirmResponse>(
    `${API_BASE}/jobs/${jobId}/schema`,
    apiRequestToSnake({ confirmed_schema: schema }),
  );
  return apiResponseToSnake<SchemaConfirmResponse>(data);
}

/** POST /api/structuring/jobs/{id}/extract — trigger entity extraction. */
export async function triggerExtraction(
  jobId: string,
): Promise<ExtractResponse> {
  const { data } = await apiClient.post<ExtractResponse>(
    `${API_BASE}/jobs/${jobId}/extract`,
  );
  return apiResponseToSnake<ExtractResponse>(data);
}

/** GET /api/structuring/jobs/{id}/records — fetch paginated structured records. */
export async function getRecords(
  jobId: string,
  page = 1,
  size = 20,
): Promise<RecordListResponse> {
  const { data } = await apiClient.get<RecordListResponse>(
    `${API_BASE}/jobs/${jobId}/records`,
    { params: { page, size } },
  );
  return apiResponseToSnake<RecordListResponse>(data);
}

/** POST /api/structuring/jobs/{id}/create-tasks — create annotation tasks from results. */
export async function createAnnotationTasks(
  jobId: string,
): Promise<CreateTaskResponse> {
  const { data } = await apiClient.post<CreateTaskResponse>(
    `${API_BASE}/jobs/${jobId}/create-tasks`,
  );
  return apiResponseToSnake<CreateTaskResponse>(data);
}
