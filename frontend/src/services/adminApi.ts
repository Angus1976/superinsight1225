/**
 * Admin Configuration API Service
 * 
 * Provides API client functions for admin configuration management including:
 * - Dashboard data
 * - LLM configuration
 * - Database connections
 * - Sync strategies
 * - SQL builder
 * - Configuration history
 * - Third-party tools
 */

import apiClient from './api/client';

// ==================== Types ====================

export type ConfigType = 'llm' | 'database' | 'sync_strategy' | 'third_party';
export type DatabaseType = 'postgresql' | 'mysql' | 'sqlite' | 'oracle' | 'sqlserver';
export type SyncMode = 'full' | 'incremental' | 'realtime';
export type LLMType = 'local_ollama' | 'openai' | 'qianwen' | 'zhipu' | 'hunyuan' | 'custom';
export type ThirdPartyToolType = 'text_to_sql' | 'ai_annotation' | 'data_processing' | 'custom';

// Validation
export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

export interface ValidationResult {
  is_valid: boolean;
  errors: ValidationError[];
  warnings: string[];
}

export interface ConnectionTestResult {
  success: boolean;
  latency_ms: number;
  error_message?: string;
  details?: Record<string, unknown>;
}

// Dashboard
export interface DashboardData {
  system_health: Record<string, string>;
  key_metrics: Record<string, number>;
  recent_alerts: Array<Record<string, unknown>>;
  quick_actions: Array<{ name: string; path: string }>;
  config_summary: Record<string, number>;
}

// LLM Configuration
export interface LLMConfigBase {
  llm_type: LLMType;
  model_name: string;
  api_endpoint?: string;
  api_key?: string;
  temperature: number;
  max_tokens: number;
  timeout_seconds: number;
  extra_config: Record<string, unknown>;
}

export interface LLMConfigCreate extends LLMConfigBase {
  name: string;
  description?: string;
  is_default?: boolean;
}

export interface LLMConfigUpdate {
  name?: string;
  description?: string;
  llm_type?: LLMType;
  model_name?: string;
  api_endpoint?: string;
  api_key?: string;
  temperature?: number;
  max_tokens?: number;
  timeout_seconds?: number;
  extra_config?: Record<string, unknown>;
  is_default?: boolean;
  is_active?: boolean;
}

export interface LLMConfigResponse extends LLMConfigBase {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  is_default: boolean;
  api_key_masked?: string;
  created_at: string;
  updated_at: string;
}

// Database Configuration
export interface DBConfigBase {
  db_type: DatabaseType;
  host: string;
  port: number;
  database: string;
  username: string;
  password?: string;
  is_readonly: boolean;
  ssl_enabled: boolean;
  extra_config: Record<string, unknown>;
}

export interface DBConfigCreate extends DBConfigBase {
  name: string;
  description?: string;
}

export interface DBConfigUpdate {
  name?: string;
  description?: string;
  db_type?: DatabaseType;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  is_readonly?: boolean;
  ssl_enabled?: boolean;
  extra_config?: Record<string, unknown>;
  is_active?: boolean;
}

export interface DBConfigResponse {
  id: string;
  name: string;
  description?: string;
  db_type: DatabaseType;
  host: string;
  port: number;
  database: string;
  username: string;
  password_masked?: string;
  is_readonly: boolean;
  ssl_enabled: boolean;
  extra_config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}


// Sync Strategy
export interface FilterCondition {
  field: string;
  operator: string;
  value: unknown;
}

export interface SyncStrategyBase {
  mode: SyncMode;
  incremental_field?: string;
  schedule?: string;
  filter_conditions: FilterCondition[];
  batch_size: number;
  enabled: boolean;
}

export interface SyncStrategyCreate extends SyncStrategyBase {
  db_config_id: string;
  name?: string;
}

export interface SyncStrategyUpdate {
  name?: string;
  mode?: SyncMode;
  incremental_field?: string;
  schedule?: string;
  filter_conditions?: FilterCondition[];
  batch_size?: number;
  enabled?: boolean;
}

export interface SyncStrategyResponse extends SyncStrategyBase {
  id: string;
  db_config_id: string;
  name?: string;
  last_sync_at?: string;
  last_sync_status?: string;
  created_at: string;
  updated_at: string;
}

export interface SyncHistoryResponse {
  id: string;
  strategy_id: string;
  status: string;
  started_at: string;
  completed_at?: string;
  records_synced: number;
  error_message?: string;
  details?: Record<string, unknown>;
}

export interface SyncJobResponse {
  job_id: string;
  strategy_id: string;
  status: string;
  started_at: string;
  message: string;
}

// SQL Builder
export interface WhereCondition {
  field: string;
  operator: string;
  value: unknown;
  logic: string;
}

export interface OrderByClause {
  field: string;
  direction: string;
}

export interface QueryConfig {
  tables: string[];
  columns: string[];
  where_conditions: WhereCondition[];
  order_by: OrderByClause[];
  group_by: string[];
  limit?: number;
  offset?: number;
}

export interface QueryTemplateCreate {
  name: string;
  description?: string;
  query_config: QueryConfig;
  db_config_id: string;
}

export interface QueryTemplateResponse {
  id: string;
  name: string;
  description?: string;
  query_config: QueryConfig;
  sql: string;
  db_config_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface TableInfo {
  name: string;
  schema_name?: string;
  columns: Array<Record<string, unknown>>;
  primary_key?: string[];
  foreign_keys: Array<Record<string, unknown>>;
  indexes: Array<Record<string, unknown>>;
  row_count?: number;
}

export interface DatabaseSchema {
  tables: TableInfo[];
  views: Array<Record<string, unknown>>;
}

export interface QueryResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  execution_time_ms: number;
  truncated: boolean;
}

export interface ExecuteSQLRequest {
  db_config_id: string;
  sql: string;
  limit: number;
}

// Configuration History
export interface ConfigHistoryResponse {
  id: string;
  config_type: ConfigType;
  old_value?: Record<string, unknown>;
  new_value: Record<string, unknown>;
  user_id: string;
  user_name: string;
  tenant_id?: string;
  created_at: string;
}

export interface ConfigDiff {
  added: Record<string, unknown>;
  removed: Record<string, unknown>;
  modified: Record<string, unknown>;
}

// Third-Party Tools
export interface ThirdPartyConfigBase {
  tool_type: ThirdPartyToolType;
  endpoint: string;
  api_key?: string;
  timeout_seconds: number;
  extra_config: Record<string, unknown>;
}

export interface ThirdPartyConfigCreate extends ThirdPartyConfigBase {
  name: string;
  description?: string;
}

export interface ThirdPartyConfigUpdate {
  name?: string;
  description?: string;
  tool_type?: ThirdPartyToolType;
  endpoint?: string;
  api_key?: string;
  timeout_seconds?: number;
  extra_config?: Record<string, unknown>;
  enabled?: boolean;
}

export interface ThirdPartyConfigResponse extends ThirdPartyConfigBase {
  id: string;
  name: string;
  description?: string;
  api_key_masked?: string;
  enabled: boolean;
  health_status?: string;
  last_health_check?: string;
  call_count: number;
  success_rate: number;
  avg_latency_ms: number;
  created_at: string;
  updated_at: string;
}

// ==================== API Endpoints ====================

const ADMIN_API_BASE = '/api/v1/admin';

// ==================== Service Functions ====================

export const adminApi = {
  // Dashboard
  async getDashboard(): Promise<DashboardData> {
    const response = await apiClient.get<DashboardData>(`${ADMIN_API_BASE}/dashboard`);
    return response.data;
  },

  // LLM Configuration
  async listLLMConfigs(tenantId?: string, activeOnly = true): Promise<LLMConfigResponse[]> {
    const params = { tenant_id: tenantId, active_only: activeOnly };
    const response = await apiClient.get<LLMConfigResponse[]>(`${ADMIN_API_BASE}/config/llm`, { params });
    return response.data;
  },

  async getLLMConfig(configId: string, tenantId?: string): Promise<LLMConfigResponse> {
    const params = { tenant_id: tenantId };
    const response = await apiClient.get<LLMConfigResponse>(`${ADMIN_API_BASE}/config/llm/${configId}`, { params });
    return response.data;
  },

  async createLLMConfig(config: LLMConfigCreate, userId: string, userName = 'Unknown', tenantId?: string): Promise<LLMConfigResponse> {
    const params = { user_id: userId, user_name: userName, tenant_id: tenantId };
    const response = await apiClient.post<LLMConfigResponse>(`${ADMIN_API_BASE}/config/llm`, config, { params });
    return response.data;
  },

  async updateLLMConfig(configId: string, config: LLMConfigUpdate, userId: string, userName = 'Unknown', tenantId?: string): Promise<LLMConfigResponse> {
    const params = { user_id: userId, user_name: userName, tenant_id: tenantId };
    const response = await apiClient.put<LLMConfigResponse>(`${ADMIN_API_BASE}/config/llm/${configId}`, config, { params });
    return response.data;
  },

  async deleteLLMConfig(configId: string, userId: string, userName = 'Unknown', tenantId?: string): Promise<void> {
    const params = { user_id: userId, user_name: userName, tenant_id: tenantId };
    await apiClient.delete(`${ADMIN_API_BASE}/config/llm/${configId}`, { params });
  },

  async testLLMConnection(configId: string): Promise<ConnectionTestResult> {
    const response = await apiClient.post<ConnectionTestResult>(`${ADMIN_API_BASE}/config/llm/${configId}/test`);
    return response.data;
  },

  // Database Configuration
  async listDBConfigs(tenantId?: string, activeOnly = true): Promise<DBConfigResponse[]> {
    const params = { tenant_id: tenantId, active_only: activeOnly };
    const response = await apiClient.get<DBConfigResponse[]>(`${ADMIN_API_BASE}/config/databases`, { params });
    return response.data;
  },

  async getDBConfig(configId: string, tenantId?: string): Promise<DBConfigResponse> {
    const params = { tenant_id: tenantId };
    const response = await apiClient.get<DBConfigResponse>(`${ADMIN_API_BASE}/config/databases/${configId}`, { params });
    return response.data;
  },

  async createDBConfig(config: DBConfigCreate, userId: string, userName = 'Unknown', tenantId?: string): Promise<DBConfigResponse> {
    const params = { user_id: userId, user_name: userName, tenant_id: tenantId };
    const response = await apiClient.post<DBConfigResponse>(`${ADMIN_API_BASE}/config/databases`, config, { params });
    return response.data;
  },

  async updateDBConfig(configId: string, config: DBConfigUpdate, userId: string, userName = 'Unknown', tenantId?: string): Promise<DBConfigResponse> {
    const params = { user_id: userId, user_name: userName, tenant_id: tenantId };
    const response = await apiClient.put<DBConfigResponse>(`${ADMIN_API_BASE}/config/databases/${configId}`, config, { params });
    return response.data;
  },

  async deleteDBConfig(configId: string, userId: string, userName = 'Unknown', tenantId?: string): Promise<void> {
    const params = { user_id: userId, user_name: userName, tenant_id: tenantId };
    await apiClient.delete(`${ADMIN_API_BASE}/config/databases/${configId}`, { params });
  },

  async testDBConnection(configId: string, tenantId?: string): Promise<ConnectionTestResult> {
    const params = { tenant_id: tenantId };
    const response = await apiClient.post<ConnectionTestResult>(`${ADMIN_API_BASE}/config/databases/${configId}/test`, null, { params });
    return response.data;
  },

  // Sync Strategy
  async listSyncStrategies(tenantId?: string, enabledOnly = false): Promise<SyncStrategyResponse[]> {
    const params = { tenant_id: tenantId, enabled_only: enabledOnly };
    const response = await apiClient.get<SyncStrategyResponse[]>(`${ADMIN_API_BASE}/config/sync`, { params });
    return response.data;
  },

  async getSyncStrategy(strategyId: string, tenantId?: string): Promise<SyncStrategyResponse> {
    const params = { tenant_id: tenantId };
    const response = await apiClient.get<SyncStrategyResponse>(`${ADMIN_API_BASE}/config/sync/${strategyId}`, { params });
    return response.data;
  },

  async createSyncStrategy(strategy: SyncStrategyCreate, userId: string, userName = 'Unknown', tenantId?: string): Promise<SyncStrategyResponse> {
    const params = { user_id: userId, user_name: userName, tenant_id: tenantId };
    const response = await apiClient.post<SyncStrategyResponse>(`${ADMIN_API_BASE}/config/sync`, strategy, { params });
    return response.data;
  },

  async updateSyncStrategy(strategyId: string, strategy: SyncStrategyUpdate, userId: string, userName = 'Unknown', tenantId?: string): Promise<SyncStrategyResponse> {
    const params = { user_id: userId, user_name: userName, tenant_id: tenantId };
    const response = await apiClient.put<SyncStrategyResponse>(`${ADMIN_API_BASE}/config/sync/${strategyId}`, strategy, { params });
    return response.data;
  },

  async deleteSyncStrategy(strategyId: string, userId: string, userName = 'Unknown', tenantId?: string): Promise<void> {
    const params = { user_id: userId, user_name: userName, tenant_id: tenantId };
    await apiClient.delete(`${ADMIN_API_BASE}/config/sync/${strategyId}`, { params });
  },

  async triggerSync(strategyId: string, userId: string): Promise<SyncJobResponse> {
    const params = { user_id: userId };
    const response = await apiClient.post<SyncJobResponse>(`${ADMIN_API_BASE}/config/sync/${strategyId}/trigger`, null, { params });
    return response.data;
  },

  async retrySync(jobId: string, userId: string): Promise<SyncJobResponse> {
    const params = { user_id: userId };
    const response = await apiClient.post<SyncJobResponse>(`${ADMIN_API_BASE}/config/sync/retry/${jobId}`, null, { params });
    return response.data;
  },

  async getSyncHistory(strategyId: string, limit = 50): Promise<SyncHistoryResponse[]> {
    const params = { limit };
    const response = await apiClient.get<SyncHistoryResponse[]>(`${ADMIN_API_BASE}/config/sync/${strategyId}/history`, { params });
    return response.data;
  },

  // SQL Builder
  async getDBSchema(dbConfigId: string): Promise<DatabaseSchema> {
    const response = await apiClient.get<DatabaseSchema>(`${ADMIN_API_BASE}/sql-builder/schema/${dbConfigId}`);
    return response.data;
  },

  async buildSQL(queryConfig: QueryConfig, dbType = 'postgresql'): Promise<{ sql: string; validation: ValidationResult }> {
    const response = await apiClient.post<{ sql: string; validation: ValidationResult }>(`${ADMIN_API_BASE}/sql-builder/build`, { query_config: queryConfig, db_type: dbType });
    return response.data;
  },

  async validateSQL(sql: string, dbType = 'postgresql'): Promise<ValidationResult> {
    const params = { sql, db_type: dbType };
    const response = await apiClient.post<ValidationResult>(`${ADMIN_API_BASE}/sql-builder/validate`, null, { params });
    return response.data;
  },

  async executeSQL(request: ExecuteSQLRequest): Promise<QueryResult> {
    const response = await apiClient.post<QueryResult>(`${ADMIN_API_BASE}/sql-builder/execute`, request);
    return response.data;
  },

  async listQueryTemplates(dbConfigId?: string, tenantId?: string): Promise<QueryTemplateResponse[]> {
    const params = { db_config_id: dbConfigId, tenant_id: tenantId };
    const response = await apiClient.get<QueryTemplateResponse[]>(`${ADMIN_API_BASE}/sql-builder/templates`, { params });
    return response.data;
  },

  async createQueryTemplate(template: QueryTemplateCreate, userId: string, tenantId?: string): Promise<QueryTemplateResponse> {
    const params = { user_id: userId, tenant_id: tenantId };
    const response = await apiClient.post<QueryTemplateResponse>(`${ADMIN_API_BASE}/sql-builder/templates`, template, { params });
    return response.data;
  },

  async deleteQueryTemplate(templateId: string): Promise<void> {
    await apiClient.delete(`${ADMIN_API_BASE}/sql-builder/templates/${templateId}`);
  },

  // Configuration History
  async getConfigHistory(params: {
    config_type?: ConfigType;
    start_time?: string;
    end_time?: string;
    user_id?: string;
    tenant_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<ConfigHistoryResponse[]> {
    const response = await apiClient.get<ConfigHistoryResponse[]>(`${ADMIN_API_BASE}/config/history`, { params });
    return response.data;
  },

  async getConfigHistoryById(historyId: string): Promise<ConfigHistoryResponse> {
    const response = await apiClient.get<ConfigHistoryResponse>(`${ADMIN_API_BASE}/config/history/${historyId}`);
    return response.data;
  },

  async getConfigDiff(historyId: string): Promise<ConfigDiff> {
    const response = await apiClient.get<ConfigDiff>(`${ADMIN_API_BASE}/config/history/${historyId}/diff`);
    return response.data;
  },

  async rollbackConfig(historyId: string, userId: string, userName = 'Unknown', reason?: string): Promise<{ success: boolean; rolled_back_config: Record<string, unknown> }> {
    const params = { user_id: userId, user_name: userName };
    const response = await apiClient.post<{ success: boolean; rolled_back_config: Record<string, unknown> }>(`${ADMIN_API_BASE}/config/history/${historyId}/rollback`, { reason }, { params });
    return response.data;
  },

  // Third-Party Tools
  async listThirdPartyConfigs(tenantId?: string): Promise<ThirdPartyConfigResponse[]> {
    const params = { tenant_id: tenantId };
    const response = await apiClient.get<ThirdPartyConfigResponse[]>(`${ADMIN_API_BASE}/config/third-party`, { params });
    return response.data;
  },

  async createThirdPartyConfig(config: ThirdPartyConfigCreate, userId: string, tenantId?: string): Promise<ThirdPartyConfigResponse> {
    const params = { user_id: userId, tenant_id: tenantId };
    const response = await apiClient.post<ThirdPartyConfigResponse>(`${ADMIN_API_BASE}/config/third-party`, config, { params });
    return response.data;
  },

  async updateThirdPartyConfig(configId: string, config: ThirdPartyConfigUpdate, userId: string, tenantId?: string): Promise<ThirdPartyConfigResponse> {
    const params = { user_id: userId, tenant_id: tenantId };
    const response = await apiClient.put<ThirdPartyConfigResponse>(`${ADMIN_API_BASE}/config/third-party/${configId}`, config, { params });
    return response.data;
  },

  async deleteThirdPartyConfig(configId: string, userId: string): Promise<void> {
    const params = { user_id: userId };
    await apiClient.delete(`${ADMIN_API_BASE}/config/third-party/${configId}`, { params });
  },

  async checkThirdPartyHealth(configId: string): Promise<ConnectionTestResult> {
    const response = await apiClient.post<ConnectionTestResult>(`${ADMIN_API_BASE}/config/third-party/${configId}/health`);
    return response.data;
  },

  // Validation
  async validateLLMConfig(config: LLMConfigCreate): Promise<ValidationResult> {
    const response = await apiClient.post<ValidationResult>(`${ADMIN_API_BASE}/validate/llm`, config);
    return response.data;
  },

  async validateDBConfig(config: DBConfigCreate): Promise<ValidationResult> {
    const response = await apiClient.post<ValidationResult>(`${ADMIN_API_BASE}/validate/database`, config);
    return response.data;
  },

  async validateSyncConfig(config: SyncStrategyCreate): Promise<ValidationResult> {
    const response = await apiClient.post<ValidationResult>(`${ADMIN_API_BASE}/validate/sync`, config);
    return response.data;
  },
};

// Helper functions
export const getLLMTypeName = (type: LLMType): string => {
  const names: Record<LLMType, string> = {
    local_ollama: '本地 Ollama',
    openai: 'OpenAI',
    qianwen: '通义千问',
    zhipu: '智谱 GLM',
    hunyuan: '腾讯混元',
    custom: '自定义',
  };
  return names[type] || type;
};

export const getDBTypeName = (type: DatabaseType): string => {
  const names: Record<DatabaseType, string> = {
    postgresql: 'PostgreSQL',
    mysql: 'MySQL',
    sqlite: 'SQLite',
    oracle: 'Oracle',
    sqlserver: 'SQL Server',
  };
  return names[type] || type;
};

export const getSyncModeName = (mode: SyncMode): string => {
  const names: Record<SyncMode, string> = {
    full: '全量同步',
    incremental: '增量同步',
    realtime: '实时同步',
  };
  return names[mode] || mode;
};

export const getConfigTypeName = (type: ConfigType): string => {
  const names: Record<ConfigType, string> = {
    llm: 'LLM 配置',
    database: '数据库配置',
    sync_strategy: '同步策略',
    third_party: '第三方工具',
  };
  return names[type] || type;
};

export default adminApi;
