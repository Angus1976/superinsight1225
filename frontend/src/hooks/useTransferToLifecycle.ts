/**
 * Transfer to Lifecycle Hook
 * 
 * Custom React hook for transferring AI processing results to data lifecycle stages.
 * Uses the unified /api/data-lifecycle/transfer endpoint for proper permission
 * checks and approval workflow support.
 */

import { useState, useCallback } from 'react';
import { transferDataAPI } from '@/api/dataLifecycleAPI';
import type { DataTransferRequest } from '@/api/dataLifecycleAPI';

// ============================================================================
// Types
// ============================================================================

export interface TransferDataItem {
  id: string;
  name: string;
  content: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface TransferOptions {
  dataType?: string;
  tags?: string[];
  remark?: string;
  qualityThreshold?: number;
  batchSize?: number;
}

export interface TransferParams {
  sourceType: 'structuring' | 'vectorization' | 'semantic' | 'ai_annotation';
  data: TransferDataItem[];
  targetStage: 'temp_data' | 'sample_library' | 'annotated' | 'enhanced';
  options: TransferOptions;
}

export interface TransferProgress {
  total: number;
  completed: number;
  failed: number;
  percentage: number;
}

export interface TransferResult {
  success: boolean;
  successCount: number;
  failedCount: number;
  failedItems: Array<{ id: string; reason: string }>;
}

export interface UseTransferToLifecycleReturn {
  transferData: (params: TransferParams) => Promise<TransferResult>;
  loading: boolean;
  progress: TransferProgress;
  error: string | null;
}

// ============================================================================
// Mapping helpers
// ============================================================================

/** Map frontend sourceType to backend source_type */
const SOURCE_TYPE_MAP: Record<string, DataTransferRequest['source_type']> = {
  structuring: 'structuring',
  vectorization: 'augmentation',
  semantic: 'augmentation',
  ai_annotation: 'augmentation',
};

/** Map frontend targetStage to backend target_state */
const TARGET_STATE_MAP: Record<string, DataTransferRequest['target_state']> = {
  temp_data: 'temp_stored',
  sample_library: 'in_sample_library',
  annotated: 'annotation_pending',
  enhanced: 'temp_stored', // enhanced data goes to temp first
};

// ============================================================================
// Hook: useTransferToLifecycle
// ============================================================================

export function useTransferToLifecycle(): UseTransferToLifecycleReturn {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<TransferProgress>({
    total: 0,
    completed: 0,
    failed: 0,
    percentage: 0,
  });
  const [error, setError] = useState<string | null>(null);

  /**
   * Main transfer function using the unified /api/data-lifecycle/transfer endpoint
   */
  const transferData = useCallback(async (params: TransferParams): Promise<TransferResult> => {
    const { sourceType, data, targetStage, options } = params;

    try {
      setLoading(true);
      setError(null);
      setProgress({ total: data.length, completed: 0, failed: 0, percentage: 0 });

      // Build unified transfer request
      const request: DataTransferRequest = {
        source_type: SOURCE_TYPE_MAP[sourceType] || 'augmentation',
        source_id: `${sourceType}_transfer_${Date.now()}`,
        target_state: TARGET_STATE_MAP[targetStage] || 'temp_stored',
        data_attributes: {
          category: options.dataType || sourceType,
          tags: options.tags || [sourceType],
          quality_score: options.qualityThreshold || 0.8,
          description: options.remark,
        },
        records: data.map(item => ({
          id: item.id,
          content: item.content as Record<string, any>,
          metadata: {
            name: item.name,
            sourceType,
            ...item.metadata,
          },
        })),
      };

      const response = await transferDataAPI(request);

      const result: TransferResult = {
        success: response.success,
        successCount: response.transferred_count || 0,
        failedCount: response.success ? 0 : data.length,
        failedItems: response.success ? [] : data.map(item => ({
          id: item.id,
          reason: response.message || 'Transfer failed',
        })),
      };

      setProgress({
        total: data.length,
        completed: result.successCount,
        failed: result.failedCount,
        percentage: 100,
      });

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Transfer operation failed';
      setError(errorMessage);

      setProgress(prev => ({ ...prev, failed: data.length, percentage: 100 }));

      return {
        success: false,
        successCount: 0,
        failedCount: data.length,
        failedItems: data.map(item => ({
          id: item.id,
          reason: errorMessage,
        })),
      };
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    transferData,
    loading,
    progress,
    error,
  };
}
