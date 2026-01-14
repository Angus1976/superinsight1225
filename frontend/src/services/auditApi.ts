/**
 * Audit and Compliance API Service for SuperInsight Platform
 * 
 * Provides API client functions for audit log management and compliance reporting.
 */

import apiClient from './api/client';

// ============================================================================
// Types
// ============================================================================

export interface AuditLog {
  id: string;
  event_type: string;
  user_id: string;
  resource?: string;
  action?: string;
  result?: boolean;
  details?: Record<string, unknown>;
  ip_address?: string;
  user_agent?: string;
  session_id?: string;
  timestamp: string;
  hash?: string;
}

export interface AuditLogQueryResponse {
  logs: AuditLog[];
  total: number;
  offset: number;
  limit: number;
}

export interface AuditLogQueryParams {
  user_id?: string;
  event_type?: string;
  resource?: string;
  action?: string;
  result?: boolean;
  start_time?: string;
  end_time?: string;
  ip_address?: string;
  session_id?: string;
  limit?: number;
  offset?: number;
}

export interface AuditLogExportRequest {
  start_time: string;
  end_time: string;
  format: 'json' | 'csv';
  user_id?: string;
  event_type?: string;
}

export interface IntegrityVerificationRequest {
  start_id?: string;
  end_id?: string;
  start_time?: string;
  end_time?: string;
}

export interface IntegrityVerificationResponse {
  valid: boolean;
  verified_count: number;
  error?: string;
  message?: string;
  corrupted_entry_id?: string;
}

export interface AuditStatistics {
  total_logs: number;
  event_types: Record<string, number>;
  results: Record<string, number>;
  period: {
    start?: string;
    end?: string;
  };
}

export interface ComplianceReport {
  report_id: string;
  report_type: string;
  generated_at: string;
  period_start: string;
  period_end: string;
  summary: Record<string, unknown>;
  findings?: Array<Record<string, unknown>>;
  recommendations?: string[];
  compliance_score?: number;
}

export interface ComplianceReportRequest {
  start_date: string;
  end_date: string;
  include_details?: boolean;
}

export interface AccessReportRequest {
  start_date: string;
  end_date: string;
  user_id?: string;
  resource_pattern?: string;
}

export interface PermissionChangeReportRequest {
  start_date: string;
  end_date: string;
  user_id?: string;
}

// ============================================================================
// API Functions
// ============================================================================

const BASE_URL = '/api/v1';

export const auditApi = {
  // Audit Logs
  async queryLogs(params?: AuditLogQueryParams): Promise<AuditLogQueryResponse> {
    const response = await apiClient.get<AuditLogQueryResponse>(
      `${BASE_URL}/audit/logs`,
      { params }
    );
    return response.data;
  },

  async exportLogs(data: AuditLogExportRequest): Promise<Blob> {
    const response = await apiClient.post(`${BASE_URL}/audit/logs/export`, data, {
      responseType: 'blob',
    });
    return response.data;
  },

  async verifyIntegrity(
    data: IntegrityVerificationRequest
  ): Promise<IntegrityVerificationResponse> {
    const response = await apiClient.post<IntegrityVerificationResponse>(
      `${BASE_URL}/audit/verify-integrity`,
      data
    );
    return response.data;
  },

  async getStatistics(params?: {
    start_time?: string;
    end_time?: string;
  }): Promise<AuditStatistics> {
    const response = await apiClient.get<AuditStatistics>(
      `${BASE_URL}/audit/statistics`,
      { params }
    );
    return response.data;
  },

  async applyRetentionPolicy(retentionDays: number): Promise<{
    success: boolean;
    archived_count: number;
    retention_days: number;
  }> {
    const response = await apiClient.post(`${BASE_URL}/audit/retention`, null, {
      params: { retention_days: retentionDays },
    });
    return response.data;
  },

  // Compliance Reports
  async generateGDPRReport(data: ComplianceReportRequest): Promise<ComplianceReport> {
    const response = await apiClient.post<ComplianceReport>(
      `${BASE_URL}/compliance/reports/gdpr`,
      data
    );
    return response.data;
  },

  async generateSOC2Report(data: ComplianceReportRequest): Promise<ComplianceReport> {
    const response = await apiClient.post<ComplianceReport>(
      `${BASE_URL}/compliance/reports/soc2`,
      data
    );
    return response.data;
  },

  async generateAccessReport(data: AccessReportRequest): Promise<ComplianceReport> {
    const response = await apiClient.post<ComplianceReport>(
      `${BASE_URL}/compliance/reports/access`,
      data
    );
    return response.data;
  },

  async generatePermissionChangeReport(
    data: PermissionChangeReportRequest
  ): Promise<ComplianceReport> {
    const response = await apiClient.post<ComplianceReport>(
      `${BASE_URL}/compliance/reports/permission-changes`,
      data
    );
    return response.data;
  },

  async listReports(params?: {
    report_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<{
    reports: Array<{
      id: string;
      report_type: string;
      generated_at: string;
      period_start: string;
      period_end: string;
      compliance_score?: number;
    }>;
    total: number;
    offset: number;
    limit: number;
  }> {
    const response = await apiClient.get(`${BASE_URL}/compliance/reports`, { params });
    return response.data;
  },

  async getReport(reportId: string): Promise<ComplianceReport> {
    const response = await apiClient.get<ComplianceReport>(
      `${BASE_URL}/compliance/reports/${reportId}`
    );
    return response.data;
  },
};

export default auditApi;
