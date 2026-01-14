/**
 * Snapshot API Service
 * 
 * Provides API calls for snapshot management:
 * - Snapshot creation and retrieval
 * - Snapshot restoration
 * - Scheduled snapshots
 * - Retention policy management
 */

import { apiClient } from './api/client';

// Types
export interface Snapshot {
  id: string;
  entity_type: string;
  entity_id: string;
  snapshot_type: 'full' | 'incremental';
  storage_key: string;
  size_bytes: number;
  checksum?: string;
  parent_snapshot_id?: string;
  metadata: Record<string, unknown>;
  tenant_id?: string;
  created_by?: string;
  created_at: string;
  expires_at?: string;
}

export interface SnapshotSchedule {
  id: string;
  entity_type: string;
  entity_id: string;
  schedule: string;
  snapshot_type: 'full' | 'incremental';
  enabled: boolean;
  retention_days: number;
  max_snapshots: number;
  last_run_at?: string;
  next_run_at?: string;
  tenant_id?: string;
  created_by?: string;
  created_at: string;
}

export interface RestoreResult {
  snapshot_id: string;
  entity_type: string;
  entity_id: string;
  restored_at: string;
  restored_by?: string;
}

export interface RetentionPolicy {
  max_age_days: number;
  max_count: number;
  keep_tagged: boolean;
}

export interface SnapshotStatistics {
  total_snapshots: number;
  total_size_bytes: number;
  by_type: Record<string, number>;
  generated_at: string;
}

// API Functions
export const snapshotApi = {
  // Snapshot Management
  createSnapshot: async (
    entityType: string,
    entityId: string,
    data: Record<string, unknown>,
    snapshotType: 'full' | 'incremental' = 'full',
    metadata?: Record<string, unknown>,
    expiresAt?: string,
    userId?: string,
    tenantId?: string
  ) => {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    if (tenantId) params.append('tenant_id', tenantId);
    
    const response = await apiClient.post(
      `/api/v1/snapshots/${entityType}/${entityId}?${params}`,
      {
        data,
        snapshot_type: snapshotType,
        metadata,
        expires_at: expiresAt,
      }
    );
    return response.data as { snapshot: Snapshot; message: string };
  },

  listSnapshots: async (params?: {
    entity_type?: string;
    entity_id?: string;
    tenant_id?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.append(key, String(value));
      });
    }
    
    const response = await apiClient.get(`/api/v1/snapshots?${searchParams}`);
    return response.data as { snapshots: Snapshot[]; count: number };
  },

  getSnapshot: async (snapshotId: string, tenantId?: string) => {
    const params = tenantId ? `?tenant_id=${tenantId}` : '';
    const response = await apiClient.get(`/api/v1/snapshots/${snapshotId}${params}`);
    return response.data as { snapshot: Snapshot };
  },

  getLatestSnapshot: async (
    entityType: string,
    entityId: string,
    tenantId?: string
  ) => {
    const params = tenantId ? `?tenant_id=${tenantId}` : '';
    const response = await apiClient.get(
      `/api/v1/snapshots/${entityType}/${entityId}/latest${params}`
    );
    return response.data as { snapshot: Snapshot };
  },

  restoreSnapshot: async (
    snapshotId: string,
    userId?: string,
    tenantId?: string
  ) => {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    if (tenantId) params.append('tenant_id', tenantId);
    
    const response = await apiClient.post(
      `/api/v1/snapshots/${snapshotId}/restore?${params}`
    );
    return response.data as {
      restore_result: RestoreResult;
      data: Record<string, unknown>;
      message: string;
    };
  },

  deleteSnapshot: async (snapshotId: string, tenantId?: string) => {
    const params = tenantId ? `?tenant_id=${tenantId}` : '';
    const response = await apiClient.delete(`/api/v1/snapshots/${snapshotId}${params}`);
    return response.data;
  },

  // Schedule Management
  createSchedule: async (
    entityType: string,
    entityId: string,
    schedule: string,
    snapshotType: 'full' | 'incremental' = 'full',
    retentionDays = 90,
    maxSnapshots = 100,
    userId?: string,
    tenantId?: string
  ) => {
    const params = new URLSearchParams({
      entity_type: entityType,
      entity_id: entityId,
    });
    if (userId) params.append('user_id', userId);
    if (tenantId) params.append('tenant_id', tenantId);
    
    const response = await apiClient.post(`/api/v1/snapshots/schedules?${params}`, {
      schedule,
      snapshot_type: snapshotType,
      retention_days: retentionDays,
      max_snapshots: maxSnapshots,
    });
    return response.data as { schedule: SnapshotSchedule; message: string };
  },

  // Retention Policy
  applyRetentionPolicy: async (
    entityType: string,
    entityId: string,
    policy: RetentionPolicy,
    tenantId?: string
  ) => {
    const params = tenantId ? `?tenant_id=${tenantId}` : '';
    const response = await apiClient.post(
      `/api/v1/snapshots/${entityType}/${entityId}/retention${params}`,
      policy
    );
    return response.data as { deleted_count: number; message: string };
  },

  // Statistics
  getStatistics: async (tenantId?: string) => {
    const params = tenantId ? `?tenant_id=${tenantId}` : '';
    const response = await apiClient.get(`/api/v1/snapshots/statistics${params}`);
    return response.data as { statistics: SnapshotStatistics };
  },
};

export default snapshotApi;
