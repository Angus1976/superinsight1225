/**
 * Label Studio related type definitions
 * 
 * DEPRECATED: This file now re-exports from './label-studio'.
 * All types have been consolidated into label-studio.ts.
 * 
 * API response types (number IDs) use the "Api" prefix:
 * - LabelStudioApiProject, LabelStudioApiTask, LabelStudioApiAnnotation, LabelStudioApiUser
 * 
 * For backward compatibility, the old names are re-exported as aliases.
 */

// Re-export API types with backward-compatible aliases
export type {
  LabelStudioSyncStatus,
  LabelStudioApiProject as LabelStudioProject,
  LabelStudioApiUser as LabelStudioUser,
  LabelStudioApiTask as LabelStudioTask,
  LabelStudioApiTaskData as LabelStudioTaskData,
  LabelStudioApiAnnotation as LabelStudioAnnotation,
  AnnotationValue,
  AnnotationResult,
  AnnotationQualityMetrics,
  SyncCache,
  SyncStatus,
  SyncProgress,
  LabelStudioErrorType,
  LabelStudioError,
  ExportAnnotationResult,
} from './label-studio';

export { calculateAnnotationQuality } from './label-studio';
