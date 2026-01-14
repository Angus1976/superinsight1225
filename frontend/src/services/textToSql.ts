/**
 * Text-to-SQL Service
 * 
 * Provides API client functions for Text-to-SQL configuration,
 * method switching, plugin management, and SQL generation.
 */

import apiClient from './api/client';

// ==================== Types ====================

export type MethodType = 'template' | 'llm' | 'hybrid' | 'third_party';
export type ConnectionType = 'rest_api' | 'grpc' | 'local_sdk';

export interface SQLGenerationResult {
  sql: string;
  method_used: string;
  confidence: number;
  execution_time_ms: number;
  metadata: Record<string, unknown>;
}

export interface MethodInfo {
  name: string;
  type: MethodType;
  description: string;
  supported_db_types: string[];
  is_available: boolean;
  is_enabled: boolean;
  config?: Record<string, unknown>;
  statistics?: Record<string, unknown>;
}

export interface PluginInfo {
  name: string;
  version: string;
  description: string;
  connection_type: ConnectionType;
  supported_db_types: string[];
  is_healthy: boolean;
  is_enabled: boolean;
}

export interface PluginConfig {
  name: string;
  connection_type: ConnectionType;
  endpoint?: string;
  api_key?: string;
  timeout: number;
  enabled: boolean;
  extra_config: Record<string, unknown>;
}

export interface TextToSQLConfig {
  default_method: MethodType;
  auto_select_enabled: boolean;
  fallback_enabled: boolean;
  template_config: Record<string, unknown>;
  llm_config: Record<string, unknown>;
  hybrid_config: Record<string, unknown>;
}

export interface GenerateRequest {
  query: string;
  method?: MethodType;
  db_type?: string;
  tool_name?: string;
  include_metadata?: boolean;
}

export interface GenerateResponse {
  success: boolean;
  sql: string;
  method_used: string;
  confidence: number;
  execution_time_ms: number;
  metadata: Record<string, unknown>;
}

export interface TestGenerateRequest {
  query: string;
  method?: MethodType;
  db_type?: string;
}

export interface ConfigUpdateRequest {
  default_method?: MethodType;
  auto_select_enabled?: boolean;
  fallback_enabled?: boolean;
  template_config?: Record<string, unknown>;
  llm_config?: Record<string, unknown>;
  hybrid_config?: Record<string, unknown>;
}

export interface PluginHealthStatus {
  [pluginName: string]: boolean;
}

export interface SwitcherStatistics {
  total_calls: number;
  method_calls: Record<string, number>;
  current_method: string;
  average_switch_time_ms: number;
  max_switch_time_ms: number;
  last_switch_time: string | null;
  config: {
    default_method: string;
    auto_select_enabled: boolean;
    fallback_enabled: boolean;
  };
}

// ==================== API Functions ====================

const BASE_URL = '/api/v1/text-to-sql';

/**
 * Generate SQL from natural language query
 */
export async function generateSQL(request: GenerateRequest): Promise<GenerateResponse> {
  const response = await apiClient.post<GenerateResponse>(`${BASE_URL}/methods/generate`, request);
  return response.data;
}

/**
 * Test SQL generation without persisting
 */
export async function testGenerate(request: TestGenerateRequest): Promise<GenerateResponse> {
  const response = await apiClient.post<GenerateResponse>(`${BASE_URL}/methods/test`, request);
  return response.data;
}

/**
 * List all available methods
 */
export async function getMethods(): Promise<MethodInfo[]> {
  const response = await apiClient.get<MethodInfo[]>(`${BASE_URL}/methods`);
  return response.data;
}

/**
 * Switch the default method
 */
export async function switchMethod(method: MethodType): Promise<{ success: boolean; new_method: string; switch_time_ms: number }> {
  const response = await apiClient.post<{ success: boolean; new_method: string; switch_time_ms: number }>(
    `${BASE_URL}/methods/switch`,
    null,
    { params: { method } }
  );
  return response.data;
}

/**
 * Get current default method
 */
export async function getCurrentMethod(): Promise<{ method: string; description: string }> {
  const response = await apiClient.get<{ method: string; description: string }>(`${BASE_URL}/methods/current`);
  return response.data;
}

/**
 * Get Text-to-SQL configuration
 */
export async function getConfig(): Promise<{ success: boolean; config: TextToSQLConfig }> {
  const response = await apiClient.get<{ success: boolean; config: TextToSQLConfig }>(`${BASE_URL}/config`);
  return response.data;
}

/**
 * Update Text-to-SQL configuration
 */
export async function updateConfig(request: ConfigUpdateRequest): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.put<{ success: boolean; message: string }>(`${BASE_URL}/config`, request);
  return response.data;
}

/**
 * Get switcher statistics
 */
export async function getStatistics(): Promise<{ success: boolean; statistics: SwitcherStatistics }> {
  const response = await apiClient.get<{ success: boolean; statistics: SwitcherStatistics }>(`${BASE_URL}/statistics`);
  return response.data;
}

// ==================== Plugin Management ====================

/**
 * List all registered plugins
 */
export async function getPlugins(): Promise<PluginInfo[]> {
  const response = await apiClient.get<PluginInfo[]>(`${BASE_URL}/plugins`);
  return response.data;
}

/**
 * Register a new plugin
 */
export async function registerPlugin(config: PluginConfig): Promise<PluginInfo> {
  const response = await apiClient.post<PluginInfo>(`${BASE_URL}/plugins`, config);
  return response.data;
}

/**
 * Update plugin configuration
 */
export async function updatePlugin(name: string, config: PluginConfig): Promise<PluginInfo> {
  const response = await apiClient.put<PluginInfo>(`${BASE_URL}/plugins/${name}`, config);
  return response.data;
}

/**
 * Unregister a plugin
 */
export async function unregisterPlugin(name: string): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.delete<{ success: boolean; message: string }>(`${BASE_URL}/plugins/${name}`);
  return response.data;
}

/**
 * Enable a plugin
 */
export async function enablePlugin(name: string): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post<{ success: boolean; message: string }>(`${BASE_URL}/plugins/${name}/enable`);
  return response.data;
}

/**
 * Disable a plugin
 */
export async function disablePlugin(name: string): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post<{ success: boolean; message: string }>(`${BASE_URL}/plugins/${name}/disable`);
  return response.data;
}

/**
 * Check health of all plugins
 */
export async function getPluginsHealth(): Promise<{ success: boolean; health: PluginHealthStatus; summary: { total: number; healthy: number; unhealthy: number } }> {
  const response = await apiClient.get<{ success: boolean; health: PluginHealthStatus; summary: { total: number; healthy: number; unhealthy: number } }>(`${BASE_URL}/plugins/health`);
  return response.data;
}

/**
 * Check health of a specific plugin
 */
export async function getPluginHealth(name: string): Promise<{ success: boolean; plugin: string; healthy: boolean }> {
  const response = await apiClient.get<{ success: boolean; plugin: string; healthy: boolean }>(`${BASE_URL}/plugins/${name}/health`);
  return response.data;
}

// ==================== Helper Functions ====================

/**
 * Get display name for method type
 */
export function getMethodDisplayName(method: MethodType): string {
  const names: Record<MethodType, string> = {
    template: '模板填充',
    llm: 'LLM 生成',
    hybrid: '混合方法',
    third_party: '第三方工具',
  };
  return names[method] || method;
}

/**
 * Get description for method type
 */
export function getMethodDescription(method: MethodType): string {
  const descriptions: Record<MethodType, string> = {
    template: '基于预定义模板的SQL生成，适用于结构化查询，速度快、稳定性高',
    llm: '基于大语言模型的SQL生成，适用于复杂自然语言查询，灵活性强',
    hybrid: '混合方法：模板优先，LLM回退，结合两者优势',
    third_party: '使用第三方专业Text-to-SQL工具生成',
  };
  return descriptions[method] || '';
}

/**
 * Get connection type display name
 */
export function getConnectionTypeDisplayName(type: ConnectionType): string {
  const names: Record<ConnectionType, string> = {
    rest_api: 'REST API',
    grpc: 'gRPC',
    local_sdk: '本地 SDK',
  };
  return names[type] || type;
}

// ==================== Service Object ====================

export const textToSqlService = {
  generateSQL,
  testGenerate,
  getMethods,
  switchMethod,
  getCurrentMethod,
  getConfig,
  updateConfig,
  getStatistics,
  getPlugins,
  registerPlugin,
  updatePlugin,
  unregisterPlugin,
  enablePlugin,
  disablePlugin,
  getPluginsHealth,
  getPluginHealth,
};

export default textToSqlService;
