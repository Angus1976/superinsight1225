/**
 * Skill Admin API Service
 * Wraps backend /api/v1/admin/skills endpoints for skill management.
 */

import apiClient from '@/services/api/client';
import type {
  SkillDetail,
  SkillListResponse,
  SyncResult,
  ExecuteResult,
} from '@/types/aiAssistant';

const API_BASE = '/api/v1/admin/skills';

/** Fetch all skills for the current tenant. */
export async function listSkills(): Promise<SkillListResponse> {
  const response = await apiClient.get<SkillListResponse>(API_BASE);
  return response.data;
}

/** Trigger a sync from the OpenClaw Agent into the database. */
export async function syncSkills(): Promise<SyncResult> {
  const response = await apiClient.post<SyncResult>(`${API_BASE}/sync`);
  return response.data;
}

/** Execute a deployed skill with optional parameters. */
export async function executeSkill(
  skillId: string,
  params: Record<string, unknown> = {},
): Promise<ExecuteResult> {
  const response = await apiClient.post<ExecuteResult>(
    `${API_BASE}/${skillId}/execute`,
    { parameters: params },
  );
  return response.data;
}

/** Toggle a skill's status between deployed and pending. */
export async function toggleSkillStatus(
  skillId: string,
  status: 'deployed' | 'pending',
): Promise<SkillDetail> {
  const response = await apiClient.patch<SkillDetail>(
    `${API_BASE}/${skillId}/status`,
    { status },
  );
  return response.data;
}


/** Seed ClawHub official data skills into the skill library. */
export async function seedClawHubSkills(): Promise<{
  added: number;
  skipped: number;
  admin_permissions_added?: number;
}> {
  const response = await apiClient.post<{
    added: number;
    skipped: number;
    admin_permissions_added?: number;
  }>(`${API_BASE}/seed-clawhub`);
  return response.data;
}
