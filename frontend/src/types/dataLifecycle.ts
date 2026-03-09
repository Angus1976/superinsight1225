// Data Lifecycle Management type definitions

// --- Enums as string literal unions (following project convention) ---

export type DataState =
  | 'temp_stored'
  | 'under_review'
  | 'rejected'
  | 'approved'
  | 'in_sample_library'
  | 'annotation_pending'
  | 'annotating'
  | 'annotated'
  | 'enhancing'
  | 'enhanced'
  | 'trial_calculation'
  | 'archived'
  | 'deleted';

export type ReviewStatus = 'pending' | 'approved' | 'rejected';

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export type LifecycleTaskStatus = 'created' | 'in_progress' | 'completed' | 'cancelled';

export type AnnotationType =
  | 'classification'
  | 'entity_recognition'
  | 'relation_extraction'
  | 'sentiment_analysis'
  | 'custom';

export type EnhancementType =
  | 'data_augmentation'
  | 'quality_improvement'
  | 'noise_reduction'
  | 'feature_extraction'
  | 'normalization';

// --- Core interfaces ---

export interface TempData {
  id: string;
  sourceDocumentId: string;
  content: Record<string, unknown>;
  state: DataState;
  uploadedBy: string;
  uploadedAt: string;
  reviewStatus?: ReviewStatus;
  metadata: Record<string, unknown>;
}

export interface QualityScore {
  overall: number;
  completeness: number;
  accuracy: number;
  consistency: number;
}

export interface Sample {
  id: string;
  dataId: string;
  content: Record<string, unknown>;
  category: string;
  qualityOverall: number;
  qualityCompleteness: number;
  qualityAccuracy: number;
  qualityConsistency: number;
  version: number;
  tags: string[];
  usageCount: number;
  lastUsedAt?: string;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface TaskProgress {
  total: number;
  completed: number;
  inProgress: number;
}

export interface Annotation {
  taskId: string;
  sampleId: string;
  annotatorId: string;
  labels: Record<string, unknown>[];
  comments?: string;
  confidence?: number;
}

export interface AnnotationTask {
  id: string;
  name: string;
  description: string;
  sampleIds: string[];
  annotationType: AnnotationType;
  instructions: string;
  status: LifecycleTaskStatus;
  createdBy: string;
  assignedTo: string[];
  deadline?: string;
  completedAt?: string;
  progressTotal: number;
  progressCompleted: number;
  progressInProgress: number;
  annotations: Annotation[];
}

export interface EnhancementJob {
  id: string;
  dataId: string;
  enhancementType: EnhancementType;
  status: JobStatus;
  config: Record<string, unknown>;
  result?: Record<string, unknown>;
  createdBy: string;
  createdAt: string;
  completedAt?: string;
}

export interface AITrial {
  id: string;
  name: string;
  dataStage: DataState;
  aiModel: string;
  status: JobStatus;
  config: Record<string, unknown>;
  results?: Record<string, unknown>;
  createdBy: string;
  createdAt: string;
  completedAt?: string;
}

export interface AuditLogEntry {
  id: string;
  userId: string;
  operationType: string;
  resourceType: string;
  resourceId: string;
  action: string;
  result: 'success' | 'failure' | 'partial';
  duration: number;
  details?: Record<string, unknown>;
  timestamp: string;
}

export interface StateTransition {
  fromState: DataState;
  toState: DataState;
  triggeredBy: string;
  reason?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}
