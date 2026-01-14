/**
 * Collaboration API Service (协作与审核流程 API)
 * 
 * API client for collaboration workflow management including:
 * - Task assignment and collaboration
 * - Review flow management
 * - Conflict resolution
 * - Quality control
 * - Crowdsource management
 * - Third-party platform integration
 */

import apiClient from './api/client';

const BASE_URL = '/api/v1/collaboration';

// ============== Types ==============

export interface TaskAssignment {
  task_id: string;
  annotator_id: string;
  status: string;
  assigned_at: string;
}

export interface TaskLock {
  task_id: string;
  locked_by: string;
  locked_at: string;
  success: boolean;
}

export interface AnnotationVersion {
  id: string;
  task_id: string;
  user_id: string;
  annotation: Record<string, unknown>;
  version: number;
  created_at: string;
}

export interface ReviewTask {
  id: string;
  annotation_id: string;
  annotator_id: string;
  reviewer_id?: string;
  status: string;
  level: number;
  created_at: string;
}

export interface ReviewHistory {
  id: string;
  annotation_id: string;
  reviewer_id: string;
  action: string;
  comment?: string;
  created_at: string;
}

export interface Conflict {
  id: string;
  task_id: string;
  field: string;
  annotations: Record<string, unknown>[];
  status: string;
  created_at: string;
}

export interface ConflictResolution {
  conflict_id: string;
  resolution_method: string;
  resolved_value: Record<string, unknown>;
  resolved_at: string;
}

export interface QualityRanking {
  annotator_id: string;
  accuracy: number;
  total_annotations: number;
  approved_annotations: number;
  rank: number;
}

export interface CrowdsourceTask {
  id: string;
  project_id: string;
  data_ids: string[];
  config: Record<string, unknown>;
  status: string;
  created_at: string;
}

export interface CrowdsourceAnnotator {
  id: string;
  email: string;
  name: string;
  real_name?: string;
  identity_verified: boolean;
  status: string;
  star_rating: number;
  ability_tags: string[];
  total_tasks: number;
  total_earnings: number;
}

export interface Earnings {
  annotator_id: string;
  base_amount: number;
  quality_multiplier: number;
  star_multiplier: number;
  total_amount: number;
  task_count: number;
  period_start: string;
  period_end: string;
}

export interface Platform {
  name: string;
  platform_type: string;
  status: string;
  connected_at?: string;
}

// ============== Task Assignment APIs ==============

export const collaborationApi = {
  // Task Assignment
  async assignTask(taskId: string, annotatorId?: string, autoAssign = true, priority = 1) {
    const response = await apiClient.post<TaskAssignment>(`${BASE_URL}/tasks/assign`, {
      task_id: taskId,
      annotator_id: annotatorId,
      auto_assign: autoAssign,
      priority,
    });
    return response.data;
  },

  async setTaskPriority(taskId: string, priority: number) {
    const response = await apiClient.post(`${BASE_URL}/tasks/${taskId}/priority`, null, {
      params: { priority },
    });
    return response.data;
  },

  async setTaskDeadline(taskId: string, deadline: Date) {
    const response = await apiClient.post(`${BASE_URL}/tasks/${taskId}/deadline`, null, {
      params: { deadline: deadline.toISOString() },
    });
    return response.data;
  },

  async getTaskAssignment(taskId: string) {
    const response = await apiClient.get<TaskAssignment>(`${BASE_URL}/tasks/${taskId}/assignment`);
    return response.data;
  },

  // Collaboration
  async lockTask(taskId: string, userId: string) {
    const response = await apiClient.post<TaskLock>(`${BASE_URL}/tasks/lock`, {
      task_id: taskId,
      user_id: userId,
    });
    return response.data;
  },

  async unlockTask(taskId: string, userId: string) {
    const response = await apiClient.post(`${BASE_URL}/tasks/unlock`, {
      task_id: taskId,
      user_id: userId,
    });
    return response.data;
  },

  async saveAnnotationVersion(taskId: string, userId: string, annotation: Record<string, unknown>) {
    const response = await apiClient.post<AnnotationVersion>(`${BASE_URL}/annotations/version`, {
      task_id: taskId,
      user_id: userId,
      annotation,
    });
    return response.data;
  },

  async getAnnotationVersions(taskId: string) {
    const response = await apiClient.get<{ versions: AnnotationVersion[] }>(
      `${BASE_URL}/annotations/${taskId}/versions`
    );
    return response.data.versions;
  },

  // Review
  async submitForReview(annotationId: string, annotatorId: string) {
    const response = await apiClient.post<ReviewTask>(`${BASE_URL}/reviews/submit`, {
      annotation_id: annotationId,
      annotator_id: annotatorId,
    });
    return response.data;
  },

  async approveReview(reviewTaskId: string, reviewerId: string, comment?: string) {
    const response = await apiClient.post(`${BASE_URL}/reviews/approve`, {
      review_task_id: reviewTaskId,
      reviewer_id: reviewerId,
      comment,
    });
    return response.data;
  },

  async rejectReview(reviewTaskId: string, reviewerId: string, reason: string) {
    const response = await apiClient.post(`${BASE_URL}/reviews/reject`, {
      review_task_id: reviewTaskId,
      reviewer_id: reviewerId,
      reason,
    });
    return response.data;
  },

  async getReviewHistory(annotationId: string) {
    const response = await apiClient.get<{ history: ReviewHistory[] }>(
      `${BASE_URL}/reviews/${annotationId}/history`
    );
    return response.data.history;
  },

  // Conflicts
  async detectConflicts(taskId: string) {
    const response = await apiClient.get<{ conflicts: Conflict[] }>(`${BASE_URL}/conflicts/${taskId}`);
    return response.data.conflicts;
  },

  async resolveConflictByVoting(conflictId: string) {
    const response = await apiClient.post<ConflictResolution>(`${BASE_URL}/conflicts/resolve`, {
      conflict_id: conflictId,
      resolution_method: 'voting',
    });
    return response.data;
  },

  async resolveConflictByExpert(
    conflictId: string,
    expertId: string,
    expertDecision: Record<string, unknown>
  ) {
    const response = await apiClient.post<ConflictResolution>(`${BASE_URL}/conflicts/resolve`, {
      conflict_id: conflictId,
      resolution_method: 'expert',
      expert_id: expertId,
      expert_decision: expertDecision,
    });
    return response.data;
  },

  async getConflictReport(taskId: string) {
    const response = await apiClient.get(`${BASE_URL}/conflicts/${taskId}/report`);
    return response.data;
  },

  // Quality
  async getAnnotatorAccuracy(annotatorId: string, projectId?: string) {
    const response = await apiClient.get<{ annotator_id: string; accuracy: number }>(
      `${BASE_URL}/quality/${annotatorId}/accuracy`,
      { params: projectId ? { project_id: projectId } : undefined }
    );
    return response.data;
  },

  async checkQualityThreshold(annotatorId: string, threshold = 0.8) {
    const response = await apiClient.post<{ annotator_id: string; passed: boolean }>(
      `${BASE_URL}/quality/threshold/check`,
      { annotator_id: annotatorId, threshold }
    );
    return response.data;
  },

  async getQualityRanking(projectId: string) {
    const response = await apiClient.get<{ ranking: QualityRanking[] }>(
      `${BASE_URL}/quality/${projectId}/ranking`
    );
    return response.data.ranking;
  },

  async getQualityReport(projectId: string) {
    const response = await apiClient.get(`${BASE_URL}/quality/${projectId}/report`);
    return response.data;
  },
};


// ============== Crowdsource APIs ==============

export const crowdsourceApi = {
  // Tasks
  async createTask(projectId: string, config: {
    sensitivity_level?: number;
    price_per_task?: number;
    max_annotators?: number;
  }) {
    const response = await apiClient.post<CrowdsourceTask>(`${BASE_URL}/crowdsource/tasks`, {
      project_id: projectId,
      ...config,
    });
    return response.data;
  },

  async getTask(taskId: string) {
    const response = await apiClient.get<CrowdsourceTask>(`${BASE_URL}/crowdsource/tasks/${taskId}`);
    return response.data;
  },

  async getAvailableTasks(annotatorId: string) {
    const response = await apiClient.get<{ tasks: CrowdsourceTask[] }>(
      `${BASE_URL}/crowdsource/tasks/available`,
      { params: { annotator_id: annotatorId } }
    );
    return response.data.tasks;
  },

  async claimTask(taskId: string, annotatorId: string, durationHours = 2) {
    const response = await apiClient.post(`${BASE_URL}/crowdsource/tasks/claim`, {
      task_id: taskId,
      annotator_id: annotatorId,
      duration_hours: durationHours,
    });
    return response.data;
  },

  async submitAnnotation(taskId: string, annotatorId: string, annotation: Record<string, unknown>) {
    const response = await apiClient.post(`${BASE_URL}/crowdsource/tasks/submit`, {
      task_id: taskId,
      annotator_id: annotatorId,
      annotation,
    });
    return response.data;
  },

  async approveSubmission(submissionId: string) {
    const response = await apiClient.post(`${BASE_URL}/crowdsource/submissions/${submissionId}/approve`);
    return response.data;
  },

  async rejectSubmission(submissionId: string, reason: string) {
    const response = await apiClient.post(
      `${BASE_URL}/crowdsource/submissions/${submissionId}/reject`,
      null,
      { params: { reason } }
    );
    return response.data;
  },

  // Annotators
  async registerAnnotator(data: {
    email: string;
    name: string;
    phone?: string;
    password: string;
  }) {
    const response = await apiClient.post<CrowdsourceAnnotator>(
      `${BASE_URL}/crowdsource/annotators/register`,
      data
    );
    return response.data;
  },

  async getAnnotator(annotatorId: string) {
    const response = await apiClient.get<CrowdsourceAnnotator>(
      `${BASE_URL}/crowdsource/annotators/${annotatorId}`
    );
    return response.data;
  },

  async verifyIdentity(annotatorId: string, docType: string, docNumber: string) {
    const response = await apiClient.post(`${BASE_URL}/crowdsource/annotators/verify`, {
      annotator_id: annotatorId,
      doc_type: docType,
      doc_number: docNumber,
    });
    return response.data;
  },

  async conductAbilityTest(annotatorId: string, testTasks: Array<{
    id: string;
    data: Record<string, unknown>;
    gold_answer: Record<string, unknown>;
  }>) {
    const response = await apiClient.post(
      `${BASE_URL}/crowdsource/annotators/${annotatorId}/ability-test`,
      testTasks
    );
    return response.data;
  },

  async updateStarRating(annotatorId: string, rating: number) {
    const response = await apiClient.put(
      `${BASE_URL}/crowdsource/annotators/${annotatorId}/star-rating`,
      null,
      { params: { rating } }
    );
    return response.data;
  },

  async addAbilityTags(annotatorId: string, tags: string[]) {
    const response = await apiClient.post(
      `${BASE_URL}/crowdsource/annotators/${annotatorId}/ability-tags`,
      tags
    );
    return response.data;
  },

  async setAnnotatorStatus(annotatorId: string, status: string) {
    const response = await apiClient.put(
      `${BASE_URL}/crowdsource/annotators/${annotatorId}/status`,
      null,
      { params: { status } }
    );
    return response.data;
  },

  // Billing
  async configurePricing(projectId: string, pricing: Record<string, unknown>) {
    const response = await apiClient.post(
      `${BASE_URL}/crowdsource/billing/pricing`,
      pricing,
      { params: { project_id: projectId } }
    );
    return response.data;
  },

  async getEarnings(annotatorId: string, periodStart: Date, periodEnd: Date) {
    const response = await apiClient.get<Earnings>(
      `${BASE_URL}/crowdsource/billing/${annotatorId}/earnings`,
      {
        params: {
          period_start: periodStart.toISOString(),
          period_end: periodEnd.toISOString(),
        },
      }
    );
    return response.data;
  },

  async getSettlementReport(periodStart: Date, periodEnd: Date) {
    const response = await apiClient.get(`${BASE_URL}/crowdsource/billing/settlement-report`, {
      params: {
        period_start: periodStart.toISOString(),
        period_end: periodEnd.toISOString(),
      },
    });
    return response.data;
  },

  async generateInvoice(annotatorId: string, period: string) {
    const response = await apiClient.post(
      `${BASE_URL}/crowdsource/billing/${annotatorId}/invoice`,
      null,
      { params: { period } }
    );
    return response.data;
  },

  async processWithdrawal(
    annotatorId: string,
    amount: number,
    method: 'bank_transfer' | 'alipay' | 'wechat',
    accountInfo?: Record<string, string>
  ) {
    const response = await apiClient.post(`${BASE_URL}/crowdsource/billing/withdrawal`, {
      annotator_id: annotatorId,
      amount,
      method,
      account_info: accountInfo,
    });
    return response.data;
  },

  async getBalance(annotatorId: string) {
    const response = await apiClient.get<{ annotator_id: string; balance: number }>(
      `${BASE_URL}/crowdsource/billing/${annotatorId}/balance`
    );
    return response.data;
  },
};

// ============== Platform APIs ==============

export const platformApi = {
  async registerPlatform(config: {
    name: string;
    platform_type: 'mturk' | 'scale_ai' | 'custom';
    api_key?: string;
    api_secret?: string;
    endpoint?: string;
  }) {
    const response = await apiClient.post<Platform>(`${BASE_URL}/platforms/register`, config);
    return response.data;
  },

  async unregisterPlatform(platformName: string) {
    const response = await apiClient.delete(`${BASE_URL}/platforms/${platformName}`);
    return response.data;
  },

  async getPlatform(platformName: string) {
    const response = await apiClient.get<Platform>(`${BASE_URL}/platforms/${platformName}`);
    return response.data;
  },

  async getAllPlatforms() {
    const response = await apiClient.get<{ platforms: Platform[] }>(`${BASE_URL}/platforms`);
    return response.data.platforms;
  },

  async getPlatformStatus(platformName: string) {
    const response = await apiClient.get(`${BASE_URL}/platforms/${platformName}/status`);
    return response.data;
  },

  async testConnection(platformName: string) {
    const response = await apiClient.post(`${BASE_URL}/platforms/${platformName}/test`);
    return response.data;
  },

  async syncTask(task: Record<string, unknown>) {
    const response = await apiClient.post(`${BASE_URL}/platforms/sync-task`, task);
    return response.data;
  },

  async fetchResults(platformName: string, taskId: string) {
    const response = await apiClient.get<{ results: unknown[] }>(
      `${BASE_URL}/platforms/${platformName}/results/${taskId}`
    );
    return response.data.results;
  },
};

export default {
  ...collaborationApi,
  crowdsource: crowdsourceApi,
  platform: platformApi,
};
