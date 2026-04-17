/**
 * Datalake/Warehouse API service layer.
 * Provides typed API calls for data source CRUD, schema browsing, and dashboard.
 */

import apiClient from './api/client';
import { apiRequestToSnake, apiResponseToSnake } from '@/utils/jsonCase';
import type {
  DatalakeSourceCreate,
  DatalakeSourceUpdate,
  DatalakeSourceResponse,
  ConnectionTestResult,
  DashboardOverview,
  SourceHealthStatus,
  VolumeTrendData,
  QueryPerformanceData,
  DataFlowGraph,
  TableSchema,
  TablePreview,
} from '@/types/datalake';

const BASE = '/api/v1/datalake';

export const datalakeApi = {
  // --- Data Source CRUD ---

  getSources: async (): Promise<DatalakeSourceResponse[]> => {
    const res = await apiClient.get<DatalakeSourceResponse[]>(`${BASE}/sources`);
    return apiResponseToSnake(res.data);
  },

  getSource: async (id: string): Promise<DatalakeSourceResponse> => {
    const res = await apiClient.get<DatalakeSourceResponse>(`${BASE}/sources/${id}`);
    return apiResponseToSnake(res.data);
  },

  createSource: async (data: DatalakeSourceCreate): Promise<DatalakeSourceResponse> => {
    const res = await apiClient.post<DatalakeSourceResponse>(`${BASE}/sources`, apiRequestToSnake(data));
    return apiResponseToSnake(res.data);
  },

  updateSource: async (id: string, data: DatalakeSourceUpdate): Promise<DatalakeSourceResponse> => {
    const res = await apiClient.put<DatalakeSourceResponse>(`${BASE}/sources/${id}`, apiRequestToSnake(data));
    return apiResponseToSnake(res.data);
  },

  deleteSource: async (id: string): Promise<void> => {
    await apiClient.delete(`${BASE}/sources/${id}`);
  },

  testConnection: async (id: string): Promise<ConnectionTestResult> => {
    const res = await apiClient.post<ConnectionTestResult>(`${BASE}/sources/${id}/test`);
    return apiResponseToSnake(res.data);
  },

  // --- Schema Browsing ---

  getDatabases: async (id: string): Promise<string[]> => {
    const res = await apiClient.get<string[]>(`${BASE}/sources/${id}/databases`);
    return apiResponseToSnake(res.data);
  },

  getTables: async (id: string, database: string): Promise<unknown[]> => {
    const res = await apiClient.get<unknown[]>(`${BASE}/sources/${id}/tables`, {
      params: { database },
    });
    return apiResponseToSnake(res.data);
  },

  getTableSchema: async (id: string, database: string, table: string): Promise<TableSchema> => {
    const res = await apiClient.get<TableSchema>(`${BASE}/sources/${id}/schema`, {
      params: { database, table },
    });
    return apiResponseToSnake(res.data);
  },

  getTablePreview: async (id: string, database: string, table: string, limit = 100): Promise<TablePreview> => {
    const res = await apiClient.get<TablePreview>(`${BASE}/sources/${id}/preview`, {
      params: { database, table, limit },
    });
    return apiResponseToSnake(res.data);
  },

  // --- Dashboard ---

  getDashboardOverview: async (): Promise<DashboardOverview> => {
    const res = await apiClient.get<DashboardOverview>(`${BASE}/dashboard/overview`);
    return apiResponseToSnake(res.data);
  },

  getDashboardHealth: async (): Promise<SourceHealthStatus[]> => {
    const res = await apiClient.get<SourceHealthStatus[]>(`${BASE}/dashboard/health`);
    return apiResponseToSnake(res.data);
  },

  getVolumeTrends: async (period = '7d'): Promise<VolumeTrendData> => {
    const res = await apiClient.get<VolumeTrendData>(`${BASE}/dashboard/volume-trends`, {
      params: { period },
    });
    return apiResponseToSnake(res.data);
  },

  getQueryPerformance: async (sourceId?: string): Promise<QueryPerformanceData> => {
    const res = await apiClient.get<QueryPerformanceData>(`${BASE}/dashboard/query-performance`, {
      params: sourceId ? { source_id: sourceId } : undefined,
    });
    return apiResponseToSnake(res.data);
  },

  getDataFlow: async (): Promise<DataFlowGraph> => {
    const res = await apiClient.get<DataFlowGraph>(`${BASE}/dashboard/data-flow`);
    return apiResponseToSnake(res.data);
  },
};
