/**
 * Lineage API Service
 * 
 * Provides API calls for data lineage tracking:
 * - Lineage relationship management
 * - Upstream/downstream queries
 * - Impact analysis
 * - Visualization data
 */

import { apiClient } from './api/client';

// Types
export interface LineageNode {
  entity_type: string;
  entity_id: string;
  name?: string;
  metadata: Record<string, unknown>;
}

export interface LineageEdge {
  source_type: string;
  source_id: string;
  target_type: string;
  target_id: string;
  relationship: string;
  transformation: Record<string, unknown>;
  created_at?: string;
}

export interface LineageGraph {
  nodes: LineageNode[];
  edges: LineageEdge[];
  node_count: number;
  edge_count: number;
}

export interface LineagePath {
  source_type: string;
  source_id: string;
  target_type: string;
  target_id: string;
  path: Array<{ entity_type: string; entity_id: string }>;
  length: number;
}

export interface EntityImpact {
  entity_type: string;
  entity_id: string;
  entity_name?: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  impact_type: string;
  distance: number;
  details: Record<string, unknown>;
}

export interface ImpactReport {
  source_type: string;
  source_id: string;
  change_type: string;
  affected_entities: EntityImpact[];
  affected_count: number;
  critical_paths: Array<{
    target: string;
    severity: string;
    path: LineagePath;
  }>;
  estimated_records: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  risk_factors: string[];
  recommendations: string[];
  created_at: string;
}

export interface ImpactVisualization {
  nodes: Array<{
    id: string;
    label: string;
    type: string;
    severity: string;
    impact_type?: string;
    distance?: number;
    size: number;
  }>;
  edges: Array<{
    source: string;
    target: string;
    type: string;
  }>;
  summary: {
    total_nodes: number;
    total_edges: number;
    risk_level: string;
    critical_count: number;
    high_count: number;
  };
}

// Relationship types
export const RELATIONSHIP_TYPES = [
  'derived_from',
  'transformed_to',
  'copied_from',
  'aggregated_from',
  'filtered_from',
  'joined_from',
  'enriched_by',
] as const;

export type RelationshipType = typeof RELATIONSHIP_TYPES[number];

// API Functions
export const lineageApi = {
  // Lineage Management
  addLineage: async (params: {
    source_type: string;
    source_id: string;
    target_type: string;
    target_id: string;
    relationship: RelationshipType;
    transformation?: Record<string, unknown>;
    source_columns?: string[];
    target_columns?: string[];
    user_id?: string;
    tenant_id?: string;
  }) => {
    const { user_id, tenant_id, ...body } = params;
    const searchParams = new URLSearchParams();
    if (user_id) searchParams.append('user_id', user_id);
    if (tenant_id) searchParams.append('tenant_id', tenant_id);
    
    const response = await apiClient.post(
      `/api/v1/lineage/v2?${searchParams}`,
      body
    );
    return response.data;
  },

  // Lineage Queries
  getUpstream: async (
    entityType: string,
    entityId: string,
    depth = 3,
    tenantId?: string
  ) => {
    const params = new URLSearchParams({ depth: String(depth) });
    if (tenantId) params.append('tenant_id', tenantId);
    
    const response = await apiClient.get(
      `/api/v1/lineage/v2/${entityType}/${entityId}/upstream?${params}`
    );
    return response.data as { lineage: LineageGraph };
  },

  getDownstream: async (
    entityType: string,
    entityId: string,
    depth = 3,
    tenantId?: string
  ) => {
    const params = new URLSearchParams({ depth: String(depth) });
    if (tenantId) params.append('tenant_id', tenantId);
    
    const response = await apiClient.get(
      `/api/v1/lineage/v2/${entityType}/${entityId}/downstream?${params}`
    );
    return response.data as { lineage: LineageGraph };
  },

  getFullLineage: async (
    entityType: string,
    entityId: string,
    upstreamDepth = 3,
    downstreamDepth = 3,
    tenantId?: string
  ) => {
    const params = new URLSearchParams({
      upstream_depth: String(upstreamDepth),
      downstream_depth: String(downstreamDepth),
    });
    if (tenantId) params.append('tenant_id', tenantId);
    
    const response = await apiClient.get(
      `/api/v1/lineage/v2/${entityType}/${entityId}/full?${params}`
    );
    return response.data as { lineage: LineageGraph };
  },

  findPath: async (
    sourceType: string,
    sourceId: string,
    targetType: string,
    targetId: string,
    maxDepth = 10,
    tenantId?: string
  ) => {
    const params = new URLSearchParams({ max_depth: String(maxDepth) });
    if (tenantId) params.append('tenant_id', tenantId);
    
    const response = await apiClient.get(
      `/api/v1/lineage/v2/${sourceType}/${sourceId}/path/${targetType}/${targetId}?${params}`
    );
    return response.data as { paths: LineagePath[]; count: number };
  },

  // Impact Analysis
  analyzeImpact: async (
    entityType: string,
    entityId: string,
    changeType = 'update',
    maxDepth = 5,
    tenantId?: string
  ) => {
    const params = new URLSearchParams();
    if (tenantId) params.append('tenant_id', tenantId);
    
    const response = await apiClient.post(
      `/api/v1/lineage/v2/impact/${entityType}/${entityId}/analyze?${params}`,
      { change_type: changeType, max_depth: maxDepth }
    );
    return response.data as { impact_report: ImpactReport };
  },

  getImpactVisualization: async (
    entityType: string,
    entityId: string,
    changeType = 'update',
    maxDepth = 5,
    tenantId?: string
  ) => {
    const params = new URLSearchParams({
      change_type: changeType,
      max_depth: String(maxDepth),
    });
    if (tenantId) params.append('tenant_id', tenantId);
    
    const response = await apiClient.get(
      `/api/v1/lineage/v2/impact/${entityType}/${entityId}/visualize?${params}`
    );
    return response.data as { visualization: ImpactVisualization; risk_level: string };
  },

  // Statistics
  getStatistics: async (tenantId?: string) => {
    const params = tenantId ? `?tenant_id=${tenantId}` : '';
    const response = await apiClient.get(`/api/v1/lineage/v2/statistics${params}`);
    return response.data;
  },
};

export default lineageApi;
