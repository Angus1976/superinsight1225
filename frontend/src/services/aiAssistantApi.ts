/**
 * AI Assistant API Service
 * Non-streaming: uses apiClient (axios) for POST /api/v1/ai-assistant/chat
 * Streaming: uses native fetch + ReadableStream for SSE parsing
 */

import apiClient from '@/services/api/client';
import { getToken } from '@/utils/token';
import type { ChatRequest, ChatResponse, StreamChunk, OpenClawStatus } from '@/types/aiAssistant';

const API_BASE = '/api/v1/ai-assistant';

export interface StreamCallbacks {
  onChunk: (chunk: StreamChunk) => void;
  onDone: () => void;
  onError: (error: Error) => void;
}

/**
 * Non-streaming chat — POST /api/v1/ai-assistant/chat
 */
export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>(`${API_BASE}/chat`, request);
  return response.data;
}

/**
 * Query OpenClaw gateway availability and deployed skills.
 * GET /api/v1/ai-assistant/chat/openclaw-status
 */
export async function getOpenClawStatus(): Promise<OpenClawStatus> {
  console.log('[API] Fetching OpenClaw status from:', `${API_BASE}/chat/openclaw-status`);
  try {
    const response = await apiClient.get<OpenClawStatus>(`${API_BASE}/chat/openclaw-status`);
    console.log('[API] OpenClaw status response:', response.data);
    return response.data;
  } catch (error) {
    console.error('[API] Failed to fetch OpenClaw status:', error);
    throw error;
  }
}

/**
 * Parse an SSE buffer: split by double newline, extract `data: ` payloads.
 * Returns parsed chunks and any remaining incomplete buffer.
 */
export function parseSSEBuffer(buffer: string): { chunks: StreamChunk[]; remaining: string } {
  const segments = buffer.split('\n\n');
  const remaining = segments.pop() || '';
  const chunks: StreamChunk[] = [];

  for (const segment of segments) {
    for (const line of segment.split('\n')) {
      if (!line.startsWith('data: ')) continue;
      try {
        chunks.push(JSON.parse(line.slice(6)) as StreamChunk);
      } catch {
        // skip malformed JSON
      }
    }
  }

  return { chunks, remaining };
}

/**
 * Consume a ReadableStream of SSE data, dispatching callbacks.
 */
async function consumeStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  callbacks: StreamCallbacks,
  signal: AbortSignal,
): Promise<void> {
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (!signal.aborted) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parsed = parseSSEBuffer(buffer);
      buffer = parsed.remaining;

      for (const chunk of parsed.chunks) {
        if (signal.aborted) return;
        if (chunk.error) {
          callbacks.onError(new Error(chunk.error));
          return;
        }
        if (chunk.done) {
          callbacks.onDone();
          return;
        }
        callbacks.onChunk(chunk);
      }
    }
  } catch (err: unknown) {
    if (signal.aborted) return;
    callbacks.onError(err instanceof Error ? err : new Error(String(err)));
  } finally {
    reader.cancel().catch(() => {});
  }
}

/**
 * Streaming chat — POST /api/v1/ai-assistant/chat/stream (SSE)
 * Returns an object with an `abort` function to cancel the request.
 */
export function sendMessageStream(
  request: ChatRequest,
  callbacks: StreamCallbacks,
): { abort: () => void } {
  const controller = new AbortController();
  const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const token = getToken();

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  fetch(`${baseURL}${API_BASE}/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
    signal: controller.signal,
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }
      return consumeStream(reader, callbacks, controller.signal);
    })
    .catch((err: unknown) => {
      if (controller.signal.aborted) return;
      callbacks.onError(err instanceof Error ? err : new Error(String(err)));
    });

  return { abort: () => controller.abort() };
}


// --- Data Source APIs ---

import type { AIDataSource, DataSourceConfigItem } from '@/types/aiAssistant';

/**
 * Get available data sources for the current user.
 */
export async function getAvailableDataSources(): Promise<AIDataSource[]> {
  const response = await apiClient.get<AIDataSource[]>(`${API_BASE}/data-sources/available`);
  return response.data;
}

/**
 * Get all data source configs (admin).
 */
export async function getDataSourceConfig(): Promise<AIDataSource[]> {
  const response = await apiClient.get<AIDataSource[]>(`${API_BASE}/data-sources/config`);
  return response.data;
}

/**
 * Update data source configs (admin only).
 */
export async function updateDataSourceConfig(
  sources: DataSourceConfigItem[],
): Promise<AIDataSource[]> {
  const response = await apiClient.post<AIDataSource[]>(`${API_BASE}/data-sources/config`, {
    sources,
  });
  return response.data;
}


// --- Role Permission APIs ---

export interface RolePermissionItem {
  role: string;
  source_id: string;
  allowed: boolean;
}

/**
 * Get all role-permission mappings (admin only).
 */
export async function getRolePermissions(): Promise<{ permissions: RolePermissionItem[] }> {
  const response = await apiClient.get<{ permissions: RolePermissionItem[] }>(`${API_BASE}/data-sources/role-permissions`);
  return response.data;
}

/**
 * Update role-permission mappings (admin only).
 */
export async function updateRolePermissions(permissions: RolePermissionItem[]): Promise<{ permissions: RolePermissionItem[] }> {
  const response = await apiClient.post<{ permissions: RolePermissionItem[] }>(`${API_BASE}/data-sources/role-permissions`, { permissions });
  return response.data;
}


// --- Skill Permission APIs ---

export interface SkillPermissionItem {
  role: string;
  skill_id: string;
  allowed: boolean;
}

/**
 * Get skill IDs available to the current user (filtered by role).
 */
export async function getAvailableSkills(): Promise<{ skill_ids: string[]; role: string }> {
  const response = await apiClient.get<{ skill_ids: string[]; role: string }>(`${API_BASE}/skills/available`);
  return response.data;
}

/**
 * Get all role-skill permission mappings (admin only).
 */
export async function getSkillRolePermissions(): Promise<{ permissions: SkillPermissionItem[] }> {
  const response = await apiClient.get<{ permissions: SkillPermissionItem[] }>(`${API_BASE}/skills/role-permissions`);
  return response.data;
}

/**
 * Update role-skill permission mappings (admin only).
 */
export async function updateSkillRolePermissions(
  permissions: SkillPermissionItem[],
): Promise<{ permissions: SkillPermissionItem[] }> {
  const response = await apiClient.post<{ permissions: SkillPermissionItem[] }>(
    `${API_BASE}/skills/role-permissions`,
    { permissions },
  );
  return response.data;
}

/**
 * Initialize admin role with all deployed skills (admin only).
 */
export async function initAdminSkillPermissions(): Promise<{ added: number; message: string }> {
  const response = await apiClient.post<{ added: number; message: string }>(`${API_BASE}/skills/init-admin`);
  return response.data;
}


// --- Access Log APIs ---

export interface AccessLogItem {
  id: number;
  tenant_id: string;
  user_id: string;
  user_role: string | null;
  event_type: string;
  resource_id: string | null;
  resource_name: string | null;
  api_key_id: string | null;
  request_type: string | null;
  success: boolean;
  error_message: string | null;
  details: Record<string, unknown>;
  duration_ms: number | null;
  created_at: string;
}

export interface AccessLogResponse {
  items: AccessLogItem[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Query AI access logs (admin only, newest first).
 */
export async function getAccessLogs(params?: {
  page?: number;
  page_size?: number;
  event_type?: string;
}): Promise<AccessLogResponse> {
  const response = await apiClient.get<AccessLogResponse>(`${API_BASE}/access-logs`, {
    params,
  });
  return response.data;
}
