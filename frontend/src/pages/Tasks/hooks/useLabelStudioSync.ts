// Label Studio sync logic extracted from Tasks page
import { useState, useCallback } from 'react';
import { App } from 'antd';
import { useTranslation } from 'react-i18next';
import { apiClient } from '@/services';
import { API_ENDPOINTS } from '@/constants';
import type { Task } from '@/types';

// Types for Label Studio API responses
interface LabelStudioProject {
  id: number;
  title: string;
  description?: string;
  task_number: number;
  num_tasks_with_annotations: number;
  created_at?: string;
  updated_at?: string;
}

interface LabelStudioTask {
  id: number;
  is_labeled: boolean;
  annotations?: LabelStudioAnnotation[];
  total_annotations?: number;
}

interface LabelStudioAnnotation {
  id: number;
  created_at: string;
  updated_at: string;
  completed_by?: number;
  result?: unknown[];
  was_cancelled?: boolean;
  ground_truth?: boolean;
  lead_time?: number;
}

interface LabelStudioProjectDetails {
  id: number;
  title: string;
  description?: string;
  task_number?: number;
  num_tasks_with_annotations?: number;
  created_at?: string;
  updated_at?: string;
  total_annotations_number?: number;
  total_predictions_number?: number;
}

export interface SyncProgress {
  current: number;
  total: number;
  status: 'idle' | 'syncing' | 'completed' | 'error';
  message: string;
}

// Cache for Label Studio API responses
interface SyncCache {
  projects: Map<number, LabelStudioProject>;
  projectTasks: Map<number, LabelStudioTask[]>;
  lastFetch: number;
}

const CACHE_TTL = 30 * 1000;

let syncCache: SyncCache = {
  projects: new Map(),
  projectTasks: new Map(),
  lastFetch: 0,
};

interface AnnotationQualityMetrics {
  totalAnnotations: number;
  avgLeadTime: number;
  completionRate: number;
  annotatorCount: number;
}

const calculateAnnotationQuality = (tasks: LabelStudioTask[]): AnnotationQualityMetrics => {
  let totalAnnotations = 0;
  let totalLeadTime = 0;
  let annotationsWithLeadTime = 0;
  const annotatorIds = new Set<number>();

  for (const task of tasks) {
    if (task.annotations?.length) {
      for (const annotation of task.annotations) {
        totalAnnotations++;
        if (annotation.lead_time && annotation.lead_time > 0) {
          totalLeadTime += annotation.lead_time;
          annotationsWithLeadTime++;
        }
        if (annotation.completed_by) annotatorIds.add(annotation.completed_by);
      }
    }
    if (task.total_annotations && task.total_annotations > 0 && !task.annotations?.length) {
      totalAnnotations += task.total_annotations;
    }
  }

  const tasksWithAnnotations = tasks.filter(t => t.is_labeled).length;
  return {
    totalAnnotations,
    avgLeadTime: annotationsWithLeadTime > 0 ? Math.round(totalLeadTime / annotationsWithLeadTime) : 0,
    completionRate: tasks.length > 0 ? Math.round((tasksWithAnnotations / tasks.length) * 100) : 0,
    annotatorCount: annotatorIds.size,
  };
};

const isCacheValid = () => Date.now() - syncCache.lastFetch < CACHE_TTL;

const fetchLabelStudioProjects = async (forceRefresh = false): Promise<LabelStudioProject[]> => {
  if (!forceRefresh && isCacheValid() && syncCache.projects.size > 0) {
    return Array.from(syncCache.projects.values());
  }
  const response = await apiClient.get<{ results: LabelStudioProject[] }>(
    API_ENDPOINTS.LABEL_STUDIO.PROJECTS
  );
  const projects = response.data.results || [];
  syncCache.projects.clear();
  projects.forEach(p => syncCache.projects.set(p.id, p));
  syncCache.lastFetch = Date.now();
  return projects;
};

const batchFetchProjectTasks = async (
  projectIds: number[],
  forceRefresh = false
): Promise<Map<number, LabelStudioTask[]>> => {
  const result = new Map<number, LabelStudioTask[]>();
  const toFetch: number[] = [];

  for (const id of projectIds) {
    if (!forceRefresh && isCacheValid() && syncCache.projectTasks.has(id)) {
      result.set(id, syncCache.projectTasks.get(id)!);
    } else {
      toFetch.push(id);
    }
  }
  if (toFetch.length === 0) return result;

  const BATCH_SIZE = 5;
  for (let i = 0; i < toFetch.length; i += BATCH_SIZE) {
    const batch = toFetch.slice(i, i + BATCH_SIZE);
    const batchResults = await Promise.allSettled(
      batch.map(async (projectId) => {
        const response = await apiClient.get<{ tasks: LabelStudioTask[] }>(
          API_ENDPOINTS.LABEL_STUDIO.TASKS(String(projectId))
        );
        return { projectId, tasks: response.data.tasks || [] };
      })
    );
    for (const settled of batchResults) {
      if (settled.status === 'fulfilled') {
        result.set(settled.value.projectId, settled.value.tasks);
        syncCache.projectTasks.set(settled.value.projectId, settled.value.tasks);
      }
    }
  }
  return result;
};

export function useLabelStudioSync(
  updateTaskFn: (params: { id: string; payload: Record<string, unknown> }) => Promise<unknown>,
  refetch: () => void,
) {
  const { t } = useTranslation(['tasks']);
  const { message } = App.useApp();
  const [syncProgress, setSyncProgress] = useState<SyncProgress>({
    current: 0, total: 0, status: 'idle', message: '',
  });
  const [syncModalOpen, setSyncModalOpen] = useState(false);

  const resetSyncState = useCallback(() => {
    setSyncModalOpen(false);
    setSyncProgress({ current: 0, total: 0, status: 'idle', message: '' });
  }, []);

  const handleSyncSingleTask = useCallback(async (task: Task) => {
    const projectId = task.label_studio_project_id;
    if (!projectId) {
      message.warning(t('syncTaskNoProject'));
      return;
    }
    const hide = message.loading(t('syncingSingleTask'), 0);
    try {
      const projectResponse = await apiClient.get<LabelStudioProjectDetails>(
        API_ENDPOINTS.LABEL_STUDIO.PROJECT_BY_ID(projectId)
      );
      const projectDetails = projectResponse.data;
      const tasksResponse = await apiClient.get<{ tasks: LabelStudioTask[] }>(
        API_ENDPOINTS.LABEL_STUDIO.TASKS(projectId)
      );
      const lsTasks = tasksResponse.data.tasks || [];
      const totalTasks = lsTasks.length;
      const completedTasks = lsTasks.filter(t => t.is_labeled).length;
      const progress = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

      const updatePayload: Record<string, unknown> = {
        total_items: totalTasks,
        completed_items: completedTasks,
        progress,
        label_studio_sync_status: 'synced',
        label_studio_last_sync: projectDetails.updated_at || new Date().toISOString(),
        label_studio_sync_error: '',
      };
      if (projectDetails.title && projectDetails.title !== task.name && !/^Project \d+$/.test(projectDetails.title)) {
        updatePayload.name = projectDetails.title;
      }
      if (projectDetails.description !== undefined) {
        updatePayload.description = projectDetails.description || '';
      }
      await updateTaskFn({ id: task.id, payload: updatePayload });
      hide();
      message.success(t('syncSingleTaskSuccess', { progress }));
      refetch();
    } catch (error) {
      hide();
      const errorMessage = error instanceof Error ? error.message : t('syncSingleTaskFailed');
      try {
        await updateTaskFn({
          id: task.id,
          payload: {
            label_studio_sync_status: 'failed',
            label_studio_last_sync: new Date().toISOString(),
            label_studio_sync_error: errorMessage,
          },
        });
      } catch { /* ignore */ }
      message.error(t('syncSingleTaskFailed'));
      refetch();
    }
  }, [t, updateTaskFn, refetch, message]);

  const handleSyncAllTasks = useCallback(async (localTasks: Task[]) => {
    setSyncModalOpen(true);
    setSyncProgress({ current: 0, total: 0, status: 'syncing', message: t('syncingTasks') });

    try {
      setSyncProgress(prev => ({ ...prev, message: t('syncFetchingProjects') || 'Fetching projects...' }));
      const lsProjects = await fetchLabelStudioProjects();

      if (!localTasks.length) {
        setSyncProgress({ current: 0, total: 0, status: 'completed', message: t('noTasksToSync') });
        return;
      }

      // Determine tasks needing sync
      const projectMapById = new Map(lsProjects.map(p => [p.id, p]));
      const projectMapByTitle = new Map(lsProjects.map(p => [p.title.toLowerCase().trim(), p]));

      const tasksToSync = localTasks.filter(task => {
        const pid = task.label_studio_project_id;
        if (pid) {
          if (!projectMapById.has(Number(pid))) return false;
          if (task.label_studio_last_sync) {
            const syncAge = Date.now() - new Date(task.label_studio_last_sync).getTime();
            if (syncAge < 5 * 60 * 1000 && task.label_studio_sync_status === 'synced') return false;
          }
          return true;
        }
        return !!projectMapByTitle.get(task.name.toLowerCase().trim());
      });

      if (!tasksToSync.length) {
        setSyncProgress({ current: 0, total: 0, status: 'completed', message: t('allTasksSynced') });
        return;
      }

      // Collect project IDs
      const projectIdsToFetch = new Set<number>();
      const taskProjectMapping = new Map<string, number>();
      for (const task of tasksToSync) {
        let pid = task.label_studio_project_id ? Number(task.label_studio_project_id) : null;
        if (!pid) {
          const match = projectMapByTitle.get(task.name.toLowerCase().trim());
          if (match) pid = match.id;
        }
        if (pid && projectMapById.has(pid)) {
          projectIdsToFetch.add(pid);
          taskProjectMapping.set(task.id, pid);
        }
      }

      setSyncProgress(prev => ({
        ...prev, message: t('syncFetchingTasks') || 'Fetching tasks...', total: tasksToSync.length,
      }));
      const projectTasksMap = await batchFetchProjectTasks(Array.from(projectIdsToFetch));

      let successCount = 0;
      let failCount = 0;
      let linkedCount = 0;
      const UPDATE_BATCH_SIZE = 10;
      const updatePromises: Promise<void>[] = [];

      for (let i = 0; i < tasksToSync.length; i++) {
        const task = tasksToSync[i];
        setSyncProgress(prev => ({
          ...prev, current: i + 1,
          message: t('syncProgressMessage', { current: i + 1, total: tasksToSync.length }),
        }));

        const promise = (async () => {
          try {
            let pid = task.label_studio_project_id ? Number(task.label_studio_project_id) : null;
            let wasLinked = false;
            if (!pid) {
              const match = projectMapByTitle.get(task.name.toLowerCase().trim());
              if (match) { pid = match.id; wasLinked = true; } else return;
            }
            const lsTasks = projectTasksMap.get(pid!);
            if (!lsTasks) {
              await updateTaskFn({
                id: task.id,
                payload: { label_studio_sync_status: 'failed', label_studio_last_sync: new Date().toISOString(), label_studio_sync_error: t('syncErrorNoTasks') },
              });
              failCount++;
              return;
            }
            const totalTasks = lsTasks.length;
            const completedTasks = lsTasks.filter(t => t.is_labeled).length;
            const progress = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
            const payload: Record<string, unknown> = {
              total_items: totalTasks, completed_items: completedTasks, progress,
              label_studio_sync_status: 'synced', label_studio_last_sync: new Date().toISOString(),
            };
            const details = projectMapById.get(pid!);
            if (details?.title && details.title !== task.name && !/^Project \d+$/.test(details.title)) {
              payload.name = details.title;
            }
            if (wasLinked) payload.label_studio_project_id = String(pid);
            await updateTaskFn({ id: task.id, payload });
            if (wasLinked) linkedCount++;
            successCount++;
          } catch {
            try {
              await updateTaskFn({
                id: task.id,
                payload: { label_studio_sync_status: 'failed', label_studio_last_sync: new Date().toISOString() },
              });
            } catch { /* ignore */ }
            failCount++;
          }
        })();
        updatePromises.push(promise);
        if (updatePromises.length >= UPDATE_BATCH_SIZE || i === tasksToSync.length - 1) {
          await Promise.all(updatePromises);
          updatePromises.length = 0;
        }
      }

      setSyncProgress({
        current: tasksToSync.length, total: tasksToSync.length,
        status: failCount > 0 ? 'error' : 'completed',
        message: failCount === 0 && successCount > 0
          ? (linkedCount > 0 ? t('syncSuccessWithLinked', { count: successCount, linked: linkedCount }) : t('syncSuccess', { count: successCount }))
          : failCount > 0 ? t('syncPartialSuccess', { success: successCount, fail: failCount }) : t('allTasksSynced'),
      });
      refetch();
    } catch {
      setSyncProgress({ current: 0, total: 0, status: 'error', message: t('syncError') });
    }
  }, [t, updateTaskFn, refetch]);

  return {
    syncProgress, syncModalOpen, setSyncModalOpen,
    resetSyncState, handleSyncSingleTask, handleSyncAllTasks,
  };
}
