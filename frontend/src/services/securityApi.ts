/**
 * Security Monitor and Session API Service for SuperInsight Platform
 * 
 * Provides API client functions for security monitoring and session management.
 */

import apiClient from './api/client';

// ============================================================================
// Security Event Types
// ============================================================================

export type SecuritySeverity = 'low' | 'medium' | 'high' | 'critical';
export type SecurityEventStatus = 'open' | 'investigating' | 'resolved';

export interface SecurityEvent {
  id: string;
  event_type: string;
  severity: SecuritySeverity;
  user_id: string;
  details: Record<string, unknown>;
  status: SecurityEventStatus;
  created_at: string;
  resolved_at?: string;
  resolved_by?: string;
  resolution_notes?: string;
}

export interface SecurityEventListResponse {
  events: SecurityEvent[];
  total: number;
  offset: number;
  limit: number;
}

export interface SecurityEventQueryParams {
  event_type?: string;
  severity?: SecuritySeverity;
  status?: SecurityEventStatus;
  user_id?: string;
  start_time?: string;
  end_time?: string;
  limit?: number;
  offset?: number;
}

export interface ResolveEventRequest {
  resolution_notes: string;
  resolved_by: string;
}

export interface SecurityPosture {
  risk_score: number;
  events_by_type: Record<string, number>;
  trend: Array<{ date: string; count: number }>;
  recommendations: string[];
  generated_at: string;
}

export interface SecuritySummary {
  open_events: number;
  critical_events_24h: number;
  events_last_7_days: number;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  generated_at: string;
}

export interface SecurityThresholds {
  failed_login_attempts: number;
  failed_login_window_minutes: number;
  mass_download_threshold: number;
  mass_download_window_minutes: number;
  high_privilege_roles: string[];
}

export interface SecurityStatistics {
  period_days: number;
  total_events: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  generated_at: string;
}

// ============================================================================
// Session Types
// ============================================================================

export interface Session {
  id: string;
  user_id: string;
  ip_address: string;
  user_agent?: string;
  created_at: string;
  last_activity: string;
  expires_at?: string;
  metadata?: Record<string, unknown>;
}

export interface SessionListResponse {
  sessions: Session[];
  total: number;
}

export interface CreateSessionRequest {
  user_id: string;
  ip_address: string;
  user_agent?: string;
  timeout?: number;
  metadata?: Record<string, unknown>;
}

export interface SessionConfig {
  default_timeout: number;
  max_concurrent_sessions: number;
}

export interface SessionStatistics {
  total_active_sessions: number;
  total_users_with_sessions: number;
  top_users_by_sessions: Record<string, number>;
  configuration: SessionConfig;
}

// ============================================================================
// Security Monitor API Functions
// ============================================================================

const SECURITY_BASE_URL = '/api/v1/security';

export const securityMonitorApi = {
  // Security Events
  async listEvents(params?: SecurityEventQueryParams): Promise<SecurityEventListResponse> {
    const response = await apiClient.get<SecurityEventListResponse>(
      `${SECURITY_BASE_URL}/events`,
      { params }
    );
    return response.data;
  },

  async getEvent(eventId: string): Promise<SecurityEvent> {
    const response = await apiClient.get<SecurityEvent>(
      `${SECURITY_BASE_URL}/events/${eventId}`
    );
    return response.data;
  },

  async resolveEvent(eventId: string, data: ResolveEventRequest): Promise<SecurityEvent> {
    const response = await apiClient.post<SecurityEvent>(
      `${SECURITY_BASE_URL}/events/${eventId}/resolve`,
      data
    );
    return response.data;
  },

  async markEventInvestigating(
    eventId: string,
    investigatorId: string
  ): Promise<SecurityEvent> {
    const response = await apiClient.post<SecurityEvent>(
      `${SECURITY_BASE_URL}/events/${eventId}/investigate`,
      null,
      { params: { investigator_id: investigatorId } }
    );
    return response.data;
  },

  // Security Posture
  async getPosture(days?: number): Promise<SecurityPosture> {
    const response = await apiClient.get<SecurityPosture>(
      `${SECURITY_BASE_URL}/posture`,
      { params: { days } }
    );
    return response.data;
  },

  async getSummary(): Promise<SecuritySummary> {
    const response = await apiClient.get<SecuritySummary>(
      `${SECURITY_BASE_URL}/posture/summary`
    );
    return response.data;
  },

  // Thresholds Configuration
  async getThresholds(): Promise<SecurityThresholds> {
    const response = await apiClient.get<SecurityThresholds>(
      `${SECURITY_BASE_URL}/thresholds`
    );
    return response.data;
  },

  async updateThresholds(
    data: Partial<SecurityThresholds>,
    adminUserId: string
  ): Promise<SecurityThresholds> {
    const response = await apiClient.put<SecurityThresholds>(
      `${SECURITY_BASE_URL}/thresholds`,
      data,
      { params: { admin_user_id: adminUserId } }
    );
    return response.data;
  },

  // Statistics
  async getStatistics(days?: number): Promise<SecurityStatistics> {
    const response = await apiClient.get<SecurityStatistics>(
      `${SECURITY_BASE_URL}/statistics`,
      { params: { days } }
    );
    return response.data;
  },
};

// ============================================================================
// Session Management API Functions
// ============================================================================

const SESSION_BASE_URL = '/api/v1/sessions';

export const sessionApi = {
  // Session CRUD
  async createSession(data: CreateSessionRequest): Promise<Session> {
    const response = await apiClient.post<Session>(SESSION_BASE_URL, data);
    return response.data;
  },

  async listSessions(params?: {
    user_id?: string;
    limit?: number;
  }): Promise<SessionListResponse> {
    const response = await apiClient.get<SessionListResponse>(SESSION_BASE_URL, {
      params,
    });
    return response.data;
  },

  async getSession(sessionId: string): Promise<Session> {
    const response = await apiClient.get<Session>(`${SESSION_BASE_URL}/${sessionId}`);
    return response.data;
  },

  async destroySession(sessionId: string): Promise<void> {
    await apiClient.delete(`${SESSION_BASE_URL}/${sessionId}`);
  },

  // Session Management
  async forceLogout(
    userId: string,
    adminUserId: string
  ): Promise<{ success: boolean; sessions_destroyed: number; user_id: string }> {
    const response = await apiClient.post(
      `${SESSION_BASE_URL}/force-logout/${userId}`,
      null,
      { params: { admin_user_id: adminUserId } }
    );
    return response.data;
  },

  async extendSession(
    sessionId: string,
    additionalSeconds: number
  ): Promise<Session> {
    const response = await apiClient.post<Session>(
      `${SESSION_BASE_URL}/${sessionId}/extend`,
      { additional_seconds: additionalSeconds }
    );
    return response.data;
  },

  async validateSession(sessionId: string): Promise<Session> {
    const response = await apiClient.post<Session>(
      `${SESSION_BASE_URL}/${sessionId}/validate`
    );
    return response.data;
  },

  // Configuration
  async getConfig(): Promise<SessionConfig> {
    const response = await apiClient.get<SessionConfig>(
      `${SESSION_BASE_URL}/config/current`
    );
    return response.data;
  },

  async updateConfig(
    data: Partial<SessionConfig>,
    adminUserId: string
  ): Promise<SessionConfig> {
    const response = await apiClient.put<SessionConfig>(
      `${SESSION_BASE_URL}/config`,
      data,
      { params: { admin_user_id: adminUserId } }
    );
    return response.data;
  },

  // Statistics
  async getStatistics(): Promise<SessionStatistics> {
    const response = await apiClient.get<SessionStatistics>(
      `${SESSION_BASE_URL}/stats/overview`
    );
    return response.data;
  },

  async cleanup(adminUserId: string): Promise<{
    success: boolean;
    cleaned_count: number;
    performed_by: string;
    performed_at: string;
  }> {
    const response = await apiClient.post(`${SESSION_BASE_URL}/cleanup`, null, {
      params: { admin_user_id: adminUserId },
    });
    return response.data;
  },

  // User Sessions
  async getUserSessions(userId: string): Promise<SessionListResponse> {
    const response = await apiClient.get<SessionListResponse>(
      `${SESSION_BASE_URL}/users/${userId}`
    );
    return response.data;
  },

  async destroyUserSessions(userId: string, adminUserId: string): Promise<void> {
    await apiClient.delete(`${SESSION_BASE_URL}/users/${userId}`, {
      params: { admin_user_id: adminUserId },
    });
  },
};

export default { securityMonitorApi, sessionApi };
