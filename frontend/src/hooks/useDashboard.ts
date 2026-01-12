// Dashboard data hook with multi-tenant support
import { useQuery } from '@tanstack/react-query';
import { dashboardService } from '@/services/dashboard';
import { useAuthStore } from '@/stores/authStore';
import { useMemo } from 'react';

interface UseDashboardOptions {
  tenantId?: string;
  workspaceId?: string;
  refreshInterval?: number;
  enabled?: boolean;
}

export function useDashboard(options: UseDashboardOptions = {}) {
  const { currentTenant, currentWorkspace } = useAuthStore();
  
  // Use provided IDs or fall back to current context
  const tenantId = options.tenantId || currentTenant?.id;
  const workspaceId = options.workspaceId || currentWorkspace?.id;
  const refreshInterval = options.refreshInterval ?? 60000;
  const enabled = options.enabled ?? true;

  // Build query key with tenant/workspace context for proper cache isolation
  const queryKeyBase = useMemo(() => 
    ['dashboard', tenantId, workspaceId].filter(Boolean),
    [tenantId, workspaceId]
  );

  const summaryQuery = useQuery({
    queryKey: [...queryKeyBase, 'summary'],
    queryFn: () => dashboardService.getSummary(tenantId, workspaceId),
    refetchInterval: refreshInterval,
    staleTime: 30000,
    enabled,
  });

  const annotationEfficiencyQuery = useQuery({
    queryKey: [...queryKeyBase, 'annotation-efficiency'],
    queryFn: () => dashboardService.getAnnotationEfficiency(24, tenantId, workspaceId),
    refetchInterval: refreshInterval,
    staleTime: 30000,
    enabled,
  });

  const userActivityQuery = useQuery({
    queryKey: [...queryKeyBase, 'user-activity'],
    queryFn: () => dashboardService.getUserActivity(24, tenantId, workspaceId),
    refetchInterval: refreshInterval,
    staleTime: 30000,
    enabled,
  });

  return {
    summary: summaryQuery.data,
    annotationEfficiency: annotationEfficiencyQuery.data,
    userActivity: userActivityQuery.data,
    isLoading: summaryQuery.isLoading || annotationEfficiencyQuery.isLoading || userActivityQuery.isLoading,
    isFetching: summaryQuery.isFetching || annotationEfficiencyQuery.isFetching || userActivityQuery.isFetching,
    error: summaryQuery.error || annotationEfficiencyQuery.error || userActivityQuery.error,
    refetch: () => {
      summaryQuery.refetch();
      annotationEfficiencyQuery.refetch();
      userActivityQuery.refetch();
    },
    // Context info for display
    tenantId,
    workspaceId,
  };
}
