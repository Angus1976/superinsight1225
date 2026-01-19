// Billing API service
import apiClient from './api/client';
import { API_ENDPOINTS } from '@/constants';
import type {
  BillingListParams,
  BillingListResponse,
  BillingRecord,
  BillingAnalysis,
  WorkHoursRanking,
  WorkHoursStatistics,
  ProjectCostBreakdown,
  DepartmentCostAllocation,
  BillingRuleVersion,
  EnhancedBillingReport,
  EnhancedReportRequest,
  BillingRuleVersionRequest,
  ExcelExportData,
  BillingStatus,
  BillingItem,
} from '@/types/billing';

const BILLING_BASE = '/api/billing';

// Backend billing record format (annotation work records)
interface BackendBillingRecord {
  id: string;
  tenant_id: string;
  user_id: string;
  task_id: string | null;
  annotation_count: number;
  time_spent: number;
  cost: number;
  billing_date: string;
  created_at: string;
}

// Transform backend records to frontend BillingRecord format
function transformBackendRecords(
  records: BackendBillingRecord[],
  tenantId: string
): BillingRecord[] {
  if (!records || records.length === 0) {
    return [];
  }

  // Group records by month to create billing periods
  const recordsByMonth: Record<string, BackendBillingRecord[]> = {};
  
  for (const record of records) {
    const date = new Date(record.billing_date);
    const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    if (!recordsByMonth[monthKey]) {
      recordsByMonth[monthKey] = [];
    }
    recordsByMonth[monthKey].push(record);
  }

  // Create BillingRecord for each month
  const billingRecords: BillingRecord[] = [];
  
  for (const [monthKey, monthRecords] of Object.entries(recordsByMonth)) {
    const [year, month] = monthKey.split('-').map(Number);
    const periodStart = new Date(year, month - 1, 1);
    const periodEnd = new Date(year, month, 0); // Last day of month
    
    // Calculate totals
    const totalAmount = monthRecords.reduce((sum, r) => sum + r.cost, 0);
    const totalAnnotations = monthRecords.reduce((sum, r) => sum + r.annotation_count, 0);
    const totalTimeSpent = monthRecords.reduce((sum, r) => sum + r.time_spent, 0);
    
    // Determine status based on date
    const now = new Date();
    const dueDate = new Date(year, month, 15); // Due on 15th of next month
    let status: BillingStatus = 'pending';
    
    if (periodEnd < new Date(now.getFullYear(), now.getMonth() - 1, 1)) {
      // More than a month old, assume paid
      status = 'paid';
    } else if (dueDate < now && status === 'pending') {
      status = 'overdue';
    }
    
    // Create billing items from records
    const items: BillingItem[] = [];
    
    // Group by user for item breakdown
    const userTotals: Record<string, { annotations: number; time: number; cost: number }> = {};
    for (const record of monthRecords) {
      if (!userTotals[record.user_id]) {
        userTotals[record.user_id] = { annotations: 0, time: 0, cost: 0 };
      }
      userTotals[record.user_id].annotations += record.annotation_count;
      userTotals[record.user_id].time += record.time_spent;
      userTotals[record.user_id].cost += record.cost;
    }
    
    // Create items for annotation work
    if (totalAnnotations > 0) {
      items.push({
        id: `${monthKey}-annotations`,
        description: `Annotation work (${Object.keys(userTotals).length} users)`,
        quantity: totalAnnotations,
        unit_price: totalAmount / totalAnnotations,
        amount: totalAmount,
        category: 'annotation',
      });
    }
    
    // Add time-based item if significant time spent
    if (totalTimeSpent > 3600) { // More than 1 hour
      const hours = Math.round(totalTimeSpent / 3600 * 10) / 10;
      items.push({
        id: `${monthKey}-time`,
        description: `Work hours (${hours}h total)`,
        quantity: hours,
        unit_price: 0, // Already included in annotation cost
        amount: 0,
        category: 'other',
      });
    }
    
    // If no items, add a placeholder
    if (items.length === 0) {
      items.push({
        id: `${monthKey}-empty`,
        description: 'No billing activity',
        quantity: 0,
        unit_price: 0,
        amount: 0,
        category: 'other',
      });
    }
    
    const billingRecord: BillingRecord = {
      id: `bill-${tenantId}-${monthKey}`,
      tenant_id: tenantId,
      period_start: periodStart.toISOString(),
      period_end: periodEnd.toISOString(),
      total_amount: Math.round(totalAmount * 100) / 100,
      status,
      items,
      created_at: monthRecords[0]?.created_at || new Date().toISOString(),
      due_date: dueDate.toISOString(),
      paid_at: status === 'paid' ? new Date(year, month, 10).toISOString() : undefined,
    };
    
    billingRecords.push(billingRecord);
  }
  
  // Sort by period_start descending (newest first)
  billingRecords.sort((a, b) => 
    new Date(b.period_start).getTime() - new Date(a.period_start).getTime()
  );
  
  return billingRecords;
}

export const billingService = {
  // Get billing records list
  async getList(tenantId: string, params: BillingListParams = {}): Promise<BillingListResponse> {
    const response = await apiClient.get<{
      tenant_id: string;
      record_count: number;
      records: BackendBillingRecord[];
    }>(
      API_ENDPOINTS.BILLING.RECORDS(tenantId),
      { params }
    );
    
    // Transform backend records to frontend format
    const transformedRecords = transformBackendRecords(
      response.data.records || [],
      tenantId
    );
    
    // Apply status filter if provided
    let filteredRecords = transformedRecords;
    if (params.status) {
      filteredRecords = transformedRecords.filter(r => r.status === params.status);
    }
    
    // Apply pagination
    const page = params.page || 1;
    const pageSize = params.page_size || 10;
    const startIndex = (page - 1) * pageSize;
    const paginatedRecords = filteredRecords.slice(startIndex, startIndex + pageSize);
    
    return {
      items: paginatedRecords,
      total: filteredRecords.length,
      page,
      page_size: pageSize,
    };
  },

  // Get single billing record
  async getById(tenantId: string, id: string): Promise<BillingRecord> {
    const response = await apiClient.get<BillingRecord>(
      `${API_ENDPOINTS.BILLING.RECORDS(tenantId)}/${id}`
    );
    return response.data;
  },

  // Get billing analysis
  async getAnalysis(tenantId: string): Promise<BillingAnalysis> {
    const response = await apiClient.get<{
      tenant_id: string;
      period: string;
      total_cost: number;
      total_annotations: number;
      total_time_spent: number;
      average_cost_per_annotation: number;
      average_cost_per_hour: number;
      top_users: Array<{ user_id: string; cost: number; annotations: number; time_spent: number }>;
      cost_trend: Array<{ date: string; cost: number; annotations: number }>;
    }>(
      API_ENDPOINTS.BILLING.ANALYSIS(tenantId)
    );
    // Transform backend response to frontend expected format
    const data = response.data;
    return {
      total_spending: data.total_cost || 0,
      average_monthly: data.average_cost_per_hour || 0,
      trend_percentage: 0, // Backend doesn't provide this directly
      by_category: [],
      monthly_trends: (data.cost_trend || []).map(t => ({
        month: t.date,
        amount: t.cost,
      })),
    };
  },

  // Get work hours ranking
  async getWorkHoursRanking(tenantId: string): Promise<WorkHoursRanking[]> {
    const response = await apiClient.get<WorkHoursRanking[]>(
      `${API_ENDPOINTS.BILLING.RECORDS(tenantId)}/ranking`
    );
    return response.data;
  },

  // Export billing data
  async exportToExcel(tenantId: string, params: BillingListParams = {}): Promise<Blob> {
    const response = await apiClient.get<Blob>(
      `${API_ENDPOINTS.BILLING.RECORDS(tenantId)}/export`,
      {
        params,
        responseType: 'blob',
      }
    );
    return response.data;
  },

  // ============================================================================
  // Enhanced Report Service APIs
  // ============================================================================

  // Generate enhanced billing report
  async getEnhancedReport(request: EnhancedReportRequest): Promise<EnhancedBillingReport> {
    const response = await apiClient.post<EnhancedBillingReport>(
      `${BILLING_BASE}/enhanced-report`,
      request
    );
    return response.data;
  },

  // Get work hours statistics
  async getWorkHoursStatistics(
    tenantId: string,
    startDate: string,
    endDate: string
  ): Promise<{ statistics: WorkHoursStatistics[]; user_count: number }> {
    const response = await apiClient.get<{ statistics: WorkHoursStatistics[]; user_count: number }>(
      `${BILLING_BASE}/work-hours/${tenantId}`,
      { params: { start_date: startDate, end_date: endDate } }
    );
    return response.data;
  },

  // Get project cost breakdown
  async getProjectBreakdown(
    tenantId: string,
    startDate: string,
    endDate: string
  ): Promise<{ breakdowns: ProjectCostBreakdown[]; total_cost: number }> {
    const response = await apiClient.get<{ breakdowns: ProjectCostBreakdown[]; total_cost: number }>(
      `${BILLING_BASE}/project-breakdown/${tenantId}`,
      { params: { start_date: startDate, end_date: endDate } }
    );
    return response.data;
  },

  // Get department cost allocation
  async getDepartmentAllocation(
    tenantId: string,
    startDate: string,
    endDate: string
  ): Promise<{ allocations: DepartmentCostAllocation[]; total_cost: number }> {
    const response = await apiClient.get<{ allocations: DepartmentCostAllocation[]; total_cost: number }>(
      `${BILLING_BASE}/department-allocation/${tenantId}`,
      { params: { start_date: startDate, end_date: endDate } }
    );
    return response.data;
  },

  // Create billing rule version
  async createRuleVersion(request: BillingRuleVersionRequest): Promise<{ rule: BillingRuleVersion }> {
    const response = await apiClient.post<{ rule: BillingRuleVersion }>(
      `${BILLING_BASE}/rules/versions`,
      request
    );
    return response.data;
  },

  // Approve billing rule version
  async approveRuleVersion(
    tenantId: string,
    version: number,
    approvedBy: string
  ): Promise<{ rule: BillingRuleVersion }> {
    const response = await apiClient.post<{ rule: BillingRuleVersion }>(
      `${BILLING_BASE}/rules/versions/${tenantId}/${version}/approve`,
      { approved_by: approvedBy }
    );
    return response.data;
  },

  // Get billing rule history
  async getRuleHistory(tenantId: string): Promise<{
    active_version: number | null;
    versions: BillingRuleVersion[];
  }> {
    const response = await apiClient.get<{
      active_version: number | null;
      versions: BillingRuleVersion[];
    }>(
      `${BILLING_BASE}/rules/versions/${tenantId}`
    );
    return response.data;
  },

  // Configure project mappings
  async configureProjectMappings(
    tenantId: string,
    mappings: Record<string, string>
  ): Promise<{ status: string }> {
    const response = await apiClient.post<{ status: string }>(
      `${BILLING_BASE}/mappings/projects`,
      { tenant_id: tenantId, mappings }
    );
    return response.data;
  },

  // Configure department mappings
  async configureDepartmentMappings(
    tenantId: string,
    projectMappings: Record<string, string>,
    userMappings: Record<string, string>
  ): Promise<{ status: string }> {
    const response = await apiClient.post<{ status: string }>(
      `${BILLING_BASE}/mappings/departments`,
      {
        tenant_id: tenantId,
        project_mappings: projectMappings,
        user_mappings: userMappings
      }
    );
    return response.data;
  },

  // Export to Excel format
  async getExcelExportData(
    tenantId: string,
    startDate: string,
    endDate: string,
    reportType: string = 'detailed'
  ): Promise<ExcelExportData> {
    const response = await apiClient.get<ExcelExportData>(
      `${BILLING_BASE}/export-excel/${tenantId}`,
      { params: { start_date: startDate, end_date: endDate, report_type: reportType } }
    );
    return response.data;
  },

  // Get cost trends
  async getCostTrends(tenantId: string, days: number = 30): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>(
      `${BILLING_BASE}/analytics/trends/${tenantId}`,
      { params: { days } }
    );
    return response.data;
  },

  // Get user productivity
  async getUserProductivity(tenantId: string, days: number = 30): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>(
      `${BILLING_BASE}/analytics/productivity/${tenantId}`,
      { params: { days } }
    );
    return response.data;
  },

  // Get cost forecast
  async getCostForecast(tenantId: string, targetMonth: string): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>(
      `${BILLING_BASE}/analytics/forecast/${tenantId}/${targetMonth}`
    );
    return response.data;
  },

  // Get optimization recommendations
  async getOptimizationRecommendations(tenantId: string, days: number = 30): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>(
      `${BILLING_BASE}/analytics/recommendations/${tenantId}`,
      { params: { days } }
    );
    return response.data;
  },
};
