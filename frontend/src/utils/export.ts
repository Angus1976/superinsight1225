/**
 * Export utility functions for task data
 * Supports CSV, JSON, and Excel export with proper escaping and i18n support
 */

import * as XLSX from 'xlsx';
import type { Task, TaskStatus, TaskPriority, AnnotationType, LabelStudioSyncStatus } from '@/types';

/**
 * CSV export options
 */
export interface CSVExportOptions {
  /** Include task ID column */
  includeId?: boolean;
  /** Include description column */
  includeDescription?: boolean;
  /** Include Label Studio project ID */
  includeLabelStudioId?: boolean;
  /** Include sync status */
  includeSyncStatus?: boolean;
  /** Include tags */
  includeTags?: boolean;
  /** Custom filename (without extension) */
  filename?: string;
  /** Translation function for headers */
  t?: (key: string) => string;
}

/**
 * Default CSV export options
 */
const defaultOptions: CSVExportOptions = {
  includeId: true,
  includeDescription: false,
  includeLabelStudioId: false,
  includeSyncStatus: true,
  includeTags: false,
};

/**
 * Escape a value for CSV format
 * Handles quotes, commas, and newlines
 */
export const escapeCSVValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return '';
  }
  
  const stringValue = String(value);
  
  // Check if escaping is needed
  const needsEscaping = 
    stringValue.includes(',') || 
    stringValue.includes('"') || 
    stringValue.includes('\n') ||
    stringValue.includes('\r');
  
  if (needsEscaping) {
    // Escape double quotes by doubling them
    const escaped = stringValue.replace(/"/g, '""');
    return `"${escaped}"`;
  }
  
  return stringValue;
};

/**
 * Format date for CSV export
 */
export const formatDateForCSV = (dateString?: string): string => {
  if (!dateString) return '';
  try {
    return new Date(dateString).toLocaleDateString();
  } catch {
    return dateString;
  }
};

/**
 * Format datetime for CSV export
 */
export const formatDateTimeForCSV = (dateString?: string): string => {
  if (!dateString) return '';
  try {
    return new Date(dateString).toLocaleString();
  } catch {
    return dateString;
  }
};

/**
 * Get translated status text
 */
const getStatusText = (status: TaskStatus, t?: (key: string) => string): string => {
  const statusMap: Record<TaskStatus, string> = {
    pending: t?.('statusPending') || 'Pending',
    in_progress: t?.('statusInProgress') || 'In Progress',
    completed: t?.('statusCompleted') || 'Completed',
    cancelled: t?.('statusCancelled') || 'Cancelled',
  };
  return statusMap[status] || status;
};

/**
 * Get translated priority text
 */
const getPriorityText = (priority: TaskPriority, t?: (key: string) => string): string => {
  const priorityMap: Record<TaskPriority, string> = {
    low: t?.('priorityLow') || 'Low',
    medium: t?.('priorityMedium') || 'Medium',
    high: t?.('priorityHigh') || 'High',
    urgent: t?.('priorityUrgent') || 'Urgent',
  };
  return priorityMap[priority] || priority;
};

/**
 * Get translated annotation type text
 */
const getAnnotationTypeText = (type: AnnotationType, t?: (key: string) => string): string => {
  const typeMap: Record<AnnotationType, string> = {
    text_classification: t?.('typeTextClassification') || 'Text Classification',
    ner: t?.('typeNER') || 'Named Entity Recognition',
    sentiment: t?.('typeSentiment') || 'Sentiment Analysis',
    qa: t?.('typeQA') || 'Question & Answer',
    custom: t?.('typeCustom') || 'Custom',
  };
  return typeMap[type] || type;
};

/**
 * Get translated sync status text
 */
const getSyncStatusText = (status?: string, t?: (key: string) => string): string => {
  if (!status) return t?.('syncStatusNotLinked') || 'Not Linked';
  
  const statusMap: Record<string, string> = {
    synced: t?.('syncStatusSynced') || 'Synced',
    pending: t?.('syncStatusPending') || 'Pending',
    failed: t?.('syncStatusFailed') || 'Failed',
  };
  return statusMap[status] || status;
};

/**
 * Build CSV headers based on options
 */
const buildCSVHeaders = (options: CSVExportOptions): string[] => {
  const { t, includeId, includeDescription, includeLabelStudioId, includeSyncStatus, includeTags } = options;
  
  const headers: string[] = [];
  
  if (includeId) {
    headers.push(t?.('tasks.columns.id') || 'ID');
  }
  
  headers.push(
    t?.('tasks.columns.name') || 'Name',
    t?.('tasks.columns.status') || 'Status',
    t?.('tasks.columns.priority') || 'Priority',
    t?.('tasks.columns.annotationType') || 'Annotation Type',
    t?.('tasks.columns.progress') || 'Progress',
    t?.('tasks.columns.completedItems') || 'Completed',
    t?.('tasks.columns.totalItems') || 'Total',
    t?.('tasks.columns.assignee') || 'Assignee',
    t?.('tasks.columns.createdAt') || 'Created At',
    t?.('tasks.columns.dueDate') || 'Due Date'
  );
  
  if (includeDescription) {
    headers.push(t?.('description') || 'Description');
  }
  
  if (includeSyncStatus) {
    headers.push(t?.('syncStatus') || 'Sync Status');
  }
  
  if (includeLabelStudioId) {
    headers.push(t?.('tasks.detail.projectId') || 'Label Studio Project ID');
  }
  
  if (includeTags) {
    headers.push(t?.('tagsLabel') || 'Tags');
  }
  
  return headers;
};

/**
 * Build CSV row for a task
 */
const buildCSVRow = (task: Task, options: CSVExportOptions): string[] => {
  const { t, includeId, includeDescription, includeLabelStudioId, includeSyncStatus, includeTags } = options;
  
  const row: string[] = [];
  
  if (includeId) {
    row.push(escapeCSVValue(task.id));
  }
  
  row.push(
    escapeCSVValue(task.name),
    escapeCSVValue(getStatusText(task.status, t)),
    escapeCSVValue(getPriorityText(task.priority, t)),
    escapeCSVValue(getAnnotationTypeText(task.annotation_type, t)),
    escapeCSVValue(`${task.progress}%`),
    escapeCSVValue(task.completed_items),
    escapeCSVValue(task.total_items),
    escapeCSVValue(task.assignee_name || ''),
    escapeCSVValue(formatDateForCSV(task.created_at)),
    escapeCSVValue(formatDateForCSV(task.due_date))
  );
  
  if (includeDescription) {
    row.push(escapeCSVValue(task.description || ''));
  }
  
  if (includeSyncStatus) {
    row.push(escapeCSVValue(getSyncStatusText(task.label_studio_sync_status, t)));
  }
  
  if (includeLabelStudioId) {
    row.push(escapeCSVValue(task.label_studio_project_id || ''));
  }
  
  if (includeTags) {
    row.push(escapeCSVValue(task.tags?.join(', ') || ''));
  }
  
  return row;
};

/**
 * Export tasks to CSV format
 * @param tasks - Array of tasks to export
 * @param options - Export options
 */
export const exportTasksToCSV = (
  tasks: Task[],
  options: CSVExportOptions = {}
): void => {
  const mergedOptions = { ...defaultOptions, ...options };
  
  // Build headers
  const headers = buildCSVHeaders(mergedOptions);
  
  // Build rows
  const rows = tasks.map(task => buildCSVRow(task, mergedOptions));
  
  // Combine into CSV content
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n');
  
  // Add BOM for Excel compatibility with UTF-8
  const BOM = '\uFEFF';
  const csvWithBOM = BOM + csvContent;
  
  // Create and download file
  const filename = mergedOptions.filename || `tasks_${new Date().toISOString().split('T')[0]}`;
  downloadFile(csvWithBOM, `${filename}.csv`, 'text/csv;charset=utf-8');
};

/**
 * Download a file with the given content
 */
export const downloadFile = (
  content: string,
  filename: string,
  mimeType: string
): void => {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';
  
  document.body.appendChild(link);
  link.click();
  
  // Cleanup
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Export tasks with custom field selection
 * @param tasks - Array of tasks to export
 * @param fields - Array of field names to include
 * @param options - Export options
 */
export const exportTasksWithCustomFields = (
  tasks: Task[],
  fields: (keyof Task)[],
  options: { filename?: string; t?: (key: string) => string } = {}
): void => {
  const { filename, t } = options;
  
  // Field to header mapping
  const fieldHeaders: Record<keyof Task, string> = {
    id: t?.('tasks.columns.id') || 'ID',
    name: t?.('tasks.columns.name') || 'Name',
    description: t?.('description') || 'Description',
    status: t?.('tasks.columns.status') || 'Status',
    priority: t?.('tasks.columns.priority') || 'Priority',
    annotation_type: t?.('tasks.columns.annotationType') || 'Annotation Type',
    assignee_id: t?.('assigneeId') || 'Assignee ID',
    assignee_name: t?.('tasks.columns.assignee') || 'Assignee',
    created_by: t?.('createdBy') || 'Created By',
    created_at: t?.('tasks.columns.createdAt') || 'Created At',
    updated_at: t?.('updatedAt') || 'Updated At',
    due_date: t?.('tasks.columns.dueDate') || 'Due Date',
    progress: t?.('tasks.columns.progress') || 'Progress',
    total_items: t?.('tasks.columns.totalItems') || 'Total Items',
    completed_items: t?.('tasks.columns.completedItems') || 'Completed Items',
    tenant_id: t?.('tenantId') || 'Tenant ID',
    label_studio_project_id: t?.('tasks.detail.projectId') || 'Label Studio Project ID',
    label_studio_sync_status: t?.('syncStatus') || 'Sync Status',
    label_studio_last_sync: t?.('lastSync') || 'Last Sync',
    label_studio_sync_error: t?.('syncError') || 'Sync Error',
    tags: t?.('tagsLabel') || 'Tags',
  };
  
  // Build headers
  const headers = fields.map(field => fieldHeaders[field] || String(field));
  
  // Build rows
  const rows = tasks.map(task => {
    return fields.map(field => {
      const value = task[field];
      
      // Special formatting for certain fields
      if (field === 'status') {
        return escapeCSVValue(getStatusText(value as TaskStatus, t));
      }
      if (field === 'priority') {
        return escapeCSVValue(getPriorityText(value as TaskPriority, t));
      }
      if (field === 'annotation_type') {
        return escapeCSVValue(getAnnotationTypeText(value as AnnotationType, t));
      }
      if (field === 'label_studio_sync_status') {
        return escapeCSVValue(getSyncStatusText(value as string, t));
      }
      if (field === 'progress') {
        return escapeCSVValue(`${value}%`);
      }
      if (field === 'created_at' || field === 'updated_at' || field === 'due_date' || field === 'label_studio_last_sync') {
        return escapeCSVValue(formatDateForCSV(value as string));
      }
      if (field === 'tags' && Array.isArray(value)) {
        return escapeCSVValue(value.join(', '));
      }
      
      return escapeCSVValue(value);
    });
  });
  
  // Combine into CSV content
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n');
  
  // Add BOM for Excel compatibility
  const BOM = '\uFEFF';
  const csvWithBOM = BOM + csvContent;
  
  // Download
  const exportFilename = filename || `tasks_${new Date().toISOString().split('T')[0]}`;
  downloadFile(csvWithBOM, `${exportFilename}.csv`, 'text/csv;charset=utf-8');
};


/**
 * JSON export options
 */
export interface JSONExportOptions {
  /** Include annotation results from Label Studio */
  includeAnnotations?: boolean;
  /** Include project configuration */
  includeProjectConfig?: boolean;
  /** Include sync metadata */
  includeSyncMetadata?: boolean;
  /** Custom filename (without extension) */
  filename?: string;
  /** Translation function for status/priority values */
  t?: (key: string) => string;
  /** Pretty print JSON (default: true) */
  prettyPrint?: boolean;
}

/**
 * Default JSON export options
 */
const defaultJSONOptions: JSONExportOptions = {
  includeAnnotations: true,
  includeProjectConfig: true,
  includeSyncMetadata: true,
  prettyPrint: true,
};

/**
 * Annotation result structure for JSON export
 */
export interface ExportAnnotationResult {
  id?: number;
  task_id: number;
  result: unknown[];
  created_at?: string;
  updated_at?: string;
  completed_by?: number;
  was_cancelled?: boolean;
  lead_time?: number;
}

/**
 * Project configuration for JSON export
 */
export interface ExportProjectConfig {
  project_id?: string;
  annotation_type: AnnotationType;
  label_config?: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * Sync metadata for JSON export
 */
export interface ExportSyncMetadata {
  sync_status?: LabelStudioSyncStatus;
  last_sync?: string;
  sync_error?: string;
}

/**
 * Complete task export structure for JSON
 */
export interface ExportTaskData {
  /** Task basic information */
  task: {
    id: string;
    name: string;
    description?: string;
    status: TaskStatus;
    status_text?: string;
    priority: TaskPriority;
    priority_text?: string;
    annotation_type: AnnotationType;
    annotation_type_text?: string;
    assignee_id?: string;
    assignee_name?: string;
    created_by: string;
    created_at: string;
    updated_at: string;
    due_date?: string;
    progress: number;
    total_items: number;
    completed_items: number;
    tenant_id: string;
    tags?: string[];
  };
  /** Project configuration (optional) */
  project_config?: ExportProjectConfig;
  /** Sync metadata (optional) */
  sync_metadata?: ExportSyncMetadata;
  /** Annotation results (optional) */
  annotations?: ExportAnnotationResult[];
}

/**
 * Batch export structure for JSON
 */
export interface ExportBatchData {
  /** Export metadata */
  export_info: {
    exported_at: string;
    total_tasks: number;
    export_version: string;
    include_annotations: boolean;
    include_project_config: boolean;
    include_sync_metadata: boolean;
  };
  /** Array of task data */
  tasks: ExportTaskData[];
  /** Summary statistics */
  summary: {
    total_tasks: number;
    by_status: Record<TaskStatus, number>;
    by_priority: Record<TaskPriority, number>;
    by_annotation_type: Record<AnnotationType, number>;
    total_items: number;
    completed_items: number;
    overall_progress: number;
  };
}

/**
 * Build export task data from a Task object
 */
const buildExportTaskData = (
  task: Task,
  options: JSONExportOptions,
  annotations?: ExportAnnotationResult[]
): ExportTaskData => {
  const { t, includeProjectConfig, includeSyncMetadata, includeAnnotations } = options;
  
  const exportData: ExportTaskData = {
    task: {
      id: task.id,
      name: task.name,
      description: task.description,
      status: task.status,
      status_text: t ? getStatusText(task.status, t) : undefined,
      priority: task.priority,
      priority_text: t ? getPriorityText(task.priority, t) : undefined,
      annotation_type: task.annotation_type,
      annotation_type_text: t ? getAnnotationTypeText(task.annotation_type, t) : undefined,
      assignee_id: task.assignee_id,
      assignee_name: task.assignee_name,
      created_by: task.created_by,
      created_at: task.created_at,
      updated_at: task.updated_at,
      due_date: task.due_date,
      progress: task.progress,
      total_items: task.total_items,
      completed_items: task.completed_items,
      tenant_id: task.tenant_id,
      tags: task.tags,
    },
  };
  
  // Include project configuration if requested
  if (includeProjectConfig) {
    exportData.project_config = {
      project_id: task.label_studio_project_id,
      annotation_type: task.annotation_type,
      created_at: task.created_at,
      updated_at: task.updated_at,
    };
  }
  
  // Include sync metadata if requested
  if (includeSyncMetadata) {
    exportData.sync_metadata = {
      sync_status: task.label_studio_sync_status,
      last_sync: task.label_studio_last_sync,
      sync_error: task.label_studio_sync_error,
    };
  }
  
  // Include annotations if provided and requested
  if (includeAnnotations && annotations) {
    exportData.annotations = annotations;
  }
  
  return exportData;
};

/**
 * Calculate summary statistics for batch export
 */
const calculateExportSummary = (tasks: Task[]): ExportBatchData['summary'] => {
  const byStatus: Record<TaskStatus, number> = {
    pending: 0,
    in_progress: 0,
    completed: 0,
    cancelled: 0,
  };
  
  const byPriority: Record<TaskPriority, number> = {
    low: 0,
    medium: 0,
    high: 0,
    urgent: 0,
  };
  
  const byAnnotationType: Record<AnnotationType, number> = {
    text_classification: 0,
    ner: 0,
    sentiment: 0,
    qa: 0,
    custom: 0,
  };
  
  let totalItems = 0;
  let completedItems = 0;
  
  for (const task of tasks) {
    byStatus[task.status]++;
    byPriority[task.priority]++;
    byAnnotationType[task.annotation_type]++;
    totalItems += task.total_items;
    completedItems += task.completed_items;
  }
  
  const overallProgress = totalItems > 0 
    ? Math.round((completedItems / totalItems) * 100) 
    : 0;
  
  return {
    total_tasks: tasks.length,
    by_status: byStatus,
    by_priority: byPriority,
    by_annotation_type: byAnnotationType,
    total_items: totalItems,
    completed_items: completedItems,
    overall_progress: overallProgress,
  };
};

/**
 * Export a single task to JSON format
 * @param task - Task to export
 * @param options - Export options
 * @param annotations - Optional annotation results
 */
export const exportTaskToJSON = (
  task: Task,
  options: JSONExportOptions = {},
  annotations?: ExportAnnotationResult[]
): void => {
  const mergedOptions = { ...defaultJSONOptions, ...options };
  
  const exportData = buildExportTaskData(task, mergedOptions, annotations);
  
  // Convert to JSON string
  const jsonContent = mergedOptions.prettyPrint 
    ? JSON.stringify(exportData, null, 2)
    : JSON.stringify(exportData);
  
  // Generate filename
  const filename = mergedOptions.filename || `task_${task.id}_${new Date().toISOString().split('T')[0]}`;
  
  // Download file
  downloadFile(jsonContent, `${filename}.json`, 'application/json;charset=utf-8');
};

/**
 * Export multiple tasks to JSON format (batch export)
 * @param tasks - Array of tasks to export
 * @param options - Export options
 * @param annotationsMap - Optional map of task ID to annotation results
 */
export const exportTasksToJSON = (
  tasks: Task[],
  options: JSONExportOptions = {},
  annotationsMap?: Map<string, ExportAnnotationResult[]>
): void => {
  const mergedOptions = { ...defaultJSONOptions, ...options };
  
  // Build export data for each task
  const taskDataArray = tasks.map(task => {
    const annotations = annotationsMap?.get(task.id);
    return buildExportTaskData(task, mergedOptions, annotations);
  });
  
  // Build batch export structure
  const batchExportData: ExportBatchData = {
    export_info: {
      exported_at: new Date().toISOString(),
      total_tasks: tasks.length,
      export_version: '1.0',
      include_annotations: mergedOptions.includeAnnotations ?? true,
      include_project_config: mergedOptions.includeProjectConfig ?? true,
      include_sync_metadata: mergedOptions.includeSyncMetadata ?? true,
    },
    tasks: taskDataArray,
    summary: calculateExportSummary(tasks),
  };
  
  // Convert to JSON string
  const jsonContent = mergedOptions.prettyPrint 
    ? JSON.stringify(batchExportData, null, 2)
    : JSON.stringify(batchExportData);
  
  // Generate filename
  const filename = mergedOptions.filename || `tasks_export_${new Date().toISOString().split('T')[0]}`;
  
  // Download file
  downloadFile(jsonContent, `${filename}.json`, 'application/json;charset=utf-8');
};

/**
 * Export tasks to JSON with fetched annotation results
 * This is an async version that fetches annotations from the API
 * @param tasks - Array of tasks to export
 * @param fetchAnnotations - Function to fetch annotations for a project
 * @param options - Export options
 */
export const exportTasksToJSONWithAnnotations = async (
  tasks: Task[],
  fetchAnnotations: (projectId: string) => Promise<ExportAnnotationResult[]>,
  options: JSONExportOptions = {}
): Promise<void> => {
  const mergedOptions = { ...defaultJSONOptions, ...options };
  
  // Fetch annotations for tasks that have Label Studio projects
  const annotationsMap = new Map<string, ExportAnnotationResult[]>();
  
  if (mergedOptions.includeAnnotations) {
    const tasksWithProjects = tasks.filter(t => t.label_studio_project_id);
    
    // Fetch annotations in parallel with concurrency limit
    const BATCH_SIZE = 5;
    for (let i = 0; i < tasksWithProjects.length; i += BATCH_SIZE) {
      const batch = tasksWithProjects.slice(i, i + BATCH_SIZE);
      const results = await Promise.allSettled(
        batch.map(async task => {
          const annotations = await fetchAnnotations(task.label_studio_project_id!);
          return { taskId: task.id, annotations };
        })
      );
      
      for (const result of results) {
        if (result.status === 'fulfilled') {
          annotationsMap.set(result.value.taskId, result.value.annotations);
        }
      }
    }
  }
  
  // Export with fetched annotations
  exportTasksToJSON(tasks, mergedOptions, annotationsMap);
};

/**
 * Validate JSON export data structure
 * Useful for testing and debugging
 */
export const validateJSONExportData = (data: unknown): data is ExportBatchData => {
  if (!data || typeof data !== 'object') return false;
  
  const batchData = data as ExportBatchData;
  
  // Check required fields
  if (!batchData.export_info || typeof batchData.export_info !== 'object') return false;
  if (!batchData.tasks || !Array.isArray(batchData.tasks)) return false;
  if (!batchData.summary || typeof batchData.summary !== 'object') return false;
  
  // Check export_info fields
  const { export_info } = batchData;
  if (typeof export_info.exported_at !== 'string') return false;
  if (typeof export_info.total_tasks !== 'number') return false;
  if (typeof export_info.export_version !== 'string') return false;
  
  // Check each task has required fields
  for (const taskData of batchData.tasks) {
    if (!taskData.task || typeof taskData.task !== 'object') return false;
    if (typeof taskData.task.id !== 'string') return false;
    if (typeof taskData.task.name !== 'string') return false;
  }
  
  return true;
};


/**
 * Excel export options
 */
export interface ExcelExportOptions {
  /** Include task ID column */
  includeId?: boolean;
  /** Include description column */
  includeDescription?: boolean;
  /** Include Label Studio project ID */
  includeLabelStudioId?: boolean;
  /** Include sync status */
  includeSyncStatus?: boolean;
  /** Include tags */
  includeTags?: boolean;
  /** Include summary statistics sheet */
  includeSummary?: boolean;
  /** Include charts data sheet */
  includeChartsData?: boolean;
  /** Custom filename (without extension) */
  filename?: string;
  /** Translation function for headers */
  t?: (key: string) => string;
}

/**
 * Default Excel export options
 */
const defaultExcelOptions: ExcelExportOptions = {
  includeId: true,
  includeDescription: false,
  includeLabelStudioId: false,
  includeSyncStatus: true,
  includeTags: false,
  includeSummary: true,
  includeChartsData: true,
};

/**
 * Summary statistics for Excel export
 */
interface ExcelSummaryStats {
  totalTasks: number;
  byStatus: Record<TaskStatus, number>;
  byPriority: Record<TaskPriority, number>;
  byAnnotationType: Record<AnnotationType, number>;
  totalItems: number;
  completedItems: number;
  overallProgress: number;
  overdueCount: number;
  nearDueCount: number;
  unassignedCount: number;
}

/**
 * Calculate summary statistics for Excel export
 */
const calculateExcelSummaryStats = (tasks: Task[]): ExcelSummaryStats => {
  const byStatus: Record<TaskStatus, number> = {
    pending: 0,
    in_progress: 0,
    completed: 0,
    cancelled: 0,
  };
  
  const byPriority: Record<TaskPriority, number> = {
    low: 0,
    medium: 0,
    high: 0,
    urgent: 0,
  };
  
  const byAnnotationType: Record<AnnotationType, number> = {
    text_classification: 0,
    ner: 0,
    sentiment: 0,
    qa: 0,
    custom: 0,
  };
  
  let totalItems = 0;
  let completedItems = 0;
  let overdueCount = 0;
  let nearDueCount = 0;
  let unassignedCount = 0;
  
  const now = new Date();
  const threeDaysFromNow = new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000);
  
  for (const task of tasks) {
    byStatus[task.status]++;
    byPriority[task.priority]++;
    byAnnotationType[task.annotation_type]++;
    totalItems += task.total_items;
    completedItems += task.completed_items;
    
    // Check overdue
    if (task.due_date && task.status !== 'completed') {
      const dueDate = new Date(task.due_date);
      if (dueDate < now) {
        overdueCount++;
      } else if (dueDate <= threeDaysFromNow) {
        nearDueCount++;
      }
    }
    
    // Check unassigned
    if (!task.assignee_id) {
      unassignedCount++;
    }
  }
  
  const overallProgress = totalItems > 0 
    ? Math.round((completedItems / totalItems) * 100) 
    : 0;
  
  return {
    totalTasks: tasks.length,
    byStatus,
    byPriority,
    byAnnotationType,
    totalItems,
    completedItems,
    overallProgress,
    overdueCount,
    nearDueCount,
    unassignedCount,
  };
};

/**
 * Build Excel headers for tasks sheet
 */
const buildExcelHeaders = (options: ExcelExportOptions): string[] => {
  const { t, includeId, includeDescription, includeLabelStudioId, includeSyncStatus, includeTags } = options;
  
  const headers: string[] = [];
  
  if (includeId) {
    headers.push(t?.('tasks.export.headers.id') || 'ID');
  }
  
  headers.push(
    t?.('tasks.export.headers.name') || 'Name',
    t?.('tasks.export.headers.status') || 'Status',
    t?.('tasks.export.headers.priority') || 'Priority',
    t?.('tasks.export.headers.annotationType') || 'Annotation Type',
    t?.('tasks.export.headers.progress') || 'Progress (%)',
    t?.('tasks.export.headers.completedItems') || 'Completed',
    t?.('tasks.export.headers.totalItems') || 'Total',
    t?.('tasks.export.headers.assignee') || 'Assignee',
    t?.('tasks.export.headers.createdAt') || 'Created At',
    t?.('tasks.export.headers.dueDate') || 'Due Date'
  );
  
  if (includeDescription) {
    headers.push(t?.('tasks.export.headers.description') || 'Description');
  }
  
  if (includeSyncStatus) {
    headers.push(t?.('tasks.export.headers.syncStatus') || 'Sync Status');
  }
  
  if (includeLabelStudioId) {
    headers.push(t?.('tasks.export.headers.labelStudioProjectId') || 'Label Studio Project ID');
  }
  
  if (includeTags) {
    headers.push(t?.('tasks.export.headers.tags') || 'Tags');
  }
  
  return headers;
};

/**
 * Build Excel row for a task
 */
const buildExcelRow = (task: Task, options: ExcelExportOptions): (string | number | Date | null)[] => {
  const { t, includeId, includeDescription, includeLabelStudioId, includeSyncStatus, includeTags } = options;
  
  const row: (string | number | Date | null)[] = [];
  
  if (includeId) {
    row.push(task.id);
  }
  
  row.push(
    task.name,
    getStatusText(task.status, t),
    getPriorityText(task.priority, t),
    getAnnotationTypeText(task.annotation_type, t),
    task.progress, // Number for Excel formatting
    task.completed_items,
    task.total_items,
    task.assignee_name || '',
    task.created_at ? new Date(task.created_at) : null,
    task.due_date ? new Date(task.due_date) : null
  );
  
  if (includeDescription) {
    row.push(task.description || '');
  }
  
  if (includeSyncStatus) {
    row.push(getSyncStatusText(task.label_studio_sync_status, t));
  }
  
  if (includeLabelStudioId) {
    row.push(task.label_studio_project_id || '');
  }
  
  if (includeTags) {
    row.push(task.tags?.join(', ') || '');
  }
  
  return row;
};

/**
 * Create summary sheet data
 */
const createSummarySheetData = (
  stats: ExcelSummaryStats,
  t?: (key: string) => string
): (string | number)[][] => {
  const data: (string | number)[][] = [];
  
  // Title
  data.push([t?.('tasks.export.excel.summaryTitle') || 'Task Summary Statistics']);
  data.push([]); // Empty row
  
  // Overview section
  data.push([t?.('tasks.export.excel.overview') || 'Overview']);
  data.push([t?.('tasks.export.excel.totalTasks') || 'Total Tasks', stats.totalTasks]);
  data.push([t?.('tasks.export.excel.totalItems') || 'Total Items', stats.totalItems]);
  data.push([t?.('tasks.export.excel.completedItems') || 'Completed Items', stats.completedItems]);
  data.push([t?.('tasks.export.excel.overallProgress') || 'Overall Progress (%)', stats.overallProgress]);
  data.push([t?.('tasks.export.excel.overdueCount') || 'Overdue Tasks', stats.overdueCount]);
  data.push([t?.('tasks.export.excel.nearDueCount') || 'Near Due Tasks', stats.nearDueCount]);
  data.push([t?.('tasks.export.excel.unassignedCount') || 'Unassigned Tasks', stats.unassignedCount]);
  data.push([]); // Empty row
  
  // Status breakdown
  data.push([t?.('tasks.export.excel.byStatus') || 'By Status']);
  data.push([t?.('statusPending') || 'Pending', stats.byStatus.pending]);
  data.push([t?.('statusInProgress') || 'In Progress', stats.byStatus.in_progress]);
  data.push([t?.('statusCompleted') || 'Completed', stats.byStatus.completed]);
  data.push([t?.('statusCancelled') || 'Cancelled', stats.byStatus.cancelled]);
  data.push([]); // Empty row
  
  // Priority breakdown
  data.push([t?.('tasks.export.excel.byPriority') || 'By Priority']);
  data.push([t?.('priorityLow') || 'Low', stats.byPriority.low]);
  data.push([t?.('priorityMedium') || 'Medium', stats.byPriority.medium]);
  data.push([t?.('priorityHigh') || 'High', stats.byPriority.high]);
  data.push([t?.('priorityUrgent') || 'Urgent', stats.byPriority.urgent]);
  data.push([]); // Empty row
  
  // Annotation type breakdown
  data.push([t?.('tasks.export.excel.byAnnotationType') || 'By Annotation Type']);
  data.push([t?.('typeTextClassification') || 'Text Classification', stats.byAnnotationType.text_classification]);
  data.push([t?.('typeNER') || 'Named Entity Recognition', stats.byAnnotationType.ner]);
  data.push([t?.('typeSentiment') || 'Sentiment Analysis', stats.byAnnotationType.sentiment]);
  data.push([t?.('typeQA') || 'Question & Answer', stats.byAnnotationType.qa]);
  data.push([t?.('typeCustom') || 'Custom', stats.byAnnotationType.custom]);
  
  return data;
};

/**
 * Create charts data sheet for visualization
 */
const createChartsDataSheet = (
  stats: ExcelSummaryStats,
  t?: (key: string) => string
): (string | number)[][] => {
  const data: (string | number)[][] = [];
  
  // Status chart data
  data.push([t?.('tasks.export.excel.statusChartData') || 'Status Distribution']);
  data.push([t?.('tasks.export.excel.category') || 'Category', t?.('tasks.export.excel.count') || 'Count', t?.('tasks.export.excel.percentage') || 'Percentage (%)']);
  const totalForStatus = stats.totalTasks || 1;
  data.push([t?.('statusPending') || 'Pending', stats.byStatus.pending, Math.round((stats.byStatus.pending / totalForStatus) * 100)]);
  data.push([t?.('statusInProgress') || 'In Progress', stats.byStatus.in_progress, Math.round((stats.byStatus.in_progress / totalForStatus) * 100)]);
  data.push([t?.('statusCompleted') || 'Completed', stats.byStatus.completed, Math.round((stats.byStatus.completed / totalForStatus) * 100)]);
  data.push([t?.('statusCancelled') || 'Cancelled', stats.byStatus.cancelled, Math.round((stats.byStatus.cancelled / totalForStatus) * 100)]);
  data.push([]); // Empty row
  
  // Priority chart data
  data.push([t?.('tasks.export.excel.priorityChartData') || 'Priority Distribution']);
  data.push([t?.('tasks.export.excel.category') || 'Category', t?.('tasks.export.excel.count') || 'Count', t?.('tasks.export.excel.percentage') || 'Percentage (%)']);
  data.push([t?.('priorityLow') || 'Low', stats.byPriority.low, Math.round((stats.byPriority.low / totalForStatus) * 100)]);
  data.push([t?.('priorityMedium') || 'Medium', stats.byPriority.medium, Math.round((stats.byPriority.medium / totalForStatus) * 100)]);
  data.push([t?.('priorityHigh') || 'High', stats.byPriority.high, Math.round((stats.byPriority.high / totalForStatus) * 100)]);
  data.push([t?.('priorityUrgent') || 'Urgent', stats.byPriority.urgent, Math.round((stats.byPriority.urgent / totalForStatus) * 100)]);
  data.push([]); // Empty row
  
  // Annotation type chart data
  data.push([t?.('tasks.export.excel.annotationTypeChartData') || 'Annotation Type Distribution']);
  data.push([t?.('tasks.export.excel.category') || 'Category', t?.('tasks.export.excel.count') || 'Count', t?.('tasks.export.excel.percentage') || 'Percentage (%)']);
  data.push([t?.('typeTextClassification') || 'Text Classification', stats.byAnnotationType.text_classification, Math.round((stats.byAnnotationType.text_classification / totalForStatus) * 100)]);
  data.push([t?.('typeNER') || 'Named Entity Recognition', stats.byAnnotationType.ner, Math.round((stats.byAnnotationType.ner / totalForStatus) * 100)]);
  data.push([t?.('typeSentiment') || 'Sentiment Analysis', stats.byAnnotationType.sentiment, Math.round((stats.byAnnotationType.sentiment / totalForStatus) * 100)]);
  data.push([t?.('typeQA') || 'Question & Answer', stats.byAnnotationType.qa, Math.round((stats.byAnnotationType.qa / totalForStatus) * 100)]);
  data.push([t?.('typeCustom') || 'Custom', stats.byAnnotationType.custom, Math.round((stats.byAnnotationType.custom / totalForStatus) * 100)]);
  data.push([]); // Empty row
  
  // Progress overview
  data.push([t?.('tasks.export.excel.progressOverview') || 'Progress Overview']);
  data.push([t?.('tasks.export.excel.metric') || 'Metric', t?.('tasks.export.excel.value') || 'Value']);
  data.push([t?.('tasks.export.excel.totalItems') || 'Total Items', stats.totalItems]);
  data.push([t?.('tasks.export.excel.completedItems') || 'Completed Items', stats.completedItems]);
  data.push([t?.('tasks.export.excel.remainingItems') || 'Remaining Items', stats.totalItems - stats.completedItems]);
  data.push([t?.('tasks.export.excel.completionRate') || 'Completion Rate (%)', stats.overallProgress]);
  
  return data;
};

/**
 * Apply column widths to worksheet
 */
const applyColumnWidths = (worksheet: XLSX.WorkSheet, headers: string[]): void => {
  const colWidths = headers.map(header => ({
    wch: Math.max(header.length + 2, 12) // Minimum width of 12
  }));
  worksheet['!cols'] = colWidths;
};

/**
 * Export tasks to Excel format with multiple sheets
 * @param tasks - Array of tasks to export
 * @param options - Export options
 */
export const exportTasksToExcel = (
  tasks: Task[],
  options: ExcelExportOptions = {}
): void => {
  const mergedOptions = { ...defaultExcelOptions, ...options };
  const { t, includeSummary, includeChartsData, filename } = mergedOptions;
  
  // Create workbook
  const workbook = XLSX.utils.book_new();
  
  // Build tasks sheet
  const headers = buildExcelHeaders(mergedOptions);
  const rows = tasks.map(task => buildExcelRow(task, mergedOptions));
  const tasksData = [headers, ...rows];
  
  const tasksSheet = XLSX.utils.aoa_to_sheet(tasksData);
  applyColumnWidths(tasksSheet, headers);
  
  // Format date columns (columns 9 and 10 for Created At and Due Date)
  // Note: Column indices depend on includeId option
  const dateFormat = 'yyyy-mm-dd';
  const startCol = mergedOptions.includeId ? 9 : 8;
  for (let row = 1; row <= tasks.length; row++) {
    const createdAtCell = XLSX.utils.encode_cell({ r: row, c: startCol });
    const dueDateCell = XLSX.utils.encode_cell({ r: row, c: startCol + 1 });
    
    if (tasksSheet[createdAtCell] && tasksSheet[createdAtCell].v instanceof Date) {
      tasksSheet[createdAtCell].z = dateFormat;
      tasksSheet[createdAtCell].t = 'd';
    }
    if (tasksSheet[dueDateCell] && tasksSheet[dueDateCell].v instanceof Date) {
      tasksSheet[dueDateCell].z = dateFormat;
      tasksSheet[dueDateCell].t = 'd';
    }
  }
  
  // Add tasks sheet
  XLSX.utils.book_append_sheet(
    workbook, 
    tasksSheet, 
    t?.('tasks.export.excel.tasksSheet') || 'Tasks'
  );
  
  // Calculate statistics
  const stats = calculateExcelSummaryStats(tasks);
  
  // Add summary sheet if requested
  if (includeSummary) {
    const summaryData = createSummarySheetData(stats, t);
    const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
    
    // Set column widths for summary sheet
    summarySheet['!cols'] = [{ wch: 25 }, { wch: 15 }];
    
    XLSX.utils.book_append_sheet(
      workbook, 
      summarySheet, 
      t?.('tasks.export.excel.summarySheet') || 'Summary'
    );
  }
  
  // Add charts data sheet if requested
  if (includeChartsData) {
    const chartsData = createChartsDataSheet(stats, t);
    const chartsSheet = XLSX.utils.aoa_to_sheet(chartsData);
    
    // Set column widths for charts sheet
    chartsSheet['!cols'] = [{ wch: 25 }, { wch: 12 }, { wch: 15 }];
    
    XLSX.utils.book_append_sheet(
      workbook, 
      chartsSheet, 
      t?.('tasks.export.excel.chartsSheet') || 'Charts Data'
    );
  }
  
  // Generate filename
  const exportFilename = filename || `tasks_export_${new Date().toISOString().split('T')[0]}`;
  
  // Write and download file
  XLSX.writeFile(workbook, `${exportFilename}.xlsx`);
};

/**
 * Export a single task to Excel format
 * @param task - Task to export
 * @param options - Export options
 */
export const exportTaskToExcel = (
  task: Task,
  options: ExcelExportOptions = {}
): void => {
  exportTasksToExcel([task], {
    ...options,
    includeSummary: false,
    includeChartsData: false,
    filename: options.filename || `task_${task.id}_${new Date().toISOString().split('T')[0]}`,
  });
};

/**
 * Validate Excel export options
 */
export const validateExcelExportOptions = (options: unknown): options is ExcelExportOptions => {
  if (!options || typeof options !== 'object') return true; // Empty options are valid
  
  const opts = options as Record<string, unknown>;
  
  // Check boolean options
  const booleanKeys = [
    'includeId', 'includeDescription', 'includeLabelStudioId',
    'includeSyncStatus', 'includeTags', 'includeSummary', 'includeChartsData'
  ];
  
  for (const key of booleanKeys) {
    if (key in opts && typeof opts[key] !== 'boolean' && opts[key] !== undefined) {
      return false;
    }
  }
  
  // Check filename
  if ('filename' in opts && typeof opts.filename !== 'string' && opts.filename !== undefined) {
    return false;
  }
  
  // Check translation function
  if ('t' in opts && typeof opts.t !== 'function' && opts.t !== undefined) {
    return false;
  }
  
  return true;
};
