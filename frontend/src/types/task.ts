// Task type definitions

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled';
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';
export type AnnotationType = 'text_classification' | 'ner' | 'sentiment' | 'qa' | 'custom';

// Re-export Label Studio types from dedicated module
export type { LabelStudioSyncStatus } from './labelStudio';
export type {
  LabelStudioProject,
  LabelStudioTask,
  LabelStudioTaskData,
  LabelStudioUser,
  LabelStudioAnnotation,
  AnnotationResult,
  AnnotationValue,
  LabelStudioError,
  LabelStudioErrorType,
  AnnotationQualityMetrics,
  SyncCache,
  SyncProgress,
  SyncStatus,
  ExportAnnotationResult,
} from './labelStudio';
export { calculateAnnotationQuality } from './labelStudio';

// Import for local use
import type { LabelStudioSyncStatus, LabelStudioTask } from './labelStudio';

export interface Task {
  id: string;
  name: string;
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  annotation_type: AnnotationType;
  assignee_id?: string;
  assignee_name?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  due_date?: string;
  progress: number;
  total_items: number;
  completed_items: number;
  tenant_id: string;
  label_studio_project_id?: string;
  label_studio_sync_status?: LabelStudioSyncStatus;
  label_studio_last_sync?: string;
  label_studio_sync_error?: string;
  tags?: string[];
}

// Annotation page props types
export interface AnnotationGuideProps {
  projectId: number;
  currentTaskIndex: number;
  totalTasks: number;
  onOpenLabelStudio: () => void;
  onBackToTask: () => void;
}

export interface AnnotationStatsProps {
  totalTasks: number;
  completedCount: number;
  currentTaskIndex: number;
  progress: number;
  tasks: LabelStudioTask[];
  onJumpToTask: (index: number) => void;
}

export interface AnnotationActionsProps {
  currentTask: LabelStudioTask;
  syncInProgress: boolean;
  onNextTask: () => void;
  onSkipTask: () => void;
  onSyncProgress: () => void;
}

export interface CurrentTaskInfoProps {
  task: LabelStudioTask;
}

export interface TaskListParams {
  page?: number;
  page_size?: number;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: string;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateTaskPayload {
  name: string;
  description?: string;
  priority: TaskPriority;
  annotation_type: AnnotationType;
  assignee_id?: string;
  due_date?: string;
  tags?: string[];
  data_source?: {
    type: 'file' | 'api';
    config: Record<string, unknown>;
  };
}

export interface UpdateTaskPayload {
  name?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: string;
  due_date?: string;
  tags?: string[];
  label_studio_project_id?: string;
  progress?: number;
  completed_items?: number;
  total_items?: number;
  label_studio_sync_status?: 'synced' | 'pending' | 'failed';
  label_studio_last_sync?: string;
  label_studio_sync_error?: string;
}

export interface TaskStats {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  cancelled: number;
  overdue: number;
}
