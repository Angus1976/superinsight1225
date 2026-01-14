/**
 * Quality API Service - 质量管理 API 服务
 * 对应后端 API: quality_rules.py, quality.py, quality_reports.py, quality_alerts.py
 */

import apiClient from './api/client';

// Types
export interface QualityScore {
  annotation_id: string;
  dimension_scores: Record<string, number>;
  total_score: number;
  weights: Record<string, number>;
  scored_at: string;
}

export interface ConsistencyScore {
  task_id: string;
  score: number;
  method: string;
  annotator_count: number;
}

export interface QualityRule {
  id: string;
  name: string;
  description?: string;
  rule_type: 'builtin' | 'custom';
  config: Record<string, unknown>;
  script?: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  priority: number;
  project_id: string;
  enabled: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface QualityRuleTemplate {
  id: string;
  name: string;
  description?: string;
  rule_type: string;
  config: Record<string, unknown>;
  severity: string;
  category: string;
}

export interface QualityIssue {
  rule_id: string;
  rule_name: string;
  severity: string;
  message: string;
  field?: string;
}

export interface CheckResult {
  annotation_id: string;
  passed: boolean;
  issues: QualityIssue[];
  checked_rules: number;
  checked_at: string;
}

export interface BatchCheckResult {
  project_id: string;
  total_checked: number;
  passed_count: number;
  failed_count: number;
  results: CheckResult[];
}

export interface RagasEvaluationResult {
  question: string;
  answer: string;
  contexts: string[];
  ground_truth?: string;
  scores: Record<string, number>;
  overall_score: number;
}

export interface BatchRagasResult {
  total_evaluated: number;
  average_scores: Record<string, number>;
  results: RagasEvaluationResult[];
}

export interface TrendPoint {
  date: string;
  score: number;
  dimension?: string;
  count: number;
}

export interface AnnotatorRanking {
  rank: number;
  annotator_id: string;
  annotator_name: string;
  total_annotations: number;
  average_score: number;
  accuracy: number;
  pass_rate: number;
}

export interface ProjectQualityReport {
  project_id: string;
  period_start: string;
  period_end: string;
  total_annotations: number;
  average_scores: Record<string, number>;
  quality_trend: TrendPoint[];
  issue_distribution: Record<string, number>;
  generated_at: string;
}

export interface AnnotatorRankingReport {
  project_id: string;
  period: string;
  rankings: AnnotatorRanking[];
}

export interface QualityTrendReport {
  project_id: string;
  granularity: string;
  data_points: TrendPoint[];
}

export interface QualityAlert {
  id: string;
  project_id: string;
  annotation_id?: string;
  triggered_dimensions: string[];
  scores: Record<string, number>;
  severity: 'critical' | 'high' | 'medium' | 'low';
  escalation_level: number;
  status: 'open' | 'acknowledged' | 'resolved';
  created_at: string;
  resolved_at?: string;
}

export interface AlertConfig {
  project_id: string;
  thresholds: Record<string, number>;
  enabled: boolean;
  notification_channels: string[];
}

// Request types
export interface CreateRuleRequest {
  name: string;
  description?: string;
  rule_type: 'builtin' | 'custom';
  config?: Record<string, unknown>;
  script?: string;
  severity?: string;
  priority?: number;
  project_id: string;
}

export interface UpdateRuleRequest {
  name?: string;
  description?: string;
  config?: Record<string, unknown>;
  script?: string;
  severity?: string;
  priority?: number;
  enabled?: boolean;
}

export interface ScoreRequest {
  gold_standard?: Record<string, unknown>;
}

export interface BatchCheckRequest {
  project_id: string;
  annotation_ids?: string[];
}

export interface RagasEvaluateRequest {
  question: string;
  answer: string;
  contexts: string[];
  ground_truth?: string;
  metrics?: string[];
}

export interface RagasBatchRequest {
  dataset: Array<{
    question: string;
    answer: string;
    contexts?: string[];
    ground_truth?: string;
  }>;
  metrics?: string[];
}

export interface ProjectReportRequest {
  project_id: string;
  start_date: string;
  end_date: string;
}

export interface RankingRequest {
  project_id: string;
  period?: string;
}

export interface TrendReportRequest {
  project_id: string;
  granularity?: 'day' | 'week' | 'month';
}

export interface ExportRequest {
  report_type: string;
  report_data: Record<string, unknown>;
  format: 'pdf' | 'excel' | 'html' | 'json';
}

export interface ScheduleReportRequest {
  project_id: string;
  report_type: string;
  schedule: string;
  recipients: string[];
}

export interface AlertConfigRequest {
  project_id: string;
  thresholds: Record<string, number>;
  notification_channels?: string[];
}

export interface SilenceRequest {
  project_id: string;
  duration_minutes: number;
}

// API Service
export const qualityApi = {
  // Quality Rules
  async createRule(request: CreateRuleRequest): Promise<QualityRule> {
    const response = await apiClient.post<QualityRule>('/api/v1/quality-rules', request);
    return response.data;
  },

  async listRules(projectId: string): Promise<QualityRule[]> {
    const response = await apiClient.get<QualityRule[]>('/api/v1/quality-rules', {
      params: { project_id: projectId },
    });
    return response.data;
  },

  async getRule(ruleId: string): Promise<QualityRule> {
    const response = await apiClient.get<QualityRule>(`/api/v1/quality-rules/${ruleId}`);
    return response.data;
  },

  async updateRule(ruleId: string, request: UpdateRuleRequest): Promise<QualityRule> {
    const response = await apiClient.put<QualityRule>(`/api/v1/quality-rules/${ruleId}`, request);
    return response.data;
  },

  async deleteRule(ruleId: string): Promise<void> {
    await apiClient.delete(`/api/v1/quality-rules/${ruleId}`);
  },

  async createRuleFromTemplate(templateId: string, projectId: string): Promise<QualityRule[]> {
    const response = await apiClient.post<QualityRule[]>('/api/v1/quality-rules/from-template', {
      template_id: templateId,
      project_id: projectId,
    });
    return response.data;
  },

  async listTemplates(): Promise<QualityRuleTemplate[]> {
    const response = await apiClient.get<QualityRuleTemplate[]>('/api/v1/quality-rules/templates/list');
    return response.data;
  },

  // Quality Scoring
  async scoreAnnotation(annotationId: string, request?: ScoreRequest): Promise<QualityScore> {
    const response = await apiClient.post<QualityScore>(
      `/api/v1/quality/score/${annotationId}`,
      request || {}
    );
    return response.data;
  },

  async calculateConsistency(taskId: string): Promise<ConsistencyScore> {
    const response = await apiClient.post<ConsistencyScore>(`/api/v1/quality/consistency/${taskId}`);
    return response.data;
  },

  // Quality Checking
  async checkAnnotation(annotationId: string): Promise<CheckResult> {
    const response = await apiClient.post<CheckResult>(`/api/v1/quality/check/${annotationId}`);
    return response.data;
  },

  async batchCheck(request: BatchCheckRequest): Promise<BatchCheckResult> {
    const response = await apiClient.post<BatchCheckResult>('/api/v1/quality/batch-check', request);
    return response.data;
  },

  // Ragas Evaluation
  async ragasEvaluate(request: RagasEvaluateRequest): Promise<RagasEvaluationResult> {
    const response = await apiClient.post<RagasEvaluationResult>('/api/v1/quality/ragas/evaluate', request);
    return response.data;
  },

  async ragasBatchEvaluate(request: RagasBatchRequest): Promise<BatchRagasResult> {
    const response = await apiClient.post<BatchRagasResult>('/api/v1/quality/ragas/batch-evaluate', request);
    return response.data;
  },

  // Quality Reports
  async generateProjectReport(request: ProjectReportRequest): Promise<ProjectQualityReport> {
    const response = await apiClient.post<ProjectQualityReport>('/api/v1/quality-reports/project', request);
    return response.data;
  },

  async generateAnnotatorRanking(request: RankingRequest): Promise<AnnotatorRankingReport> {
    const response = await apiClient.post<AnnotatorRankingReport>('/api/v1/quality-reports/annotator-ranking', request);
    return response.data;
  },

  async generateTrendReport(request: TrendReportRequest): Promise<QualityTrendReport> {
    const response = await apiClient.post<QualityTrendReport>('/api/v1/quality-reports/trend', request);
    return response.data;
  },

  async exportReport(request: ExportRequest): Promise<Blob> {
    const response = await apiClient.post('/api/v1/quality-reports/export', request, {
      responseType: 'blob',
    });
    return response.data;
  },

  async scheduleReport(request: ScheduleReportRequest): Promise<{ id: string; schedule: string }> {
    const response = await apiClient.post('/api/v1/quality-reports/schedule', request);
    return response.data;
  },

  // Quality Alerts
  async configureAlerts(request: AlertConfigRequest): Promise<AlertConfig> {
    const response = await apiClient.post<AlertConfig>('/api/v1/quality-alerts/configure', request);
    return response.data;
  },

  async listAlerts(projectId: string, status?: string): Promise<QualityAlert[]> {
    const response = await apiClient.get<QualityAlert[]>('/api/v1/quality-alerts', {
      params: { project_id: projectId, status },
    });
    return response.data;
  },

  async acknowledgeAlert(alertId: string): Promise<QualityAlert> {
    const response = await apiClient.post<QualityAlert>(`/api/v1/quality-alerts/${alertId}/acknowledge`);
    return response.data;
  },

  async resolveAlert(alertId: string): Promise<QualityAlert> {
    const response = await apiClient.post<QualityAlert>(`/api/v1/quality-alerts/${alertId}/resolve`);
    return response.data;
  },

  async setSilencePeriod(request: SilenceRequest): Promise<void> {
    await apiClient.post('/api/v1/quality-alerts/silence', request);
  },
};

export default qualityApi;
