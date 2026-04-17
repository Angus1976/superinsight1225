/**
 * Toolkit Store
 *
 * Manages smart processing routing state: file upload, profiling,
 * strategy routing, and pipeline execution via the Toolkit API.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import apiClient from '@/services/api/client';
import { apiResponseToSnake } from '@/utils/jsonCase';
import type { AxiosError } from 'axios';
import type {
  StrategyCandidate,
  ExecutionStatus,
  ProcessingMode,
} from '@/types/toolkit';

// ============================================================================
// API Response Types
// ============================================================================

interface UploadResponse {
  file_id: string;
  filename: string;
  size: number;
}

interface RouteResponse {
  plan: Record<string, unknown>;
  candidates: StrategyCandidate[];
  origin: string;
}

interface ExecuteResponse {
  execution_id: string;
  status: string;
}


// ============================================================================
// Store Interface
// ============================================================================

interface ToolkitState {
  // Data
  fileId: string | null;
  profile: Record<string, unknown> | null;
  plan: Record<string, unknown> | null;
  candidates: StrategyCandidate[];
  mode: ProcessingMode;
  selectedStrategy: string | null;
  executionStatus: ExecutionStatus | null;

  // Loading states
  isUploading: boolean;
  isRouting: boolean;
  isExecuting: boolean;

  // Error
  error: string | null;
}

interface ToolkitActions {
  uploadFile: (file: File, origin: string) => Promise<void>;
  routeFile: (origin: string) => Promise<void>;
  selectStrategy: (name: string) => void;
  executePipeline: () => Promise<void>;
  setMode: (mode: ProcessingMode) => void;
  clearError: () => void;
  reset: () => void;
}

export type ToolkitStore = ToolkitState & ToolkitActions;

// ============================================================================
// Helpers
// ============================================================================

const API_BASE = '/api/toolkit';

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

const initialState: ToolkitState = {
  fileId: null,
  profile: null,
  plan: null,
  candidates: [],
  mode: 'auto',
  selectedStrategy: null,
  executionStatus: null,
  isUploading: false,
  isRouting: false,
  isExecuting: false,
  error: null,
};

// ============================================================================
// Store
// ============================================================================

export const useToolkitStore = create<ToolkitStore>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // ------------------------------------------------------------------
      // uploadFile — POST /api/toolkit/upload + POST /api/toolkit/profile/{id}
      // ------------------------------------------------------------------
      uploadFile: async (file: File, _origin: string): Promise<void> => {
        set({ isUploading: true, error: null }, false, 'uploadFile/start');
        try {
          const formData = new FormData();
          formData.append('file', file);

          const uploadRes = await apiClient.post<UploadResponse>(
            `${API_BASE}/upload`,
            formData,
            { headers: { 'Content-Type': 'multipart/form-data' } },
          );
          const data = apiResponseToSnake<UploadResponse>(uploadRes.data);

          // Profile the uploaded file immediately
          const profileRes = await apiClient.post<Record<string, unknown>>(
            `${API_BASE}/profile/${data.file_id}`,
          );
          const profile = apiResponseToSnake<Record<string, unknown>>(profileRes.data);

          set({
            fileId: data.file_id,
            profile,
            isUploading: false,
          }, false, 'uploadFile/success');
        } catch (err) {
          set({ isUploading: false, error: extractErrorMessage(err) }, false, 'uploadFile/error');
          throw err;
        }
      },

      // ------------------------------------------------------------------
      // routeFile — POST /api/toolkit/route/{file_id}?origin=xxx
      // ------------------------------------------------------------------
      routeFile: async (origin: string): Promise<void> => {
        const { fileId } = get();
        if (!fileId) {
          set({ error: 'No file uploaded' }, false, 'routeFile/noFile');
          return;
        }

        set({ isRouting: true, error: null }, false, 'routeFile/start');
        try {
          const routeRes = await apiClient.post<RouteResponse>(
            `${API_BASE}/route/${fileId}`,
            null,
            { params: { origin } },
          );
          const data = apiResponseToSnake<RouteResponse>(routeRes.data);

          const topStrategy = data.candidates.length > 0
            ? data.candidates[0].name
            : null;

          set({
            plan: data.plan,
            candidates: data.candidates,
            selectedStrategy: topStrategy,
            isRouting: false,
          }, false, 'routeFile/success');
        } catch (err) {
          set({ isRouting: false, error: extractErrorMessage(err) }, false, 'routeFile/error');
          throw err;
        }
      },

      // ------------------------------------------------------------------
      // selectStrategy — sync action for manual mode
      // ------------------------------------------------------------------
      selectStrategy: (name: string): void => {
        set({ selectedStrategy: name }, false, 'selectStrategy');
      },

      // ------------------------------------------------------------------
      // executePipeline — POST /api/toolkit/execute/{file_id}
      // ------------------------------------------------------------------
      executePipeline: async (): Promise<void> => {
        const { fileId, selectedStrategy, mode } = get();
        if (!fileId) {
          set({ error: 'No file uploaded' }, false, 'executePipeline/noFile');
          return;
        }

        set({ isExecuting: true, error: null }, false, 'executePipeline/start');
        try {
          const strategyParam = mode === 'manual' ? selectedStrategy : null;

          const execRes = await apiClient.post<ExecuteResponse>(
            `${API_BASE}/execute/${fileId}`,
            null,
            { params: strategyParam ? { strategy_name: strategyParam } : undefined },
          );
          const data = apiResponseToSnake<ExecuteResponse>(execRes.data);

          set({
            executionStatus: {
              executionId: data.execution_id,
              status: data.status as ExecutionStatus['status'],
              progress: 0,
            },
            isExecuting: false,
          }, false, 'executePipeline/success');
        } catch (err) {
          set({ isExecuting: false, error: extractErrorMessage(err) }, false, 'executePipeline/error');
          throw err;
        }
      },

      // ------------------------------------------------------------------
      // setMode — switch between auto and manual
      // ------------------------------------------------------------------
      setMode: (mode: ProcessingMode): void => {
        set({ mode }, false, 'setMode');
      },

      // ------------------------------------------------------------------
      // Local state actions
      // ------------------------------------------------------------------
      clearError: () => set({ error: null }, false, 'clearError'),
      reset: () => set(initialState, false, 'reset'),
    }),
    { name: 'ToolkitStore' },
  ),
);
