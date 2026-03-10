/**
 * Transfer to Lifecycle Hook
 * 
 * Custom React hook for transferring AI processing results to data lifecycle stages.
 * Supports batch processing, progress tracking, and error handling.
 */

import { useState, useCallback } from 'react';
import { dataLifecycleApi } from '@/services/dataLifecycle';

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
// Constants
// ============================================================================

const DEFAULT_BATCH_SIZE = 100;
const MAX_CONCURRENT_REQUESTS = 3;

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
   * Map source data to lifecycle data payload
   */
  const mapToLifecycleData = useCallback((
    sourceType: string,
    item: TransferDataItem,
    options: TransferOptions
  ) => {
    const baseMetadata = {
      source: 'ai_processing',
      sourceType,
      sourceId: item.id,
      ...(options.dataType && { dataType: options.dataType }),
      ...(options.tags && { tags: options.tags }),
      ...(options.remark && { remark: options.remark }),
    };

    return {
      name: item.name,
      content: item.content,
      metadata: {
        ...baseMetadata,
        ...item.metadata,
      },
    };
  }, []);

  /**
   * Transfer a single batch of items
   */
  const transferBatch = useCallback(async (
    batch: TransferDataItem[],
    targetStage: string,
    sourceType: string,
    options: TransferOptions
  ): Promise<{ successCount: number; failedItems: Array<{ id: string; reason: string }> }> => {
    const results = {
      successCount: 0,
      failedItems: [] as Array<{ id: string; reason: string }>,
    };

    for (const item of batch) {
      try {
        const payload = mapToLifecycleData(sourceType, item, options);

        // Call appropriate API based on target stage
        switch (targetStage) {
          case 'temp_data':
            await dataLifecycleApi.createTempData(payload);
            break;
          case 'sample_library':
            await dataLifecycleApi.createSample({
              ...payload,
              data_type: options.dataType || 'text',
            });
            break;
          case 'annotated':
            // For annotated stage, we need to create annotation task
            await dataLifecycleApi.createAnnotationTask({
              name: payload.name,
              data_id: item.id,
              priority: 'medium',
              metadata: payload.metadata,
            });
            break;
          case 'enhanced':
            // For enhanced stage, we need to create enhancement job
            await dataLifecycleApi.createEnhancement({
              name: payload.name,
              type: 'custom',
              target_data_id: item.id,
              config: payload.content,
            });
            break;
          default:
            throw new Error(`Unsupported target stage: ${targetStage}`);
        }

        results.successCount++;
      } catch (err) {
        results.failedItems.push({
          id: item.id,
          reason: err instanceof Error ? err.message : 'Unknown error',
        });
      }
    }

    return results;
  }, [mapToLifecycleData]);

  /**
   * Split array into chunks
   */
  const chunk = <T,>(array: T[], size: number): T[][] => {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  };

  /**
   * Update progress state
   */
  const updateProgress = useCallback((completed: number, failed: number, total: number) => {
    const percentage = total > 0 ? Math.round(((completed + failed) / total) * 100) : 0;
    setProgress({
      total,
      completed,
      failed,
      percentage,
    });
  }, []);

  /**
   * Main transfer function with batch processing and concurrency control
   */
  const transferData = useCallback(async (params: TransferParams): Promise<TransferResult> => {
    const { sourceType, data, targetStage, options } = params;
    const batchSize = options.batchSize || DEFAULT_BATCH_SIZE;

    try {
      setLoading(true);
      setError(null);
      
      // Initialize progress
      updateProgress(0, 0, data.length);

      // Split data into batches
      const batches = chunk(data, batchSize);
      
      let totalSuccessCount = 0;
      const allFailedItems: Array<{ id: string; reason: string }> = [];

      // Process batches with concurrency control
      for (let i = 0; i < batches.length; i += MAX_CONCURRENT_REQUESTS) {
        const batchGroup = batches.slice(i, i + MAX_CONCURRENT_REQUESTS);
        
        // Process batch group concurrently
        const batchPromises = batchGroup.map(batch =>
          transferBatch(batch, targetStage, sourceType, options)
        );

        const batchResults = await Promise.allSettled(batchPromises);

        // Aggregate results
        batchResults.forEach((result) => {
          if (result.status === 'fulfilled') {
            totalSuccessCount += result.value.successCount;
            allFailedItems.push(...result.value.failedItems);
          } else {
            // If entire batch failed, mark all items as failed
            const batchIndex = batchResults.indexOf(result);
            const failedBatch = batchGroup[batchIndex];
            failedBatch.forEach(item => {
              allFailedItems.push({
                id: item.id,
                reason: result.reason instanceof Error ? result.reason.message : 'Batch processing failed',
              });
            });
          }
        });

        // Update progress after each batch group
        updateProgress(totalSuccessCount, allFailedItems.length, data.length);
      }

      const transferResult: TransferResult = {
        success: allFailedItems.length === 0,
        successCount: totalSuccessCount,
        failedCount: allFailedItems.length,
        failedItems: allFailedItems,
      };

      return transferResult;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Transfer operation failed';
      setError(errorMessage);
      
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
  }, [transferBatch, updateProgress]);

  return {
    transferData,
    loading,
    progress,
    error,
  };
}
