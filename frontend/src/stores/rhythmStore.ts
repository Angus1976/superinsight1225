/**
 * Rhythm Store
 *
 * Manages annotation rhythm configuration (rate, concurrency, priority rules)
 * and real-time rhythm status (current rate, queue depth, resource usage).
 *
 * - updateRate: updates config.ratePerMinute
 * - updatePriority: replaces config.priorityRules
 */

import { create } from 'zustand';
import type { RhythmConfig, PriorityRule, RhythmStatus } from '@/services/aiAnnotationApi';

interface RhythmStoreState {
  config: RhythmConfig;
  status: RhythmStatus;

  updateRate: (rate: number) => void;
  updatePriority: (rules: PriorityRule[]) => void;
}

const DEFAULT_CONFIG: RhythmConfig = {
  ratePerMinute: 60,
  concurrency: 4,
  priorityRules: [],
};

const DEFAULT_STATUS: RhythmStatus = {
  currentRate: 0,
  queueDepth: 0,
  resourceUsage: 0,
};

export const useRhythmStore = create<RhythmStoreState>()(
  (set) => ({
    config: { ...DEFAULT_CONFIG },
    status: { ...DEFAULT_STATUS },

    updateRate: (rate: number) => {
      set((state) => ({
        config: { ...state.config, ratePerMinute: rate },
      }));
    },

    updatePriority: (rules: PriorityRule[]) => {
      set((state) => ({
        config: { ...state.config, priorityRules: rules },
      }));
    },
  })
);
