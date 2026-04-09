/**
 * Enhancement job API — 薄封装，为旧列表补充 camelCase 展示字段。
 */
import { dataLifecycleApi, type EnhancementJob as ApiEnhancementJob } from '@/services/dataLifecycle';

export type EnhancementJob = {
  id: string;
  name: string;
  type: string;
  status: ApiEnhancementJob['status'];
  progress: number;
  iterations?: number;
  maxIterations?: number;
  createdAt: string;
  completedAt?: string;
  currentVersion: number;
};

function mapJob(j: ApiEnhancementJob): EnhancementJob {
  const m = j.metadata as Record<string, unknown> | undefined;
  return {
    id: j.id,
    name: (typeof m?.name === 'string' ? m.name : j.data_id) as string,
    type: j.enhancement_type,
    status: j.status,
    progress: j.progress,
    iterations: typeof m?.iterations === 'number' ? m.iterations : undefined,
    maxIterations: typeof m?.max_iterations === 'number' ? m.max_iterations : undefined,
    createdAt: j.created_at,
    completedAt: j.completed_at,
    currentVersion: j.current_version,
  };
}

export const enhancementApi = {
  async list(page: number, pageSize: number) {
    const res = await dataLifecycleApi.listEnhancements({
      page,
      page_size: pageSize,
    });
    return {
      items: res.items.map(mapJob),
      total: res.total,
      page: res.page,
      page_size: res.page_size,
    };
  },
  start: (id: string) => dataLifecycleApi.startEnhancement(id),
  pause: (id: string) => dataLifecycleApi.pauseEnhancement(id),
  resume: (id: string) => dataLifecycleApi.resumeEnhancement(id),
  cancel: (id: string) => dataLifecycleApi.cancelEnhancement(id),
  rollback: (id: string, version: number) =>
    dataLifecycleApi.rollbackEnhancement(id, version),
};
