/**
 * Annotation Task API — 薄封装，列表页使用 camelCase 与旧 UI 状态别名。
 */
import { dataLifecycleApi, type AnnotationTask as ApiAnnotationTask } from '@/services/dataLifecycle';

export type AnnotationTask = {
  id: string;
  name: string;
  description?: string;
  status: 'pending' | 'inProgress' | 'completed' | 'cancelled';
  priority?: string;
  assignee?: string;
  dueDate?: string;
  progress: number;
  createdAt: string;
};

function mapStatus(s: ApiAnnotationTask['status']): AnnotationTask['status'] {
  if (s === 'created') return 'pending';
  if (s === 'in_progress') return 'inProgress';
  if (s === 'completed') return 'completed';
  return 'cancelled';
}

function mapTask(t: ApiAnnotationTask): AnnotationTask {
  const meta = t.metadata;
  const priority =
    meta && typeof meta === 'object' && 'priority' in meta && typeof (meta as { priority?: unknown }).priority === 'string'
      ? (meta as { priority: string }).priority
      : 'medium';

  return {
    id: t.id,
    name: t.name,
    description: t.description,
    status: mapStatus(t.status),
    priority,
    assignee: t.assigned_to?.[0],
    dueDate: t.deadline,
    progress: typeof t.progress === 'number' ? t.progress : 0,
    createdAt: t.created_at,
  };
}

export const annotationTaskApi = {
  async list(page: number, pageSize: number) {
    const res = await dataLifecycleApi.listAnnotationTasks({
      page,
      page_size: pageSize,
    });
    return {
      items: res.items.map(mapTask),
      total: res.total,
      page: res.page,
      page_size: res.page_size,
    };
  },
  start: (id: string) => dataLifecycleApi.startAnnotationTask(id),
  complete: (id: string) => dataLifecycleApi.completeAnnotationTask(id),
  cancel: (id: string) => dataLifecycleApi.cancelAnnotationTask(id),
};
