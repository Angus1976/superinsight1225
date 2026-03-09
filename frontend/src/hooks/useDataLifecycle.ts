/**
 * Data Lifecycle Management Hooks
 * 
 * Custom React hooks for data lifecycle operations.
 * Integrates with API client and Zustand store for state management.
 */

import { useCallback, useEffect } from 'react';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';
import { dataLifecycleApi, TempData, Sample, Review, AnnotationTask, EnhancementJob, AITrial } from '@/services/dataLifecycle';
import { useDataLifecycleStore, dataLifecycleSelectors } from '@/stores/dataLifecycleStore';

// ============================================================================
// Types
// ============================================================================

export interface UseTempDataReturn {
  data: TempData[];
  loading: boolean;
  error: string | null;
  pagination: { page: number; pageSize: number; total: number };
  fetchTempData: (params?: { page?: number; pageSize?: number; state?: string }) => Promise<void>;
  createTempData: (payload: { name: string; content: Record<string, unknown>; metadata?: Record<string, unknown> }) => Promise<void>;
  updateTempData: (id: string, payload: Partial<TempData>) => Promise<void>;
  deleteTempData: (id: string) => Promise<void>;
  archiveTempData: (id: string) => Promise<void>;
  restoreTempData: (id: string) => Promise<void>;
  setFilters: (filters: Record<string, unknown>) => void;
  clearFilters: () => void;
}

export interface UseSampleLibraryReturn {
  samples: Sample[];
  loading: boolean;
  error: string | null;
  pagination: { page: number; pageSize: number; total: number };
  fetchSamples: (params?: { page?: number; pageSize?: number; search?: string; dataType?: string }) => Promise<void>;
  addToLibrary: (dataId: string) => Promise<void>;
  removeFromLibrary: (id: string) => Promise<void>;
  exportSample: (id: string) => Promise<void>;
  setFilters: (filters: Record<string, unknown>) => void;
  clearFilters: () => void;
}

export interface UseReviewReturn {
  reviews: Review[];
  loading: boolean;
  error: string | null;
  pagination: { page: number; pageSize: number; total: number };
  fetchReviews: (params?: { page?: number; pageSize?: number; status?: string }) => Promise<void>;
  submitForReview: (targetType: string, targetId: string) => Promise<void>;
  approveReview: (id: string) => Promise<void>;
  rejectReview: (id: string, reason: string) => Promise<void>;
  cancelReview: (id: string) => Promise<void>;
  setFilters: (filters: Record<string, unknown>) => void;
  clearFilters: () => void;
}

export interface UseAnnotationTaskReturn {
  tasks: AnnotationTask[];
  loading: boolean;
  error: string | null;
  pagination: { page: number; pageSize: number; total: number };
  fetchTasks: (params?: { page?: number; pageSize?: number; status?: string; priority?: string }) => Promise<void>;
  createTask: (payload: { name: string; description?: string; data_id: string; priority: string; assignee?: string }) => Promise<void>;
  updateTask: (id: string, payload: Partial<AnnotationTask>) => Promise<void>;
  startTask: (id: string) => Promise<void>;
  completeTask: (id: string) => Promise<void>;
  cancelTask: (id: string) => Promise<void>;
  assignTask: (id: string, assignee: string) => Promise<void>;
  setFilters: (filters: Record<string, unknown>) => void;
  clearFilters: () => void;
}

export interface UseEnhancementReturn {
  jobs: EnhancementJob[];
  loading: boolean;
  error: string | null;
  pagination: { page: number; pageSize: number; total: number };
  fetchJobs: (params?: { page?: number; pageSize?: number; status?: string; type?: string }) => Promise<void>;
  createJob: (payload: { name: string; type: string; target_data_id: string; config?: Record<string, unknown> }) => Promise<void>;
  startJob: (id: string) => Promise<void>;
  pauseJob: (id: string) => Promise<void>;
  resumeJob: (id: string) => Promise<void>;
  cancelJob: (id: string) => Promise<void>;
  rollbackJob: (id: string, version: number) => Promise<void>;
  getHistory: (id: string) => Promise<Array<{ version: number; timestamp: string; changes: Record<string, unknown> }>>;
  addToLibrary: (id: string) => Promise<void>;
  setFilters: (filters: Record<string, unknown>) => void;
  clearFilters: () => void;
}

export interface UseAITrialReturn {
  trials: AITrial[];
  loading: boolean;
  error: string | null;
  pagination: { page: number; pageSize: number; total: number };
  fetchTrials: (params?: { page?: number; pageSize?: number; status?: string; model?: string }) => Promise<void>;
  createTrial: (payload: { name: string; model: string; target_data_id: string; config?: Record<string, unknown> }) => Promise<void>;
  startTrial: (id: string) => Promise<void>;
  stopTrial: (id: string) => Promise<void>;
  getResults: (id: string) => Promise<{
    trials: Array<{ trial_id: string; success: boolean; score: number; duration: number; error?: string }>;
    summary: { total: number; successful: number; failed: number; success_rate: number; avg_score: number; avg_duration: number };
  }>;
  exportResults: (id: string) => Promise<void>;
  compareTrials: (ids: string[]) => Promise<{
    trials: AITrial[];
    comparison: { success_rate: Record<string, number>; avg_score: Record<string, number>; avg_duration: Record<string, number> };
  }>;
  setFilters: (filters: Record<string, unknown>) => void;
  clearFilters: () => void;
}

// ============================================================================
// Hook: useTempData
// ============================================================================

export function useTempData(): UseTempDataReturn {
  const { t } = useTranslation('dataLifecycle');
  
  const store = useDataLifecycleStore();
  
  const {
    tempDataList,
    tempDataPagination,
    tempDataFilters,
    isLoading,
    error,
    setTempDataList,
    setTempDataFilters,
    resetTempDataFilters,
    setLoading,
    setError,
  } = store;

  const fetchTempData = useCallback(async (params?: { page?: number; pageSize?: number; state?: string }) => {
    try {
      setLoading(true);
      setError(null);
      const response = await dataLifecycleApi.listTempData({
        page: params?.page || tempDataPagination.page,
        page_size: params?.pageSize || tempDataPagination.pageSize,
        state: params?.state,
      });
      setTempDataList(response.items, response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch temp data');
      message.error(t('common.messages.operationFailed'));
    } finally {
      setLoading(false);
    }
  }, [tempDataPagination.page, tempDataPagination.pageSize, setTempDataList, setLoading, setError, t]);

  const createTempData = useCallback(async (payload: { name: string; content: Record<string, unknown>; metadata?: Record<string, unknown> }) => {
    try {
      setLoading(true);
      await dataLifecycleApi.createTempData(payload);
      message.success(t('tempData.messages.createSuccess'));
      fetchTempData({ page: 1 });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create temp data');
      message.error(t('tempData.messages.createFailed'));
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchTempData, t]);

  const updateTempData = useCallback(async (id: string, payload: Partial<TempData>) => {
    try {
      setLoading(true);
      await dataLifecycleApi.updateTempData(id, payload);
      message.success(t('tempData.messages.updateSuccess'));
      fetchTempData({ page: tempDataPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update temp data');
      message.error(t('tempData.messages.updateFailed'));
    } finally {
      setLoading(false);
    }
  }, [tempDataPagination.page, setLoading, setError, fetchTempData, t]);

  const deleteTempData = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.deleteTempData(id);
      message.success(t('tempData.messages.deleteSuccess'));
      fetchTempData({ page: tempDataPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete temp data');
      message.error(t('tempData.messages.deleteFailed'));
    } finally {
      setLoading(false);
    }
  }, [tempDataPagination.page, setLoading, setError, fetchTempData, t]);

  const archiveTempData = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.archiveTempData(id);
      message.success(t('tempData.messages.archiveSuccess'));
      fetchTempData({ page: tempDataPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive temp data');
      message.error(t('tempData.messages.archiveFailed'));
    } finally {
      setLoading(false);
    }
  }, [tempDataPagination.page, setLoading, setError, fetchTempData, t]);

  const restoreTempData = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.restoreTempData(id);
      message.success(t('tempData.messages.restoreSuccess'));
      fetchTempData({ page: tempDataPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restore temp data');
      message.error(t('tempData.messages.restoreFailed'));
    } finally {
      setLoading(false);
    }
  }, [tempDataPagination.page, setLoading, setError, fetchTempData, t]);

  const setFilters = useCallback((filters: Record<string, unknown>) => {
    setTempDataFilters(filters);
  }, [setTempDataFilters]);

  const clearFilters = useCallback(() => {
    resetTempDataFilters();
  }, [resetTempDataFilters]);

  return {
    data: tempDataList,
    loading: isLoading,
    error,
    pagination: tempDataPagination,
    fetchTempData,
    createTempData,
    updateTempData,
    deleteTempData,
    archiveTempData,
    restoreTempData,
    setFilters,
    clearFilters,
  };
}

// ============================================================================
// Hook: useSampleLibrary
// ============================================================================

export function useSampleLibrary(): UseSampleLibraryReturn {
  const { t } = useTranslation('dataLifecycle');
  
  const store = useDataLifecycleStore();
  
  const {
    sampleList,
    samplePagination,
    sampleFilters,
    isLoading,
    error,
    setSampleList,
    setSampleFilters,
    resetSampleFilters,
    setLoading,
    setError,
  } = store;

  const fetchSamples = useCallback(async (params?: { page?: number; pageSize?: number; search?: string; dataType?: string }) => {
    try {
      setLoading(true);
      setError(null);
      const response = await dataLifecycleApi.listSamples({
        page: params?.page || samplePagination.page,
        page_size: params?.pageSize || samplePagination.pageSize,
        search: params?.search,
        data_type: params?.dataType,
      });
      setSampleList(response.items, response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch samples');
      message.error(t('common.messages.operationFailed'));
    } finally {
      setLoading(false);
    }
  }, [samplePagination.page, samplePagination.pageSize, setSampleList, setLoading, setError, t]);

  const addToLibrary = useCallback(async (dataId: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.addToLibrary(dataId);
      message.success(t('sampleLibrary.messages.addSuccess'));
      fetchSamples({ page: samplePagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add to library');
      message.error(t('sampleLibrary.messages.addFailed'));
    } finally {
      setLoading(false);
    }
  }, [samplePagination.page, setLoading, setError, fetchSamples, t]);

  const removeFromLibrary = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.removeFromLibrary(id);
      message.success(t('sampleLibrary.messages.removeSuccess'));
      fetchSamples({ page: samplePagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove from library');
      message.error(t('sampleLibrary.messages.removeFailed'));
    } finally {
      setLoading(false);
    }
  }, [samplePagination.page, setLoading, setError, fetchSamples, t]);

  const exportSample = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.exportSample(id);
      message.success(t('common.messages.exportSuccess'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export sample');
      message.error(t('common.messages.exportFailed'));
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, t]);

  const setFilters = useCallback((filters: Record<string, unknown>) => {
    setSampleFilters(filters);
  }, [setSampleFilters]);

  const clearFilters = useCallback(() => {
    resetSampleFilters();
  }, [resetSampleFilters]);

  return {
    samples: sampleList,
    loading: isLoading,
    error,
    pagination: samplePagination,
    fetchSamples,
    addToLibrary,
    removeFromLibrary,
    exportSample,
    setFilters,
    clearFilters,
  };
}

// ============================================================================
// Hook: useReview
// ============================================================================

export function useReview(): UseReviewReturn {
  const { t } = useTranslation('dataLifecycle');
  
  const store = useDataLifecycleStore();
  
  const {
    reviewList,
    reviewPagination,
    reviewFilters,
    isLoading,
    error,
    setReviewList,
    setReviewFilters,
    resetReviewFilters,
    setLoading,
    setError,
  } = store;

  const fetchReviews = useCallback(async (params?: { page?: number; pageSize?: number; status?: string }) => {
    try {
      setLoading(true);
      setError(null);
      const response = await dataLifecycleApi.listReviews({
        page: params?.page || reviewPagination.page,
        page_size: params?.pageSize || reviewPagination.pageSize,
        status: params?.status,
      });
      setReviewList(response.items, response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch reviews');
      message.error(t('common.messages.operationFailed'));
    } finally {
      setLoading(false);
    }
  }, [reviewPagination.page, reviewPagination.pageSize, setReviewList, setLoading, setError, t]);

  const submitForReview = useCallback(async (targetType: string, targetId: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.submitForReview(targetType, targetId);
      message.success(t('review.messages.submitSuccess'));
      fetchReviews({ page: 1 });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit for review');
      message.error(t('review.messages.submitFailed'));
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchReviews, t]);

  const approveReview = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.approveReview(id);
      message.success(t('review.messages.approveSuccess'));
      fetchReviews({ page: reviewPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve review');
      message.error(t('review.messages.approveFailed'));
    } finally {
      setLoading(false);
    }
  }, [reviewPagination.page, setLoading, setError, fetchReviews, t]);

  const rejectReview = useCallback(async (id: string, reason: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.rejectReview(id, reason);
      message.success(t('review.messages.rejectSuccess'));
      fetchReviews({ page: reviewPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject review');
      message.error(t('review.messages.rejectFailed'));
    } finally {
      setLoading(false);
    }
  }, [reviewPagination.page, setLoading, setError, fetchReviews, t]);

  const cancelReview = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.cancelReview(id);
      message.success(t('review.messages.cancelSuccess'));
      fetchReviews({ page: reviewPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel review');
      message.error(t('review.messages.cancelFailed'));
    } finally {
      setLoading(false);
    }
  }, [reviewPagination.page, setLoading, setError, fetchReviews, t]);

  const setFilters = useCallback((filters: Record<string, unknown>) => {
    setReviewFilters(filters);
  }, [setReviewFilters]);

  const clearFilters = useCallback(() => {
    resetReviewFilters();
  }, [resetReviewFilters]);

  return {
    reviews: reviewList,
    loading: isLoading,
    error,
    pagination: reviewPagination,
    fetchReviews,
    submitForReview,
    approveReview,
    rejectReview,
    cancelReview,
    setFilters,
    clearFilters,
  };
}

// ============================================================================
// Hook: useAnnotationTask
// ============================================================================

export function useAnnotationTask(): UseAnnotationTaskReturn {
  const { t } = useTranslation('dataLifecycle');
  
  const store = useDataLifecycleStore();
  
  const {
    annotationTaskList,
    annotationTaskPagination,
    annotationTaskFilters,
    isLoading,
    error,
    setAnnotationTaskList,
    setAnnotationTaskFilters,
    resetAnnotationTaskFilters,
    setLoading,
    setError,
  } = store;

  const fetchTasks = useCallback(async (params?: { page?: number; pageSize?: number; status?: string; priority?: string }) => {
    try {
      setLoading(true);
      setError(null);
      const response = await dataLifecycleApi.listAnnotationTasks({
        page: params?.page || annotationTaskPagination.page,
        page_size: params?.pageSize || annotationTaskPagination.pageSize,
        status: params?.status,
        priority: params?.priority,
      });
      setAnnotationTaskList(response.items, response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tasks');
      message.error(t('common.messages.operationFailed'));
    } finally {
      setLoading(false);
    }
  }, [annotationTaskPagination.page, annotationTaskPagination.pageSize, setAnnotationTaskList, setLoading, setError, t]);

  const createTask = useCallback(async (payload: { name: string; description?: string; data_id: string; priority: string; assignee?: string }) => {
    try {
      setLoading(true);
      await dataLifecycleApi.createAnnotationTask(payload);
      message.success(t('annotationTask.messages.createSuccess'));
      fetchTasks({ page: 1 });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create task');
      message.error(t('annotationTask.messages.createFailed'));
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchTasks, t]);

  const updateTask = useCallback(async (id: string, payload: Partial<AnnotationTask>) => {
    try {
      setLoading(true);
      await dataLifecycleApi.updateAnnotationTask(id, payload);
      message.success(t('common.messages.saveSuccess'));
      fetchTasks({ page: annotationTaskPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update task');
      message.error(t('common.messages.saveFailed'));
    } finally {
      setLoading(false);
    }
  }, [annotationTaskPagination.page, setLoading, setError, fetchTasks, t]);

  const startTask = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.startAnnotationTask(id);
      message.success(t('annotationTask.messages.startSuccess'));
      fetchTasks({ page: annotationTaskPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start task');
      message.error(t('annotationTask.messages.startFailed'));
    } finally {
      setLoading(false);
    }
  }, [annotationTaskPagination.page, setLoading, setError, fetchTasks, t]);

  const completeTask = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.completeAnnotationTask(id);
      message.success(t('annotationTask.messages.completeSuccess'));
      fetchTasks({ page: annotationTaskPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete task');
      message.error(t('annotationTask.messages.completeFailed'));
    } finally {
      setLoading(false);
    }
  }, [annotationTaskPagination.page, setLoading, setError, fetchTasks, t]);

  const cancelTask = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.cancelAnnotationTask(id);
      message.success(t('annotationTask.messages.cancelSuccess'));
      fetchTasks({ page: annotationTaskPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel task');
      message.error(t('annotationTask.messages.cancelFailed'));
    } finally {
      setLoading(false);
    }
  }, [annotationTaskPagination.page, setLoading, setError, fetchTasks, t]);

  const assignTask = useCallback(async (id: string, assignee: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.assignAnnotationTask(id, assignee);
      message.success(t('annotationTask.messages.assignSuccess'));
      fetchTasks({ page: annotationTaskPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign task');
      message.error(t('annotationTask.messages.assignFailed'));
    } finally {
      setLoading(false);
    }
  }, [annotationTaskPagination.page, setLoading, setError, fetchTasks, t]);

  const setFilters = useCallback((filters: Record<string, unknown>) => {
    setAnnotationTaskFilters(filters);
  }, [setAnnotationTaskFilters]);

  const clearFilters = useCallback(() => {
    resetAnnotationTaskFilters();
  }, [resetAnnotationTaskFilters]);

  return {
    tasks: annotationTaskList,
    loading: isLoading,
    error,
    pagination: annotationTaskPagination,
    fetchTasks,
    createTask,
    updateTask,
    startTask,
    completeTask,
    cancelTask,
    assignTask,
    setFilters,
    clearFilters,
  };
}

// ============================================================================
// Hook: useEnhancement
// ============================================================================

export function useEnhancement(): UseEnhancementReturn {
  const { t } = useTranslation('dataLifecycle');
  
  const store = useDataLifecycleStore();
  
  const {
    enhancementList,
    enhancementPagination,
    enhancementFilters,
    isLoading,
    error,
    setEnhancementList,
    setEnhancementFilters,
    resetEnhancementFilters,
    setLoading,
    setError,
  } = store;

  const fetchJobs = useCallback(async (params?: { page?: number; pageSize?: number; status?: string; type?: string }) => {
    try {
      setLoading(true);
      setError(null);
      const response = await dataLifecycleApi.listEnhancements({
        page: params?.page || enhancementPagination.page,
        page_size: params?.pageSize || enhancementPagination.pageSize,
        status: params?.status,
        type: params?.type,
      });
      setEnhancementList(response.items, response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch enhancements');
      message.error(t('common.messages.operationFailed'));
    } finally {
      setLoading(false);
    }
  }, [enhancementPagination.page, enhancementPagination.pageSize, setEnhancementList, setLoading, setError, t]);

  const createJob = useCallback(async (payload: { name: string; type: string; target_data_id: string; config?: Record<string, unknown> }) => {
    try {
      setLoading(true);
      await dataLifecycleApi.createEnhancement(payload);
      message.success(t('enhancement.messages.createSuccess'));
      fetchJobs({ page: 1 });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create enhancement');
      message.error(t('enhancement.messages.createFailed'));
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchJobs, t]);

  const startJob = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.startEnhancement(id);
      message.success(t('enhancement.messages.startSuccess'));
      fetchJobs({ page: enhancementPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start enhancement');
      message.error(t('enhancement.messages.startFailed'));
    } finally {
      setLoading(false);
    }
  }, [enhancementPagination.page, setLoading, setError, fetchJobs, t]);

  const pauseJob = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.pauseEnhancement(id);
      message.success(t('enhancement.messages.pauseSuccess'));
      fetchJobs({ page: enhancementPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause enhancement');
      message.error(t('enhancement.messages.pauseFailed'));
    } finally {
      setLoading(false);
    }
  }, [enhancementPagination.page, setLoading, setError, fetchJobs, t]);

  const resumeJob = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.resumeEnhancement(id);
      message.success(t('enhancement.messages.resumeSuccess'));
      fetchJobs({ page: enhancementPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume enhancement');
      message.error(t('enhancement.messages.resumeFailed'));
    } finally {
      setLoading(false);
    }
  }, [enhancementPagination.page, setLoading, setError, fetchJobs, t]);

  const cancelJob = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.cancelEnhancement(id);
      message.success(t('enhancement.messages.cancelSuccess'));
      fetchJobs({ page: enhancementPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel enhancement');
      message.error(t('enhancement.messages.cancelFailed'));
    } finally {
      setLoading(false);
    }
  }, [enhancementPagination.page, setLoading, setError, fetchJobs, t]);

  const rollbackJob = useCallback(async (id: string, version: number) => {
    try {
      setLoading(true);
      await dataLifecycleApi.rollbackEnhancement(id, version);
      message.success(t('enhancement.messages.rollbackSuccess'));
      fetchJobs({ page: enhancementPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback enhancement');
      message.error(t('enhancement.messages.rollbackFailed'));
    } finally {
      setLoading(false);
    }
  }, [enhancementPagination.page, setLoading, setError, fetchJobs, t]);

  const getHistory = useCallback(async (id: string) => {
    try {
      return await dataLifecycleApi.getEnhancementHistory(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get history');
      return [];
    }
  }, [setError]);

  const addToLibrary = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.addToLibrary(id);
      message.success(t('sampleLibrary.messages.addSuccess'));
      fetchJobs({ page: enhancementPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add to library');
      message.error(t('sampleLibrary.messages.addFailed'));
    } finally {
      setLoading(false);
    }
  }, [enhancementPagination.page, setLoading, setError, fetchJobs, t]);

  const setFilters = useCallback((filters: Record<string, unknown>) => {
    setEnhancementFilters(filters);
  }, [setEnhancementFilters]);

  const clearFilters = useCallback(() => {
    resetEnhancementFilters();
  }, [resetEnhancementFilters]);

  return {
    jobs: enhancementList,
    loading: isLoading,
    error,
    pagination: enhancementPagination,
    fetchJobs,
    createJob,
    startJob,
    pauseJob,
    resumeJob,
    cancelJob,
    rollbackJob,
    getHistory,
    addToLibrary,
    setFilters,
    clearFilters,
  };
}

// ============================================================================
// Hook: useAITrial
// ============================================================================

export function useAITrial(): UseAITrialReturn {
  const { t } = useTranslation('dataLifecycle');
  
  const store = useDataLifecycleStore();
  
  const {
    aiTrialList,
    aiTrialPagination,
    aiTrialFilters,
    isLoading,
    error,
    setAITrialList,
    setAITrialFilters,
    resetAITrialFilters,
    setLoading,
    setError,
  } = store;

  const fetchTrials = useCallback(async (params?: { page?: number; pageSize?: number; status?: string; model?: string }) => {
    try {
      setLoading(true);
      setError(null);
      const response = await dataLifecycleApi.listAITrials({
        page: params?.page || aiTrialPagination.page,
        page_size: params?.pageSize || aiTrialPagination.pageSize,
        status: params?.status,
        model: params?.model,
      });
      setAITrialList(response.items, response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch trials');
      message.error(t('common.messages.operationFailed'));
    } finally {
      setLoading(false);
    }
  }, [aiTrialPagination.page, aiTrialPagination.pageSize, setAITrialList, setLoading, setError, t]);

  const createTrial = useCallback(async (payload: { name: string; model: string; target_data_id: string; config?: Record<string, unknown> }) => {
    try {
      setLoading(true);
      await dataLifecycleApi.createAITrial(payload);
      message.success(t('aiTrial.messages.createSuccess'));
      fetchTrials({ page: 1 });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create trial');
      message.error(t('aiTrial.messages.createFailed'));
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, fetchTrials, t]);

  const startTrial = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.startAITrial(id);
      message.success(t('aiTrial.messages.startSuccess'));
      fetchTrials({ page: aiTrialPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start trial');
      message.error(t('aiTrial.messages.startFailed'));
    } finally {
      setLoading(false);
    }
  }, [aiTrialPagination.page, setLoading, setError, fetchTrials, t]);

  const stopTrial = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.stopAITrial(id);
      message.success(t('aiTrial.messages.stopSuccess'));
      fetchTrials({ page: aiTrialPagination.page });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop trial');
      message.error(t('aiTrial.messages.stopFailed'));
    } finally {
      setLoading(false);
    }
  }, [aiTrialPagination.page, setLoading, setError, fetchTrials, t]);

  const getResults = useCallback(async (id: string) => {
    try {
      return await dataLifecycleApi.getAITrialResults(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get results');
      return { trials: [], summary: { total: 0, successful: 0, failed: 0, success_rate: 0, avg_score: 0, avg_duration: 0 } };
    }
  }, [setError]);

  const exportResults = useCallback(async (id: string) => {
    try {
      setLoading(true);
      await dataLifecycleApi.exportAITrialResults(id);
      message.success(t('common.messages.exportSuccess'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export results');
      message.error(t('common.messages.exportFailed'));
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, t]);

  const compareTrials = useCallback(async (ids: string[]) => {
    try {
      return await dataLifecycleApi.compareAITrials(ids);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare trials');
      return { trials: [], comparison: { success_rate: {}, avg_score: {}, avg_duration: {} } };
    }
  }, [setError]);

  const setFilters = useCallback((filters: Record<string, unknown>) => {
    setAITrialFilters(filters);
  }, [setAITrialFilters]);

  const clearFilters = useCallback(() => {
    resetAITrialFilters();
  }, [resetAITrialFilters]);

  return {
    trials: aiTrialList,
    loading: isLoading,
    error,
    pagination: aiTrialPagination,
    fetchTrials,
    createTrial,
    startTrial,
    stopTrial,
    getResults,
    exportResults,
    compareTrials,
    setFilters,
    clearFilters,
  };
}

// ============================================================================
// Default export
// ============================================================================

export default {
  useTempData,
  useSampleLibrary,
  useReview,
  useAnnotationTask,
  useEnhancement,
  useAITrial,
};