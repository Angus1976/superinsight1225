/**
 * Execution Store
 *
 * Manages AI annotation execution state for multiple concurrent tasks.
 * Tracks progress, distributions, errors, and supports pause/resume.
 *
 * Uses Record<string, ExecutionState> instead of Map for Zustand reactivity.
 */

import { create } from 'zustand';
import type { ExecutionError } from '@/services/aiAnnotationApi';

export interface ExecutionState {
  progress: number;          // 0-100
  processed: number;
  remaining: number;
  estimatedTime: number;     // 秒
  confidenceDistribution: { range: string; count: number }[];
  labelDistribution: { label: string; count: number }[];
  errors: ExecutionError[];
  status: 'running' | 'paused' | 'completed' | 'error';
}

interface ExecutionStoreState {
  executions: Record<string, ExecutionState>;

  startExecution: (taskId: string) => void;
  pauseExecution: (taskId: string) => void;
  updateProgress: (taskId: string, data: Partial<ExecutionState>) => void;
}

const DEFAULT_EXECUTION_STATE: ExecutionState = {
  progress: 0,
  processed: 0,
  remaining: 0,
  estimatedTime: 0,
  confidenceDistribution: [],
  labelDistribution: [],
  errors: [],
  status: 'running',
};

export const useExecutionStore = create<ExecutionStoreState>()(
  (set, get) => ({
    executions: {},

    /**
     * Initialize a new execution entry with default state.
     */
    startExecution: (taskId: string) => {
      set((state) => ({
        executions: {
          ...state.executions,
          [taskId]: { ...DEFAULT_EXECUTION_STATE },
        },
      }));
    },

    /**
     * Pause execution — sets status to 'paused', preserves processed/labelDistribution.
     */
    pauseExecution: (taskId: string) => {
      const current = get().executions[taskId];
      if (!current) return;

      set((state) => ({
        executions: {
          ...state.executions,
          [taskId]: { ...current, status: 'paused' },
        },
      }));
    },

    /**
     * Merge partial state into an execution entry.
     * Ensures progress is monotonically increasing.
     */
    updateProgress: (taskId: string, data: Partial<ExecutionState>) => {
      const current = get().executions[taskId];
      if (!current) return;

      // Enforce monotonically increasing progress
      const newProgress = data.progress !== undefined
        ? Math.max(data.progress, current.progress)
        : current.progress;

      set((state) => ({
        executions: {
          ...state.executions,
          [taskId]: { ...current, ...data, progress: newProgress },
        },
      }));
    },
  })
);
