/**
 * React Query hooks for Datalake/Warehouse API.
 * Follows existing project patterns (useBilling, useTask, useDashboard).
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { message } from 'antd';
import { datalakeApi } from '@/services/datalakeApi';
import type {
  DatalakeSourceCreate,
  DatalakeSourceUpdate,
} from '@/types/datalake';

// Query key factory for cache management
const datalakeKeys = {
  all: ['datalake'] as const,
  sources: () => [...datalakeKeys.all, 'sources'] as const,
  source: (id: string) => [...datalakeKeys.all, 'sources', id] as const,
  databases: (id: string) => [...datalakeKeys.all, 'databases', id] as const,
  tables: (id: string, db: string) => [...datalakeKeys.all, 'tables', id, db] as const,
  dashboard: () => [...datalakeKeys.all, 'dashboard'] as const,
  overview: () => [...datalakeKeys.dashboard(), 'overview'] as const,
  health: () => [...datalakeKeys.dashboard(), 'health'] as const,
  volumeTrends: (period: string) => [...datalakeKeys.dashboard(), 'volume-trends', period] as const,
  queryPerformance: (sourceId?: string) => [...datalakeKeys.dashboard(), 'query-performance', sourceId] as const,
  dataFlow: () => [...datalakeKeys.dashboard(), 'data-flow'] as const,
};

// ============================================================================
// Data Source Queries
// ============================================================================

export function useDatalakeSources() {
  return useQuery({
    queryKey: datalakeKeys.sources(),
    queryFn: datalakeApi.getSources,
  });
}

export function useDatalakeSource(id: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: datalakeKeys.source(id),
    queryFn: () => datalakeApi.getSource(id),
    enabled: options?.enabled ?? !!id,
  });
}

// ============================================================================
// Data Source Mutations
// ============================================================================

export function useCreateDatalakeSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DatalakeSourceCreate) => datalakeApi.createSource(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datalakeKeys.sources() });
      queryClient.invalidateQueries({ queryKey: datalakeKeys.dashboard() });
    },
  });
}

export function useUpdateDatalakeSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DatalakeSourceUpdate }) =>
      datalakeApi.updateSource(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: datalakeKeys.source(id) });
      queryClient.invalidateQueries({ queryKey: datalakeKeys.sources() });
    },
  });
}

export function useDeleteDatalakeSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => datalakeApi.deleteSource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datalakeKeys.sources() });
      queryClient.invalidateQueries({ queryKey: datalakeKeys.dashboard() });
    },
  });
}

export function useTestDatalakeConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => datalakeApi.testConnection(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datalakeKeys.sources() });
      queryClient.invalidateQueries({ queryKey: datalakeKeys.health() });
    },
  });
}

// ============================================================================
// Schema Browsing Queries
// ============================================================================

export function useDatalakeDatabases(id: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: datalakeKeys.databases(id),
    queryFn: () => datalakeApi.getDatabases(id),
    enabled: options?.enabled ?? !!id,
  });
}

export function useDatalakeTables(id: string, database: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: datalakeKeys.tables(id, database),
    queryFn: () => datalakeApi.getTables(id, database),
    enabled: options?.enabled ?? (!!id && !!database),
  });
}

// ============================================================================
// Dashboard Queries
// ============================================================================

export function useDashboardOverview() {
  return useQuery({
    queryKey: datalakeKeys.overview(),
    queryFn: datalakeApi.getDashboardOverview,
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useDashboardHealth() {
  return useQuery({
    queryKey: datalakeKeys.health(),
    queryFn: datalakeApi.getDashboardHealth,
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useVolumeTrends(period = '7d') {
  return useQuery({
    queryKey: datalakeKeys.volumeTrends(period),
    queryFn: () => datalakeApi.getVolumeTrends(period),
    staleTime: 60000,
  });
}

export function useQueryPerformance(sourceId?: string) {
  return useQuery({
    queryKey: datalakeKeys.queryPerformance(sourceId),
    queryFn: () => datalakeApi.getQueryPerformance(sourceId),
    staleTime: 30000,
  });
}

export function useDataFlow() {
  return useQuery({
    queryKey: datalakeKeys.dataFlow(),
    queryFn: datalakeApi.getDataFlow,
    staleTime: 60000,
  });
}
