/**
 * Data Permission API Service for SuperInsight Platform
 * 
 * Provides API client functions for data-level permission control,
 * policy management, approval workflows, and access logging.
 */

import apiClient from './api/client';

// ============================================================================
// Enumerations
// ============================================================================

export type DataPermissionAction = 'read' | 'write' | 'delete' | 'export' | 'annotate' | 'review';
export type ResourceLevel = 'dataset' | 'record' | 'field';
export type PolicySourceType = 'ldap' | 'oauth' | 'oidc' | 'custom_json' | 'custom_yaml';
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled';
export type SensitivityLevel = 'public' | 'internal' | 'confidential' | 'top_secret';
export type ClassificationMethod = 'manual' | 'rule_based' | 'ai_based';
export type MaskingAlgorithmType = 'replacement' | 'partial' | 'encryption' | 'hash' | 'nullify';
export type AccessLogOperation = 'read' | 'modify' | 'export' | 'api_call';
export type ScenarioType = 'management' | 'annotation' | 'query' | 'api';

// ============================================================================
// Permission Types
// ============================================================================

export interface PermissionResult {
  allowed: boolean;
  reason?: string;
  requires_approval: boolean;
  masked_fields: string[];
  conditions_applied?: Record<string, unknown>;
}

export interface PermissionCheckRequest {
  user_id: string;
  resource_type: string;
  resource_id: string;
  action: DataPermissionAction;
  field_name?: string;
  context?: Record<string, unknown>;
}

export interface GrantPermissionRequest {
  user_id?: string;
  role_id?: string;
  resource_level: ResourceLevel;
  resource_type: string;
  resource_id: string;
  field_name?: string;
  action: DataPermissionAction;
  conditions?: Record<string, unknown>;
  tags?: string[];
  expires_at?: string;
  is_temporary?: boolean;
}

export interface RevokePermissionRequest {
  user_id?: string;
  role_id?: string;
  resource_type: string;
  resource_id: string;
  action: DataPermissionAction;
  field_name?: string;
}

export interface DataPermission {
  id: string;
  tenant_id: string;
  resource_level: ResourceLevel;
  resource_type: string;
  resource_id: string;
  field_name?: string;
  user_id?: string;
  role_id?: string;
  action: DataPermissionAction;
  conditions?: Record<string, unknown>;
  tags?: string[];
  granted_by: string;
  granted_at: string;
  expires_at?: string;
  is_active: boolean;
  is_temporary: boolean;
}

export interface TemporaryGrant {
  permission_id: string;
  user_id: string;
  resource: string;
  action: string;
  granted_at: string;
  expires_at: string;
}

// ============================================================================
// Policy Types
// ============================================================================

export interface LDAPConfig {
  url: string;
  base_dn: string;
  bind_dn: string;
  bind_password: string;
  user_filter?: string;
  group_filter?: string;
  attribute_mapping: Record<string, string>;
  use_ssl?: boolean;
  timeout?: number;
}

export interface OAuthConfig {
  provider_url: string;
  client_id: string;
  client_secret: string;
  scopes?: string[];
  claims_mapping: Record<string, string>;
  use_pkce?: boolean;
}

export interface CustomPolicyConfig {
  format: 'json' | 'yaml';
  content: string;
  validation_schema?: Record<string, unknown>;
}

export interface ImportResult {
  success: boolean;
  imported_count: number;
  updated_count: number;
  skipped_count: number;
  conflicts: PolicyConflict[];
  errors: string[];
}

export interface PolicyConflict {
  id: string;
  conflict_type: string;
  description: string;
  existing_policy: Record<string, unknown>;
  new_policy: Record<string, unknown>;
  suggested_resolution?: string;
}

export interface ConflictResolution {
  conflict_id: string;
  resolution: 'keep_existing' | 'use_new' | 'merge';
  merge_config?: Record<string, unknown>;
}

export interface SyncSchedule {
  source_id: string;
  cron_expression: string;
  enabled: boolean;
  last_sync_at?: string;
  next_sync_at?: string;
}

export interface SyncResult {
  success: boolean;
  source_id: string;
  synced_at: string;
  added_count: number;
  updated_count: number;
  removed_count: number;
  errors: string[];
}

export interface PolicySource {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  source_type: PolicySourceType;
  is_active: boolean;
  last_sync_at?: string;
  last_sync_status?: string;
  created_at: string;
}

// ============================================================================
// Approval Types
// ============================================================================

export interface CreateApprovalRequest {
  resource: string;
  resource_type: string;
  action: string;
  reason: string;
  sensitivity_level?: SensitivityLevel;
}

export interface ApprovalDecision {
  decision: 'approved' | 'rejected';
  comments?: string;
}

export interface ApprovalResult {
  request_id: string;
  status: ApprovalStatus;
  decision?: string;
  decided_by?: string;
  decided_at?: string;
  comments?: string;
  next_approver?: string;
}

export interface ApprovalRequest {
  id: string;
  tenant_id: string;
  requester_id: string;
  resource: string;
  resource_type: string;
  action: string;
  reason: string;
  sensitivity_level: SensitivityLevel;
  status: ApprovalStatus;
  current_level: number;
  created_at: string;
  expires_at: string;
  resolved_at?: string;
}

export interface ApprovalAction {
  id: string;
  request_id: string;
  approver_id: string;
  approval_level: number;
  decision: string;
  comments?: string;
  delegated_from?: string;
  action_at: string;
}

export interface DelegationRequest {
  delegate_to: string;
  start_date: string;
  end_date: string;
}

export interface Delegation {
  id: string;
  delegator_id: string;
  delegate_id: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  created_at: string;
}

export interface ApprovalWorkflowConfig {
  name: string;
  description?: string;
  sensitivity_levels: SensitivityLevel[];
  approval_levels: Array<Record<string, unknown>>;
  timeout_hours?: number;
  auto_approve_conditions?: Array<Record<string, unknown>>;
}

// ============================================================================
// Access Log Types
// ============================================================================

export interface AccessLogFilter {
  user_id?: string;
  resource?: string;
  resource_type?: string;
  operation_type?: AccessLogOperation;
  sensitivity_level?: SensitivityLevel;
  start_time?: string;
  end_time?: string;
  ip_address?: string;
  limit?: number;
  offset?: number;
}

export interface AccessLog {
  id: string;
  tenant_id: string;
  user_id: string;
  operation_type: AccessLogOperation;
  resource: string;
  resource_type: string;
  fields_accessed?: string[];
  details?: Record<string, unknown>;
  record_count?: number;
  ip_address?: string;
  user_agent?: string;
  sensitivity_level?: SensitivityLevel;
  timestamp: string;
}

export interface AccessLogListResponse {
  logs: AccessLog[];
  total: number;
  offset: number;
  limit: number;
}

export interface AccessStatistics {
  total_accesses: number;
  by_operation: Record<string, number>;
  by_resource_type: Record<string, number>;
  by_sensitivity: Record<string, number>;
  by_user: Record<string, number>;
  time_range: { start: string; end: string };
}

// ============================================================================
// Classification Types
// ============================================================================

export interface ClassificationSchema {
  name: string;
  description?: string;
  categories: Array<Record<string, unknown>>;
  rules?: Array<Record<string, unknown>>;
}

export interface ClassificationRule {
  name: string;
  pattern: string;
  category: string;
  sensitivity_level: SensitivityLevel;
  priority?: number;
}

export interface ClassificationResult {
  dataset_id: string;
  total_fields: number;
  classified_count: number;
  classifications: FieldClassification[];
  errors: string[];
}

export interface FieldClassification {
  field_name: string;
  category: string;
  sensitivity_level: SensitivityLevel;
  method: ClassificationMethod;
  confidence_score?: number;
}

export interface ClassificationUpdate {
  dataset_id: string;
  field_name?: string;
  category: string;
  sensitivity_level: SensitivityLevel;
}

export interface BatchUpdateResult {
  success: boolean;
  updated_count: number;
  failed_count: number;
  errors: string[];
}

export interface ClassificationReport {
  tenant_id: string;
  generated_at: string;
  total_datasets: number;
  total_fields: number;
  by_sensitivity: Record<string, number>;
  by_category: Record<string, number>;
  by_method: Record<string, number>;
  unclassified_count: number;
}

export interface DataClassification {
  id: string;
  tenant_id: string;
  dataset_id: string;
  field_name?: string;
  category: string;
  sensitivity_level: SensitivityLevel;
  classified_by: ClassificationMethod;
  confidence_score?: number;
  manually_verified: boolean;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Masking Types
// ============================================================================

export interface MaskingRule {
  id?: string;
  name: string;
  description?: string;
  field_pattern: string;
  algorithm: MaskingAlgorithmType;
  algorithm_config?: Record<string, unknown>;
  applicable_roles?: string[];
  conditions?: Array<Record<string, unknown>>;
  priority?: number;
  is_active?: boolean;
  created_at?: string;
}

export interface MaskingPreview {
  original_value: string;
  masked_value: string;
  algorithm: MaskingAlgorithmType;
  rule_name: string;
}

// ============================================================================
// API Functions
// ============================================================================

const BASE_URL = '/api/v1/data-permissions';
const POLICY_URL = '/api/v1/policies';
const APPROVAL_URL = '/api/v1/approvals';
const ACCESS_LOG_URL = '/api/v1/access-logs';
const CLASSIFICATION_URL = '/api/v1/classifications';
const MASKING_URL = '/api/v1/masking';

export const dataPermissionApi = {
  // Permission Management
  async checkPermission(data: PermissionCheckRequest): Promise<PermissionResult> {
    const response = await apiClient.post<PermissionResult>(`${BASE_URL}/check`, data);
    return response.data;
  },

  async grantPermission(data: GrantPermissionRequest): Promise<DataPermission> {
    const response = await apiClient.post<DataPermission>(`${BASE_URL}/grant`, data);
    return response.data;
  },

  async revokePermission(data: RevokePermissionRequest): Promise<{ success: boolean }> {
    const response = await apiClient.post<{ success: boolean }>(`${BASE_URL}/revoke`, data);
    return response.data;
  },

  async listPermissions(params?: {
    user_id?: string;
    role_id?: string;
    resource_type?: string;
    resource_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ permissions: DataPermission[]; total: number }> {
    const response = await apiClient.get<{ permissions: DataPermission[]; total: number }>(
      BASE_URL,
      { params }
    );
    return response.data;
  },

  async getUserPermissions(userId: string): Promise<DataPermission[]> {
    const response = await apiClient.get<DataPermission[]>(`${BASE_URL}/user/${userId}`);
    return response.data;
  },

  async testPermission(data: PermissionCheckRequest): Promise<PermissionResult> {
    const response = await apiClient.post<PermissionResult>(`${BASE_URL}/test`, data);
    return response.data;
  },

  // Policy Management
  async importLDAPPolicies(config: LDAPConfig): Promise<ImportResult> {
    const response = await apiClient.post<ImportResult>(`${POLICY_URL}/import/ldap`, config);
    return response.data;
  },

  async importOAuthPolicies(config: OAuthConfig): Promise<ImportResult> {
    const response = await apiClient.post<ImportResult>(`${POLICY_URL}/import/oauth`, config);
    return response.data;
  },

  async importCustomPolicies(config: CustomPolicyConfig): Promise<ImportResult> {
    const response = await apiClient.post<ImportResult>(`${POLICY_URL}/import/custom`, config);
    return response.data;
  },

  async listPolicySources(): Promise<PolicySource[]> {
    const response = await apiClient.get<PolicySource[]>(`${POLICY_URL}/sources`);
    return response.data;
  },

  async syncPolicies(sourceId: string): Promise<SyncResult> {
    const response = await apiClient.post<SyncResult>(`${POLICY_URL}/sync/${sourceId}`);
    return response.data;
  },

  async getConflicts(): Promise<PolicyConflict[]> {
    const response = await apiClient.get<PolicyConflict[]>(`${POLICY_URL}/conflicts`);
    return response.data;
  },

  async resolveConflict(data: ConflictResolution): Promise<{ success: boolean }> {
    const response = await apiClient.post<{ success: boolean }>(
      `${POLICY_URL}/conflicts/resolve`,
      data
    );
    return response.data;
  },

  async configureSyncSchedule(sourceId: string, cronExpression: string): Promise<SyncSchedule> {
    const response = await apiClient.post<SyncSchedule>(`${POLICY_URL}/sources/${sourceId}/schedule`, {
      cron_expression: cronExpression,
    });
    return response.data;
  },

  // Approval Workflow
  async createApprovalRequest(data: CreateApprovalRequest): Promise<ApprovalRequest> {
    const response = await apiClient.post<ApprovalRequest>(`${APPROVAL_URL}/request`, data);
    return response.data;
  },

  async approveRequest(requestId: string, decision: ApprovalDecision): Promise<ApprovalResult> {
    const response = await apiClient.post<ApprovalResult>(
      `${APPROVAL_URL}/${requestId}/approve`,
      decision
    );
    return response.data;
  },

  async getPendingApprovals(userId?: string): Promise<ApprovalRequest[]> {
    const response = await apiClient.get<ApprovalRequest[]>(`${APPROVAL_URL}/pending`, {
      params: { user_id: userId },
    });
    return response.data;
  },

  async getApprovalHistory(requestId: string): Promise<ApprovalAction[]> {
    const response = await apiClient.get<ApprovalAction[]>(`${APPROVAL_URL}/${requestId}/history`);
    return response.data;
  },

  async getMyApprovals(status?: ApprovalStatus): Promise<ApprovalRequest[]> {
    const response = await apiClient.get<ApprovalRequest[]>(`${APPROVAL_URL}/my`, {
      params: { status },
    });
    return response.data;
  },

  async delegateApproval(data: DelegationRequest): Promise<Delegation> {
    const response = await apiClient.post<Delegation>(`${APPROVAL_URL}/delegate`, data);
    return response.data;
  },

  async getWorkflowConfigs(): Promise<ApprovalWorkflowConfig[]> {
    const response = await apiClient.get<ApprovalWorkflowConfig[]>(`${APPROVAL_URL}/workflows`);
    return response.data;
  },

  async createWorkflowConfig(config: ApprovalWorkflowConfig): Promise<ApprovalWorkflowConfig> {
    const response = await apiClient.post<ApprovalWorkflowConfig>(
      `${APPROVAL_URL}/workflows`,
      config
    );
    return response.data;
  },

  // Access Logs
  async queryAccessLogs(filters?: AccessLogFilter): Promise<AccessLogListResponse> {
    const response = await apiClient.get<AccessLogListResponse>(ACCESS_LOG_URL, {
      params: filters,
    });
    return response.data;
  },

  async exportAccessLogs(filters: AccessLogFilter, format: 'csv' | 'json'): Promise<Blob> {
    const response = await apiClient.get(`${ACCESS_LOG_URL}/export`, {
      params: { ...filters, format },
      responseType: 'blob',
    });
    return response.data;
  },

  async getAccessStatistics(params?: {
    start_time?: string;
    end_time?: string;
  }): Promise<AccessStatistics> {
    const response = await apiClient.get<AccessStatistics>(`${ACCESS_LOG_URL}/statistics`, {
      params,
    });
    return response.data;
  },

  // Data Classification
  async autoClassify(datasetId: string, useAI?: boolean): Promise<ClassificationResult> {
    const response = await apiClient.post<ClassificationResult>(
      `${CLASSIFICATION_URL}/auto-classify`,
      { dataset_id: datasetId, use_ai: useAI }
    );
    return response.data;
  },

  async batchUpdateClassification(updates: ClassificationUpdate[]): Promise<BatchUpdateResult> {
    const response = await apiClient.post<BatchUpdateResult>(
      `${CLASSIFICATION_URL}/batch-update`,
      { updates }
    );
    return response.data;
  },

  async getClassificationReport(datasetId?: string): Promise<ClassificationReport> {
    const response = await apiClient.get<ClassificationReport>(`${CLASSIFICATION_URL}/report`, {
      params: { dataset_id: datasetId },
    });
    return response.data;
  },

  async listClassifications(params?: {
    dataset_id?: string;
    sensitivity_level?: SensitivityLevel;
    limit?: number;
    offset?: number;
  }): Promise<{ classifications: DataClassification[]; total: number }> {
    const response = await apiClient.get<{ classifications: DataClassification[]; total: number }>(
      CLASSIFICATION_URL,
      { params }
    );
    return response.data;
  },

  async createClassificationRule(rule: ClassificationRule): Promise<ClassificationRule> {
    const response = await apiClient.post<ClassificationRule>(
      `${CLASSIFICATION_URL}/rules`,
      rule
    );
    return response.data;
  },

  async listClassificationRules(): Promise<ClassificationRule[]> {
    const response = await apiClient.get<ClassificationRule[]>(`${CLASSIFICATION_URL}/rules`);
    return response.data;
  },

  // Data Masking
  async listMaskingRules(): Promise<MaskingRule[]> {
    const response = await apiClient.get<MaskingRule[]>(`${MASKING_URL}/rules`);
    return response.data;
  },

  async createMaskingRule(rule: Omit<MaskingRule, 'id' | 'created_at'>): Promise<MaskingRule> {
    const response = await apiClient.post<MaskingRule>(`${MASKING_URL}/rules`, rule);
    return response.data;
  },

  async updateMaskingRule(
    ruleId: string,
    rule: Partial<MaskingRule>
  ): Promise<MaskingRule> {
    const response = await apiClient.put<MaskingRule>(`${MASKING_URL}/rules/${ruleId}`, rule);
    return response.data;
  },

  async deleteMaskingRule(ruleId: string): Promise<void> {
    await apiClient.delete(`${MASKING_URL}/rules/${ruleId}`);
  },

  async previewMasking(
    value: string,
    algorithm: MaskingAlgorithmType,
    config?: Record<string, unknown>
  ): Promise<MaskingPreview> {
    const response = await apiClient.post<MaskingPreview>(`${MASKING_URL}/preview`, {
      value,
      algorithm,
      config,
    });
    return response.data;
  },

  async getMaskingRulesForUser(userId: string, resource: string): Promise<MaskingRule[]> {
    const response = await apiClient.get<MaskingRule[]>(`${MASKING_URL}/rules/user/${userId}`, {
      params: { resource },
    });
    return response.data;
  },
};

export default dataPermissionApi;
