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
