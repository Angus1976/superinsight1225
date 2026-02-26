/**
 * Trial Store
 *
 * Manages trial (试算) results for small-sample pre-annotation runs.
 * Supports multiple trial comparisons and clearing history.
 */

import { create } from 'zustand';

export interface TrialConfig {
  sampleSize: number;        // 10-100
  engineId?: string;
  annotationType: string;
  confidenceThreshold: number;
}

export interface TrialResult {
  trialId: string;
  config: TrialConfig;
  accuracy: number;
  avgConfidence: number;
  confidenceDistribution: { range: string; count: number }[];
  labelDistribution: { label: string; count: number }[];
  duration: number;          // ms
  timestamp: string;
}

interface TrialStoreState {
  trials: TrialResult[];
  addTrial: (result: TrialResult) => void;
  clearTrials: () => void;
}

export const useTrialStore = create<TrialStoreState>()(
  (set) => ({
    trials: [],

    /**
     * Append a new trial result to the list.
     */
    addTrial: (result: TrialResult) => {
      set((state) => ({
        trials: [...state.trials, result],
      }));
    },

    /**
     * Reset trials to empty array.
     */
    clearTrials: () => {
      set({ trials: [] });
    },
  })
);
