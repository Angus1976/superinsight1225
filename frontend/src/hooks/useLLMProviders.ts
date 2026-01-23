/**
 * LLM Providers Hook
 * 
 * Custom hooks for managing LLM provider configurations using TanStack Query.
 * Provides data fetching, caching, and mutation operations for LLM providers.
 * 
 * **Requirements: 6.1, 6.3**
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  llmService,
  llmProviderService,
  type LLMConfig,
  type HealthStatus,
  type MethodInfo,
  type ProviderConfig,
  type ProviderConfigCreate,
  type ProviderConfigUpdate,
} from '@/services/llm';
import {
  adminApi,
  type LLMConfigResponse,
  type LLMConfigCreate,
  type LLMConfigUpdate,
  type ConnectionTestResult,
} from '@/services/adminApi';
import { useAuthStore } from '@/stores/authStore';

// Query keys for cache management
export const LLM_QUERY_KEYS = {
  config: ['llm', 'config'] as const,
  providers: ['llm', 'providers'] as const,
  provider: (id: string) => ['llm', 'providers', id] as const,
  health: ['llm', 'health'] as const,
  methods: ['llm', 'methods'] as const,
  adminConfigs: ['admin', 'llm-configs'] as const,
  adminConfig: (id: string) => ['admin', 'llm-configs', id] as const,
};

/**
 * Hook for fetching LLM configuration
 */
export function useLLMConfig(tenantId?: string) {
  return useQuery({
    queryKey: [...LLM_QUERY_KEYS.config, tenantId],
    queryFn: () => llmService.getConfig(tenantId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook for fetching LLM methods
 */
export function useLLMMethods() {
  return useQuery({
    queryKey: LLM_QUERY_KEYS.methods,
    queryFn: () => llmService.getMethods(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook for fetching LLM health status
 */
export function useLLMHealth() {
  return useQuery({
    queryKey: LLM_QUERY_KEYS.health,
    queryFn: () => llmService.getHealth(),
    refetchInterval: 60 * 1000, // Refetch every 60 seconds
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook for managing LLM providers (using admin API)
 * This is the main hook for CRUD operations on LLM configurations
 */
export function useLLMProviders(tenantId?: string, activeOnly = false) {
  const { t } = useTranslation(['admin', 'common']);
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  // Fetch providers list
  const providersQuery = useQuery({
    queryKey: [...LLM_QUERY_KEYS.adminConfigs, tenantId, activeOnly],
    queryFn: () => adminApi.listLLMConfigs(tenantId, activeOnly),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Create provider mutation
  const createMutation = useMutation({
    mutationFn: (config: LLMConfigCreate) =>
      adminApi.createLLMConfig(config, user?.id || '', user?.username || '', tenantId),
    onSuccess: () => {
      message.success(t('llm.configSaveSuccess'));
      queryClient.invalidateQueries({ queryKey: LLM_QUERY_KEYS.adminConfigs });
    },
    onError: (error: Error) => {
      message.error(`${t('llm.configSaveFailed')}: ${error.message}`);
    },
  });

  // Update provider mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, config }: { id: string; config: LLMConfigUpdate }) =>
      adminApi.updateLLMConfig(id, config, user?.id || '', user?.username || '', tenantId),
    onSuccess: () => {
      message.success(t('llm.configSaveSuccess'));
      queryClient.invalidateQueries({ queryKey: LLM_QUERY_KEYS.adminConfigs });
    },
    onError: (error: Error) => {
      message.error(`${t('llm.configSaveFailed')}: ${error.message}`);
    },
  });

  // Delete provider mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      adminApi.deleteLLMConfig(id, user?.id || '', user?.username || '', tenantId),
    onSuccess: () => {
      message.success(t('common:deleteSuccess'));
      queryClient.invalidateQueries({ queryKey: LLM_QUERY_KEYS.adminConfigs });
    },
    onError: (error: Error) => {
      message.error(`${t('common:deleteFailed')}: ${error.message}`);
    },
  });

  // Test connection mutation
  const testConnectionMutation = useMutation({
    mutationFn: (id: string) => adminApi.testLLMConnection(id),
    onSuccess: (result, id) => {
      if (result.success) {
        message.success(`${t('llm.status.connectionSuccess')} (${result.latency_ms}ms)`);
      } else {
        message.error(`${t('llm.status.connectionFailed')}: ${result.error_message}`);
      }
    },
    onError: (error: Error) => {
      message.error(`${t('llm.status.connectionFailed')}: ${error.message}`);
    },
  });

  return {
    // Data
    providers: providersQuery.data || [],
    isLoading: providersQuery.isLoading,
    isError: providersQuery.isError,
    error: providersQuery.error,

    // Refetch
    refetch: providersQuery.refetch,

    // Mutations
    createProvider: createMutation.mutate,
    createProviderAsync: createMutation.mutateAsync,
    isCreating: createMutation.isPending,

    updateProvider: (id: string, config: LLMConfigUpdate) =>
      updateMutation.mutate({ id, config }),
    updateProviderAsync: (id: string, config: LLMConfigUpdate) =>
      updateMutation.mutateAsync({ id, config }),
    isUpdating: updateMutation.isPending,

    deleteProvider: deleteMutation.mutate,
    deleteProviderAsync: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,

    testConnection: testConnectionMutation.mutate,
    testConnectionAsync: testConnectionMutation.mutateAsync,
    isTesting: testConnectionMutation.isPending,
  };
}

/**
 * Hook for fetching a single LLM provider
 */
export function useLLMProvider(id: string, tenantId?: string) {
  return useQuery({
    queryKey: [...LLM_QUERY_KEYS.adminConfig(id), tenantId],
    queryFn: () => adminApi.getLLMConfig(id, tenantId),
    enabled: !!id,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Hook for testing LLM connection
 */
export function useTestLLMConnection() {
  const { t } = useTranslation(['admin', 'common']);

  return useMutation({
    mutationFn: (configId: string) => adminApi.testLLMConnection(configId),
    onSuccess: (result) => {
      if (result.success) {
        message.success(`${t('llm.status.connectionSuccess')} (${result.latency_ms}ms)`);
      } else {
        message.error(`${t('llm.status.connectionFailed')}: ${result.error_message}`);
      }
    },
    onError: (error: Error) => {
      message.error(`${t('llm.status.connectionFailed')}: ${error.message}`);
    },
  });
}

/**
 * Hook for updating LLM configuration
 */
export function useUpdateLLMConfig(tenantId?: string) {
  const { t } = useTranslation(['admin', 'common']);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (config: LLMConfig) => llmService.updateConfig(config, tenantId),
    onSuccess: () => {
      message.success(t('llm.configSaveSuccess'));
      queryClient.invalidateQueries({ queryKey: LLM_QUERY_KEYS.config });
      queryClient.invalidateQueries({ queryKey: LLM_QUERY_KEYS.health });
    },
    onError: (error: Error) => {
      message.error(`${t('llm.configSaveFailed')}: ${error.message}`);
    },
  });
}

/**
 * Hook for hot reloading LLM configuration
 */
export function useHotReloadLLMConfig(tenantId?: string) {
  const { t } = useTranslation(['admin', 'common']);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => llmService.hotReload(tenantId),
    onSuccess: () => {
      message.success(t('llm.hotReloadSuccess'));
      queryClient.invalidateQueries({ queryKey: LLM_QUERY_KEYS.config });
      queryClient.invalidateQueries({ queryKey: LLM_QUERY_KEYS.health });
    },
    onError: (error: Error) => {
      message.error(`${t('llm.hotReloadFailed')}: ${error.message}`);
    },
  });
}

/**
 * Hook for switching LLM method
 */
export function useSwitchLLMMethod() {
  const { t } = useTranslation(['admin', 'common']);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (method: string) => llmService.switchMethod(method as Parameters<typeof llmService.switchMethod>[0]),
    onSuccess: () => {
      message.success(t('llm.switchMethodSuccess', { defaultValue: '切换方法成功' }));
      queryClient.invalidateQueries({ queryKey: LLM_QUERY_KEYS.config });
    },
    onError: (error: Error) => {
      message.error(`${t('llm.switchMethodFailed', { defaultValue: '切换方法失败' })}: ${error.message}`);
    },
  });
}

/**
 * Hook for LLM text generation
 */
export function useLLMGenerate() {
  const { t } = useTranslation(['admin', 'common']);

  return useMutation({
    mutationFn: (request: Parameters<typeof llmService.generate>[0]) =>
      llmService.generate(request),
    onError: (error: Error) => {
      message.error(`${t('llm.generateFailed', { defaultValue: '生成失败' })}: ${error.message}`);
    },
  });
}

/**
 * Combined hook for LLM configuration page
 * Provides all data and operations needed for the LLM config page
 */
export function useLLMConfigPage(tenantId?: string) {
  const configQuery = useLLMConfig(tenantId);
  const methodsQuery = useLLMMethods();
  const healthQuery = useLLMHealth();
  const updateConfig = useUpdateLLMConfig(tenantId);
  const hotReload = useHotReloadLLMConfig(tenantId);

  return {
    // Data
    config: configQuery.data,
    methods: methodsQuery.data || [],
    health: healthQuery.data || {},

    // Loading states
    isLoading: configQuery.isLoading || methodsQuery.isLoading,
    isHealthLoading: healthQuery.isLoading,

    // Error states
    isError: configQuery.isError || methodsQuery.isError,
    error: configQuery.error || methodsQuery.error,

    // Refetch functions
    refetchConfig: configQuery.refetch,
    refetchHealth: healthQuery.refetch,
    refetchAll: () => {
      configQuery.refetch();
      methodsQuery.refetch();
      healthQuery.refetch();
    },

    // Mutations
    updateConfig: updateConfig.mutate,
    updateConfigAsync: updateConfig.mutateAsync,
    isUpdating: updateConfig.isPending,

    hotReload: hotReload.mutate,
    hotReloadAsync: hotReload.mutateAsync,
    isReloading: hotReload.isPending,
  };
}

// Export types
export type {
  LLMConfig,
  HealthStatus,
  MethodInfo,
  ProviderConfig,
  ProviderConfigCreate,
  ProviderConfigUpdate,
  LLMConfigResponse,
  LLMConfigCreate,
  LLMConfigUpdate,
  ConnectionTestResult,
};
