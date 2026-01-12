/**
 * Label Studio Integration Types
 * 
 * Strict type definitions for Label Studio integration.
 * These types ensure type safety for all Label Studio interactions.
 */

// ============================================================================
// Label Studio Project Types
// ============================================================================

/** Label Studio project status */
export type LabelStudioProjectStatus = 'active' | 'archived' | 'completed';

/** Label Studio project */
export interface LabelStudioProject {
  /** Project ID */
  id: string;
  /** Project title */
  title: string;
  /** Project description */
  description?: string;
  /** Project status */
  status: LabelStudioProjectStatus;
  /** Label config XML */
  label_config: string;
  /** Created timestamp */
  created_at: string;
  /** Updated timestamp */
  updated_at: string;
  /** Task count */
  task_count: number;
  /** Completed task count */
  completed_task_count: number;
  /** Total annotations count */
  total_annotations_count: number;
  /** Project settings */
  settings?: LabelStudioProjectSettings;
}

/** Label Studio project settings */
export interface LabelStudioProjectSettings {
  /** Enable predictions */
  enable_predictions?: boolean;
  /** Show predictions to annotators */
  show_predictions_to_annotators?: boolean;
  /** Minimum annotations per task */
  min_annotations_per_task?: number;
  /** Maximum annotations per task */
  max_annotations_per_task?: number;
  /** Enable skip button */
  enable_skip?: boolean;
  /** Enable empty annotations */
  enable_empty_annotation?: boolean;
  /** Sampling method */
  sampling?: 'sequential' | 'random' | 'uniform';
  /** Show instruction */
  show_instruction?: boolean;
  /** Instruction text */
  instruction?: string;
}

// ============================================================================
// Label Studio Task Types
// ============================================================================

/** Label Studio task status */
export type LabelStudioTaskStatus = 'pending' | 'in_progress' | 'completed' | 'skipped';

/** Label Studio task */
export interface LabelStudioTask {
  /** Task ID */
  id: string;
  /** Project ID */
  project_id: string;
  /** Task data */
  data: Record<string, unknown>;
  /** Task status */
  status: LabelStudioTaskStatus;
  /** Annotations */
  annotations: LabelStudioAnnotation[];
  /** Predictions */
  predictions: LabelStudioPrediction[];
  /** Created timestamp */
  created_at: string;
  /** Updated timestamp */
  updated_at: string;
  /** Is labeled */
  is_labeled: boolean;
  /** Overlap (number of annotators) */
  overlap: number;
  /** Inner ID */
  inner_id?: number;
  /** Total annotations */
  total_annotations: number;
  /** Cancelled annotations */
  cancelled_annotations: number;
  /** Total predictions */
  total_predictions: number;
  /** File upload */
  file_upload?: string;
  /** Meta info */
  meta?: Record<string, unknown>;
}

// ============================================================================
// Label Studio Annotation Types
// ============================================================================

/** Label Studio annotation */
export interface LabelStudioAnnotation {
  /** Annotation ID */
  id: string;
  /** Task ID */
  task_id: string;
  /** Project ID */
  project_id: string;
  /** Completed by user ID */
  completed_by: string;
  /** Annotation result */
  result: LabelStudioAnnotationResult[];
  /** Was cancelled */
  was_cancelled: boolean;
  /** Ground truth */
  ground_truth: boolean;
  /** Created timestamp */
  created_at: string;
  /** Updated timestamp */
  updated_at: string;
  /** Lead time (seconds) */
  lead_time?: number;
  /** Parent prediction ID */
  parent_prediction?: string;
  /** Parent annotation ID */
  parent_annotation?: string;
  /** Last action */
  last_action?: 'prediction' | 'propagated_annotation' | 'imported' | 'submitted' | 'updated' | 'skipped' | 'accepted' | 'rejected' | 'fixed_and_accepted';
}

/** Label Studio annotation result */
export interface LabelStudioAnnotationResult {
  /** Result ID */
  id: string;
  /** From name (control tag name) */
  from_name: string;
  /** To name (object tag name) */
  to_name: string;
  /** Result type */
  type: LabelStudioResultType;
  /** Value */
  value: LabelStudioResultValue;
  /** Origin (manual, prediction, etc.) */
  origin?: 'manual' | 'prediction' | 'imported';
  /** Score (for predictions) */
  score?: number;
  /** Read only */
  readonly?: boolean;
  /** Hidden */
  hidden?: boolean;
}

/** Label Studio result types */
export type LabelStudioResultType = 
  | 'choices'
  | 'labels'
  | 'rating'
  | 'textarea'
  | 'number'
  | 'datetime'
  | 'taxonomy'
  | 'rectangle'
  | 'polygon'
  | 'ellipse'
  | 'keypoint'
  | 'brush'
  | 'relation'
  | 'pairwise'
  | 'ranker';

/** Label Studio result value */
export interface LabelStudioResultValue {
  /** Choices (for classification) */
  choices?: string[];
  /** Labels (for NER/sequence labeling) */
  labels?: string[];
  /** Text (for text areas) */
  text?: string[];
  /** Rating value */
  rating?: number;
  /** Number value */
  number?: number;
  /** Datetime value */
  datetime?: string;
  /** Taxonomy path */
  taxonomy?: string[][];
  /** Start offset (for text) */
  start?: number;
  /** End offset (for text) */
  end?: number;
  /** Start offset (alias) */
  startOffset?: number;
  /** End offset (alias) */
  endOffset?: number;
  /** X coordinate (for regions) */
  x?: number;
  /** Y coordinate (for regions) */
  y?: number;
  /** Width (for regions) */
  width?: number;
  /** Height (for regions) */
  height?: number;
  /** Rotation (for regions) */
  rotation?: number;
  /** Points (for polygons) */
  points?: number[][];
  /** Keypoint coordinates */
  keypointlabels?: string[];
  /** Brush format */
  format?: 'rle' | 'brush';
  /** RLE data */
  rle?: number[];
  /** Brush strokes */
  brushlabels?: string[];
  /** Relation direction */
  direction?: 'right' | 'left' | 'bi';
  /** Ranker items */
  ranker?: string[];
}

// ============================================================================
// Label Studio Prediction Types
// ============================================================================

/** Label Studio prediction */
export interface LabelStudioPrediction {
  /** Prediction ID */
  id: string;
  /** Task ID */
  task_id: string;
  /** Project ID */
  project_id: string;
  /** Model version */
  model_version?: string;
  /** Prediction result */
  result: LabelStudioAnnotationResult[];
  /** Score */
  score?: number;
  /** Created timestamp */
  created_at: string;
  /** Updated timestamp */
  updated_at: string;
}

// ============================================================================
// Label Studio User Types
// ============================================================================

/** Label Studio user role */
export type LabelStudioUserRole = 'owner' | 'manager' | 'annotator' | 'reviewer';

/** Label Studio user */
export interface LabelStudioUser {
  /** User ID */
  id: string;
  /** Username */
  username: string;
  /** Email */
  email: string;
  /** First name */
  first_name?: string;
  /** Last name */
  last_name?: string;
  /** Avatar URL */
  avatar?: string;
  /** Is active */
  is_active: boolean;
  /** Created timestamp */
  created_at: string;
  /** Last activity */
  last_activity?: string;
}

/** Label Studio project member */
export interface LabelStudioProjectMember {
  /** User */
  user: LabelStudioUser;
  /** Role in project */
  role: LabelStudioUserRole;
  /** Joined timestamp */
  joined_at: string;
}

// ============================================================================
// Label Studio Message Types (for iframe communication)
// ============================================================================

/** Label Studio message types */
export type LabelStudioMessageType =
  | 'labelStudio:ready'
  | 'labelStudio:annotationCreated'
  | 'labelStudio:annotationUpdated'
  | 'labelStudio:annotationDeleted'
  | 'labelStudio:taskCompleted'
  | 'labelStudio:taskSkipped'
  | 'labelStudio:taskChanged'
  | 'labelStudio:progressUpdate'
  | 'labelStudio:error'
  | 'labelStudio:heartbeat'
  | 'ls:ready'
  | 'ls:annotationCreated'
  | 'ls:annotationUpdated'
  | 'ls:annotationDeleted'
  | 'ls:taskCompleted'
  | 'ls:taskSkipped'
  | 'ls:taskChanged'
  | 'ls:progressUpdate'
  | 'ls:error'
  | 'ls:heartbeat';

/** Label Studio message */
export interface LabelStudioMessage<T = unknown> {
  /** Message type */
  type: LabelStudioMessageType;
  /** Message payload */
  payload?: T;
  /** Task ID */
  taskId?: string;
  /** Annotation ID */
  annotationId?: string;
  /** Progress info */
  progress?: {
    completed: number;
    total: number;
  };
  /** Timestamp */
  timestamp?: number;
}

/** Label Studio ready message payload */
export interface LabelStudioReadyPayload {
  /** Project ID */
  projectId: string;
  /** Task ID */
  taskId?: string;
  /** User info */
  user?: {
    id: string;
    username: string;
  };
}

/** Label Studio annotation message payload */
export interface LabelStudioAnnotationPayload {
  /** Annotation */
  annotation: LabelStudioAnnotation;
  /** Task ID */
  taskId: string;
  /** Project ID */
  projectId: string;
}

/** Label Studio error message payload */
export interface LabelStudioErrorPayload {
  /** Error message */
  message: string;
  /** Error code */
  code?: string;
  /** Error details */
  details?: Record<string, unknown>;
}

// ============================================================================
// Label Studio Embed Props Types
// ============================================================================

/** Label Studio embed configuration */
export interface LabelStudioEmbedConfig {
  /** Project ID */
  projectId: string;
  /** Task ID (optional, for specific task) */
  taskId?: string;
  /** Base URL for Label Studio */
  baseUrl?: string;
  /** Authentication token */
  token?: string;
  /** Enable hotkeys */
  enableHotkeys?: boolean;
  /** Enable post message communication */
  enablePostMessage?: boolean;
  /** Iframe mode */
  mode?: 'iframe' | 'embedded';
}

/** Label Studio embed callbacks */
export interface LabelStudioEmbedCallbacks {
  /** Called when annotation is created */
  onAnnotationCreate?: (annotation: LabelStudioAnnotation) => void;
  /** Called when annotation is updated */
  onAnnotationUpdate?: (annotation: LabelStudioAnnotation) => void;
  /** Called when annotation is deleted */
  onAnnotationDelete?: (annotationId: string) => void;
  /** Called when task is completed */
  onTaskComplete?: (taskId: string) => void;
  /** Called when task is skipped */
  onTaskSkip?: (taskId: string) => void;
  /** Called when progress updates */
  onProgressUpdate?: (progress: { completed: number; total: number }) => void;
  /** Called when error occurs */
  onError?: (error: LabelStudioErrorPayload) => void;
  /** Called when Label Studio is ready */
  onReady?: (payload: LabelStudioReadyPayload) => void;
}

/** Label Studio embed props */
export interface LabelStudioEmbedProps extends LabelStudioEmbedConfig, LabelStudioEmbedCallbacks {
  /** Iframe height */
  height?: number | string;
  /** Iframe width */
  width?: number | string;
  /** Custom class name */
  className?: string;
  /** Custom style */
  style?: React.CSSProperties;
  /** Loading component */
  loadingComponent?: React.ReactNode;
  /** Error component */
  errorComponent?: React.ReactNode;
}

// ============================================================================
// Label Studio API Types
// ============================================================================

/** Create project request */
export interface CreateLabelStudioProjectRequest {
  /** Project title */
  title: string;
  /** Project description */
  description?: string;
  /** Label config XML */
  label_config: string;
  /** Project settings */
  settings?: Partial<LabelStudioProjectSettings>;
}

/** Update project request */
export interface UpdateLabelStudioProjectRequest {
  /** Project title */
  title?: string;
  /** Project description */
  description?: string;
  /** Label config XML */
  label_config?: string;
  /** Project settings */
  settings?: Partial<LabelStudioProjectSettings>;
}

/** Import tasks request */
export interface ImportLabelStudioTasksRequest {
  /** Tasks data */
  tasks: Array<{
    data: Record<string, unknown>;
    predictions?: LabelStudioPrediction[];
    annotations?: LabelStudioAnnotation[];
  }>;
}

/** Export annotations request */
export interface ExportLabelStudioAnnotationsRequest {
  /** Export format */
  format: 'JSON' | 'JSON_MIN' | 'CSV' | 'TSV' | 'CONLL2003' | 'COCO' | 'VOC' | 'YOLO';
  /** Include predictions */
  include_predictions?: boolean;
  /** Only completed tasks */
  only_completed?: boolean;
}

// ============================================================================
// Type Guards
// ============================================================================

/** Check if value is a valid LabelStudioProject */
export const isLabelStudioProject = (value: unknown): value is LabelStudioProject => {
  if (!value || typeof value !== 'object') return false;
  const project = value as Record<string, unknown>;
  return (
    typeof project.id === 'string' &&
    typeof project.title === 'string' &&
    typeof project.label_config === 'string' &&
    typeof project.created_at === 'string'
  );
};

/** Check if value is a valid LabelStudioTask */
export const isLabelStudioTask = (value: unknown): value is LabelStudioTask => {
  if (!value || typeof value !== 'object') return false;
  const task = value as Record<string, unknown>;
  return (
    typeof task.id === 'string' &&
    typeof task.project_id === 'string' &&
    typeof task.data === 'object' &&
    typeof task.created_at === 'string'
  );
};

/** Check if value is a valid LabelStudioAnnotation */
export const isLabelStudioAnnotation = (value: unknown): value is LabelStudioAnnotation => {
  if (!value || typeof value !== 'object') return false;
  const annotation = value as Record<string, unknown>;
  return (
    typeof annotation.id === 'string' &&
    typeof annotation.task_id === 'string' &&
    typeof annotation.completed_by === 'string' &&
    Array.isArray(annotation.result)
  );
};

/** Check if value is a valid LabelStudioMessage */
export const isLabelStudioMessage = (value: unknown): value is LabelStudioMessage => {
  if (!value || typeof value !== 'object') return false;
  const message = value as Record<string, unknown>;
  return typeof message.type === 'string';
};
