// Billing data hooks
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { billingService } from '@/services/billing';
import type {
  BillingListParams,
  EnhancedReportRequest,
  BillingRuleVersionRequest,
} from '@/types/billing';

// Query key factory for billing
export const billingKeys = {
  all: ['billing'] as const,
  lists: () => [...billingKeys.all, 'list'] as const,
  list: (tenantId: string, params?: BillingListParams) => [...billingKeys.lists(), tenantId, params] as const,
  details: () => [...billingKeys.all, 'detail'] as const,
  detail: (tenantId: string, id: string) => [...billingKeys.details(), tenantId, id] as const,
  analysis: (tenantId: string) => [...billingKeys.all, 'analysis', tenantId] as const,
  ranking: (tenantId: string, period?: string) => [...billingKeys.all, 'ranking', tenantId, period] as const,
  workHours: (tenantId: string, startDate: string, endDate: string) =>
    [...billingKeys.all, 'workHours', tenantId, startDate, endDate] as const,
  projectBreakdown: (tenantId: string, startDate: string, endDate: string) =>
    [...billingKeys.all, 'projectBreakdown', tenantId, startDate, endDate] as const,
  departmentAllocation: (tenantId: string, startDate: string, endDate: string) =>
    [...billingKeys.all, 'departmentAllocation', tenantId, startDate, endDate] as const,
  costTrends: (tenantId: string, days: number) => [...billingKeys.all, 'costTrends', tenantId, days] as const,
  userProductivity: (tenantId: string, days: number) => [...billingKeys.all, 'userProductivity', tenantId, days] as const,
  costForecast: (tenantId: string, targetMonth: string) => [...billingKeys.all, 'costForecast', tenantId, targetMonth] as const,
  ruleHistory: (tenantId: string) => [...billingKeys.all, 'ruleHistory', tenantId] as const,
};

// Hook for billing records list
export function useBillingList(tenantId: string, params?: BillingListParams) {
  return useQuery({
    queryKey: billingKeys.list(tenantId, params),
    queryFn: () => billingService.getList(tenantId, params),
    staleTime: 30000,
    enabled: !!tenantId,
  });
}

// Hook for billing record detail
export function useBillingDetail(tenantId: string, id: string) {
  return useQuery({
    queryKey: billingKeys.detail(tenantId, id),
    queryFn: () => billingService.getById(tenantId, id),
    enabled: !!tenantId && !!id,
  });
}

// Hook for billing analysis
export function useBillingAnalysis(tenantId: string) {
  return useQuery({
    queryKey: billingKeys.analysis(tenantId),
    queryFn: () => billingService.getAnalysis(tenantId),
    staleTime: 60000,
    enabled: !!tenantId,
  });
}

// Hook for work hours ranking
export function useWorkHoursRanking(tenantId: string, period: 'week' | 'month' | 'quarter' = 'month') {
  return useQuery({
    queryKey: billingKeys.ranking(tenantId, period),
    queryFn: () => billingService.getWorkHoursRanking(tenantId),
    staleTime: 60000,
    refetchInterval: 300000, // Refresh every 5 minutes
    enabled: !!tenantId,
  });
}

// Hook for work hours statistics
export function useWorkHoursStatistics(tenantId: string, startDate: string, endDate: string) {
  return useQuery({
    queryKey: billingKeys.workHours(tenantId, startDate, endDate),
    queryFn: () => billingService.getWorkHoursStatistics(tenantId, startDate, endDate),
    staleTime: 60000,
    enabled: !!tenantId && !!startDate && !!endDate,
  });
}

// Hook for project cost breakdown
export function useProjectBreakdown(tenantId: string, startDate: string, endDate: string) {
  return useQuery({
    queryKey: billingKeys.projectBreakdown(tenantId, startDate, endDate),
    queryFn: () => billingService.getProjectBreakdown(tenantId, startDate, endDate),
    staleTime: 60000,
    enabled: !!tenantId && !!startDate && !!endDate,
  });
}

// Hook for department cost allocation
export function useDepartmentAllocation(tenantId: string, startDate: string, endDate: string) {
  return useQuery({
    queryKey: billingKeys.departmentAllocation(tenantId, startDate, endDate),
    queryFn: () => billingService.getDepartmentAllocation(tenantId, startDate, endDate),
    staleTime: 60000,
    enabled: !!tenantId && !!startDate && !!endDate,
  });
}

// Hook for cost trends
export function useCostTrends(tenantId: string, days: number = 30) {
  return useQuery({
    queryKey: billingKeys.costTrends(tenantId, days),
    queryFn: () => billingService.getCostTrends(tenantId, days),
    staleTime: 60000,
    enabled: !!tenantId,
  });
}

// Hook for user productivity
export function useUserProductivity(tenantId: string, days: number = 30) {
  return useQuery({
    queryKey: billingKeys.userProductivity(tenantId, days),
    queryFn: () => billingService.getUserProductivity(tenantId, days),
    staleTime: 60000,
    enabled: !!tenantId,
  });
}

// Hook for cost forecast
export function useCostForecast(tenantId: string, targetMonth: string) {
  return useQuery({
    queryKey: billingKeys.costForecast(tenantId, targetMonth),
    queryFn: () => billingService.getCostForecast(tenantId, targetMonth),
    staleTime: 300000, // 5 minutes
    enabled: !!tenantId && !!targetMonth,
  });
}

// Hook for rule history
export function useRuleHistory(tenantId: string) {
  return useQuery({
    queryKey: billingKeys.ruleHistory(tenantId),
    queryFn: () => billingService.getRuleHistory(tenantId),
    staleTime: 60000,
    enabled: !!tenantId,
  });
}

// Mutation for generating enhanced report
export function useGenerateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: EnhancedReportRequest) => billingService.getEnhancedReport(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: billingKeys.all });
    },
  });
}

// Mutation for creating rule version
export function useCreateRuleVersion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: BillingRuleVersionRequest) => billingService.createRuleVersion(request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: billingKeys.ruleHistory(variables.tenant_id) });
    },
  });
}

// Mutation for approving rule version
export function useApproveRuleVersion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ tenantId, version, approvedBy }: { tenantId: string; version: number; approvedBy: string }) =>
      billingService.approveRuleVersion(tenantId, version, approvedBy),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: billingKeys.ruleHistory(variables.tenantId) });
    },
  });
}

// Mutation for exporting to Excel
export function useExportBilling() {
  return useMutation({
    mutationFn: ({ tenantId, params }: { tenantId: string; params?: BillingListParams }) =>
      billingService.exportToExcel(tenantId, params),
    onSuccess: (blob) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `billing-export-${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });
}

// Composite hook for billing dashboard
export function useBillingDashboard(tenantId: string) {
  const listQuery = useBillingList(tenantId);
  const analysisQuery = useBillingAnalysis(tenantId);
  const rankingQuery = useWorkHoursRanking(tenantId);
  const trendsQuery = useCostTrends(tenantId);

  return {
    records: listQuery.data,
    analysis: analysisQuery.data,
    ranking: rankingQuery.data,
    trends: trendsQuery.data,
    isLoading: listQuery.isLoading || analysisQuery.isLoading || rankingQuery.isLoading || trendsQuery.isLoading,
    error: listQuery.error || analysisQuery.error || rankingQuery.error || trendsQuery.error,
    refetch: () => {
      listQuery.refetch();
      analysisQuery.refetch();
      rankingQuery.refetch();
      trendsQuery.refetch();
    },
  };
}
