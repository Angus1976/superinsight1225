/**
 * Semantic Store
 *
 * Manages AI semantic analysis workflow state: jobs and semantic records.
 * Handles API interactions for the semantic pipeline.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import apiClient from '@/services/api/client';
import { apiResponseToSnake } from '@/utils/jsonCase';
import type { AxiosError } from 'axios';

// ============================================================================
// Types
// ============================================================================

export type SemJobStatus =
  | 'pending'
  | 'extracting'
  | 'processing'
  | 'completed'
  | 'failed';

export type SemanticRecordType = 'entity' | 'relationship' | 'summary';

export interface SemanticProgressInfo {
  stage: string;
  current: number;
  total: number;
  percent: number;
}

export interface SemanticJob {
  job_id: string;
  status: SemJobStatus;
  file_name: string;
  file_type: string;
  record_count: number;
  error_message: string | null;
  progress_info: SemanticProgressInfo | null;
  created_at: string;
  updated_at: string;
}

export interface SemanticRecord {
  id: string;
  record_type: SemanticRecordType;
  content: Record<string, unknown>;
  confidence: number;
  created_at: string;
}

export interface SemRecordPagination {
  page: number;
  size: number;
  total: number;
}

// ============================================================================
// API Response Types
// ============================================================================

interface SemJobCreateResponse {
  job_id: string;
  status: string;
  file_name: string;
  file_type: string;
  created_at: string;
  message: string;
}

interface SemJobListItem {
  job_id: string;
  status: string;
  file_name: string;
  file_type: string;
  progress_info: SemanticProgressInfo | null;
  created_at: string;
}

interface SemJobListResponse {
  items: SemJobListItem[];
  total: number;
}

interface SemRecordListResponse {
  items: SemanticRecord[];
  total: number;
  page: number;
  size: number;
}

// ============================================================================
// Store Interface
// ============================================================================

interface SemanticState {
  // Data
  currentJob: SemanticJob | null;
  jobs: SemanticJob[];
  records: SemanticRecord[];
  recordPagination: SemRecordPagination;

  // Loading states
  isUploading: boolean;
  isLoadingJob: boolean;
  isLoadingJobs: boolean;
  isLoadingRecords: boolean;

  // Error
  error: string | null;
}

interface SemanticActions {
  // API actions
  uploadFile: (file: File) => Promise<string>;
  fetchJob: (jobId: string) => Promise<void>;
  fetchJobs: () => Promise<void>;
  fetchRecords: (jobId: string, page?: number, size?: number, recordType?: SemanticRecordType) => Promise<void>;

  // Local state actions
  setCurrentJob: (job: SemanticJob | null) => void;
  clearError: () => void;
  reset: () => void;
}

export type SemanticStore = SemanticState & SemanticActions;

// ============================================================================
// Helpers
// ============================================================================

const API_BASE = '/api/semantic';

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

const initialPagination: SemRecordPagination = {
  page: 1,
  size: 20,
  total: 0,
};

const initialState: SemanticState = {
  currentJob: null,
  jobs: [],
  records: [],
  recordPagination: initialPagination,
  isUploading: false,
  isLoadingJob: false,
  isLoadingJobs: false,
  isLoadingRecords: false,
  error: null,
};

// ============================================================================
// Store
// ============================================================================

export const useSemanticStore = create<SemanticStore>()(
  devtools(
    (set) => ({
      ...initialState,

      // ------------------------------------------------------------------
      // uploadFile — POST /api/semantic/jobs (multipart/form-data)
      // ------------------------------------------------------------------
      uploadFile: async (file: File): Promise<string> => {
        set({ isUploading: true, error: null }, false, 'uploadFile/start');
        try {
          const formData = new FormData();
          formData.append('file', file);

          const createRes = await apiClient.post<SemJobCreateResponse>(
            `${API_BASE}/jobs`,
            formData,
            { headers: { 'Content-Type': 'multipart/form-data' } },
          );
          const data = apiResponseToSnake<SemJobCreateResponse>(createRes.data);

          const newJob: SemanticJob = {
            job_id: data.job_id,
            status: data.status as SemJobStatus,
            file_name: data.file_name,
            file_type: data.file_type,
            record_count: 0,
            error_message: null,
            progress_info: null,
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
      // fetchJob — GET /api/semantic/jobs/{id}
      // ------------------------------------------------------------------
      fetchJob: async (jobId: string): Promise<void> => {
        set({ isLoadingJob: true, error: null }, false, 'fetchJob/start');
        try {
          const jobRes = await apiClient.get<SemanticJob>(`${API_BASE}/jobs/${jobId}`);
          const data = apiResponseToSnake<SemanticJob>(jobRes.data);

          const job: SemanticJob = {
            ...data,
            status: data.status as SemJobStatus,
          };

          set((state) => ({
            currentJob: job,
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
      // fetchJobs — GET /api/semantic/jobs
      // ------------------------------------------------------------------
      fetchJobs: async (): Promise<void> => {
        set({ isLoadingJobs: true, error: null }, false, 'fetchJobs/start');
        try {
          const listRes = await apiClient.get<SemJobListResponse>(`${API_BASE}/jobs`);
          const data = apiResponseToSnake<SemJobListResponse>(listRes.data);

          const jobs: SemanticJob[] = data.items.map((item) => ({
            job_id: item.job_id,
            status: item.status as SemJobStatus,
            file_name: item.file_name,
            file_type: item.file_type,
            record_count: 0,
            error_message: null,
            progress_info: item.progress_info ?? null,
            created_at: item.created_at,
            updated_at: item.created_at,
          }));

          set({ jobs, isLoadingJobs: false }, false, 'fetchJobs/success');
        } catch (err) {
          set({ isLoadingJobs: false, error: extractErrorMessage(err) }, false, 'fetchJobs/error');
          throw err;
        }
      },

      // ------------------------------------------------------------------
      // fetchRecords — GET /api/semantic/jobs/{id}/records (paginated, optional record_type filter)
      // ------------------------------------------------------------------
      fetchRecords: async (jobId: string, page = 1, size = 20, recordType?: SemanticRecordType): Promise<void> => {
        set({ isLoadingRecords: true, error: null }, false, 'fetchRecords/start');
        try {
          const params: Record<string, unknown> = { page, size };
          if (recordType) {
            params.record_type = recordType;
          }

          const recordsRes = await apiClient.get<SemRecordListResponse>(
            `${API_BASE}/jobs/${jobId}/records`,
            { params },
          );
          const data = apiResponseToSnake<SemRecordListResponse>(recordsRes.data);

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
      // Local state actions
      // ------------------------------------------------------------------
      setCurrentJob: (job) => set({ currentJob: job }, false, 'setCurrentJob'),
      clearError: () => set({ error: null }, false, 'clearError'),
      reset: () => set(initialState, false, 'reset'),
    }),
    { name: 'SemanticStore' },
  ),
);
