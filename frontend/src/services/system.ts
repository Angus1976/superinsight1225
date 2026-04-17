// System management service
import apiClient from './api/client';
import { apiRequestToSnake, apiResponseToSnake } from '@/utils/jsonCase';
import type {
  SystemTenant,
  TenantUsage,
  SystemMetrics,
  SystemAlert,
  SystemAuditLog,
  SystemConfig,
  CreateTenantRequest,
  UpdateTenantRequest,
  SystemMetricsQuery,
  TenantUsageQuery,
} from '@/types';

export const systemService = {
  // Tenant management
  async getTenants(): Promise<SystemTenant[]> {
    const response = await apiClient.get('/admin/tenants');
    return apiResponseToSnake(response.data);
  },

  async getTenant(id: string): Promise<SystemTenant> {
    const response = await apiClient.get(`/admin/tenants/${id}`);
    return apiResponseToSnake(response.data);
  },

  async createTenant(data: CreateTenantRequest): Promise<SystemTenant> {
    const response = await apiClient.post('/admin/tenants', apiRequestToSnake(data));
    return apiResponseToSnake(response.data);
  },

  async updateTenant(id: string, data: UpdateTenantRequest): Promise<SystemTenant> {
    const response = await apiClient.put(`/admin/tenants/${id}`, apiRequestToSnake(data));
    return apiResponseToSnake(response.data);
  },

  async deleteTenant(id: string): Promise<void> {
    await apiClient.delete(`/admin/tenants/${id}`);
  },

  async getTenantUsage(query: TenantUsageQuery): Promise<TenantUsage[]> {
    const response = await apiClient.get('/admin/tenants/usage', { params: query });
    return apiResponseToSnake(response.data);
  },

  // System monitoring
  async getSystemMetrics(query: SystemMetricsQuery): Promise<SystemMetrics[]> {
    const response = await apiClient.get('/admin/system/metrics', { params: query });
    return apiResponseToSnake(response.data);
  },

  async getSystemHealth(): Promise<{
    status: 'healthy' | 'degraded' | 'unhealthy';
    services: any[];
    uptime: number;
  }> {
    const response = await apiClient.get('/admin/system/health');
    return apiResponseToSnake(response.data);
  },

  async getSystemAlerts(params?: {
    type?: string;
    status?: string;
    limit?: number;
  }): Promise<SystemAlert[]> {
    const response = await apiClient.get('/admin/system/alerts', { params });
    return apiResponseToSnake(response.data);
  },

  async acknowledgeAlert(id: string): Promise<void> {
    await apiClient.post(`/admin/system/alerts/${id}/acknowledge`);
  },

  async resolveAlert(id: string): Promise<void> {
    await apiClient.post(`/admin/system/alerts/${id}/resolve`);
  },

  // Audit logs
  async getAuditLogs(params?: {
    tenant_id?: string;
    user_id?: string;
    action?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }): Promise<{
    logs: SystemAuditLog[];
    total: number;
  }> {
    const response = await apiClient.get('/admin/audit-logs', { params });
    return apiResponseToSnake(response.data);
  },

  // System configuration
  async getSystemConfig(): Promise<SystemConfig> {
    const response = await apiClient.get('/admin/system/config');
    return apiResponseToSnake(response.data);
  },

  async updateSystemConfig(config: Partial<SystemConfig>): Promise<SystemConfig> {
    const response = await apiClient.put('/admin/system/config', apiRequestToSnake(config));
    return apiResponseToSnake(response.data);
  },

  // Maintenance operations
  async enableMaintenanceMode(message?: string): Promise<void> {
    await apiClient.post('/admin/system/maintenance', apiRequestToSnake({ enabled: true, message }));
  },

  async disableMaintenanceMode(): Promise<void> {
    await apiClient.post('/admin/system/maintenance', apiRequestToSnake({ enabled: false }));
  },

  async restartService(serviceName: string): Promise<void> {
    await apiClient.post(`/admin/system/services/${serviceName}/restart`);
  },

  async getSystemLogs(params?: {
    service?: string;
    level?: string;
    start_time?: string;
    end_time?: string;
    limit?: number;
  }): Promise<{
    logs: Array<{
      timestamp: string;
      level: string;
      service: string;
      message: string;
      details?: Record<string, any>;
    }>;
    total: number;
  }> {
    const response = await apiClient.get('/admin/system/logs', { params });
    return apiResponseToSnake(response.data);
  },
};