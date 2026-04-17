/**
 * Structuring Store
 *
 * Manages AI data structuring workflow state: jobs, schemas, and records.
 * Handles API interactions for the full structuring pipeline.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import apiClient from '@/services/api/client';
import { apiRequestToSnake, apiResponseToSnake } from '@/utils/jsonCase';
import type { AxiosError } from 'axios';

// ============================================================================
// Types
// ============================================================================

export type FieldType =
  | 'string'
  | 'integer'
  | 'float'
  | 'boolean'
  | 'date'
  | 'entity'
  | 'list';

export type JobStatus =
  | 'pending'
  | 'extracting'
  | 'inferring'
  | 'confirming'
  | 'extracting_entities'
  | 'completed'
  | 'failed';

export interface SchemaField {
  name: string;
  field_type: FieldType;
  description: string;
  required: boolean;
  entity_type?: string | null;
}

export interface InferredSchema {
  fields: SchemaField[];
  confidence: number;
  source_description: string;
}

export interface StructuringJob {
  job_id: string;
  status: JobStatus;
  file_name: string;
  file_type: string;
  record_count: number;
  raw_content: string | null;
  inferred_schema: InferredSchema | null;
  confirmed_schema: InferredSchema | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface StructuredRecord {
  id: string;
  fields: Record<string, unknown>;
  confidence: number;
  source_span: string | null;
  created_at: string;
}

export interface RecordPagination {
  page: number;
  size: number;
  total: number;
}

// ============================================================================
// API Response Types
// ============================================================================

interface JobCreateResponse {
  job_id: string;
  status: string;
  file_name: string;
  file_type: string;
  created_at: string;
  message: string;
}

interface RecordListResponse {
  items: StructuredRecord[];
  total: number;
  page: number;
  size: number;
}

// ============================================================================
// Store Interface
// ============================================================================

interface StructuringState {
  // Data
  currentJob: StructuringJob | null;
  jobs: StructuringJob[];
  schema: InferredSchema | null;
  records: StructuredRecord[];
  recordPagination: RecordPagination;

  // Loading states
  isUploading: boolean;
  isLoadingJob: boolean;
  isConfirmingSchema: boolean;
  isExtracting: boolean;
  isLoadingRecords: boolean;
  isCreatingTasks: boolean;

  // Error
  error: string | null;
}

interface StructuringActions {
  // API actions
  uploadFile: (file: File) => Promise<string>;
  fetchJob: (jobId: string) => Promise<void>;
  confirmSchema: (jobId: string, schema: InferredSchema) => Promise<void>;
  startExtraction: (jobId: string) => Promise<void>;
  fetchRecords: (jobId: string, page?: number, size?: number) => Promise<void>;
  createAnnotationTasks: (jobId: string) => Promise<void>;

  // Local state actions
  setCurrentJob: (job: StructuringJob | null) => void;
  clearError: () => void;
  reset: () => void;
}

export type StructuringStore = StructuringState & StructuringActions;

// ============================================================================
// Helpers
// ============================================================================

const API_BASE = '/api/structuring';

function extractErrorMessage(err: unknown): string {
  const axiosErr = err as AxiosError<{ detail?: string }>;
  if (axiosErr.response?.data?.detail) {
    return axiosErr.response.data.detail;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return 'Unknown error';
}

// ============================================================================
// Initial State
// ============================================================================

const initialPagination: RecordPagination = {
  page: 1,
  size: 20,
  total: 0,
};

const initialState: StructuringState = {
  currentJob: null,
  jobs: [],
  schema: null,
  records: [],
  recordPagination: initialPagination,
  isUploading: false,
  isLoadingJob: false,
  isConfirmingSchema: false,
  isExtracting: false,
  isLoadingRecords: false,
  isCreatingTasks: false,
  error: null,
};

// ============================================================================
// Store
// ============================================================================

export const useStructuringStore = create<StructuringStore>()(
  devtools(
    (set) => ({
      ...initialState,

      // ------------------------------------------------------------------
      // uploadFile — POST /api/structuring/jobs (multipart/form-data)
      // ------------------------------------------------------------------
      uploadFile: async (file: File): Promise<string> => {
        set({ isUploading: true, error: null }, false, 'uploadFile/start');
        try {
          const formData = new FormData();
          formData.append('file', file);

          const createRes = await apiClient.post<JobCreateResponse>(
            `${API_BASE}/jobs`,
            formData,
            { 
              headers: { 'Content-Type': 'multipart/form-data' },
              timeout: 60000, // 60 seconds for file upload
            },
          );
          const data = apiResponseToSnake<JobCreateResponse>(createRes.data);

          const newJob: StructuringJob = {
            job_id: data.job_id,
            status: data.status as JobStatus,
            file_name: data.file_name,
            file_type: data.file_type,
            record_count: 0,
            raw_content: null,
            inferred_schema: null,
            confirmed_schema: null,
            error_message: null,
            created_at: data.created_at,
            updated_at: data.created_at,
          };

          set((state) => ({
            currentJob: newJob,
            jobs: [newJob, ...state.jobs],
            isUploading: false,
          }), false, 'uploadFile/success');

          return data.job_id;
        } catch (err) {
          set({ isUploading: false, error: extractErrorMessage(err) }, false, 'uploadFile/error');
          throw err;
        }
      },

      // ------------------------------------------------------------------
      // fetchJob — GET /api/structuring/jobs/{id}
      // ------------------------------------------------------------------
      fetchJob: async (jobId: string): Promise<void> => {
        set({ isLoadingJob: true, error: null }, false, 'fetchJob/start');
        try {
          const jobRes = await apiClient.get<StructuringJob>(`${API_BASE}/jobs/${jobId}`);
          const data = apiResponseToSnake<StructuringJob>(jobRes.data);

          const job: StructuringJob = {
            ...data,
            status: data.status as JobStatus,
          };

          set((state) => ({
            currentJob: job,
            schema: job.confirmed_schema ?? job.inferred_schema ?? state.schema,
            jobs: state.jobs.some((j) => j.job_id === jobId)
              ? state.jobs.map((j) => (j.job_id === jobId ? job : j))
              : [job, ...state.jobs],
            isLoadingJob: false,
          }), false, 'fetchJob/success');
        } catch (err) {
          set({ isLoadingJob: false, error: extractErrorMessage(err) }, false, 'fetchJob/error');
          throw err;
        }
      },

      // ------------------------------------------------------------------
      // confirmSchema — PUT /api/structuring/jobs/{id}/schema
      // ------------------------------------------------------------------
      confirmSchema: async (jobId: string, schema: InferredSchema): Promise<void> => {
        set({ isConfirmingSchema: true, error: null }, false, 'confirmSchema/start');
        try {
          await apiClient.put(
            `${API_BASE}/jobs/${jobId}/schema`,
            apiRequestToSnake({ confirmed_schema: schema }),
          );

          set((state) => ({
            schema,
            currentJob: state.currentJob
              ? { ...state.currentJob, confirmed_schema: schema }
              : null,
            isConfirmingSchema: false,
          }), false, 'confirmSchema/success');
        } catch (err) {
          set({ isConfirmingSchema: false, error: extractErrorMessage(err) }, false, 'confirmSchema/error');
          throw err;
        }
      },

      // ------------------------------------------------------------------
      // startExtraction — POST /api/structuring/jobs/{id}/extract
      // ------------------------------------------------------------------
      startExtraction: async (jobId: string): Promise<void> => {
        set({ isExtracting: true, error: null }, false, 'startExtraction/start');
        try {
          await apiClient.post(`${API_BASE}/jobs/${jobId}/extract`);

          set((state) => ({
            currentJob: state.currentJob
              ? { ...state.currentJob, status: 'extracting_entities' as JobStatus }
              : null,
            isExtracting: false,
          }), false, 'startExtraction/success');
        } catch (err) {
          set({ isExtracting: false, error: extractErrorMessage(err) }, false, 'startExtraction/error');
          throw err;
        }
      },

      // ------------------------------------------------------------------
      // fetchRecords — GET /api/structuring/jobs/{id}/records (paginated)
      // ------------------------------------------------------------------
      fetchRecords: async (jobId: string, page = 1, size = 20): Promise<void> => {
        set({ isLoadingRecords: true, error: null }, false, 'fetchRecords/start');
        try {
          const recordsRes = await apiClient.get<RecordListResponse>(
            `${API_BASE}/jobs/${jobId}/records`,
            { params: { page, size } },
          );
          const data = apiResponseToSnake<RecordListResponse>(recordsRes.data);

          set({
            records: data.items,
            recordPagination: { page: data.page, size: data.size, total: data.total },
            isLoadingRecords: false,
          }, false, 'fetchRecords/success');
        } catch (err) {
          set({ isLoadingRecords: false, error: extractErrorMessage(err) }, false, 'fetchRecords/error');
          throw err;
        }
      },

      // ------------------------------------------------------------------
      // createAnnotationTasks — POST /api/structuring/jobs/{id}/create-tasks
      // ------------------------------------------------------------------
      createAnnotationTasks: async (jobId: string): Promise<void> => {
        set({ isCreatingTasks: true, error: null }, false, 'createAnnotationTasks/start');
        try {
          await apiClient.post(`${API_BASE}/jobs/${jobId}/create-tasks`);
          set({ isCreatingTasks: false }, false, 'createAnnotationTasks/success');
        } catch (err) {
          set({ isCreatingTasks: false, error: extractErrorMessage(err) }, false, 'createAnnotationTasks/error');
          throw err;
        }
      },

      // ------------------------------------------------------------------
      // Local state actions
      // ------------------------------------------------------------------
      setCurrentJob: (job) => set({ currentJob: job }, false, 'setCurrentJob'),
      clearError: () => set({ error: null }, false, 'clearError'),
      reset: () => set(initialState, false, 'reset'),
    }),
    { name: 'StructuringStore' },
  ),
);
