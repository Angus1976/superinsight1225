/**
 * Versioning API Service
 * 
 * Provides API calls for version management:
 * - Version creation and retrieval
 * - Version history and rollback
 * - Change tracking
 * - Diff computation
 */

import { apiClient } from './api/client';

// Types
export interface Version {
  id: string;
  entity_type: string;
  entity_id: string;
  version: string;
  version_number: number;
  version_type: string;
  status: string;
  parent_version_id?: string;
  message?: string;
  tags: string[];
  checksum?: string;
  data_size_bytes: number;
  metadata: Record<string, unknown>;
  tenant_id?: string;
  created_by?: string;
  created_at: string;
}

export interface ChangeRecord {
  id: string;
  entity_type: string;
  entity_id: string;
  change_type: 'create' | 'update' | 'delete';
  old_snapshot?: Record<string, unknown>;
  new_snapshot?: Record<string, unknown>;
  diff?: {
    added: Record<string, unknown>;
    removed: Record<string, unknown>;
    modified: Record<string, unknown>;
  };
  user_id: string;
  metadata: Record<string, unknown>;
  tenant_id?: string;
  created_at: string;
}

export interface DiffResult {
  diff_level: 'field' | 'line';
  changes: Array<{
    field: string;
    change_type: 'added' | 'removed' | 'modified';
    old_value: unknown;
    new_value: unknown;
  }>;
  unified_diff: string[];
  summary: {
    added: number;
    removed: number;
    modified: number;
  };
}

export interface MergeResult {
  merged: Record<string, unknown>;
  conflicts: Array<{
    field: string;
    base_value: unknown;
    ours_value: unknown;
    theirs_value: unknown;
  }>;
  has_conflicts: boolean;
}

export interface TimelineEntry {
  id: string;
  timestamp: string;
  change_type: string;
  user_id: string;
  summary: string;
  diff?: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

// API Functions
export const versioningApi = {
  // Version Management
  createVersion: async (
    entityType: string,
    entityId: string,
    data: Record<string, unknown>,
    message: string,
    versionType: 'major' | 'minor' | 'patch' = 'patch',
    metadata?: Record<string, unknown>
  ) => {
    const response = await apiClient.post(`/api/v1/versioning/${entityType}/${entityId}`, {
      data,
      message,
      version_type: versionType,
      metadata,
    });
    return response.data;
  },

  getVersionHistory: async (
    entityType: string,
    entityId: string,
    limit = 50,
    tenantId?: string
  ) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (tenantId) params.append('tenant_id', tenantId);
    
    const response = await apiClient.get(
      `/api/v1/versioning/${entityType}/${entityId}?${params}`
    );
    return response.data as { versions: Version[]; count: number };
  },

  getVersion: async (
    entityType: string,
    entityId: string,
    version: string,
    tenantId?: string
  ) => {
    const params = tenantId ? `?tenant_id=${tenantId}` : '';
    const response = await apiClient.get(
      `/api/v1/versioning/${entityType}/${entityId}/${version}${params}`
    );
    return response.data as { version: Version };
  },

  rollbackVersion: async (
    entityType: string,
    entityId: string,
    targetVersion: string,
    userId?: string
  ) => {
    const params = userId ? `?user_id=${userId}` : '';
    const response = await apiClient.post(
      `/api/v1/versioning/${entityType}/${entityId}/rollback${params}`,
      { target_version: targetVersion }
    );
    return response.data;
  },

  addTag: async (versionId: string, tag: string, userId?: string) => {
    const params = userId ? `?user_id=${userId}` : '';
    const response = await apiClient.post(
      `/api/v1/versioning/${versionId}/tags${params}`,
      { tag }
    );
    return response.data;
  },

  // Change Tracking
  getChanges: async (params: {
    entity_type?: string;
    entity_id?: string;
    user_id?: string;
    change_type?: string;
    start_time?: string;
    end_time?: string;
    tenant_id?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.append(key, String(value));
    });
    
    const response = await apiClient.get(`/api/v1/versioning/changes?${searchParams}`);
    return response.data as { changes: ChangeRecord[]; count: number };
  },

  getEntityTimeline: async (
    entityType: string,
    entityId: string,
    limit = 100,
    tenantId?: string
  ) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (tenantId) params.append('tenant_id', tenantId);
    
    const response = await apiClient.get(
      `/api/v1/versioning/changes/${entityType}/${entityId}/timeline?${params}`
    );
    return response.data as { timeline: TimelineEntry[]; count: number };
  },

  getChangeStatistics: async (params?: {
    entity_type?: string;
    tenant_id?: string;
    start_time?: string;
    end_time?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.append(key, String(value));
      });
    }
    
    const response = await apiClient.get(
      `/api/v1/versioning/changes/statistics?${searchParams}`
    );
    return response.data;
  },

  // Diff and Merge
  computeDiff: async (
    oldData: Record<string, unknown>,
    newData: Record<string, unknown>,
    diffLevel: 'field' | 'line' = 'field'
  ) => {
    const response = await apiClient.post('/api/v1/versioning/diff', {
      old_data: oldData,
      new_data: newData,
      diff_level: diffLevel,
    });
    return response.data as { diff: DiffResult };
  },

  threeWayMerge: async (
    base: Record<string, unknown>,
    ours: Record<string, unknown>,
    theirs: Record<string, unknown>
  ) => {
    const response = await apiClient.post('/api/v1/versioning/merge', {
      base,
      ours,
      theirs,
    });
    return response.data as { merge_result: MergeResult };
  },

  resolveConflict: async (
    merged: Record<string, unknown>,
    conflicts: MergeResult['conflicts'],
    field: string,
    resolution: 'ours' | 'theirs' | 'base' | 'custom',
    customValue?: unknown
  ) => {
    const response = await apiClient.post('/api/v1/versioning/merge/resolve', {
      merged,
      conflicts,
      field,
      resolution,
      custom_value: customValue,
    });
    return response.data as { merge_result: MergeResult };
  },
};

export default versioningApi;
