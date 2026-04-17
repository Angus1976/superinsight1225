/**
 * AI Integration — gateway management & platform LLM bridge (OpenClaw).
 */
import apiClient from './api/client';
import { apiRequestToSnake, apiResponseToSnake } from '@/utils/jsonCase';

const BASE = '/api/v1/ai-integration/gateways';

export interface AIGatewayRow {
  id: string;
  name: string;
  gateway_type: string;
  tenant_id: string;
  status: string;
  configuration: Record<string, unknown>;
  rate_limit_per_minute: number;
  quota_per_day: number;
  created_at: string;
  updated_at: string;
  last_active_at?: string | null;
}

export interface GatewayLlmLinkView {
  gateway_id: string;
  tenant_id: string;
  linked: boolean;
  llm_configuration_id?: string | null;
  llm_provider?: string | null;
  llm_model?: string | null;
  linked_at?: string | null;
  source: string;
  env_preview: Record<string, string>;
}

export interface LinkGatewayLlmBody {
  llm_configuration_id?: string | null;
  model_override?: string;
  temperature_override?: number;
  max_tokens_override?: number;
}

export async function listGateways(params?: {
  tenant_id?: string;
  gateway_type?: string;
}): Promise<AIGatewayRow[]> {
  const r = await apiClient.get(BASE, { params });
  return apiResponseToSnake<AIGatewayRow[]>(r.data);
}

export async function linkGatewayLlm(
  gatewayId: string,
  body: LinkGatewayLlmBody
): Promise<Record<string, unknown>> {
  const r = await apiClient.post(`${BASE}/${gatewayId}/llm-config`, apiRequestToSnake(body));
  return apiResponseToSnake<Record<string, unknown>>(r.data);
}

export async function getGatewayLlmLink(gatewayId: string): Promise<GatewayLlmLinkView> {
  const r = await apiClient.get(`${BASE}/${gatewayId}/llm-link`);
  return apiResponseToSnake<GatewayLlmLinkView>(r.data);
}

export async function getGatewayLlmStatus(gatewayId: string): Promise<Record<string, unknown>> {
  const r = await apiClient.get(`${BASE}/${gatewayId}/llm-status`);
  return apiResponseToSnake<Record<string, unknown>>(r.data);
}
