// LLM Configuration types

export interface LLMConfig {
  id: string;
  name: string;
  provider: 'openai' | 'azure' | 'anthropic' | 'ollama' | 'custom';
  base_url?: string;
  model_name: string;
  parameters: Record<string, any>;
  is_active: boolean;
  tenant_id?: string;
  created_at: string;
  updated_at: string;
}

export interface LLMConfigCreate {
  name: string;
  provider: 'openai' | 'azure' | 'anthropic' | 'ollama' | 'custom';
  api_key: string;
  base_url?: string;
  model_name: string;
  parameters?: Record<string, any>;
  tenant_id?: string;
}

export interface LLMConfigUpdate {
  name?: string;
  provider?: 'openai' | 'azure' | 'anthropic' | 'ollama' | 'custom';
  api_key?: string;
  base_url?: string;
  model_name?: string;
  parameters?: Record<string, any>;
  is_active?: boolean;
}

export interface Application {
  id: string;
  code: string;
  name: string;
  description?: string;
  llm_usage_pattern?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMBinding {
  id: string;
  llm_config: LLMConfig;
  application: Application;
  priority: number;
  max_retries: number;
  timeout_seconds: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMBindingCreate {
  llm_config_id: string;
  application_id: string;
  priority: number;
  max_retries?: number;
  timeout_seconds?: number;
}

export interface LLMBindingUpdate {
  priority?: number;
  max_retries?: number;
  timeout_seconds?: number;
  is_active?: boolean;
}

export interface TestConnectionResult {
  status: 'success' | 'failed';
  latency_ms?: number;
  error?: string;
}
