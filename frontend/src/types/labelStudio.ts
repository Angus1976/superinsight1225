/**
 * Label Studio related type definitions
 * Extracted and improved for better type safety
 */

// Sync status types
export type LabelStudioSyncStatus = 'synced' | 'pending' | 'failed';

// Label Studio project from API
export interface LabelStudioProject {
  id: number;
  title: string;
  description?: string;
  task_number: number;
  num_tasks_with_annotations: number;
  created_at?: string;
  updated_at?: string;
  total_annotations_number?: number;
  total_predictions_number?: number;
  label_config?: string;
  created_by?: LabelStudioUser;
}

export interface LabelStudioUser {
  id: number;
  username: string;
  email?: string;
}

// Label Studio task from API
export interface LabelStudioTask {
  id: number;
  data: LabelStudioTaskData;
  project: number;
  is_labeled: boolean;
  annotations: LabelStudioAnnotation[];
  total_annotations?: number;
}

export interface LabelStudioTaskData {
  text: string;
  [key: string]: unknown;
}

// Label Studio annotation
export interface LabelStudioAnnotation {
  id: number;
  created_at: string;
  updated_at: string;
  completed_by?: number;
  result?: AnnotationValue[];
  was_cancelled?: boolean;
  ground_truth?: boolean;
  lead_time?: number; // Time spent on annotation in seconds
}

export interface AnnotationValue {
  value: Record<string, unknown>;
  from_name: string;
  to_name: string;
  type: string;
}

// Annotation result for creating/updating
export interface AnnotationResult {
  id?: number;
  result: AnnotationValue[];
  task: number;
  created_at?: string;
  updated_at?: string;
}

// Annotation quality metrics
export interface AnnotationQualityMetrics {
  totalAnnotations: number;
  avgLeadTime: number; // Average time per annotation in seconds
  completionRate: number; // Percentage of tasks with annotations
  annotatorCount: number; // Number of unique annotators
}

// Sync cache types
export interface SyncCache {
  projects: Map<number, LabelStudioProject>;
  projectTasks: Map<number, LabelStudioTask[]>;
  lastFetch: number;
}

// Sync progress state
export type SyncStatus = 'idle' | 'syncing' | 'completed' | 'error';

export interface SyncProgress {
  current: number;
  total: number;
  status: SyncStatus;
  message: string;
}

// Label Studio error types
export type LabelStudioErrorType = 'not_found' | 'auth' | 'network' | 'service' | 'unknown';

export interface LabelStudioError {
  type: LabelStudioErrorType;
  message: string;
  details?: string;
}

// Export annotation result for export functionality
export interface ExportAnnotationResult {
  id: number;
  task_id: number;
  result: unknown[];
  created_at?: string;
  updated_at?: string;
  completed_by?: number;
  was_cancelled?: boolean;
  lead_time?: number;
}

/**
 * Calculate annotation quality metrics from Label Studio tasks
 */
export const calculateAnnotationQuality = (tasks: LabelStudioTask[]): AnnotationQualityMetrics => {
  let totalAnnotations = 0;
  let totalLeadTime = 0;
  let annotationsWithLeadTime = 0;
  const annotatorIds = new Set<number>();
  
  for (const task of tasks) {
    if (task.annotations && task.annotations.length > 0) {
      for (const annotation of task.annotations) {
        totalAnnotations++;
        
        if (annotation.lead_time && annotation.lead_time > 0) {
          totalLeadTime += annotation.lead_time;
          annotationsWithLeadTime++;
        }
        
        if (annotation.completed_by) {
          annotatorIds.add(annotation.completed_by);
        }
      }
    }
    
    if (task.total_annotations && task.total_annotations > 0 && (!task.annotations || task.annotations.length === 0)) {
      totalAnnotations += task.total_annotations;
    }
  }
  
  const tasksWithAnnotations = tasks.filter(t => t.is_labeled).length;
  const completionRate = tasks.length > 0 
    ? Math.round((tasksWithAnnotations / tasks.length) * 100) 
    : 0;
  
  const avgLeadTime = annotationsWithLeadTime > 0 
    ? Math.round(totalLeadTime / annotationsWithLeadTime) 
    : 0;
  
  return {
    totalAnnotations,
    avgLeadTime,
    completionRate,
    annotatorCount: annotatorIds.size,
  };
};
