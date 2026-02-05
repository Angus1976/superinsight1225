/**
 * AI Annotation API Service
 *
 * Provides API client functions for AI-assisted annotation features:
 * - Pre-annotation batch processing
 * - Real-time suggestions
 * - Post-validation quality checks
 * - Task management
 * - Engine management
 * - WebSocket collaboration
 */

import apiClient from './api/client';

// ==================== Types ====================

// Pre-Annotation Types
export interface PreAnnotationRequest {
  project_id: string;
  document_ids: string[];
  annotation_type?: string;
  engine_id?: string;
  samples?: Array<Record<string, unknown>>;
  confidence_threshold?: number;
  batch_size?: number;
}

export interface PreAnnotationResponse {
  task_id: string;
  status: string;
  message: string;
  total_documents: number;
}

export interface PreAnnotationProgress {
  task_id: string;
  status: string;
  progress: number;
  processed_count: number;
  total_count: number;
  estimated_remaining_seconds: number;
}

export interface PreAnnotationResult {
  document_id: string;
  annotations: AnnotationItem[];
  confidence: number;
  needs_review: boolean;
  processing_time_ms: number;
}

// Annotation Types
export interface AnnotationItem {
  label: string;
  start: number;
  end: number;
  text: string;
  confidence: number;
}

// Suggestion Types
export interface SuggestionRequest {
  document_id: string;
  text: string;
  context?: string;
  annotation_type?: string;
  position?: { start: number; end: number };
}

export interface SuggestionResponse {
  suggestion_id: string;
  document_id: string;
  annotations: AnnotationItem[];
  confidence: number;
  latency_ms: number;
}

export interface FeedbackRequest {
  suggestion_id: string;
  accepted: boolean;
  modified_annotation?: AnnotationItem;
  reason?: string;
}

// Batch Coverage Types
export interface BatchCoverageRequest {
  project_id: string;
  document_ids: string[];
  pattern_type: string;
  min_confidence?: number;
}

export interface BatchCoverageResponse {
  applied_count: number;
  skipped_count: number;
  conflicts: ConflictInfo[];
}

// Conflict Types
export interface ConflictInfo {
  conflict_id: string;
  document_id: string;
  conflict_type: 'overlap' | 'label_mismatch' | 'boundary';
  annotations: AnnotationItem[];
  users: UserInfo[];
  created_at: string;
  status: 'pending' | 'resolved';
}

export interface UserInfo {
  id: string;
  name: string;
  avatar?: string;
  role: 'annotator' | 'reviewer' | 'admin';
}

export interface ConflictResolutionRequest {
  conflict_id: string;
  resolution: 'accepted' | 'rejected' | 'modified';
  resolved_annotation?: AnnotationItem;
  resolution_notes?: string;
}

// Validation Types
export interface ValidationRequest {
  project_id: string;
  document_ids?: string[];
  validation_types?: string[];
  custom_rules?: Array<Record<string, unknown>>;
}

export interface ValidationResponse {
  validation_id: string;
  status: string;
  message: string;
}

export interface QualityReport {
  project_id: string;
  overall_score: number;
  accuracy_score: number;
  consistency_score: number;
  completeness_score: number;
  total_annotations: number;
  issues_count: number;
  recommendations: string[];
  generated_at: string;
}

export interface Inconsistency {
  inconsistency_id: string;
  type: string;
  severity: 'low' | 'medium' | 'high';
  affected_documents: string[];
  description: string;
  suggested_fix?: string;
}

// Engine Types
export interface EngineInfo {
  engine_id: string;
  engine_type: string;
  name: string;
  status: 'active' | 'inactive' | 'error';
  supported_types: string[];
  config?: Record<string, unknown>;
}

export interface EngineRegistrationRequest {
  engine_type: string;
  engine_name: string;
  config: Record<string, unknown>;
  description?: string;
}

export interface EngineComparisonRequest {
  engine_ids: string[];
  test_documents: string[];
  annotation_type?: string;
}

export interface EngineComparisonResponse {
  comparison_id: string;
  results: Array<{
    engine_id: string;
    accuracy: number;
    latency_ms: number;
    throughput: number;
  }>;
  recommendation?: string;
}

// Task Types
export interface TaskAssignmentRequest {
  task_id: string;
  user_id?: string;
  role?: string;
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  deadline?: string;
}

export interface TaskAssignment {
  assignment_id: string;
  task_id: string;
  user_id: string;
  status: string;
  assigned_at: string;
}

export interface TaskSubmissionRequest {
  task_id: string;
  annotations: AnnotationItem[];
  time_spent_seconds?: number;
  notes?: string;
}

export interface AnnotationTask {
  task_id: string;
  title: string;
  project_id: string;
  project_name: string;
  assigned_to?: string;
  assigned_by: 'manual' | 'ai';
  status: 'pending' | 'in_progress' | 'review' | 'completed';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  deadline?: string;
  metrics: TaskMetrics;
  created_at: string;
}

export interface TaskMetrics {
  total_items: number;
  human_annotated: number;
  ai_pre_annotated: number;
  ai_suggested: number;
  review_required: number;
}

export interface TaskListResponse {
  tasks: AnnotationTask[];
  total_count: number;
  page: number;
  page_size: number;
}

// Progress Types
export interface ProgressMetrics {
  project_id: string;
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  pending_tasks: number;
  completion_rate: number;
  avg_time_per_task_minutes: number;
  active_annotators: number;
  active_reviewers: number;
}

// AI Metrics Types
export interface AIMetrics {
  total_annotations: number;
  human_annotations: number;
  ai_pre_annotations: number;
  ai_suggestions: number;
  ai_acceptance_rate: number;
  time_saved_hours: number;
  quality_score: number;
}

// Quality Metrics Types
export interface QualityMetrics {
  overview: {
    ai_accuracy: number;
    agreement_rate: number;
    total_samples: number;
    active_alerts: number;
  };
  accuracy_trend: Array<{
    date: string;
    ai_accuracy: number;
    human_accuracy: number;
    agreement_rate: number;
    sample_count: number;
  }>;
  confidence_distribution: Array<{
    range: string;
    count: number;
    acceptance_rate: number;
  }>;
  engine_performance: Array<{
    engine_id: string;
    engine_name: string;
    accuracy: number;
    confidence: number;
    samples: number;
    suggestions: number;
    acceptance_rate: number;
  }>;
  degradation_alerts: Array<{
    alert_id: string;
    metric: string;
    current_value: number;
    previous_value: number;
    degradation_rate: number;
    severity: string;
    recommendation: string;
    timestamp: string;
  }>;
}

// Routing Config Types
export interface RoutingConfig {
  low_confidence_threshold: number;
  high_confidence_threshold: number;
  auto_assign_high_confidence: boolean;
  skill_based_routing: boolean;
  workload_balancing: boolean;
  review_levels: number;
}

// ==================== API Functions ====================

const BASE_URL = '/api/v1/annotation';

// Pre-Annotation APIs
export async function submitPreAnnotation(request: PreAnnotationRequest): Promise<PreAnnotationResponse> {
  const response = await apiClient.post<PreAnnotationResponse>(`${BASE_URL}/pre-annotate`, request);
  return response.data;
}

export async function getPreAnnotationProgress(taskId: string): Promise<PreAnnotationProgress> {
  const response = await apiClient.get<PreAnnotationProgress>(`${BASE_URL}/pre-annotate/${taskId}/progress`);
  return response.data;
}

export async function getPreAnnotationResults(taskId: string): Promise<PreAnnotationResult[]> {
  const response = await apiClient.get<PreAnnotationResult[]>(`${BASE_URL}/pre-annotate/${taskId}/results`);
  return response.data;
}

// Suggestion APIs
export async function getSuggestion(request: SuggestionRequest): Promise<SuggestionResponse> {
  const response = await apiClient.post<SuggestionResponse>(`${BASE_URL}/suggestion`, request);
  return response.data;
}

export async function submitFeedback(request: FeedbackRequest): Promise<{ status: string; message: string }> {
  const response = await apiClient.post<{ status: string; message: string }>(`${BASE_URL}/feedback`, request);
  return response.data;
}

export async function applyBatchCoverage(request: BatchCoverageRequest): Promise<BatchCoverageResponse> {
  const response = await apiClient.post<BatchCoverageResponse>(`${BASE_URL}/batch-coverage`, request);
  return response.data;
}

export async function getConflicts(projectId: string, status?: string): Promise<ConflictInfo[]> {
  const params = status ? { status } : {};
  const response = await apiClient.get<ConflictInfo[]>(`${BASE_URL}/conflicts/${projectId}`, { params });
  return response.data;
}

export async function resolveConflict(request: ConflictResolutionRequest): Promise<{ status: string; message: string }> {
  const response = await apiClient.post<{ status: string; message: string }>(`${BASE_URL}/conflicts/resolve`, request);
  return response.data;
}

// Validation APIs
export async function validateAnnotations(request: ValidationRequest): Promise<ValidationResponse> {
  const response = await apiClient.post<ValidationResponse>(`${BASE_URL}/validate`, request);
  return response.data;
}

export async function getQualityReport(projectId: string): Promise<QualityReport> {
  const response = await apiClient.get<QualityReport>(`${BASE_URL}/quality-report/${projectId}`);
  return response.data;
}

export async function getInconsistencies(projectId: string, severity?: string, limit?: number): Promise<Inconsistency[]> {
  const params: Record<string, unknown> = {};
  if (severity) params.severity = severity;
  if (limit) params.limit = limit;
  const response = await apiClient.get<Inconsistency[]>(`${BASE_URL}/inconsistencies/${projectId}`, { params });
  return response.data;
}

export async function createReviewTasks(
  projectId: string,
  documentIds: string[],
  reviewType?: string,
  priority?: string,
  assigneeId?: string
): Promise<{ task_ids: string[]; total_created: number }> {
  const response = await apiClient.post<{ task_ids: string[]; total_created: number }>(`${BASE_URL}/review-tasks`, {
    project_id: projectId,
    document_ids: documentIds,
    review_type: reviewType || 'quality',
    priority: priority || 'normal',
    assignee_id: assigneeId,
  });
  return response.data;
}

// Engine APIs
export async function listEngines(): Promise<{ engines: EngineInfo[]; count: number }> {
  const response = await apiClient.get<{ engines: EngineInfo[]; count: number }>(`${BASE_URL}/engines`);
  return response.data;
}

export async function registerEngine(request: EngineRegistrationRequest): Promise<{ engine_id: string; status: string; message: string }> {
  const response = await apiClient.post<{ engine_id: string; status: string; message: string }>(`${BASE_URL}/engines`, request);
  return response.data;
}

export async function compareEngines(request: EngineComparisonRequest): Promise<EngineComparisonResponse> {
  const response = await apiClient.post<EngineComparisonResponse>(`${BASE_URL}/engines/compare`, request);
  return response.data;
}

export async function updateEngineConfig(engineId: string, config: Record<string, unknown>): Promise<{ status: string; message: string }> {
  const response = await apiClient.put<{ status: string; message: string }>(`${BASE_URL}/engines/${engineId}`, config);
  return response.data;
}

// Task APIs
export async function assignTask(request: TaskAssignmentRequest): Promise<TaskAssignment> {
  const response = await apiClient.post<TaskAssignment>(`${BASE_URL}/tasks/assign`, request);
  return response.data;
}

export async function getTaskDetails(taskId: string): Promise<AnnotationTask> {
  const response = await apiClient.get<AnnotationTask>(`${BASE_URL}/tasks/${taskId}`);
  return response.data;
}

export async function submitAnnotation(request: TaskSubmissionRequest): Promise<{ status: string; message: string }> {
  const response = await apiClient.post<{ status: string; message: string }>(`${BASE_URL}/submit`, request);
  return response.data;
}

export async function getProgressMetrics(projectId: string): Promise<ProgressMetrics> {
  const response = await apiClient.get<ProgressMetrics>(`${BASE_URL}/progress/${projectId}`);
  return response.data;
}

export async function getTasks(params: {
  project_id?: string;
  status?: string;
  assigned_to?: string;
  page?: number;
  page_size?: number;
}): Promise<TaskListResponse> {
  const response = await apiClient.get<TaskListResponse>(`${BASE_URL}/tasks`, { params });
  return response.data;
}

// Metrics APIs
export async function getAIMetrics(projectId?: string): Promise<AIMetrics> {
  const params = projectId ? { project_id: projectId } : {};
  const response = await apiClient.get<AIMetrics>(`${BASE_URL}/metrics`, { params });
  return response.data;
}

export async function getQualityMetrics(projectId: string, dateRange?: string, engineId?: string): Promise<QualityMetrics> {
  const params: Record<string, string> = { project_id: projectId };
  if (dateRange) params.date_range = dateRange;
  if (engineId) params.engine_id = engineId;
  const response = await apiClient.get<QualityMetrics>(`${BASE_URL}/quality-metrics`, { params });
  return response.data;
}

// Routing Config APIs
export async function getRoutingConfig(): Promise<{ config: RoutingConfig; status: string; message: string }> {
  const response = await apiClient.get<{ config: RoutingConfig; status: string; message: string }>(`${BASE_URL}/routing/config`);
  return response.data;
}

export async function updateRoutingConfig(config: RoutingConfig): Promise<{ config: RoutingConfig; status: string; message: string }> {
  const response = await apiClient.put<{ config: RoutingConfig; status: string; message: string }>(`${BASE_URL}/routing/config`, config);
  return response.data;
}

// WebSocket Stats
export async function getWebSocketStats(): Promise<Record<string, unknown>> {
  const response = await apiClient.get<Record<string, unknown>>(`${BASE_URL}/ws/stats`);
  return response.data;
}

// ==================== WebSocket Helper ====================

export function createAnnotationWebSocket(
  projectId: string,
  documentId?: string,
  onMessage?: (data: unknown) => void,
  onConnect?: () => void,
  onDisconnect?: () => void,
  onError?: (error: Event) => void
): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}${BASE_URL}/ws`;
  
  const ws = new WebSocket(wsUrl);
  
  ws.onopen = () => {
    // Authenticate and join project
    ws.send(JSON.stringify({
      type: 'authenticate',
      projectId,
      documentId,
    }));
    onConnect?.();
  };
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage?.(data);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  };
  
  ws.onclose = () => {
    onDisconnect?.();
  };
  
  ws.onerror = (error) => {
    onError?.(error);
  };
  
  return ws;
}

// ==================== Export Default ====================

export default {
  // Pre-Annotation
  submitPreAnnotation,
  getPreAnnotationProgress,
  getPreAnnotationResults,
  
  // Suggestions
  getSuggestion,
  submitFeedback,
  applyBatchCoverage,
  getConflicts,
  resolveConflict,
  
  // Validation
  validateAnnotations,
  getQualityReport,
  getInconsistencies,
  createReviewTasks,
  
  // Engines
  listEngines,
  registerEngine,
  compareEngines,
  updateEngineConfig,
  
  // Tasks
  assignTask,
  getTaskDetails,
  submitAnnotation,
  getProgressMetrics,
  getTasks,
  
  // Metrics
  getAIMetrics,
  getQualityMetrics,
  
  // Routing
  getRoutingConfig,
  updateRoutingConfig,
  
  // WebSocket
  getWebSocketStats,
  createAnnotationWebSocket,
};
