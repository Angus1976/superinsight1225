// Tasks list page
import { useState, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ProTable, type ProColumns, type ActionType } from '@ant-design/pro-components';
import { 
  Button, 
  Tag, 
  Space, 
  App,
  Progress, 
  Dropdown, 
  Select,
  Input,
  DatePicker,
  Tooltip,
  Badge,
  Card,
  Statistic,
  Row,
  Col,
  Modal
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  MoreOutlined,
  ExclamationCircleOutlined,
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  DownloadOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  TagOutlined,
  UserOutlined,
  CalendarOutlined,
  BarChartOutlined,
  SyncOutlined,
  LinkOutlined,
  DisconnectOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useTasks, useDeleteTask, useBatchDeleteTasks, useUpdateTask, useTaskStats } from '@/hooks/useTask';
import { TaskCreateModal } from './TaskCreateModal';
import { TaskEditModal } from './TaskEditModal';
import { BatchEditModal } from './BatchEditModal';
import { TaskDeleteModal } from './TaskDeleteModal';
import { ExportOptionsModal, addExportHistoryEntry } from '@/components/Tasks';
import type { ExportOptions, ExportField } from '@/components/Tasks';
import { apiClient } from '@/services';
import { exportTasksToCSV, exportTasksToJSON, exportTasksToExcel, exportTasksWithCustomFields } from '@/utils/export';
import { API_ENDPOINTS } from '@/constants';
import type { Task, TaskStatus, TaskPriority } from '@/types';
import type { ExportAnnotationResult } from '@/utils/export';

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

// Annotation result from Label Studio
interface LabelStudioAnnotation {
  id: number;
  created_at: string;
  updated_at: string;
  completed_by?: number;
  result?: unknown[];
  was_cancelled?: boolean;
  ground_truth?: boolean;
  lead_time?: number; // Time spent on annotation in seconds
}

// Extended project details from Label Studio API
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

// Annotation quality metrics
interface AnnotationQualityMetrics {
  totalAnnotations: number;
  avgLeadTime: number; // Average time per annotation in seconds
  completionRate: number; // Percentage of tasks with annotations
  annotatorCount: number; // Number of unique annotators
}

// Cache for Label Studio API responses
interface SyncCache {
  projects: Map<number, LabelStudioProject>;
  projectTasks: Map<number, LabelStudioTask[]>;
  lastFetch: number;
}

// Cache TTL: 30 seconds
const CACHE_TTL = 30 * 1000;

// Global cache instance
let syncCache: SyncCache = {
  projects: new Map(),
  projectTasks: new Map(),
  lastFetch: 0,
};

/**
 * Calculate annotation quality metrics from Label Studio tasks
 * @param tasks - Array of Label Studio tasks with annotations
 * @returns Annotation quality metrics
 */
const calculateAnnotationQuality = (tasks: LabelStudioTask[]): AnnotationQualityMetrics => {
  let totalAnnotations = 0;
  let totalLeadTime = 0;
  let annotationsWithLeadTime = 0;
  const annotatorIds = new Set<number>();
  
  for (const task of tasks) {
    if (task.annotations && task.annotations.length > 0) {
      for (const annotation of task.annotations) {
        totalAnnotations++;
        
        // Track lead time (time spent on annotation)
        if (annotation.lead_time && annotation.lead_time > 0) {
          totalLeadTime += annotation.lead_time;
          annotationsWithLeadTime++;
        }
        
        // Track unique annotators
        if (annotation.completed_by) {
          annotatorIds.add(annotation.completed_by);
        }
      }
    }
    
    // Also count from total_annotations if available
    if (task.total_annotations && task.total_annotations > 0 && (!task.annotations || task.annotations.length === 0)) {
      totalAnnotations += task.total_annotations;
    }
  }
  
  const tasksWithAnnotations = tasks.filter(t => t.is_labeled).length;
  const completionRate = tasks.length > 0 
    ? Math.round((tasksWithAnnotations / tasks.length) * 100) 
    : 0;
  
  const avgLeadTime = annotationsWithLeadTime > 0 
    ? Math.round(totalLeadTime / annotationsWithLeadTime) 
    : 0;
  
  return {
    totalAnnotations,
    avgLeadTime,
    completionRate,
    annotatorCount: annotatorIds.size,
  };
};

// Sync progress state
interface SyncProgress {
  current: number;
  total: number;
  status: 'idle' | 'syncing' | 'completed' | 'error';
  message: string;
}

const statusColorMap: Record<TaskStatus, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  cancelled: 'error',
};

const priorityColorMap: Record<TaskPriority, string> = {
  low: 'green',
  medium: 'blue',
  high: 'orange',
  urgent: 'red',
};

const TasksPage: React.FC = () => {
  const { t } = useTranslation(['tasks', 'common']);
  const navigate = useNavigate();
  const { modal, message } = App.useApp();
  const actionRef = useRef<ActionType>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [currentParams, setCurrentParams] = useState({});
  const [batchAction, setBatchAction] = useState<string>('');
  const [syncProgress, setSyncProgress] = useState<SyncProgress>({
    current: 0,
    total: 0,
    status: 'idle',
    message: '',
  });
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editTaskId, setEditTaskId] = useState<string | null>(null);
  const [batchEditModalOpen, setBatchEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [tasksToDelete, setTasksToDelete] = useState<Task[]>([]);

  const { data, isLoading, refetch } = useTasks(currentParams);
  const { data: stats } = useTaskStats();
  const deleteTask = useDeleteTask();
  const batchDeleteTasks = useBatchDeleteTasks();
  const updateTask = useUpdateTask();

  // Check if cache is valid
  const isCacheValid = useCallback(() => {
    return Date.now() - syncCache.lastFetch < CACHE_TTL;
  }, []);

  // Clear cache
  const clearCache = useCallback(() => {
    syncCache = {
      projects: new Map(),
      projectTasks: new Map(),
      lastFetch: 0,
    };
  }, []);

  // Fetch all Label Studio projects with caching
  const fetchLabelStudioProjects = useCallback(async (forceRefresh = false): Promise<LabelStudioProject[]> => {
    if (!forceRefresh && isCacheValid() && syncCache.projects.size > 0) {
      console.log('[fetchLabelStudioProjects] Using cached projects');
      return Array.from(syncCache.projects.values());
    }

    console.log('[fetchLabelStudioProjects] Fetching from API...');
    const response = await apiClient.get<{ results: LabelStudioProject[] }>(
      API_ENDPOINTS.LABEL_STUDIO.PROJECTS
    );
    const projects = response.data.results || [];
    
    // Update cache
    syncCache.projects.clear();
    projects.forEach(p => syncCache.projects.set(p.id, p));
    syncCache.lastFetch = Date.now();
    
    return projects;
  }, [isCacheValid]);

  // Batch fetch tasks for multiple projects
  const batchFetchProjectTasks = useCallback(async (
    projectIds: number[],
    forceRefresh = false
  ): Promise<Map<number, LabelStudioTask[]>> => {
    const result = new Map<number, LabelStudioTask[]>();
    const projectsToFetch: number[] = [];

    // Check cache for each project
    for (const projectId of projectIds) {
      if (!forceRefresh && isCacheValid() && syncCache.projectTasks.has(projectId)) {
        result.set(projectId, syncCache.projectTasks.get(projectId)!);
      } else {
        projectsToFetch.push(projectId);
      }
    }

    if (projectsToFetch.length === 0) {
      console.log('[batchFetchProjectTasks] All projects found in cache');
      return result;
    }

    console.log(`[batchFetchProjectTasks] Fetching ${projectsToFetch.length} projects from API...`);

    // Batch fetch with concurrency limit (5 concurrent requests)
    const BATCH_SIZE = 5;
    for (let i = 0; i < projectsToFetch.length; i += BATCH_SIZE) {
      const batch = projectsToFetch.slice(i, i + BATCH_SIZE);
      const batchResults = await Promise.allSettled(
        batch.map(async (projectId) => {
          const response = await apiClient.get<{ tasks: LabelStudioTask[] }>(
            API_ENDPOINTS.LABEL_STUDIO.TASKS(String(projectId))
          );
          return { projectId, tasks: response.data.tasks || [] };
        })
      );

      // Process results
      for (const settledResult of batchResults) {
        if (settledResult.status === 'fulfilled') {
          const { projectId, tasks } = settledResult.value;
          result.set(projectId, tasks);
          syncCache.projectTasks.set(projectId, tasks);
        }
      }
    }

    return result;
  }, [isCacheValid]);

  // Determine which tasks need syncing (incremental sync)
  const getTasksNeedingSync = useCallback((
    localTasks: Task[],
    lsProjects: LabelStudioProject[]
  ): Task[] => {
    const projectMapById = new Map(lsProjects.map(p => [p.id, p]));
    const projectMapByTitle = new Map(lsProjects.map(p => [p.title.toLowerCase().trim(), p]));

    return localTasks.filter(task => {
      // Task needs sync if:
      // 1. It has a project ID and the project exists
      // 2. It doesn't have a project ID but a matching project exists by name
      // 3. It hasn't been synced recently (check last_sync timestamp)
      
      const projectId = task.label_studio_project_id;
      
      if (projectId) {
        const project = projectMapById.get(Number(projectId));
        if (!project) return false; // Project doesn't exist, skip
        
        // Check if sync is needed based on last sync time
        if (task.label_studio_last_sync) {
          const lastSync = new Date(task.label_studio_last_sync).getTime();
          const syncAge = Date.now() - lastSync;
          // Skip if synced within last 5 minutes and status is 'synced'
          if (syncAge < 5 * 60 * 1000 && task.label_studio_sync_status === 'synced') {
            return false;
          }
        }
        return true;
      }
      
      // Try to find matching project by name
      const matchingProject = projectMapByTitle.get(task.name.toLowerCase().trim());
      return !!matchingProject;
    });
  }, []);

  // Sync a single task with Label Studio - includes project details sync and annotation results
  const handleSyncSingleTask = useCallback(async (task: Task) => {
    const projectId = task.label_studio_project_id;
    
    if (!projectId) {
      message.warning(t('syncTaskNoProject'));
      return;
    }
    
    const hide = message.loading(t('syncingSingleTask'), 0);
    
    try {
      // 1. Fetch project details (name, description, updated_at)
      const projectResponse = await apiClient.get<LabelStudioProjectDetails>(
        API_ENDPOINTS.LABEL_STUDIO.PROJECT_BY_ID(projectId)
      );
      const projectDetails = projectResponse.data;
      
      // 2. Fetch tasks for this project to calculate progress and annotation results
      const tasksResponse = await apiClient.get<{ tasks: LabelStudioTask[] }>(
        API_ENDPOINTS.LABEL_STUDIO.TASKS(projectId)
      );
      const lsTasks = tasksResponse.data.tasks || [];
      
      // 3. Calculate progress from tasks
      const totalTasks = lsTasks.length;
      const completedTasks = lsTasks.filter(t => t.is_labeled).length;
      const progress = totalTasks > 0 
        ? Math.round((completedTasks / totalTasks) * 100) 
        : 0;
      
      // 4. Calculate annotation quality metrics
      const qualityMetrics = calculateAnnotationQuality(lsTasks);
      console.log('[handleSyncSingleTask] Quality metrics:', qualityMetrics);
      
      // 5. Build update payload with project details and annotation results
      const updatePayload: {
        name?: string;
        description?: string;
        total_items: number;
        completed_items: number;
        progress: number;
        label_studio_sync_status: 'synced' | 'pending' | 'failed';
        label_studio_last_sync: string;
        label_studio_sync_error?: string;
      } = {
        total_items: totalTasks,
        completed_items: completedTasks,
        progress: progress,
        label_studio_sync_status: 'synced',
        label_studio_last_sync: projectDetails.updated_at || new Date().toISOString(),
        label_studio_sync_error: '', // Clear any previous error on successful sync
      };
      
      // 6. Sync project name if available and different
      if (projectDetails.title && projectDetails.title !== task.name) {
        // Only update name if it's from Label Studio and meaningful
        // Don't overwrite if the project title is just a generic name
        const isGenericTitle = /^Project \d+$/.test(projectDetails.title);
        if (!isGenericTitle) {
          updatePayload.name = projectDetails.title;
        }
      }
      
      // 7. Sync project description if available
      if (projectDetails.description !== undefined) {
        updatePayload.description = projectDetails.description || '';
      }
      
      // 8. Update task with synced data
      await updateTask.mutateAsync({
        id: task.id,
        payload: updatePayload
      });
      
      hide();
      
      // Show detailed sync result with annotation quality info
      const syncDetails = [];
      if (updatePayload.name) {
        syncDetails.push(t('syncedProjectName'));
      }
      if (updatePayload.description !== undefined) {
        syncDetails.push(t('syncedProjectDescription'));
      }
      syncDetails.push(`${t('progress')}: ${progress}%`);
      syncDetails.push(`${t('totalItems')}: ${totalTasks}`);
      syncDetails.push(`${t('completed')}: ${completedTasks}`);
      
      // Add annotation quality info to log
      if (qualityMetrics.totalAnnotations > 0) {
        syncDetails.push(`${t('syncedAnnotations')}: ${qualityMetrics.totalAnnotations}`);
        if (qualityMetrics.avgLeadTime > 0) {
          syncDetails.push(`${t('syncedAvgTime')}: ${Math.round(qualityMetrics.avgLeadTime / 60)}min`);
        }
        if (qualityMetrics.annotatorCount > 0) {
          syncDetails.push(`${t('syncedAnnotators')}: ${qualityMetrics.annotatorCount}`);
        }
      }
      
      message.success(t('syncSingleTaskSuccess', { progress }));
      console.log('[handleSyncSingleTask] Synced details:', syncDetails.join(', '));
      
      refetch();
      
    } catch (error) {
      hide();
      console.error('[handleSyncSingleTask] Failed:', error);
      
      // Extract error message for display
      const errorMessage = error instanceof Error 
        ? error.message 
        : (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t('syncSingleTaskFailed');
      
      // Update status to failed with error message
      try {
        await updateTask.mutateAsync({
          id: task.id,
          payload: {
            label_studio_sync_status: 'failed',
            label_studio_last_sync: new Date().toISOString(),
            label_studio_sync_error: errorMessage,
          }
        });
      } catch (updateError) {
        console.error('[handleSyncSingleTask] Failed to update status:', updateError);
      }
      
      message.error(t('syncSingleTaskFailed'));
      refetch();
    }
  }, [t, updateTask, refetch, message]);

  // Handle single task delete with enhanced modal
  const handleDelete = (id: string) => {
    const task = (data?.items || []).find(t => t.id === id);
    if (task) {
      setTasksToDelete([task]);
      setDeleteModalOpen(true);
    }
  };

  // Handle opening edit modal
  const handleEdit = (taskId: string) => {
    setEditTaskId(taskId);
    setEditModalOpen(true);
  };

  // Handle opening batch edit modal
  const handleBatchEdit = () => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('selectTasksToUpdate'));
      return;
    }
    setBatchEditModalOpen(true);
  };

  // Get selected tasks for batch edit
  const getSelectedTasks = () => {
    return (data?.items || []).filter(task => selectedRowKeys.includes(task.id));
  };

  // Handle batch delete with enhanced modal
  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('selectTasksToDelete'));
      return;
    }
    const tasks = (data?.items || []).filter(task => selectedRowKeys.includes(task.id));
    setTasksToDelete(tasks);
    setDeleteModalOpen(true);
  };

  // Handle delete success callback
  const handleDeleteSuccess = (deletedIds: string[]) => {
    setDeleteModalOpen(false);
    setTasksToDelete([]);
    // Clear selection if batch delete
    if (deletedIds.length > 1) {
      setSelectedRowKeys(prev => prev.filter(id => !deletedIds.includes(id)));
    }
    refetch();
    message.success(t('tasks.delete.result.success', { count: deletedIds.length }));
  };

  const handleBatchStatusUpdate = async (status: TaskStatus) => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('selectTasksToUpdate'));
      return;
    }
    
    try {
      // Update each selected task
      await Promise.all(
        selectedRowKeys.map(id => 
          updateTask.mutateAsync({ id, payload: { status } })
        )
      );
      setSelectedRowKeys([]);
      refetch();
      message.success(t('batchUpdateSuccess'));
    } catch (error) {
      message.error(t('batchUpdateError'));
    }
  };

  const handleSyncAllTasks = async () => {
    // Show sync progress modal
    setSyncModalOpen(true);
    setSyncProgress({
      current: 0,
      total: 0,
      status: 'syncing',
      message: t('syncingTasks'),
    });
    
    try {
      // 1. Fetch Label Studio projects (with caching)
      console.log('[handleSyncAllTasks] Fetching Label Studio projects...');
      setSyncProgress(prev => ({ ...prev, message: t('syncFetchingProjects') || 'Fetching projects...' }));
      
      const lsProjects = await fetchLabelStudioProjects();
      console.log('[handleSyncAllTasks] Found', lsProjects.length, 'Label Studio projects');
      
      // 2. Get local tasks list
      const localTasks = data?.items || [];
      
      if (localTasks.length === 0) {
        setSyncProgress({
          current: 0,
          total: 0,
          status: 'completed',
          message: t('noTasksToSync'),
        });
        return;
      }
      
      // 3. Determine which tasks need syncing (incremental sync)
      const tasksToSync = getTasksNeedingSync(localTasks, lsProjects);
      
      if (tasksToSync.length === 0) {
        setSyncProgress({
          current: 0,
          total: 0,
          status: 'completed',
          message: t('allTasksSynced'),
        });
        return;
      }
      
      console.log(`[handleSyncAllTasks] ${tasksToSync.length} tasks need syncing (${localTasks.length - tasksToSync.length} skipped)`);
      
      // 4. Create project mappings
      const projectMapById = new Map(lsProjects.map(p => [p.id, p]));
      const projectMapByTitle = new Map(lsProjects.map(p => [p.title.toLowerCase().trim(), p]));
      
      // 5. Collect all project IDs that need task fetching
      const projectIdsToFetch = new Set<number>();
      const taskProjectMapping = new Map<string, number>(); // task.id -> projectId
      
      for (const task of tasksToSync) {
        let projectId = task.label_studio_project_id ? Number(task.label_studio_project_id) : null;
        
        if (!projectId) {
          const matchingProject = projectMapByTitle.get(task.name.toLowerCase().trim());
          if (matchingProject) {
            projectId = matchingProject.id;
          }
        }
        
        if (projectId && projectMapById.has(projectId)) {
          projectIdsToFetch.add(projectId);
          taskProjectMapping.set(task.id, projectId);
        }
      }
      
      // 6. Batch fetch all project tasks at once
      setSyncProgress(prev => ({ 
        ...prev, 
        message: t('syncFetchingTasks') || `Fetching tasks for ${projectIdsToFetch.size} projects...`,
        total: tasksToSync.length,
      }));
      
      const projectTasksMap = await batchFetchProjectTasks(Array.from(projectIdsToFetch));
      
      // 7. Process tasks in batches for updates
      let successCount = 0;
      let failCount = 0;
      let skippedCount = 0;
      let linkedCount = 0;
      
      const UPDATE_BATCH_SIZE = 10;
      const updatePromises: Promise<void>[] = [];
      
      for (let i = 0; i < tasksToSync.length; i++) {
        const task = tasksToSync[i];
        
        // Update progress
        setSyncProgress(prev => ({
          ...prev,
          current: i + 1,
          message: t('syncProgressMessage', { current: i + 1, total: tasksToSync.length }) || 
            `Syncing task ${i + 1} of ${tasksToSync.length}...`,
        }));
        
        const updatePromise = (async () => {
          try {
            let projectId = task.label_studio_project_id ? Number(task.label_studio_project_id) : null;
            let wasLinked = false;
            
            // Try to find matching project by name if no project ID
            if (!projectId) {
              const matchingProject = projectMapByTitle.get(task.name.toLowerCase().trim());
              if (matchingProject) {
                projectId = matchingProject.id;
                wasLinked = true;
                console.log(`[handleSyncAllTasks] Linking task "${task.name}" to project ${projectId}`);
              } else {
                skippedCount++;
                return;
              }
            }
            
            // Get project details from cache for name/description sync
            const projectDetails = projectMapById.get(projectId);
            
            // Get project tasks from cache
            const lsTasks = projectTasksMap.get(projectId);
            
            if (!lsTasks) {
              console.warn(`[handleSyncAllTasks] No tasks found for project ${projectId}`);
              
              await updateTask.mutateAsync({
                id: task.id,
                payload: {
                  label_studio_sync_status: 'failed',
                  label_studio_last_sync: new Date().toISOString(),
                  label_studio_sync_error: t('syncErrorNoTasks'),
                }
              });
              
              failCount++;
              return;
            }
            
            // Calculate progress
            const totalTasks = lsTasks.length;
            const completedTasks = lsTasks.filter(t => t.is_labeled).length;
            const progress = totalTasks > 0 
              ? Math.round((completedTasks / totalTasks) * 100) 
              : 0;
            
            // Calculate annotation quality metrics
            const qualityMetrics = calculateAnnotationQuality(lsTasks);
            
            // Build update payload with project details and annotation results
            const updatePayload: {
              name?: string;
              description?: string;
              total_items: number;
              completed_items: number;
              progress: number;
              label_studio_sync_status: 'synced' | 'pending' | 'failed';
              label_studio_last_sync: string;
              label_studio_project_id?: string;
            } = {
              total_items: totalTasks,
              completed_items: completedTasks,
              progress: progress,
              label_studio_sync_status: 'synced',
              label_studio_last_sync: new Date().toISOString(),
            };
            
            // Sync project name if available and meaningful
            if (projectDetails?.title && projectDetails.title !== task.name) {
              const isGenericTitle = /^Project \d+$/.test(projectDetails.title);
              if (!isGenericTitle) {
                updatePayload.name = projectDetails.title;
              }
            }
            
            if (wasLinked) {
              updatePayload.label_studio_project_id = String(projectId);
            }
            
            await updateTask.mutateAsync({
              id: task.id,
              payload: updatePayload
            });
            
            if (wasLinked) linkedCount++;
            successCount++;
            
            // Log with annotation quality info
            const qualityInfo = qualityMetrics.totalAnnotations > 0 
              ? `, annotations=${qualityMetrics.totalAnnotations}, annotators=${qualityMetrics.annotatorCount}`
              : '';
            console.log(`[handleSyncAllTasks] Task "${task.name}" synced: ${completedTasks}/${totalTasks} (${progress}%)${qualityInfo}`);
            
          } catch (error) {
            console.error(`[handleSyncAllTasks] Failed to sync task ${task.id}:`, error);
            
            // Extract error message
            const errorMessage = error instanceof Error 
              ? error.message 
              : (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t('syncError');
            
            try {
              await updateTask.mutateAsync({
                id: task.id,
                payload: {
                  label_studio_sync_status: 'failed',
                  label_studio_last_sync: new Date().toISOString(),
                  label_studio_sync_error: errorMessage,
                }
              });
            } catch (updateError) {
              console.error(`[handleSyncAllTasks] Failed to update task ${task.id} status:`, updateError);
            }
            
            failCount++;
          }
        })();
        
        updatePromises.push(updatePromise);
        
        // Process in batches to avoid overwhelming the server
        if (updatePromises.length >= UPDATE_BATCH_SIZE || i === tasksToSync.length - 1) {
          await Promise.all(updatePromises);
          updatePromises.length = 0;
        }
      }
      
      // 8. Show final result
      const totalSkipped = localTasks.length - tasksToSync.length + skippedCount;
      
      setSyncProgress({
        current: tasksToSync.length,
        total: tasksToSync.length,
        status: failCount > 0 ? 'error' : 'completed',
        message: failCount === 0 && successCount > 0
          ? (linkedCount > 0 
              ? t('syncSuccessWithLinked', { count: successCount, linked: linkedCount })
              : t('syncSuccess', { count: successCount }))
          : failCount > 0
            ? t('syncPartialSuccess', { success: successCount, fail: failCount })
            : t('allTasksSynced'),
      });
      
      console.log(`[handleSyncAllTasks] Sync completed: success=${successCount}, failed=${failCount}, skipped=${totalSkipped}, linked=${linkedCount}`);
      
      // 9. Refresh list
      refetch();
      
    } catch (error) {
      console.error('[handleSyncAllTasks] Sync failed:', error);
      setSyncProgress({
        current: 0,
        total: 0,
        status: 'error',
        message: t('syncError'),
      });
    }
  };

  const handleExportTasks = () => {
    // Export selected tasks or all tasks as CSV
    const tasksToExport = selectedRowKeys.length > 0 
      ? (data?.items || []).filter(task => selectedRowKeys.includes(task.id))
      : (data?.items || []);
    
    if (tasksToExport.length === 0) {
      message.warning(t('noTasksToExport'));
      return;
    }
    
    // Use the export utility with i18n support
    exportTasksToCSV(tasksToExport, {
      includeId: true,
      includeDescription: false,
      includeLabelStudioId: false,
      includeSyncStatus: true,
      includeTags: false,
      t: t,
    });
    
    message.success(t('exportSuccess'));
  };

  // JSON export handler with annotation results
  const handleExportTasksToJSON = async (includeAnnotations: boolean = true) => {
    // Export selected tasks or all tasks as JSON
    const tasksToExport = selectedRowKeys.length > 0 
      ? (data?.items || []).filter(task => selectedRowKeys.includes(task.id))
      : (data?.items || []);
    
    if (tasksToExport.length === 0) {
      message.warning(t('noTasksToExport'));
      return;
    }
    
    const hide = message.loading(t('tasks.export.exportingJson') || 'Exporting JSON data...', 0);
    
    try {
      // Fetch annotations for tasks with Label Studio projects if requested
      const annotationsMap = new Map<string, ExportAnnotationResult[]>();
      
      if (includeAnnotations) {
        const tasksWithProjects = tasksToExport.filter(task => task.label_studio_project_id);
        
        // Fetch annotations in batches
        const BATCH_SIZE = 5;
        for (let i = 0; i < tasksWithProjects.length; i += BATCH_SIZE) {
          const batch = tasksWithProjects.slice(i, i + BATCH_SIZE);
          const results = await Promise.allSettled(
            batch.map(async task => {
              try {
                const response = await apiClient.get<{ tasks: Array<{ id: number; annotations?: Array<{ id: number; result?: unknown[]; created_at?: string; updated_at?: string; completed_by?: number; was_cancelled?: boolean; lead_time?: number }> }> }>(
                  API_ENDPOINTS.LABEL_STUDIO.TASKS(task.label_studio_project_id!)
                );
                
                // Extract annotations from all tasks in the project
                const annotations: ExportAnnotationResult[] = [];
                const lsTasks = response.data.tasks || [];
                
                for (const lsTask of lsTasks) {
                  if (lsTask.annotations && lsTask.annotations.length > 0) {
                    for (const annotation of lsTask.annotations) {
                      annotations.push({
                        id: annotation.id,
                        task_id: lsTask.id,
                        result: annotation.result || [],
                        created_at: annotation.created_at,
                        updated_at: annotation.updated_at,
                        completed_by: annotation.completed_by,
                        was_cancelled: annotation.was_cancelled,
                        lead_time: annotation.lead_time,
                      });
                    }
                  }
                }
                
                return { taskId: task.id, annotations };
              } catch (error) {
                console.error(`Failed to fetch annotations for task ${task.id}:`, error);
                return { taskId: task.id, annotations: [] };
              }
            })
          );
          
          for (const result of results) {
            if (result.status === 'fulfilled') {
              annotationsMap.set(result.value.taskId, result.value.annotations);
            }
          }
        }
      }
      
      // Export to JSON with annotations
      exportTasksToJSON(tasksToExport, {
        includeAnnotations,
        includeProjectConfig: true,
        includeSyncMetadata: true,
        t: t,
        prettyPrint: true,
      }, annotationsMap);
      
      hide();
      message.success(t('tasks.export.exportJsonSuccess') || 'JSON export successful');
      
    } catch (error) {
      hide();
      console.error('JSON export failed:', error);
      message.error(t('tasks.export.exportJsonFailed') || 'JSON export failed');
    }
  };

  // Excel export handler
  const handleExportTasksToExcel = () => {
    // Export selected tasks or all tasks as Excel
    const tasksToExport = selectedRowKeys.length > 0 
      ? (data?.items || []).filter(task => selectedRowKeys.includes(task.id))
      : (data?.items || []);
    
    if (tasksToExport.length === 0) {
      message.warning(t('noTasksToExport'));
      return;
    }
    
    try {
      exportTasksToExcel(tasksToExport, {
        includeId: true,
        includeDescription: true,
        includeLabelStudioId: true,
        includeSyncStatus: true,
        includeTags: true,
        includeSummary: true,
        includeChartsData: true,
        t: t,
      });
      
      message.success(t('tasks.export.exportExcelSuccess') || 'Excel export successful');
    } catch (error) {
      console.error('Excel export failed:', error);
      message.error(t('tasks.export.exportExcelFailed') || 'Excel export failed');
    }
  };

  // Export with options handler
  const handleExportWithOptions = async (options: ExportOptions) => {
    setExportLoading(true);
    
    try {
      // Determine which tasks to export based on range
      let tasksToExport: Task[] = [];
      
      switch (options.range) {
        case 'selected':
          tasksToExport = (data?.items || []).filter(task => selectedRowKeys.includes(task.id));
          break;
        case 'filtered':
          // For filtered, we use the current data which is already filtered
          tasksToExport = data?.items || [];
          break;
        case 'all':
        default:
          tasksToExport = data?.items || [];
          break;
      }
      
      if (tasksToExport.length === 0) {
        message.warning(t('noTasksToExport'));
        setExportLoading(false);
        setExportModalOpen(false);
        return;
      }
      
      const filename = `tasks_export_${new Date().toISOString().split('T')[0]}`;
      
      // Export based on format
      switch (options.format) {
        case 'csv':
          // Use custom fields export for CSV
          exportTasksWithCustomFields(tasksToExport, options.fields as (keyof Task)[], {
            filename,
            t,
          });
          message.success(t('exportSuccess'));
          break;
          
        case 'json':
          // Fetch annotations if requested
          const annotationsMap = new Map<string, ExportAnnotationResult[]>();
          
          if (options.includeAnnotations) {
            const tasksWithProjects = tasksToExport.filter(task => task.label_studio_project_id);
            
            const BATCH_SIZE = 5;
            for (let i = 0; i < tasksWithProjects.length; i += BATCH_SIZE) {
              const batch = tasksWithProjects.slice(i, i + BATCH_SIZE);
              const results = await Promise.allSettled(
                batch.map(async task => {
                  try {
                    const response = await apiClient.get<{ tasks: Array<{ id: number; annotations?: Array<{ id: number; result?: unknown[]; created_at?: string; updated_at?: string; completed_by?: number; was_cancelled?: boolean; lead_time?: number }> }> }>(
                      API_ENDPOINTS.LABEL_STUDIO.TASKS(task.label_studio_project_id!)
                    );
                    
                    const annotations: ExportAnnotationResult[] = [];
                    const lsTasks = response.data.tasks || [];
                    
                    for (const lsTask of lsTasks) {
                      if (lsTask.annotations && lsTask.annotations.length > 0) {
                        for (const annotation of lsTask.annotations) {
                          annotations.push({
                            id: annotation.id,
                            task_id: lsTask.id,
                            result: annotation.result || [],
                            created_at: annotation.created_at,
                            updated_at: annotation.updated_at,
                            completed_by: annotation.completed_by,
                            was_cancelled: annotation.was_cancelled,
                            lead_time: annotation.lead_time,
                          });
                        }
                      }
                    }
                    
                    return { taskId: task.id, annotations };
                  } catch (error) {
                    console.error(`Failed to fetch annotations for task ${task.id}:`, error);
                    return { taskId: task.id, annotations: [] };
                  }
                })
              );
              
              for (const result of results) {
                if (result.status === 'fulfilled') {
                  annotationsMap.set(result.value.taskId, result.value.annotations);
                }
              }
            }
          }
          
          exportTasksToJSON(tasksToExport, {
            includeAnnotations: options.includeAnnotations,
            includeProjectConfig: options.includeProjectConfig,
            includeSyncMetadata: options.includeSyncMetadata,
            filename,
            t,
            prettyPrint: true,
          }, annotationsMap);
          message.success(t('tasks.export.exportJsonSuccess'));
          break;
          
        case 'excel':
          // Map fields to Excel options
          const excelOptions = {
            includeId: options.fields.includes('id'),
            includeDescription: options.fields.includes('description'),
            includeLabelStudioId: options.fields.includes('label_studio_project_id'),
            includeSyncStatus: options.fields.includes('label_studio_sync_status'),
            includeTags: options.fields.includes('tags'),
            includeSummary: true,
            includeChartsData: true,
            filename,
            t,
          };
          
          exportTasksToExcel(tasksToExport, excelOptions);
          message.success(t('tasks.export.exportExcelSuccess'));
          break;
      }
      
      // Add to export history
      addExportHistoryEntry({
        format: options.format,
        range: options.range,
        taskCount: tasksToExport.length,
        fields: options.fields,
        filename: `${filename}.${options.format === 'excel' ? 'xlsx' : options.format}`,
      });
      
      setExportModalOpen(false);
      
    } catch (error) {
      console.error('Export failed:', error);
      message.error(t('tasks.export.exportFailed') || 'Export failed');
    } finally {
      setExportLoading(false);
    }
  };

  const columns: ProColumns<Task>[] = [
    {
      title: t('status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      valueType: 'select',
      valueEnum: {
        pending: { text: t('statusPending'), status: 'Default' },
        in_progress: { text: t('statusInProgress'), status: 'Processing' },
        completed: { text: t('statusCompleted'), status: 'Success' },
        cancelled: { text: t('statusCancelled'), status: 'Error' },
      },
      render: (_, record) => {
        const statusConfig = {
          pending: { color: 'default', icon: <CalendarOutlined /> },
          in_progress: { color: 'processing', icon: <PlayCircleOutlined /> },
          completed: { color: 'success', icon: <CheckCircleOutlined /> },
          cancelled: { color: 'error', icon: <CloseCircleOutlined /> },
        };
        const statusKeyMap: Record<TaskStatus, string> = {
          pending: 'statusPending',
          in_progress: 'statusInProgress',
          completed: 'statusCompleted',
          cancelled: 'statusCancelled',
        };
        const config = statusConfig[record.status];
        return (
          <Tag color={config.color} icon={config.icon}>
            {t(statusKeyMap[record.status])}
          </Tag>
        );
      },
    },
    {
      title: t('priority'),
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      valueType: 'select',
      valueEnum: {
        low: { text: t('priorityLow') },
        medium: { text: t('priorityMedium') },
        high: { text: t('priorityHigh') },
        urgent: { text: t('priorityUrgent') },
      },
      render: (_, record) => {
        const priorityConfig = {
          low: { color: 'green', text: t('priorityLow') },
          medium: { color: 'blue', text: t('priorityMedium') },
          high: { color: 'orange', text: t('priorityHigh') },
          urgent: { color: 'red', text: t('priorityUrgent') },
        };
        const config = priorityConfig[record.priority];
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: t('annotationType'),
      dataIndex: 'annotation_type',
      key: 'annotation_type',
      width: 150,
      valueType: 'select',
      valueEnum: {
        text_classification: { text: t('typeTextClassification') },
        ner: { text: t('typeNER') },
        sentiment: { text: t('typeSentiment') },
        qa: { text: t('typeQA') },
        custom: { text: t('typeCustom') },
      },
      render: (_, record) => {
        const typeKeyMap: Record<string, string> = {
          text_classification: 'typeTextClassification',
          ner: 'typeNER',
          sentiment: 'typeSentiment',
          qa: 'typeQA',
          custom: 'typeCustom',
        };
        return (
          <Tag color="blue">
            {t(typeKeyMap[record.annotation_type] || 'typeCustom')}
          </Tag>
        );
      },
    },
    {
      title: t('progress'),
      dataIndex: 'progress',
      key: 'progress',
      width: 180,
      search: false,
      sorter: true,
      render: (_, record) => (
        <Space direction="vertical" size={0} style={{ width: '100%' }}>
          <Progress
            percent={record.progress}
            size="small"
            status={record.status === 'completed' ? 'success' : 'active'}
            strokeColor={
              record.progress >= 80 ? '#52c41a' :
              record.progress >= 50 ? '#1890ff' :
              record.progress >= 20 ? '#faad14' : '#ff4d4f'
            }
          />
          <Space size={4}>
            <span style={{ fontSize: 12, color: '#999' }}>
              {record.completed_items} / {record.total_items}
            </span>
            <Badge 
              count={record.progress} 
              showZero 
              style={{ backgroundColor: '#52c41a' }}
              size="small"
            />
          </Space>
        </Space>
      ),
    },
    {
      title: t('assignee'),
      dataIndex: 'assignee_name',
      key: 'assignee_name',
      width: 120,
      ellipsis: true,
      render: (text, record) => (
        <Space>
          <UserOutlined style={{ color: '#1890ff' }} />
          <span>{text || t('unassigned')}</span>
        </Space>
      ),
    },
    {
      title: t('dueDate'),
      dataIndex: 'due_date',
      key: 'due_date',
      width: 120,
      valueType: 'date',
      sorter: true,
      render: (_, record) => {
        if (!record.due_date) return <span style={{ color: '#999' }}>-</span>;
        const dueDate = new Date(record.due_date);
        const isOverdue = dueDate < new Date() && record.status !== 'completed';
        const isNearDue = dueDate.getTime() - Date.now() < 3 * 24 * 60 * 60 * 1000; // 3 days
        
        return (
          <Space>
            <CalendarOutlined style={{ 
              color: isOverdue ? '#ff4d4f' : isNearDue ? '#faad14' : '#1890ff' 
            }} />
            <span style={{ 
              color: isOverdue ? '#ff4d4f' : isNearDue ? '#faad14' : undefined 
            }}>
              {dueDate.toLocaleDateString()}
            </span>
            {isOverdue && <Badge status="error" text={t('overdue')} />}
            {isNearDue && !isOverdue && <Badge status="warning" text={t('nearDue')} />}
          </Space>
        );
      },
    },
    {
      title: t('created'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      valueType: 'date',
      search: false,
      sorter: true,
      render: (_, record) => (
        <Tooltip title={new Date(record.created_at).toLocaleString()}>
          {new Date(record.created_at).toLocaleDateString()}
        </Tooltip>
      ),
    },
    {
      title: t('syncStatus'),
      dataIndex: 'label_studio_sync_status',
      key: 'label_studio_sync_status',
      width: 180,
      search: false,
      render: (_, record) => {
        const syncStatus = record.label_studio_sync_status;
        const hasProjectId = !!record.label_studio_project_id;
        const lastSync = record.label_studio_last_sync;
        const syncError = record.label_studio_sync_error;
        
        // Format relative time (e.g., "5 minutes ago")
        const formatRelativeTime = (dateString: string): string => {
          const date = new Date(dateString);
          const now = new Date();
          const diffMs = now.getTime() - date.getTime();
          const diffSec = Math.floor(diffMs / 1000);
          const diffMin = Math.floor(diffSec / 60);
          const diffHour = Math.floor(diffMin / 60);
          const diffDay = Math.floor(diffHour / 24);
          
          if (diffSec < 60) {
            return t('syncTimeJustNow');
          } else if (diffMin < 60) {
            return t('syncTimeMinutesAgo', { count: diffMin });
          } else if (diffHour < 24) {
            return t('syncTimeHoursAgo', { count: diffHour });
          } else if (diffDay < 7) {
            return t('syncTimeDaysAgo', { count: diffDay });
          } else {
            return date.toLocaleDateString();
          }
        };
        
        // Determine sync status display
        const getSyncStatusConfig = () => {
          if (!hasProjectId) {
            return {
              icon: <DisconnectOutlined />,
              color: 'default',
              text: t('syncStatusNotLinked'),
              tooltip: t('syncStatusNotLinkedTip'),
              showLastSync: false,
              showError: false,
            };
          }
          
          switch (syncStatus) {
            case 'synced':
              return {
                icon: <CheckCircleOutlined />,
                color: 'success',
                text: t('syncStatusSynced'),
                tooltip: t('syncStatusSyncedTip'),
                showLastSync: true,
                showError: false,
              };
            case 'pending':
              return {
                icon: <ClockCircleOutlined spin />,
                color: 'warning',
                text: t('syncStatusPending'),
                tooltip: t('syncStatusPendingTip'),
                showLastSync: true,
                showError: false,
              };
            case 'failed':
              return {
                icon: <ExclamationCircleOutlined />,
                color: 'error',
                text: t('syncStatusFailed'),
                tooltip: syncError || t('syncStatusFailedTip'),
                showLastSync: true,
                showError: true,
              };
            default:
              return {
                icon: <ClockCircleOutlined />,
                color: 'default',
                text: t('syncStatusNotSynced'),
                tooltip: t('syncStatusNotSyncedTip'),
                showLastSync: false,
                showError: false,
              };
          }
        };
        
        const config = getSyncStatusConfig();
        
        // Build tooltip content with detailed information
        const tooltipContent = (
          <div style={{ maxWidth: 250 }}>
            <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
              {config.text}
            </div>
            {config.showLastSync && lastSync && (
              <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>
                {t('syncStatusLastSync', { time: formatRelativeTime(lastSync) })}
              </div>
            )}
            {config.showError && syncError && (
              <div style={{ fontSize: 12, color: '#ff4d4f', marginTop: 4 }}>
                {t('syncErrorInfo')}: {syncError}
              </div>
            )}
            {!config.showLastSync && (
              <div style={{ fontSize: 12, color: '#999' }}>
                {config.tooltip}
              </div>
            )}
          </div>
        );
        
        return (
          <Space direction="vertical" size={0} style={{ width: '100%' }}>
            <Space size={4}>
              <Tooltip title={tooltipContent} placement="topLeft">
                <Tag 
                  color={config.color} 
                  icon={config.icon}
                  style={{ cursor: 'pointer', marginRight: 0 }}
                >
                  {config.text}
                </Tag>
              </Tooltip>
              {hasProjectId && (
                <Tooltip title={t('syncSingleTask')}>
                  <Button
                    type="text"
                    size="small"
                    icon={<SyncOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSyncSingleTask(record);
                    }}
                    style={{ padding: '0 4px' }}
                  />
                </Tooltip>
              )}
            </Space>
            {/* Show last sync time in relative format */}
            {config.showLastSync && lastSync && (
              <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                {formatRelativeTime(lastSync)}
              </div>
            )}
            {/* Show error indicator for failed sync */}
            {config.showError && syncError && (
              <Tooltip title={syncError}>
                <div style={{ 
                  fontSize: 11, 
                  color: '#ff4d4f', 
                  marginTop: 2,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  maxWidth: 150,
                  cursor: 'help'
                }}>
                  {t('syncErrorShort')}
                </div>
              </Tooltip>
            )}
          </Space>
        );
      },
    },
    {
      title: t('actions'),
      key: 'actions',
      width: 120,
      fixed: 'right',
      search: false,
      render: (_, record) => (
        <Dropdown
          menu={{
            items: [
              {
                key: 'view',
                icon: <EyeOutlined />,
                label: t('view'),
                onClick: () => navigate(`/tasks/${record.id}`),
              },
              {
                key: 'annotate',
                icon: <EditOutlined />,
                label: t('annotateAction'),
                onClick: () => navigate(`/tasks/${record.id}/annotate`),
                disabled: record.status === 'completed',
              },
              {
                key: 'edit',
                icon: <EditOutlined />,
                label: t('edit'),
                onClick: () => handleEdit(record.id),
              },
              { type: 'divider' },
              {
                key: 'start',
                icon: <PlayCircleOutlined />,
                label: t('start'),
                onClick: () => updateTask.mutateAsync({ 
                  id: record.id, 
                  payload: { status: 'in_progress' } 
                }),
                disabled: record.status !== 'pending',
              },
              {
                key: 'complete',
                icon: <CheckCircleOutlined />,
                label: t('complete'),
                onClick: () => updateTask.mutateAsync({ 
                  id: record.id, 
                  payload: { status: 'completed' } 
                }),
                disabled: record.status !== 'in_progress',
              },
              {
                key: 'pause',
                icon: <PauseCircleOutlined />,
                label: t('pause'),
                onClick: () => updateTask.mutateAsync({ 
                  id: record.id, 
                  payload: { status: 'pending' } 
                }),
                disabled: record.status !== 'in_progress',
              },
              { type: 'divider' },
              {
                key: 'delete',
                icon: <DeleteOutlined />,
                label: t('delete'),
                danger: true,
                onClick: () => handleDelete(record.id),
              },
            ],
          }}
        >
          <Button type="text" icon={<MoreOutlined />} />
        </Dropdown>
      ),
    },
  ];

  return (
    <>
      {/* Statistics Cards */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('totalTasks')}
                value={stats.total}
                prefix={<BarChartOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('inProgress')}
                value={stats.in_progress}
                prefix={<PlayCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('completed')}
                value={stats.completed}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('overdue')}
                value={stats.overdue}
                prefix={<ExclamationCircleOutlined />}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <ProTable<Task>
        headerTitle={t('annotationTasks')}
        actionRef={actionRef}
        rowKey="id"
        loading={isLoading}
        columns={columns}
        dataSource={data?.items || []}
        scroll={{ x: 1400 }}
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
          searchText: t('search'),
          resetText: t('reset'),
          collapseRender: (collapsed) => (
            <Button
              type="link"
              icon={<FilterOutlined />}
            >
              {collapsed ? t('expandFilters') : t('collapseFilters')}
            </Button>
          ),
        }}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => 
            t('paginationTotal', { 
              start: range[0], 
              end: range[1], 
              total 
            }),
          total: data?.total || 0,
        }}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as string[]),
          selections: [
            {
              key: 'all',
              text: t('selectAll'),
              onSelect: () => {
                setSelectedRowKeys((data?.items || []).map(item => item.id));
              },
            },
            {
              key: 'invert',
              text: t('invertSelection'),
              onSelect: () => {
                const allKeys = (data?.items || []).map(item => item.id);
                setSelectedRowKeys(allKeys.filter(key => !selectedRowKeys.includes(key)));
              },
            },
            {
              key: 'none',
              text: t('selectNone'),
              onSelect: () => {
                setSelectedRowKeys([]);
              },
            },
          ],
        }}
        toolBarRender={() => [
          selectedRowKeys.length > 0 && (
            <Dropdown
              key="batchActions"
              menu={{
                items: [
                  {
                    key: 'batchEdit',
                    icon: <EditOutlined />,
                    label: t('edit'),
                    onClick: handleBatchEdit,
                  },
                  { type: 'divider' },
                  {
                    key: 'batchStart',
                    icon: <PlayCircleOutlined />,
                    label: t('batchStart'),
                    onClick: () => handleBatchStatusUpdate('in_progress'),
                  },
                  {
                    key: 'batchComplete',
                    icon: <CheckCircleOutlined />,
                    label: t('batchComplete'),
                    onClick: () => handleBatchStatusUpdate('completed'),
                  },
                  {
                    key: 'batchPause',
                    icon: <PauseCircleOutlined />,
                    label: t('batchPause'),
                    onClick: () => handleBatchStatusUpdate('pending'),
                  },
                  { type: 'divider' },
                  {
                    key: 'batchDelete',
                    icon: <DeleteOutlined />,
                    label: t('batchDelete'),
                    danger: true,
                    onClick: handleBatchDelete,
                  },
                ],
              }}
            >
              <Button icon={<MoreOutlined />}>
                {t('batchActions')} ({selectedRowKeys.length})
              </Button>
            </Dropdown>
          ),
          <Button
            key="exportOptions"
            icon={<DownloadOutlined />}
            onClick={() => setExportModalOpen(true)}
          >
            {selectedRowKeys.length > 0 
              ? t('exportSelected', { count: selectedRowKeys.length })
              : t('exportAll')
            }
          </Button>,
          <Dropdown
            key="refresh"
            menu={{
              items: [
                {
                  key: 'refreshList',
                  icon: <ReloadOutlined />,
                  label: t('refreshList'),
                  onClick: () => {
                    refetch();
                    actionRef.current?.reload();
                  },
                },
                {
                  key: 'syncAll',
                  icon: <ReloadOutlined />,
                  label: t('syncAllTasks'),
                  onClick: handleSyncAllTasks,
                },
              ],
            }}
          >
            <Button icon={<ReloadOutlined />}>
              {t('refresh')}
            </Button>
          </Dropdown>,
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
            {t('createTask')}
          </Button>,
        ]}
        onSubmit={(params) => {
          setCurrentParams(params);
        }}
        onReset={() => {
          setCurrentParams({});
        }}
        tableAlertRender={({ selectedRowKeys, onCleanSelected }) => (
          <Space size={24}>
            <span>
              {t('selectedItems', { count: selectedRowKeys.length })}
              <a style={{ marginLeft: 8 }} onClick={onCleanSelected}>
                {t('clearSelection')}
              </a>
            </span>
          </Space>
        )}
        tableAlertOptionRender={({ selectedRowKeys }) => (
          <Space size={16}>
            <a onClick={() => handleBatchStatusUpdate('in_progress')}>
              {t('batchStart')}
            </a>
            <a onClick={() => handleBatchStatusUpdate('completed')}>
              {t('batchComplete')}
            </a>
            <a onClick={handleBatchDelete} style={{ color: '#ff4d4f' }}>
              {t('batchDelete')}
            </a>
          </Space>
        )}
      />

      <TaskCreateModal
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onSuccess={() => {
          setCreateModalOpen(false);
          refetch();
        }}
      />

      {/* Export Options Modal */}
      <ExportOptionsModal
        open={exportModalOpen}
        onCancel={() => setExportModalOpen(false)}
        onExport={handleExportWithOptions}
        selectedCount={selectedRowKeys.length}
        filteredCount={data?.items?.length || 0}
        totalCount={data?.total || 0}
        loading={exportLoading}
      />

      {/* Sync Progress Modal */}
      <Modal
        title={
          <Space>
            <SyncOutlined spin={syncProgress.status === 'syncing'} />
            {t('syncProgressTitle') || 'Sync Progress'}
          </Space>
        }
        open={syncModalOpen}
        onCancel={() => {
          if (syncProgress.status !== 'syncing') {
            setSyncModalOpen(false);
            setSyncProgress({
              current: 0,
              total: 0,
              status: 'idle',
              message: '',
            });
          }
        }}
        footer={
          syncProgress.status === 'syncing' ? null : (
            <Button 
              type="primary" 
              onClick={() => {
                setSyncModalOpen(false);
                setSyncProgress({
                  current: 0,
                  total: 0,
                  status: 'idle',
                  message: '',
                });
              }}
            >
              {t('close') || 'Close'}
            </Button>
          )
        }
        closable={syncProgress.status !== 'syncing'}
        maskClosable={syncProgress.status !== 'syncing'}
      >
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          {syncProgress.total > 0 && (
            <Progress
              type="circle"
              percent={Math.round((syncProgress.current / syncProgress.total) * 100)}
              status={
                syncProgress.status === 'error' ? 'exception' :
                syncProgress.status === 'completed' ? 'success' : 'active'
              }
              format={() => `${syncProgress.current}/${syncProgress.total}`}
            />
          )}
          {syncProgress.total === 0 && syncProgress.status === 'syncing' && (
            <Progress type="circle" percent={0} status="active" />
          )}
          {syncProgress.total === 0 && syncProgress.status === 'completed' && (
            <Progress type="circle" percent={100} status="success" />
          )}
          <p style={{ marginTop: 16, color: '#666' }}>
            {syncProgress.message}
          </p>
          {syncProgress.status === 'completed' && syncProgress.total > 0 && (
            <Tag color="success" icon={<CheckCircleOutlined />}>
              {t('syncCompleted') || 'Sync Completed'}
            </Tag>
          )}
          {syncProgress.status === 'error' && (
            <Tag color="error" icon={<ExclamationCircleOutlined />}>
              {t('syncHasErrors') || 'Sync Has Errors'}
            </Tag>
          )}
        </div>
      </Modal>

      {/* Task Edit Modal */}
      <TaskEditModal
        open={editModalOpen}
        taskId={editTaskId}
        onCancel={() => {
          setEditModalOpen(false);
          setEditTaskId(null);
        }}
        onSuccess={() => {
          setEditModalOpen(false);
          setEditTaskId(null);
          refetch();
        }}
      />

      {/* Batch Edit Modal */}
      <BatchEditModal
        open={batchEditModalOpen}
        tasks={getSelectedTasks()}
        onCancel={() => setBatchEditModalOpen(false)}
        onSuccess={() => {
          setBatchEditModalOpen(false);
          setSelectedRowKeys([]);
          refetch();
        }}
      />

      {/* Task Delete Modal */}
      <TaskDeleteModal
        open={deleteModalOpen}
        tasks={tasksToDelete}
        onCancel={() => {
          setDeleteModalOpen(false);
          setTasksToDelete([]);
        }}
        onSuccess={handleDeleteSuccess}
      />
    </>
  );
};

export default TasksPage;
