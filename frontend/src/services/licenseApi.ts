/**
 * License Management API Service
 * 
 * Provides API client functions for license management operations.
 */

import { api } from './api';

// ============================================================================
// Types
// ============================================================================

export type LicenseType = 'trial' | 'basic' | 'professional' | 'enterprise';
export type LicenseStatus = 'pending' | 'active' | 'expired' | 'suspended' | 'revoked';
export type SubscriptionType = 'perpetual' | 'monthly' | 'yearly';
export type ValidityStatus = 'not_started' | 'active' | 'grace_period' | 'expired';
export type ActivationType = 'online' | 'offline';
export type AlertType = 'expiry_warning' | 'concurrent_limit' | 'resource_limit' | 'license_violation' | 'activation_failed';

export interface LicenseLimits {
  max_concurrent_users: number;
  max_cpu_cores: number;
  max_storage_gb: number;
  max_projects: number;
  max_datasets: number;
}

export interface LicenseValidity {
  start_date: string;
  end_date: string;
  subscription_type: SubscriptionType;
  grace_period_days: number;
  auto_renew: boolean;
}

export interface License {
  id: string;
  license_key: string;
  license_type: LicenseType;
  features: string[];
  limits: LicenseLimits;
  validity_start: string;
  validity_end: string;
  subscription_type: SubscriptionType;
  grace_period_days: number;
  auto_renew: boolean;
  hardware_id?: string;
  status: LicenseStatus;
  created_at: string;
  activated_at?: string;
  metadata?: Record<string, unknown>;
}

export interface LicenseStatusResponse {
  license_id: string;
  license_key: string;
  license_type: LicenseType;
  status: LicenseStatus;
  validity_status: ValidityStatus;
  days_remaining?: number;
  days_until_start?: number;
  features: string[];
  limits: LicenseLimits;
  current_usage?: UsageInfo;
  warnings: string[];
}

export interface UsageInfo {
  concurrent_users: number;
  max_concurrent_users: number;
  cpu_cores: number;
  max_cpu_cores: number;
  storage_gb: number;
  max_storage_gb: number;
  projects: number;
  max_projects: number;
  datasets: number;
  max_datasets: number;
}

export interface ActivationResult {
  success: boolean;
  license?: License;
  activation_id?: string;
  error?: string;
}

export interface OfflineActivationRequest {
  request_code: string;
  hardware_fingerprint: string;
  license_key: string;
  expires_at: string;
}

export interface ValidationResult {
  valid: boolean;
  reason?: string;
  warnings: string[];
  license_id?: string;
  license_type?: LicenseType;
  status?: LicenseStatus;
}

export interface FeatureInfo {
  name: string;
  enabled: boolean;
  description?: string;
  requires_upgrade: boolean;
  trial_available: boolean;
  trial_days_remaining?: number;
}

export interface UserSession {
  id: string;
  user_id: string;
  session_id: string;
  priority: number;
  login_time: string;
  last_activity: string;
  ip_address?: string;
  is_active: boolean;
}

export interface ConcurrentUsageInfo {
  current_users: number;
  max_users: number;
  utilization_percent: number;
  active_sessions: UserSession[];
}

export interface ResourceUsageInfo {
  cpu_cores: number;
  max_cpu_cores: number;
  cpu_utilization_percent: number;
  storage_gb: number;
  max_storage_gb: number;
  storage_utilization_percent: number;
}

export interface LicenseUsageReport {
  license_id: string;
  license_type: LicenseType;
  report_period: {
    start: string;
    end: string;
  };
  concurrent_user_stats: Record<string, unknown>;
  resource_usage_stats: Record<string, unknown>;
  feature_usage_stats: Record<string, unknown>;
  audit_summary: Record<string, number>;
  generated_at: string;
}

export interface AuditLog {
  id: string;
  license_id?: string;
  event_type: string;
  details: Record<string, unknown>;
  user_id?: string;
  ip_address?: string;
  success: boolean;
  error_message?: string;
  timestamp: string;
}

export interface Alert {
  id: string;
  alert_type: AlertType;
  severity: string;
  message: string;
  details: Record<string, unknown>;
  created_at: string;
  acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
}

export interface AlertConfig {
  alert_type: AlertType;
  enabled: boolean;
  threshold?: number;
  notification_channels: string[];
  recipients: string[];
}

// ============================================================================
// License API
// ============================================================================

export const licenseApi = {
  // License Status
  async getStatus(): Promise<LicenseStatusResponse> {
    const response = await api.get('/api/v1/license/status');
    return response.data;
  },

  async getLicense(licenseId: string): Promise<License> {
    const response = await api.get(`/api/v1/license/${licenseId}`);
    return response.data;
  },

  async listLicenses(params?: {
    status?: LicenseStatus;
    limit?: number;
    offset?: number;
  }): Promise<License[]> {
    const response = await api.get('/api/v1/license/', { params });
    return response.data;
  },

  async createLicense(data: {
    license_type: LicenseType;
    features?: string[];
    limits?: Partial<LicenseLimits>;
    validity: LicenseValidity;
    metadata?: Record<string, unknown>;
  }): Promise<License> {
    const response = await api.post('/api/v1/license/', data);
    return response.data;
  },

  async renewLicense(licenseId: string, data: {
    new_end_date: string;
    subscription_type?: SubscriptionType;
  }): Promise<License> {
    const response = await api.post(`/api/v1/license/${licenseId}/renew`, data);
    return response.data;
  },

  async upgradeLicense(licenseId: string, data: {
    new_type?: LicenseType;
    new_features?: string[];
    new_limits?: Partial<LicenseLimits>;
  }): Promise<License> {
    const response = await api.post(`/api/v1/license/${licenseId}/upgrade`, data);
    return response.data;
  },

  async revokeLicense(licenseId: string, reason: string): Promise<{ success: boolean }> {
    const response = await api.post(`/api/v1/license/${licenseId}/revoke`, { reason });
    return response.data;
  },

  async suspendLicense(licenseId: string): Promise<{ success: boolean }> {
    const response = await api.post(`/api/v1/license/${licenseId}/suspend`);
    return response.data;
  },

  async reactivateLicense(licenseId: string): Promise<{ success: boolean }> {
    const response = await api.post(`/api/v1/license/${licenseId}/reactivate`);
    return response.data;
  },

  // Features
  async getFeatures(): Promise<FeatureInfo[]> {
    const response = await api.get('/api/v1/license/features/list');
    return response.data;
  },

  async checkFeatureAccess(feature: string): Promise<{
    allowed: boolean;
    feature: string;
    reason?: string;
    requires_upgrade: boolean;
    upgrade_to?: LicenseType;
  }> {
    const response = await api.get(`/api/v1/license/features/${feature}/check`);
    return response.data;
  },

  async getLimits(): Promise<LicenseLimits> {
    const response = await api.get('/api/v1/license/limits');
    return response.data;
  },

  async validateLicense(hardwareId?: string): Promise<ValidationResult> {
    const response = await api.get('/api/v1/license/validate', {
      params: { hardware_id: hardwareId },
    });
    return response.data;
  },
};

// ============================================================================
// Activation API
// ============================================================================

export const activationApi = {
  async activateOnline(data: {
    license_key: string;
    hardware_fingerprint?: string;
  }): Promise<ActivationResult> {
    const response = await api.post('/api/v1/activation/activate', data);
    return response.data;
  },

  async generateOfflineRequest(
    licenseKey: string,
    hardwareFingerprint?: string
  ): Promise<OfflineActivationRequest> {
    const response = await api.post('/api/v1/activation/offline/request', null, {
      params: { license_key: licenseKey, hardware_fingerprint: hardwareFingerprint },
    });
    return response.data;
  },

  async activateOffline(activationCode: string): Promise<ActivationResult> {
    const response = await api.post('/api/v1/activation/offline/activate', null, {
      params: { activation_code: activationCode },
    });
    return response.data;
  },

  async verifyActivation(licenseId: string): Promise<{
    valid: boolean;
    license_id?: string;
    license_type?: string;
    expires_at?: string;
    reason?: string;
  }> {
    const response = await api.get(`/api/v1/activation/verify/${licenseId}`);
    return response.data;
  },

  async getHardwareFingerprint(): Promise<{
    fingerprint: string;
    message: string;
  }> {
    const response = await api.get('/api/v1/activation/fingerprint');
    return response.data;
  },

  async revokeActivation(licenseId: string, reason: string): Promise<{ success: boolean }> {
    const response = await api.post(`/api/v1/activation/revoke/${licenseId}`, null, {
      params: { reason },
    });
    return response.data;
  },
};

// ============================================================================
// Usage API
// ============================================================================

export const usageApi = {
  // Concurrent Users
  async getConcurrentUsage(): Promise<ConcurrentUsageInfo> {
    const response = await api.get('/api/v1/usage/concurrent');
    return response.data;
  },

  async getActiveSessions(): Promise<UserSession[]> {
    const response = await api.get('/api/v1/usage/sessions');
    return response.data;
  },

  async getUserSessions(userId: string): Promise<UserSession[]> {
    const response = await api.get(`/api/v1/usage/sessions/user/${userId}`);
    return response.data;
  },

  async registerSession(data: {
    user_id: string;
    session_id: string;
    priority?: number;
    ip_address?: string;
    user_agent?: string;
  }): Promise<UserSession> {
    const response = await api.post('/api/v1/usage/sessions/register', data);
    return response.data;
  },

  async releaseSession(sessionId: string, userId: string): Promise<{ success: boolean }> {
    const response = await api.post(`/api/v1/usage/sessions/${sessionId}/release`, null, {
      params: { user_id: userId },
    });
    return response.data;
  },

  async terminateSession(sessionId: string, reason?: string): Promise<{ success: boolean }> {
    const response = await api.post(`/api/v1/usage/sessions/${sessionId}/terminate`, null, {
      params: { reason },
    });
    return response.data;
  },

  async forceLogoutUser(userId: string, reason: string): Promise<{
    success: boolean;
    sessions_terminated: number;
  }> {
    const response = await api.post(`/api/v1/usage/sessions/user/${userId}/logout`, { reason });
    return response.data;
  },

  // Resources
  async getResourceUsage(): Promise<ResourceUsageInfo> {
    const response = await api.get('/api/v1/usage/resources');
    return response.data;
  },

  async checkAllResources(): Promise<Record<string, {
    allowed: boolean;
    reason?: string;
    warning?: string;
    current?: number;
    max?: number;
  }>> {
    const response = await api.get('/api/v1/usage/resources/check');
    return response.data;
  },

  // Reports
  async generateReport(data: {
    start_date: string;
    end_date: string;
    include_sessions?: boolean;
    include_resources?: boolean;
    include_features?: boolean;
  }, licenseId?: string): Promise<LicenseUsageReport> {
    const response = await api.post('/api/v1/usage/report', data, {
      params: { license_id: licenseId },
    });
    return response.data;
  },

  async getDailySummary(date?: string): Promise<Record<string, unknown>> {
    const response = await api.get('/api/v1/usage/report/daily', {
      params: { date },
    });
    return response.data;
  },

  async getUsageTrend(days?: number): Promise<Record<string, unknown>[]> {
    const response = await api.get('/api/v1/usage/report/trend', {
      params: { days },
    });
    return response.data;
  },

  // Audit Logs
  async queryAuditLogs(filter: {
    license_id?: string;
    event_type?: string;
    user_id?: string;
    start_time?: string;
    end_time?: string;
    success?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<AuditLog[]> {
    const response = await api.post('/api/v1/usage/audit/query', filter);
    return response.data;
  },

  async getAuditLog(logId: string): Promise<AuditLog> {
    const response = await api.get(`/api/v1/usage/audit/${logId}`);
    return response.data;
  },

  async getAuditStats(params?: {
    start_time?: string;
    end_time?: string;
    license_id?: string;
  }): Promise<Record<string, number>> {
    const response = await api.get('/api/v1/usage/audit/stats', { params });
    return response.data;
  },

  async exportAuditLogs(params: {
    start_time: string;
    end_time: string;
    format?: 'csv' | 'json';
    license_id?: string;
  }): Promise<Blob> {
    const response = await api.get('/api/v1/usage/audit/export', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },
};

export default {
  license: licenseApi,
  activation: activationApi,
  usage: usageApi,
};
