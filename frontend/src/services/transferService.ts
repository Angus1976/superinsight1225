// Transfer Service for AI Processing to Data Lifecycle
// Handles data validation, mapping, and batch transfer operations

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

export interface ValidationResult {
  valid: boolean;
  errors: Array<{ field: string; message: string }>;
}

export interface LifecycleDataPayload {
  name: string;
  content: Record<string, unknown>;
  metadata: {
    source: string;
    sourceType: string;
    sourceId: string;
    dataType?: string;
    tags?: string[];
    remark?: string;
    [key: string]: unknown;
  };
}

export interface TransferResult {
  success: boolean;
  successCount: number;
  failedCount: number;
  skippedCount: number;
  failedItems: Array<{
    id: string;
    name: string;
    reason: string;
    suggestion?: string;
  }>;
  duration: number;
}

// ============================================================================
// Constants
// ============================================================================

const MAX_DATA_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_NAME_LENGTH = 200;
const MAX_BATCH_SIZE = 100;

// ============================================================================
// Validation Functions
// ============================================================================

/**
 * Validate transfer data items
 * Checks for required fields, data size, and format
 */
export function validateData(data: TransferDataItem[]): ValidationResult {
  const errors: Array<{ field: string; message: string }> = [];

  if (!data || data.length === 0) {
    errors.push({ field: 'data', message: 'No data items provided' });
    return { valid: false, errors };
  }

  data.forEach((item, index) => {
    // Check required fields
    if (!item.id || typeof item.id !== 'string' || item.id.trim() === '') {
      errors.push({ field: `data[${index}].id`, message: 'ID is required and must be a non-empty string' });
    }

    if (!item.name || typeof item.name !== 'string' || item.name.trim() === '') {
      errors.push({ field: `data[${index}].name`, message: 'Name is required and must be a non-empty string' });
    }

    if (item.name && item.name.length > MAX_NAME_LENGTH) {
      errors.push({ field: `data[${index}].name`, message: `Name exceeds maximum length of ${MAX_NAME_LENGTH} characters` });
    }

    if (!item.content || typeof item.content !== 'object' || Array.isArray(item.content)) {
      errors.push({ field: `data[${index}].content`, message: 'Content is required and must be an object' });
    }

    // Check data size
    try {
      const dataSize = JSON.stringify(item).length;
      if (dataSize > MAX_DATA_SIZE) {
        errors.push({ 
          field: `data[${index}]`, 
          message: `Data size (${(dataSize / 1024 / 1024).toFixed(2)}MB) exceeds limit of ${MAX_DATA_SIZE / 1024 / 1024}MB` 
        });
      }
    } catch (e) {
      errors.push({ field: `data[${index}]`, message: 'Failed to calculate data size' });
    }

    // Validate quality score if present
    if (item.metadata?.qualityScore !== undefined) {
      const score = item.metadata.qualityScore as number;
      if (typeof score !== 'number' || score < 0 || score > 1) {
        errors.push({ field: `data[${index}].metadata.qualityScore`, message: 'Quality score must be a number between 0 and 1' });
      }
    }
  });

  return {
    valid: errors.length === 0,
    errors
  };
}

// ============================================================================
// Data Mapping Functions
// ============================================================================

/**
 * Map transfer data to lifecycle data format based on source type
 */
export function mapToLifecycleData(
  sourceType: string,
  data: TransferDataItem,
  options: TransferOptions
): LifecycleDataPayload {
  const baseMetadata = {
    source: 'ai_processing',
    sourceType,
    sourceId: data.id,
    dataType: options.dataType,
    tags: options.tags,
    remark: options.remark
  };

  switch (sourceType) {
    case 'structuring':
      return {
        name: data.name,
        content: data.content,
        metadata: {
          ...baseMetadata,
          parsedAt: data.metadata?.parsedAt as string | undefined
        }
      };

    case 'vectorization':
      return {
        name: data.name.substring(0, 50),
        content: {
          text: data.content.text,
          vector: data.content.vector,
          dimensions: data.content.dimensions
        },
        metadata: {
          ...baseMetadata,
          model: data.metadata?.model as string | undefined
        }
      };

    case 'semantic':
      return {
        name: data.name.substring(0, 50),
        content: {
          text: data.content.text,
          entities: data.content.entities,
          relations: data.content.relations,
          semanticType: data.content.type
        },
        metadata: {
          ...baseMetadata,
          semanticType: data.content.type as string | undefined
        }
      };

    case 'ai_annotation':
      return {
        name: data.name,
        content: {
          originalData: data.content.data,
          annotations: data.content.annotations,
          confidence: data.metadata?.avgConfidence
        },
        metadata: {
          ...baseMetadata,
          taskName: data.name,
          qualityScore: data.metadata?.avgConfidence as number | undefined
        }
      };

    default:
      // Generic mapping for unknown source types
      return {
        name: data.name,
        content: data.content,
        metadata: baseMetadata
      };
  }
}

// ============================================================================
// Permission Functions
// ============================================================================

/**
 * Check if user has permission to transfer data
 * Note: This is a placeholder. Actual implementation should integrate with
 * the permission management system.
 */
export async function checkPermissions(
  userId: string,
  targetStage: string
): Promise<boolean> {
  // TODO: Integrate with actual permission manager
  // For now, return true to allow transfers
  // In production, this should call the permission API
  
  try {
    // Example implementation:
    // const hasPermission = await permissionManager.checkPermission(
    //   userId,
    //   { type: 'data_transfer', id: targetStage },
    //   'create'
    // );
    // return hasPermission;
    
    return true;
  } catch (error) {
    console.error('Permission check failed:', error);
    return false;
  }
}

// ============================================================================
// Batch Transfer Functions
// ============================================================================

/**
 * Split array into chunks of specified size
 */
function chunk<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

/**
 * Process a single batch of transfers
 */
async function processBatch(
  batch: TransferDataItem[],
  sourceType: string,
  targetStage: string,
  options: TransferOptions,
  transferFn: (payload: LifecycleDataPayload) => Promise<void>
): Promise<TransferResult> {
  const startTime = Date.now();
  const results: TransferResult = {
    success: true,
    successCount: 0,
    failedCount: 0,
    skippedCount: 0,
    failedItems: [],
    duration: 0
  };

  for (const item of batch) {
    try {
      // Apply quality threshold filter if specified
      if (options.qualityThreshold !== undefined) {
        const qualityScore = item.metadata?.qualityScore as number | undefined;
        if (qualityScore !== undefined && qualityScore < options.qualityThreshold) {
          results.skippedCount++;
          continue;
        }
      }

      // Map data to lifecycle format
      const payload = mapToLifecycleData(sourceType, item, options);

      // Execute transfer
      await transferFn(payload);
      results.successCount++;
    } catch (error) {
      results.failedCount++;
      results.failedItems.push({
        id: item.id,
        name: item.name,
        reason: error instanceof Error ? error.message : 'Unknown error',
        suggestion: 'Please check the data format and try again'
      });
    }
  }

  results.duration = Date.now() - startTime;
  results.success = results.failedCount === 0;

  return results;
}

/**
 * Merge multiple transfer results into a single result
 */
function mergeResults(results: TransferResult[]): TransferResult {
  return results.reduce(
    (acc, result) => ({
      success: acc.success && result.success,
      successCount: acc.successCount + result.successCount,
      failedCount: acc.failedCount + result.failedCount,
      skippedCount: acc.skippedCount + result.skippedCount,
      failedItems: [...acc.failedItems, ...result.failedItems],
      duration: acc.duration + result.duration
    }),
    {
      success: true,
      successCount: 0,
      failedCount: 0,
      skippedCount: 0,
      failedItems: [],
      duration: 0
    }
  );
}

/**
 * Execute batch transfer with concurrency control
 */
export async function batchTransfer(
  items: TransferDataItem[],
  sourceType: string,
  targetStage: string,
  options: TransferOptions,
  transferFn: (payload: LifecycleDataPayload) => Promise<void>,
  onProgress?: (completed: number, total: number) => void
): Promise<TransferResult> {
  const batchSize = options.batchSize || MAX_BATCH_SIZE;
  const maxConcurrent = 3;

  // Split items into batches
  const batches = chunk(items, batchSize);
  const results: TransferResult[] = [];

  // Process batches with concurrency control
  for (let i = 0; i < batches.length; i += maxConcurrent) {
    const batchGroup = batches.slice(i, i + maxConcurrent);
    
    const batchPromises = batchGroup.map(batch =>
      processBatch(batch, sourceType, targetStage, options, transferFn)
    );

    const batchResults = await Promise.allSettled(batchPromises);
    
    batchResults.forEach(result => {
      if (result.status === 'fulfilled') {
        results.push(result.value);
      } else {
        // Handle batch-level failure
        results.push({
          success: false,
          successCount: 0,
          failedCount: batchGroup[0]?.length || 0,
          skippedCount: 0,
          failedItems: batchGroup[0]?.map(item => ({
            id: item.id,
            name: item.name,
            reason: result.reason?.message || 'Batch processing failed',
            suggestion: 'Please try again or contact support'
          })) || [],
          duration: 0
        });
      }
    });

    // Update progress
    if (onProgress) {
      const completed = Math.min((i + maxConcurrent) * batchSize, items.length);
      onProgress(completed, items.length);
    }
  }

  // Merge all results
  return mergeResults(results);
}

// ============================================================================
// Exports
// ============================================================================

export const transferService = {
  validateData,
  mapToLifecycleData,
  checkPermissions,
  batchTransfer
};

export default transferService;
