/**
 * Ontology Expert Collaboration API Service (本体专家协作 API)
 * 
 * API client for ontology expert collaboration including:
 * - Expert Management (专家管理)
 * - Template Management (模板管理)
 * - Collaboration Sessions (协作会话)
 * - Approval Workflows (审批流程)
 * - Validation Rules (验证规则)
 * - Impact Analysis (影响分析)
 * - I18n Support (国际化支持)
 * 
 * Requirements: Task 20 - Frontend React Components
 */

import apiClient from './api/client';

const BASE_URL = '/api/v1/ontology-collaboration';

// ============== Types ==============

// Expert Management Types
export type ExpertiseArea = 
  | '金融' 
  | '医疗' 
  | '制造' 
  | '政务' 
  | '法律' 
  | '教育';

export type CertificationType = 
  | 'CFA' 
  | 'CPA' 
  | 'PMP' 
  | 'CISSP' 
  | 'AWS_CERTIFIED' 
  | 'AZURE_CERTIFIED' 
  | 'OTHER';

export type ExpertStatus = 'active' | 'inactive' | 'pending' | 'suspended';

export type AvailabilityLevel = 'high' | 'medium' | 'low' | 'unavailable';

export interface ExpertProfile {
  id: string;
  name: string;
  email: string;
  expertise_areas: ExpertiseArea[];
  certifications: CertificationType[];
  languages: string[];
  department?: string;
  title?: string;
  bio?: string;
  status: ExpertStatus;
  availability: AvailabilityLevel;
  contribution_score: number;
  created_at: string;
  updated_at: string;
}

export interface ExpertCreateRequest {
  name: string;
  email: string;
  expertise_areas: ExpertiseArea[];
  certifications?: CertificationType[];
  languages?: string[];
  department?: string;
  title?: string;
  bio?: string;
}

export interface ExpertUpdateRequest {
  name?: string;
  expertise_areas?: ExpertiseArea[];
  certifications?: CertificationType[];
  languages?: string[];
  department?: string;
  title?: string;
  bio?: string;
  status?: ExpertStatus;
  availability?: AvailabilityLevel;
}

export interface ExpertMetrics {
  expert_id: string;
  total_contributions: number;
  accepted_contributions: number;
  rejected_contributions: number;
  quality_score: number;
  recognition_score: number;
  acceptance_rate: number;
}

export interface ExpertRecommendation {
  id: string;
  name: string;
  expertise_areas: ExpertiseArea[];
  contribution_score: number;
  availability: AvailabilityLevel;
  match_score: number;
}

export interface ExpertListResponse {
  experts: ExpertProfile[];
  offset: number;
  limit: number;
  total: number;
}

export interface ExpertRecommendationResponse {
  experts: ExpertRecommendation[];
  ontology_area: string;
  total_count: number;
}

// Template Types
export interface OntologyTemplate {
  id: string;
  name: string;
  industry: string;
  version: string;
  description?: string;
  entity_types: EntityTypeDefinition[];
  relation_types: RelationTypeDefinition[];
  validation_rules: ValidationRuleDefinition[];
  usage_count: number;
  parent_template_id?: string;
  lineage: string[];
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface EntityTypeDefinition {
  id: string;
  name: string;
  name_en?: string;
  description?: string;
  attributes: AttributeDefinition[];
  is_core?: boolean;
}

export interface RelationTypeDefinition {
  id: string;
  name: string;
  name_en?: string;
  description?: string;
  source_type: string;
  target_type: string;
  is_core?: boolean;
}

export interface AttributeDefinition {
  name: string;
  type: string;
  required?: boolean;
  description?: string;
}

export interface ValidationRuleDefinition {
  id: string;
  name: string;
  rule_type: string;
  target_entity_type: string;
  target_field?: string;
  validation_logic: string;
  error_message_key: string;
}

export interface TemplateListResponse {
  templates: OntologyTemplate[];
  offset: number;
  limit: number;
  total: number;
}

export interface TemplateInstantiateRequest {
  project_id: string;
  customizations?: Record<string, unknown>;
}

export interface TemplateCustomizeRequest {
  add_entity_types?: EntityTypeDefinition[];
  remove_entity_types?: string[];
  add_relation_types?: RelationTypeDefinition[];
  remove_relation_types?: string[];
}

// Collaboration Types
export interface CollaborationSession {
  id: string;
  ontology_id: string;
  participants: string[];
  active_locks: Record<string, ElementLock>;
  created_at: string;
  last_activity: string;
}

export interface ElementLock {
  element_id: string;
  locked_by: string;
  locked_at: string;
  expires_at: string;
}

export interface ChangeRequest {
  id: string;
  ontology_id: string;
  requester_id: string;
  change_type: 'ADD' | 'MODIFY' | 'DELETE';
  target_element: string;
  proposed_changes: Record<string, unknown>;
  description?: string;
  status: ChangeRequestStatus;
  impact_analysis?: ImpactReport;
  created_at: string;
  updated_at: string;
}

export type ChangeRequestStatus = 
  | 'draft' 
  | 'submitted' 
  | 'in_review' 
  | 'approved' 
  | 'rejected' 
  | 'changes_requested';

// Approval Types
export interface ApprovalChain {
  id: string;
  name: string;
  ontology_area: string;
  levels: ApprovalLevel[];
  approval_type: 'PARALLEL' | 'SEQUENTIAL';
  created_at: string;
}

export interface ApprovalLevel {
  level_number: number;
  approvers: string[];
  deadline_hours: number;
  min_approvals?: number;
}

export interface ApprovalChainCreateRequest {
  name: string;
  ontology_area: string;
  levels: ApprovalLevel[];
  approval_type?: 'PARALLEL' | 'SEQUENTIAL';
}

export interface PendingApproval {
  change_request_id: string;
  ontology_area: string;
  requester_name: string;
  change_type: string;
  target_element: string;
  deadline: string;
  current_level: number;
}

// Impact Analysis Types
export interface ImpactReport {
  change_request_id: string;
  affected_entity_count: number;
  affected_relation_count: number;
  affected_projects: string[];
  migration_complexity: 'LOW' | 'MEDIUM' | 'HIGH';
  estimated_migration_hours: number;
  breaking_changes: BreakingChange[];
  recommendations: string[];
  requires_high_impact_approval: boolean;
  generated_at: string;
}

export interface BreakingChange {
  element_id: string;
  element_type: string;
  reason: string;
  affected_count: number;
}

// Validation Types
export interface ValidationRule {
  id: string;
  name: string;
  rule_type: string;
  target_entity_type: string;
  target_field?: string;
  validation_logic: string;
  error_message_key: string;
  region: 'CN' | 'HK' | 'TW' | 'INTL';
  industry?: string;
}

export interface ValidationResult {
  is_valid: boolean;
  errors: ValidationError[];
}

export interface ValidationError {
  field: string;
  rule_id: string;
  message: string;
  suggestion?: string;
}

// I18n Types
export interface OntologyTranslation {
  element_id: string;
  language: string;
  name: string;
  description?: string;
  help_text?: string;
}

// ============== Expert Management APIs ==============

export const ontologyExpertApi = {
  // Expert CRUD
  async createExpert(data: ExpertCreateRequest): Promise<ExpertProfile> {
    const response = await apiClient.post<ExpertProfile>(`${BASE_URL}/experts`, data);
    return response.data;
  },

  async getExpert(expertId: string): Promise<ExpertProfile> {
    const response = await apiClient.get<ExpertProfile>(`${BASE_URL}/experts/${expertId}`);
    return response.data;
  },

  async updateExpert(expertId: string, data: ExpertUpdateRequest): Promise<ExpertProfile> {
    const response = await apiClient.put<ExpertProfile>(`${BASE_URL}/experts/${expertId}`, data);
    return response.data;
  },

  async deleteExpert(expertId: string): Promise<void> {
    await apiClient.delete(`${BASE_URL}/experts/${expertId}`);
  },

  async listExperts(params?: {
    expertise_area?: ExpertiseArea;
    language?: string;
    status?: ExpertStatus;
    offset?: number;
    limit?: number;
  }): Promise<ExpertListResponse> {
    const response = await apiClient.get<ExpertListResponse>(`${BASE_URL}/experts`, { params });
    return response.data;
  },

  // Expert Recommendations
  async recommendExperts(
    ontologyArea: string,
    limit = 5
  ): Promise<ExpertRecommendationResponse> {
    const response = await apiClient.get<ExpertRecommendationResponse>(
      `${BASE_URL}/experts/recommend`,
      { params: { ontology_area: ontologyArea, limit } }
    );
    return response.data;
  },

  // Expert Metrics
  async getExpertMetrics(expertId: string): Promise<ExpertMetrics> {
    const response = await apiClient.get<ExpertMetrics>(
      `${BASE_URL}/experts/${expertId}/metrics`
    );
    return response.data;
  },
};

// ============== Template APIs ==============

export const ontologyTemplateApi = {
  async listTemplates(params?: {
    industry?: string;
    offset?: number;
    limit?: number;
  }): Promise<TemplateListResponse> {
    const response = await apiClient.get<TemplateListResponse>(`${BASE_URL}/templates`, { params });
    return response.data;
  },

  async getTemplate(templateId: string): Promise<OntologyTemplate> {
    const response = await apiClient.get<OntologyTemplate>(`${BASE_URL}/templates/${templateId}`);
    return response.data;
  },

  async instantiateTemplate(
    templateId: string,
    data: TemplateInstantiateRequest
  ): Promise<{ instance_id: string; template_id: string; project_id: string }> {
    const response = await apiClient.post(
      `${BASE_URL}/templates/${templateId}/instantiate`,
      data
    );
    return response.data;
  },

  async customizeTemplate(
    templateId: string,
    data: TemplateCustomizeRequest
  ): Promise<OntologyTemplate> {
    const response = await apiClient.post<OntologyTemplate>(
      `${BASE_URL}/templates/${templateId}/customize`,
      data
    );
    return response.data;
  },

  async importTemplate(
    templateData: Record<string, unknown>,
    format = 'json'
  ): Promise<OntologyTemplate> {
    const response = await apiClient.post<OntologyTemplate>(
      `${BASE_URL}/templates/import`,
      templateData,
      { params: { format } }
    );
    return response.data;
  },

  async exportTemplate(templateId: string, format = 'json'): Promise<Blob> {
    const response = await apiClient.get(`${BASE_URL}/templates/${templateId}/export`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  },
};

// ============== Collaboration APIs ==============

export const ontologyCollaborationApi = {
  async createSession(ontologyId: string): Promise<CollaborationSession> {
    const response = await apiClient.post<CollaborationSession>(
      `${BASE_URL}/collaboration/sessions`,
      { ontology_id: ontologyId }
    );
    return response.data;
  },

  async joinSession(sessionId: string, expertId: string): Promise<CollaborationSession> {
    const response = await apiClient.post<CollaborationSession>(
      `${BASE_URL}/collaboration/sessions/${sessionId}/join`,
      { expert_id: expertId }
    );
    return response.data;
  },

  async lockElement(
    sessionId: string,
    elementId: string,
    expertId: string
  ): Promise<ElementLock> {
    const response = await apiClient.post<ElementLock>(
      `${BASE_URL}/collaboration/sessions/${sessionId}/lock`,
      { element_id: elementId, expert_id: expertId }
    );
    return response.data;
  },

  async unlockElement(sessionId: string, elementId: string): Promise<void> {
    await apiClient.delete(
      `${BASE_URL}/collaboration/sessions/${sessionId}/lock/${elementId}`
    );
  },

  async createChangeRequest(data: {
    ontology_id: string;
    change_type: 'ADD' | 'MODIFY' | 'DELETE';
    target_element: string;
    proposed_changes: Record<string, unknown>;
    description?: string;
  }): Promise<ChangeRequest> {
    const response = await apiClient.post<ChangeRequest>(
      `${BASE_URL}/collaboration/change-requests`,
      data
    );
    return response.data;
  },

  async resolveConflict(
    conflictId: string,
    resolution: 'accept_theirs' | 'accept_mine' | 'manual_merge',
    mergedContent?: Record<string, unknown>
  ): Promise<void> {
    await apiClient.post(`${BASE_URL}/collaboration/conflicts/${conflictId}/resolve`, {
      resolution,
      merged_content: mergedContent,
    });
  },

  async getSessionParticipants(sessionId: string): Promise<{
    session_id: string;
    participants: string[];
    count: number;
  }> {
    const response = await apiClient.get(
      `${BASE_URL}/collaboration/sessions/${sessionId}/participants`
    );
    return response.data;
  },
};

// ============== Approval Workflow APIs ==============

export const ontologyApprovalApi = {
  async createApprovalChain(data: ApprovalChainCreateRequest): Promise<ApprovalChain> {
    const response = await apiClient.post<ApprovalChain>(
      `${BASE_URL}/workflow/approval-chains`,
      data
    );
    return response.data;
  },

  async listApprovalChains(ontologyArea?: string): Promise<ApprovalChain[]> {
    const response = await apiClient.get<{ chains: ApprovalChain[] }>(
      `${BASE_URL}/workflow/approval-chains`,
      { params: ontologyArea ? { ontology_area: ontologyArea } : undefined }
    );
    return response.data.chains;
  },

  async approveChangeRequest(
    changeRequestId: string,
    expertId: string,
    reason?: string
  ): Promise<void> {
    await apiClient.post(`${BASE_URL}/workflow/change-requests/${changeRequestId}/approve`, {
      expert_id: expertId,
      action: 'approve',
      reason,
    });
  },

  async rejectChangeRequest(
    changeRequestId: string,
    expertId: string,
    reason: string
  ): Promise<void> {
    await apiClient.post(`${BASE_URL}/workflow/change-requests/${changeRequestId}/reject`, {
      expert_id: expertId,
      action: 'reject',
      reason,
    });
  },

  async requestChanges(
    changeRequestId: string,
    expertId: string,
    feedback: string
  ): Promise<void> {
    await apiClient.post(
      `${BASE_URL}/workflow/change-requests/${changeRequestId}/request-changes`,
      {
        expert_id: expertId,
        action: 'request_changes',
        feedback,
      }
    );
  },

  async getPendingApprovals(expertId: string): Promise<PendingApproval[]> {
    const response = await apiClient.get<{ approvals: PendingApproval[] }>(
      `${BASE_URL}/workflow/pending-approvals`,
      { params: { expert_id: expertId } }
    );
    return response.data.approvals;
  },
};

// ============== Validation APIs ==============

export const ontologyValidationApi = {
  async listRules(params?: {
    entity_type?: string;
    region?: string;
    industry?: string;
  }): Promise<ValidationRule[]> {
    const response = await apiClient.get<{ rules: ValidationRule[] }>(
      `${BASE_URL}/validation/rules`,
      { params }
    );
    return response.data.rules;
  },

  async createRule(data: Omit<ValidationRule, 'id'>): Promise<ValidationRule> {
    const response = await apiClient.post<ValidationRule>(
      `${BASE_URL}/validation/rules`,
      data
    );
    return response.data;
  },

  async validate(
    entity: Record<string, unknown>,
    entityType: string,
    region = 'CN',
    industry?: string
  ): Promise<ValidationResult> {
    const response = await apiClient.post<ValidationResult>(
      `${BASE_URL}/validation/validate`,
      { entity, entity_type: entityType, region, industry }
    );
    return response.data;
  },

  async getChineseBusinessValidators(): Promise<ValidationRule[]> {
    const response = await apiClient.get<{ rules: ValidationRule[] }>(
      `${BASE_URL}/validation/chinese-business`
    );
    return response.data.rules;
  },
};

// ============== Impact Analysis APIs ==============

export const ontologyImpactApi = {
  async analyzeChange(data: {
    ontology_id: string;
    element_id: string;
    change_type: 'ADD' | 'MODIFY' | 'DELETE';
    proposed_changes?: Record<string, unknown>;
  }): Promise<ImpactReport> {
    const response = await apiClient.post<ImpactReport>(
      `${BASE_URL}/impact/analyze`,
      data
    );
    return response.data;
  },

  async getImpactReport(changeRequestId: string): Promise<ImpactReport> {
    const response = await apiClient.get<ImpactReport>(
      `${BASE_URL}/impact/reports/${changeRequestId}`
    );
    return response.data;
  },
};

// ============== I18n APIs ==============

export const ontologyI18nApi = {
  async addTranslation(
    elementId: string,
    data: { language: string; name: string; description?: string; help_text?: string }
  ): Promise<void> {
    await apiClient.post(`${BASE_URL}/i18n/ontology/${elementId}/translations`, data);
  },

  async getTranslation(elementId: string, language: string): Promise<OntologyTranslation> {
    const response = await apiClient.get<OntologyTranslation>(
      `${BASE_URL}/i18n/ontology/${elementId}/translations/${language}`
    );
    return response.data;
  },

  async getMissingTranslations(ontologyId: string, language: string): Promise<string[]> {
    const response = await apiClient.get<{ missing: string[] }>(
      `${BASE_URL}/i18n/ontology/${ontologyId}/missing/${language}`
    );
    return response.data.missing;
  },

  async exportTranslations(ontologyId: string, language: string): Promise<Record<string, unknown>> {
    const response = await apiClient.get(
      `${BASE_URL}/i18n/ontology/${ontologyId}/export/${language}`
    );
    return response.data;
  },

  async importTranslations(
    ontologyId: string,
    language: string,
    translations: Record<string, Record<string, string>>
  ): Promise<void> {
    await apiClient.post(`${BASE_URL}/i18n/ontology/${ontologyId}/import/${language}`, {
      translations,
      format: 'json',
    });
  },
};

// Export all APIs
export default {
  expert: ontologyExpertApi,
  template: ontologyTemplateApi,
  collaboration: ontologyCollaborationApi,
  approval: ontologyApprovalApi,
  validation: ontologyValidationApi,
  impact: ontologyImpactApi,
  i18n: ontologyI18nApi,
};
