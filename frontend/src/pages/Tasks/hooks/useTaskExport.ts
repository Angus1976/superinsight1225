// Task export logic extracted from Tasks page
import { useState, useCallback } from 'react';
import { App } from 'antd';
import { useTranslation } from 'react-i18next';
import { apiClient } from '@/services';
import { API_ENDPOINTS } from '@/constants';
import { exportTasksToCSV, exportTasksToJSON, exportTasksToExcel, exportTasksWithCustomFields } from '@/utils/export';
import { addExportHistoryEntry } from '@/components/Tasks';
import type { ExportOptions } from '@/components/Tasks';
import type { Task } from '@/types';
import type { ExportAnnotationResult } from '@/utils/export';

async function fetchAnnotationsForTasks(
  tasks: Task[],
): Promise<Map<string, ExportAnnotationResult[]>> {
  const annotationsMap = new Map<string, ExportAnnotationResult[]>();
  const tasksWithProjects = tasks.filter(task => task.label_studio_project_id);
  const BATCH_SIZE = 5;

  for (let i = 0; i < tasksWithProjects.length; i += BATCH_SIZE) {
    const batch = tasksWithProjects.slice(i, i + BATCH_SIZE);
    const results = await Promise.allSettled(
      batch.map(async task => {
        try {
          const response = await apiClient.get<{
            tasks: Array<{
              id: number;
              annotations?: Array<{
                id: number; result?: unknown[]; created_at?: string;
                updated_at?: string; completed_by?: number;
                was_cancelled?: boolean; lead_time?: number;
              }>;
            }>;
          }>(API_ENDPOINTS.LABEL_STUDIO.TASKS(task.label_studio_project_id!));

          const annotations: ExportAnnotationResult[] = [];
          for (const lsTask of response.data.tasks || []) {
            for (const ann of lsTask.annotations || []) {
              annotations.push({
                id: ann.id, task_id: lsTask.id, result: ann.result || [],
                created_at: ann.created_at, updated_at: ann.updated_at,
                completed_by: ann.completed_by, was_cancelled: ann.was_cancelled,
                lead_time: ann.lead_time,
              });
            }
          }
          return { taskId: task.id, annotations };
        } catch {
          return { taskId: task.id, annotations: [] as ExportAnnotationResult[] };
        }
      })
    );
    for (const r of results) {
      if (r.status === 'fulfilled') annotationsMap.set(r.value.taskId, r.value.annotations);
    }
  }
  return annotationsMap;
}

export function useTaskExport() {
  const { t } = useTranslation(['tasks']);
  const { message } = App.useApp();
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);

  const handleExportCSV = useCallback((tasks: Task[]) => {
    if (!tasks.length) { message.warning(t('noTasksToExport')); return; }
    exportTasksToCSV(tasks, { includeId: true, includeDescription: false, includeLabelStudioId: false, includeSyncStatus: true, includeTags: false, t });
    message.success(t('exportSuccess'));
  }, [t, message]);

  const handleExportWithOptions = useCallback(async (options: ExportOptions, allTasks: Task[], selectedTasks: Task[]) => {
    setExportLoading(true);
    try {
      let tasksToExport: Task[];
      switch (options.range) {
        case 'selected': tasksToExport = selectedTasks; break;
        case 'filtered':
        case 'all':
        default: tasksToExport = allTasks; break;
      }
      if (!tasksToExport.length) {
        message.warning(t('noTasksToExport'));
        setExportModalOpen(false);
        return;
      }
      const filename = `tasks_export_${new Date().toISOString().split('T')[0]}`;

      switch (options.format) {
        case 'csv':
          exportTasksWithCustomFields(tasksToExport, options.fields as (keyof Task)[], { filename, t });
          message.success(t('exportSuccess'));
          break;
        case 'json': {
          const annotationsMap = options.includeAnnotations
            ? await fetchAnnotationsForTasks(tasksToExport) : new Map();
          exportTasksToJSON(tasksToExport, {
            includeAnnotations: options.includeAnnotations, includeProjectConfig: options.includeProjectConfig,
            includeSyncMetadata: options.includeSyncMetadata, filename, t, prettyPrint: true,
          }, annotationsMap);
          message.success(t('export.exportJsonSuccess'));
          break;
        }
        case 'excel':
          exportTasksToExcel(tasksToExport, {
            includeId: options.fields.includes('id'), includeDescription: options.fields.includes('description'),
            includeLabelStudioId: options.fields.includes('label_studio_project_id'),
            includeSyncStatus: options.fields.includes('label_studio_sync_status'),
            includeTags: options.fields.includes('tags'), includeSummary: true, includeChartsData: true, filename, t,
          });
          message.success(t('export.exportExcelSuccess'));
          break;
      }
      addExportHistoryEntry({
        format: options.format, range: options.range, taskCount: tasksToExport.length,
        fields: options.fields, filename: `${filename}.${options.format === 'excel' ? 'xlsx' : options.format}`,
      });
      setExportModalOpen(false);
    } catch {
      message.error(t('export.exportFailed') || 'Export failed');
    } finally {
      setExportLoading(false);
    }
  }, [t, message]);

  return { exportModalOpen, setExportModalOpen, exportLoading, handleExportCSV, handleExportWithOptions };
}
