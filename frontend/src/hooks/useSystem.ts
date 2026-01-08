// System management hooks
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { message } from 'antd';
import { systemService } from '@/services';
import type {
  CreateTenantRequest,
  UpdateTenantRequest,
  SystemMetricsQuery,
  TenantUsageQuery,
  SystemConfig,
} from '@/types';

// Tenant management hooks
export const useTenants = () => {
  return useQuery({
    queryKey: ['tenants'],
    queryFn: systemService.getTenants,
  });
};

export const useTenant = (id: string) => {
  return useQuery({
    queryKey: ['tenant', id],
    queryFn: () => systemService.getTenant(id),
    enabled: !!id,
  });
};

export const useCreateTenant = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateTenantRequest) => systemService.createTenant(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      message.success('Tenant created successfully');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || 'Failed to create tenant');
    },
  });
};

export const useUpdateTenant = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTenantRequest }) =>
      systemService.updateTenant(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      queryClient.invalidateQueries({ queryKey: ['tenant', id] });
      message.success('Tenant updated successfully');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || 'Failed to update tenant');
    },
  });
};

export const useDeleteTenant = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) => systemService.deleteTenant(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      message.success('Tenant deleted successfully');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || 'Failed to delete tenant');
    },
  });
};

export const useTenantUsage = (query: TenantUsageQuery) => {
  return useQuery({
    queryKey: ['tenant-usage', query],
    queryFn: () => systemService.getTenantUsage(query),
  });
};

// System monitoring hooks
export const useSystemMetrics = (query: SystemMetricsQuery) => {
  return useQuery({
    queryKey: ['system-metrics', query],
    queryFn: () => systemService.getSystemMetrics(query),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
};

export const useSystemHealth = () => {
  return useQuery({
    queryKey: ['system-health'],
    queryFn: systemService.getSystemHealth,
    refetchInterval: 10000, // Refresh every 10 seconds
  });
};

export const useSystemAlerts = (params?: {
  type?: string;
  status?: string;
  limit?: number;
}) => {
  return useQuery({
    queryKey: ['system-alerts', params],
    queryFn: () => systemService.getSystemAlerts(params),
    refetchInterval: 15000, // Refresh every 15 seconds
  });
};

export const useAcknowledgeAlert = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) => systemService.acknowledgeAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-alerts'] });
      message.success('Alert acknowledged');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || 'Failed to acknowledge alert');
    },
  });
};

export const useResolveAlert = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) => systemService.resolveAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-alerts'] });
      message.success('Alert resolved');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || 'Failed to resolve alert');
    },
  });
};

// Audit logs hooks
export const useAuditLogs = (params?: {
  tenant_id?: string;
  user_id?: string;
  action?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}) => {
  return useQuery({
    queryKey: ['audit-logs', params],
    queryFn: () => systemService.getAuditLogs(params),
  });
};

// System configuration hooks
export const useSystemConfig = () => {
  return useQuery({
    queryKey: ['system-config'],
    queryFn: systemService.getSystemConfig,
  });
};

export const useUpdateSystemConfig = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (config: Partial<SystemConfig>) =>
      systemService.updateSystemConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-config'] });
      message.success('System configuration updated successfully');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || 'Failed to update configuration');
    },
  });
};

// Maintenance operations hooks
export const useMaintenanceMode = () => {
  const queryClient = useQueryClient();
  
  const enableMaintenance = useMutation({
    mutationFn: (message?: string) => systemService.enableMaintenanceMode(message),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-config'] });
      message.success('Maintenance mode enabled');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || 'Failed to enable maintenance mode');
    },
  });

  const disableMaintenance = useMutation({
    mutationFn: () => systemService.disableMaintenanceMode(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-config'] });
      message.success('Maintenance mode disabled');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || 'Failed to disable maintenance mode');
    },
  });

  return { enableMaintenance, disableMaintenance };
};

export const useRestartService = () => {
  return useMutation({
    mutationFn: (serviceName: string) => systemService.restartService(serviceName),
    onSuccess: () => {
      message.success('Service restart initiated');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || 'Failed to restart service');
    },
  });
};

export const useSystemLogs = (params?: {
  service?: string;
  level?: string;
  start_time?: string;
  end_time?: string;
  limit?: number;
}) => {
  return useQuery({
    queryKey: ['system-logs', params],
    queryFn: () => systemService.getSystemLogs(params),
  });
};