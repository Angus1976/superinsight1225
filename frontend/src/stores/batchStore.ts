/**
 * Batch Store
 *
 * Manages batch annotation configuration, progress tracking, and quality-based auto-pause.
 * When autoStop is enabled and a batch result's accuracy falls below the qualityThreshold,
 * the result status is automatically set to 'paused' (Req 3.4).
 */

import { create } from 'zustand';

export interface BatchConfig {
  batchSize: number;         // 默认 100
  intervalSeconds: number;
  qualityThreshold: number;  // 准确率阈值
  autoStop: boolean;
}

export interface BatchProgress {
  currentBatch: number;
  totalBatches: number;
  batchResults: BatchResult[];
}

export interface BatchResult {
  batchIndex: number;
  accuracy: number;
  processedCount: number;
  status: 'completed' | 'paused' | 'failed';
}

interface BatchStoreState {
  config: BatchConfig;
  progress: BatchProgress | null;

  setConfig: (config: Partial<BatchConfig>) => void;
  addBatchResult: (result: BatchResult) => void;
}

const DEFAULT_CONFIG: BatchConfig = {
  batchSize: 100,
  intervalSeconds: 30,
  qualityThreshold: 0.8,
  autoStop: true,
};

export const useBatchStore = create<BatchStoreState>()(
  (set, get) => ({
    config: { ...DEFAULT_CONFIG },
    progress: null,

    /**
     * Merge partial config into existing config.
     */
    setConfig: (partial: Partial<BatchConfig>) => {
      set((state) => ({
        config: { ...state.config, ...partial },
      }));
    },

    /**
     * Append a batch result, increment currentBatch, and auto-pause
     * if autoStop is enabled and accuracy < qualityThreshold.
     */
    addBatchResult: (result: BatchResult) => {
      const { config, progress } = get();

      // Auto-pause: override status when quality is below threshold
      const finalResult: BatchResult =
        config.autoStop && result.accuracy < config.qualityThreshold
          ? { ...result, status: 'paused' }
          : result;

      const currentProgress = progress ?? {
        currentBatch: 0,
        totalBatches: 0,
        batchResults: [],
      };

      set({
        progress: {
          ...currentProgress,
          currentBatch: currentProgress.currentBatch + 1,
          batchResults: [...currentProgress.batchResults, finalResult],
        },
      });
    },
  })
);
