// AI Assistant types — mirrors backend Pydantic models in src/api/ai_assistant.py

export type ChatMode = 'direct' | 'openclaw';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  max_tokens?: number;
  temperature?: number;
  mode?: ChatMode;
  gateway_id?: string;
  skill_ids?: string[];
  data_source_ids?: string[];
  output_mode?: OutputMode;
  workflow_id?: string;
}

export interface SkillInfo {
  id: string;
  name: string;
  version: string;
  status: string;
  description?: string;
}

export interface OpenClawStatus {
  available: boolean;
  gateway_id: string | null;
  gateway_name: string | null;
  skills: SkillInfo[];
  error?: string;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ChatResponse {
  content: string;
  model: string;
  usage?: TokenUsage;
}

export interface StreamChunk {
  content?: string;
  error?: string;
  done: boolean;
}

// --- Skill Admin types (mirrors backend schemas) ---

export interface SkillDetail extends SkillInfo {
  category?: string;
  gateway_id: string;
  gateway_name: string;
  deployed_at?: string;
  created_at: string;
}

export interface SkillListResponse {
  skills: SkillDetail[];
  total: number;
}

export interface SyncResult {
  added: number;
  updated: number;
  removed: number;
  skills: SkillDetail[];
}

export interface ExecuteResult {
  success: boolean;
  result?: Record<string, unknown>;
  error?: string;
  execution_time_ms?: number;
}

export interface ExecuteRequest {
  parameters: Record<string, unknown>;
}

export interface StatusToggleRequest {
  status: 'deployed' | 'pending';
}


// --- Data Source types ---

export type OutputMode = 'merge' | 'compare';

export interface AIDataSourceTable {
  id: string;
  label: string;
  fields?: string[];
}

export interface AIDataSource {
  id: string;
  label: string;
  description: string;
  category: string;
  enabled: boolean;
  access_mode: string;
  tables?: AIDataSourceTable[];
}

export interface DataSourceConfigItem {
  id: string;
  label?: string;
  enabled?: boolean;
  access_mode?: string;
}


// --- Workflow types ---

export interface WorkflowItem {
  id: string;
  name: string;
  description?: string;
  status: 'enabled' | 'disabled';
  is_preset: boolean;
  skill_ids: string[];
  data_source_auth: DataSourceAuth[];
  output_modes: string[];
  visible_roles: string[];
  preset_prompt?: string;
  name_en?: string;
  description_en?: string;
  created_at: string;
  updated_at: string;
}

export interface DataSourceAuth {
  source_id: string;
  tables: string[];  // ["*"] = all tables
}

export interface TodayStats {
  chat_count: number;
  workflow_count: number;
  data_source_count: number;
  details?: {
    chats: StatsDetail[];
    workflows: StatsDetail[];
    data_sources: StatsDetail[];
  };
}

export interface StatsDetail {
  id: string;
  name: string;
  timestamp: string;
}
