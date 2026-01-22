/**
 * LLM Integration Service
 * 
 * Provides API client functions for LLM configuration, generation, and health checks.
 */

import apiClient from './api/client';

// ==================== Types ====================

export type LLMMethod = 
  | 'local_ollama'
  | 'cloud_openai'
  | 'cloud_azure'
  | 'china_qwen'
  | 'china_zhipu'
  | 'china_baidu'
  | 'china_hunyuan';

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface LLMResponse {
  content: string;
  usage: TokenUsage;
  model: string;
  provider: string;
  latency_ms: number;
  finish_reason?: string;
  metadata?: Record<string, unknown>;
}

export interface EmbeddingResponse {
  embedding: number[];
  model: string;
  provider: string;
  dimensions: number;
  latency_ms: number;
}

export interface GenerateOptions {
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  top_k?: number;
  stop_sequences?: string[];
  stream?: boolean;
  presence_penalty?: number;
  frequency_penalty?: number;
}

export interface GenerateRequest {
  prompt: string;
  options?: GenerateOptions;
  method?: LLMMethod;
  model?: string;
  system_prompt?: string;
  messages?: Array<{ role: string; content: string }>;
}

export interface EmbedRequest {
  text: string;
  method?: LLMMethod;
  model?: string;
}

export interface LocalConfig {
  ollama_url: string;
  default_model: string;
  timeout: number;
  max_retries: number;
}

export interface CloudConfig {
  openai_api_key?: string;
  openai_base_url: string;
  openai_model: string;
  azure_endpoint?: string;
  azure_api_key?: string;
  azure_deployment?: string;
  azure_api_version: string;
  timeout: number;
  max_retries: number;
}

export interface ChinaLLMConfig {
  qwen_api_key?: string;
  qwen_model: string;
  zhipu_api_key?: string;
  zhipu_model: string;
  baidu_api_key?: string;
  baidu_secret_key?: string;
  baidu_model: string;
  hunyuan_secret_id?: string;
  hunyuan_secret_key?: string;
  hunyuan_model: string;
  timeout: number;
  max_retries: number;
}

export interface LLMConfig {
  default_method: LLMMethod;
  local_config: LocalConfig;
  cloud_config: CloudConfig;
  china_config: ChinaLLMConfig;
  enabled_methods: LLMMethod[];
}

export interface HealthStatus {
  method: LLMMethod;
  available: boolean;
  latency_ms?: number;
  model?: string;
  error?: string;
  last_check?: string;
}

export interface MethodInfo {
  method: LLMMethod;
  name: string;
  description: string;
  enabled: boolean;
  configured: boolean;
  models: string[];
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: {
    error_code: string;
    message: string;
    provider?: string;
    suggestions?: string[];
    retry_after?: number;
  };
}

// ==================== API Endpoints ====================

const LLM_API_BASE = '/api/v1/llm';

// ==================== Service Functions ====================

export const llmService = {
  /**
   * Generate text using LLM
   */
  async generate(request: GenerateRequest): Promise<LLMResponse> {
    const response = await apiClient.post<ApiResponse<LLMResponse>>(
      `${LLM_API_BASE}/generate`,
      request
    );
    return response.data.data;
  },

  /**
   * Generate text embedding
   */
  async embed(request: EmbedRequest): Promise<EmbeddingResponse> {
    const response = await apiClient.post<ApiResponse<EmbeddingResponse>>(
      `${LLM_API_BASE}/embed`,
      request
    );
    return response.data.data;
  },

  /**
   * Get LLM configuration
   */
  async getConfig(tenantId?: string): Promise<LLMConfig> {
    const params = tenantId ? { tenant_id: tenantId } : {};
    const response = await apiClient.get<ApiResponse<LLMConfig>>(
      `${LLM_API_BASE}/config`,
      { params }
    );
    return response.data.data;
  },

  /**
   * Update LLM configuration
   */
  async updateConfig(config: LLMConfig, tenantId?: string): Promise<LLMConfig> {
    const params = tenantId ? { tenant_id: tenantId } : {};
    const response = await apiClient.put<ApiResponse<LLMConfig>>(
      `${LLM_API_BASE}/config`,
      config,
      { params }
    );
    return response.data.data;
  },

  /**
   * Validate LLM configuration
   */
  async validateConfig(config: LLMConfig): Promise<ValidationResult> {
    const response = await apiClient.post<ValidationResult>(
      `${LLM_API_BASE}/config/validate`,
      config
    );
    return response.data;
  },

  /**
   * Test connection to LLM provider
   */
  async testConnection(method: LLMMethod): Promise<HealthStatus> {
    const response = await apiClient.post<ApiResponse<HealthStatus>>(
      `${LLM_API_BASE}/config/test`,
      { method }
    );
    return response.data.data;
  },

  /**
   * Get health status of all providers
   */
  async getHealth(method?: LLMMethod): Promise<Record<string, HealthStatus>> {
    const params = method ? { method } : {};
    const response = await apiClient.get<ApiResponse<Record<string, HealthStatus>>>(
      `${LLM_API_BASE}/health`,
      { params }
    );
    return response.data.data;
  },

  /**
   * List available LLM methods
   */
  async getMethods(): Promise<MethodInfo[]> {
    const response = await apiClient.get<ApiResponse<MethodInfo[]>>(
      `${LLM_API_BASE}/methods`
    );
    return response.data.data;
  },

  /**
   * Get current default method
   */
  async getCurrentMethod(): Promise<LLMMethod> {
    const response = await apiClient.get<{ success: boolean; data: { method: LLMMethod } }>(
      `${LLM_API_BASE}/current-method`
    );
    return response.data.data.method;
  },

  /**
   * Switch default method
   */
  async switchMethod(method: LLMMethod): Promise<void> {
    await apiClient.post(`${LLM_API_BASE}/switch-method`, { method });
  },

  /**
   * List available models
   */
  async getModels(method?: LLMMethod): Promise<Record<string, string[]> | { method: string; models: string[] }> {
    const params = method ? { method } : {};
    const response = await apiClient.get<{ success: boolean; data: Record<string, string[]> | { method: string; models: string[] } }>(
      `${LLM_API_BASE}/models`,
      { params }
    );
    return response.data.data;
  },

  /**
   * Hot reload configuration
   */
  async hotReload(tenantId?: string): Promise<LLMConfig> {
    const params = tenantId ? { tenant_id: tenantId } : {};
    const response = await apiClient.post<{ success: boolean; data: { config: LLMConfig } }>(
      `${LLM_API_BASE}/reload`,
      null,
      { params }
    );
    return response.data.data.config;
  },
};

// ==================== Helper Functions ====================

/**
 * Get human-readable name for LLM method
 */
export function getMethodName(method: LLMMethod): string {
  const names: Record<LLMMethod, string> = {
    local_ollama: 'Local Ollama',
    cloud_openai: 'OpenAI',
    cloud_azure: 'Azure OpenAI',
    china_qwen: '通义千问 (Qwen)',
    china_zhipu: '智谱 GLM',
    china_baidu: '文心一言',
    china_hunyuan: '腾讯混元',
  };
  return names[method] || method;
}

/**
 * Get method category
 */
export function getMethodCategory(method: LLMMethod): 'local' | 'cloud' | 'china' {
  if (method === 'local_ollama') return 'local';
  if (method.startsWith('cloud_')) return 'cloud';
  return 'china';
}

/**
 * Check if API key is masked
 */
export function isApiKeyMasked(key?: string): boolean {
  if (!key) return false;
  return key.includes('*');
}

// ==================== Provider Management Functions ====================

/**
 * Provider configuration types for CRUD operations
 */
export interface ProviderConfig {
  id: string;
  name: string;
  provider_type: string;
  deployment_mode: 'local' | 'cloud';
  is_active: boolean;
  is_fallback: boolean;
  status: 'healthy' | 'unhealthy' | 'unknown';
  created_at: string;
  updated_at: string;
  config?: Record<string, unknown>;
}

export interface ProviderConfigCreate {
  name: string;
  provider_type: string;
  deployment_mode: 'local' | 'cloud';
  config: Record<string, unknown>;
  is_fallback?: boolean;
}

export interface ProviderConfigUpdate {
  name?: string;
  config?: Record<string, unknown>;
  is_fallback?: boolean;
}

export const llmProviderService = {
  /**
   * List all LLM providers
   */
  async getProviders(): Promise<ProviderConfig[]> {
    const response = await apiClient.get<ApiResponse<ProviderConfig[]>>(
      `${LLM_API_BASE}/providers`
    );
    return response.data.data;
  },

  /**
   * Get a single provider by ID
   */
  async getProvider(id: string): Promise<ProviderConfig> {
    const response = await apiClient.get<ApiResponse<ProviderConfig>>(
      `${LLM_API_BASE}/providers/${id}`
    );
    return response.data.data;
  },

  /**
   * Create a new provider
   */
  async createProvider(data: ProviderConfigCreate): Promise<ProviderConfig> {
    const response = await apiClient.post<ApiResponse<ProviderConfig>>(
      `${LLM_API_BASE}/providers`,
      data
    );
    return response.data.data;
  },

  /**
   * Update an existing provider
   */
  async updateProvider(id: string, data: ProviderConfigUpdate): Promise<ProviderConfig> {
    const response = await apiClient.put<ApiResponse<ProviderConfig>>(
      `${LLM_API_BASE}/providers/${id}`,
      data
    );
    return response.data.data;
  },

  /**
   * Delete a provider
   */
  async deleteProvider(id: string): Promise<void> {
    await apiClient.delete(`${LLM_API_BASE}/providers/${id}`);
  },

  /**
   * Test provider connection
   */
  async testConnection(id: string): Promise<HealthStatus> {
    const response = await apiClient.post<ApiResponse<HealthStatus>>(
      `${LLM_API_BASE}/providers/${id}/test`
    );
    return response.data.data;
  },

  /**
   * Activate a provider (set as active)
   */
  async activateProvider(id: string): Promise<void> {
    await apiClient.post(`${LLM_API_BASE}/providers/${id}/activate`);
  },

  /**
   * Set provider as fallback
   */
  async setFallbackProvider(id: string): Promise<void> {
    await apiClient.post(`${LLM_API_BASE}/providers/${id}/set-fallback`);
  },

  /**
   * Get provider health status
   */
  async getProviderHealth(id: string): Promise<HealthStatus> {
    const response = await apiClient.get<ApiResponse<HealthStatus>>(
      `${LLM_API_BASE}/providers/${id}/health`
    );
    return response.data.data;
  },
};

export default llmService;
