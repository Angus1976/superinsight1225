// Dashboard service with multi-tenant support
import apiClient from './api/client';
import { API_ENDPOINTS } from '@/constants';
import type { DashboardSummary, AnnotationEfficiency, UserActivityMetrics, AIModelMetrics, ProjectMetrics } from '@/types';

// Helper to build params with tenant/workspace context
const buildParams = (
  baseParams: Record<string, unknown>,
  tenantId?: string,
  workspaceId?: string
) => {
  const params = { ...baseParams };
  if (tenantId) params.tenant_id = tenantId;
  if (workspaceId) params.workspace_id = workspaceId;
  return params;
};

export const dashboardService = {
  async getSummary(tenantId?: string, workspaceId?: string): Promise<DashboardSummary> {
    const response = await apiClient.get<DashboardSummary>(API_ENDPOINTS.METRICS.SUMMARY, {
      params: buildParams({}, tenantId, workspaceId),
    });
    return response.data;
  },

  async getAnnotationEfficiency(hours = 24, tenantId?: string, workspaceId?: string): Promise<AnnotationEfficiency> {
    const response = await apiClient.get<AnnotationEfficiency>(API_ENDPOINTS.METRICS.ANNOTATION_EFFICIENCY, {
      params: buildParams({ hours }, tenantId, workspaceId),
    });
    return response.data;
  },

  async getUserActivity(hours = 24, tenantId?: string, workspaceId?: string): Promise<UserActivityMetrics> {
    const response = await apiClient.get<UserActivityMetrics>(API_ENDPOINTS.METRICS.USER_ACTIVITY, {
      params: buildParams({ hours }, tenantId, workspaceId),
    });
    return response.data;
  },

  async getAIModels(modelName?: string, hours = 24, tenantId?: string, workspaceId?: string): Promise<AIModelMetrics> {
    const response = await apiClient.get<AIModelMetrics>(API_ENDPOINTS.METRICS.AI_MODELS, {
      params: buildParams({ model_name: modelName, hours }, tenantId, workspaceId),
    });
    return response.data;
  },

  async getProjects(projectId?: string, hours = 24, tenantId?: string, workspaceId?: string): Promise<ProjectMetrics> {
    const response = await apiClient.get<ProjectMetrics>(API_ENDPOINTS.METRICS.PROJECTS, {
      params: buildParams({ project_id: projectId, hours }, tenantId, workspaceId),
    });
    return response.data;
  },
};
