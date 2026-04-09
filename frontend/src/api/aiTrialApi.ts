/**
 * AI Trial API — 薄封装，对齐 Data Lifecycle 列表组件的 camelCase 字段。
 */
import { dataLifecycleApi, type AITrial as AITrialRow } from '@/services/dataLifecycle';

export type AITrial = {
  id: string;
  name: string;
  model: string;
  status: AITrialRow['status'];
  trialCount: number;
  successRate: number;
  avgScore: number;
  createdAt: string;
  completedAt?: string;
};

function mapTrial(t: AITrialRow): AITrial {
  return {
    id: t.id,
    name: t.name,
    model: t.model,
    status: t.status,
    trialCount: t.trial_count,
    successRate: t.success_rate,
    avgScore: t.avg_score,
    createdAt: t.created_at,
    completedAt: t.completed_at,
  };
}

export const aiTrialApi = {
  async list(page: number, pageSize: number) {
    const res = await dataLifecycleApi.listAITrials({
      page,
      page_size: pageSize,
    });
    return {
      items: res.items.map(mapTrial),
      total: res.total,
      page: res.page,
      page_size: res.page_size,
    };
  },
  start: (id: string) => dataLifecycleApi.startAITrial(id),
  stop: (id: string) => dataLifecycleApi.stopAITrial(id),
  exportResults: (id: string) => dataLifecycleApi.exportAITrialResults(id),
};
