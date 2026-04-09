/**
 * Data Lifecycle Management Store
 * 
 * Centralized state management for data lifecycle-related data.
 * Uses Zustand with proper TypeScript typing and clear action patterns.
 */
import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import type { 
  TempData, 
  Sample, 
  Review, 
  AnnotationTask, 
  EnhancementJob, 
  AITrial 
} from '@/services/dataLifecycle';

// ============================================================================
// Types
// ============================================================================

// Filter Types
export interface TempDataFilters {
  state?: string;
  search?: string;
}

export interface SampleFilters {
  dataType?: string;
  minQualityScore?: number;
  search?: string;
}

export interface ReviewFilters {
  status?: string;
  requester?: string;
}

export interface AnnotationTaskFilters {
  status?: string;
  priority?: string;
  assignee?: string;
}

export interface EnhancementFilters {
  status?: string;
  type?: string;
}

export interface AITrialFilters {
  status?: string;
  model?: string;
}

// Pagination Types
export interface Pagination {
  page: number;
  pageSize: number;
  total: number;
}

// State Interface
interface DataLifecycleState {
  // Temp Data
  tempDataList: TempData[];
  tempDataPagination: Pagination;
  tempDataFilters: TempDataFilters;
  currentTempData: TempData | null;
  
  // Sample Library
  sampleList: Sample[];
  samplePagination: Pagination;
  sampleFilters: SampleFilters;
  currentSample: Sample | null;
  
  // Reviews
  reviewList: Review[];
  reviewPagination: Pagination;
  reviewFilters: ReviewFilters;
  currentReview: Review | null;
  
  // Annotation Tasks
  annotationTaskList: AnnotationTask[];
  annotationTaskPagination: Pagination;
  annotationTaskFilters: AnnotationTaskFilters;
  currentAnnotationTask: AnnotationTask | null;
  
  // Enhancement Jobs
  enhancementList: EnhancementJob[];
  enhancementPagination: Pagination;
  enhancementFilters: EnhancementFilters;
  currentEnhancement: EnhancementJob | null;
  
  // AI Trials
  aiTrialList: AITrial[];
  aiTrialPagination: Pagination;
  aiTrialFilters: AITrialFilters;
  currentAITrial: AITrial | null;
  
  // UI State
  activeTab: string;
  isLoading: boolean;
  error: string | null;
}

// Actions Interface
interface DataLifecycleActions {
  // Temp Data Actions
  setTempDataList: (list: TempData[], total: number) => void;
  setTempDataFilters: (filters: Partial<TempDataFilters>) => void;
  resetTempDataFilters: () => void;
  setCurrentTempData: (data: TempData | null) => void;
  updateTempData: (id: string, updates: Partial<TempData>) => void;
  removeTempData: (id: string) => void;
  
  // Sample Library Actions
  setSampleList: (list: Sample[], total: number) => void;
  setSampleFilters: (filters: Partial<SampleFilters>) => void;
  resetSampleFilters: () => void;
  setCurrentSample: (sample: Sample | null) => void;
  updateSample: (id: string, updates: Partial<Sample>) => void;
  removeSample: (id: string) => void;
  
  // Review Actions
  setReviewList: (list: Review[], total: number) => void;
  setReviewFilters: (filters: Partial<ReviewFilters>) => void;
  resetReviewFilters: () => void;
  setCurrentReview: (review: Review | null) => void;
  updateReview: (id: string, updates: Partial<Review>) => void;
  removeReview: (id: string) => void;
  
  // Annotation Task Actions
  setAnnotationTaskList: (list: AnnotationTask[], total: number) => void;
  setAnnotationTaskFilters: (filters: Partial<AnnotationTaskFilters>) => void;
  resetAnnotationTaskFilters: () => void;
  setCurrentAnnotationTask: (task: AnnotationTask | null) => void;
  updateAnnotationTask: (id: string, updates: Partial<AnnotationTask>) => void;
  removeAnnotationTask: (id: string) => void;
  
  // Enhancement Actions
  setEnhancementList: (list: EnhancementJob[], total: number) => void;
  setEnhancementFilters: (filters: Partial<EnhancementFilters>) => void;
  resetEnhancementFilters: () => void;
  setCurrentEnhancement: (job: EnhancementJob | null) => void;
  updateEnhancement: (id: string, updates: Partial<EnhancementJob>) => void;
  removeEnhancement: (id: string) => void;
  
  // AI Trial Actions
  setAITrialList: (list: AITrial[], total: number) => void;
  setAITrialFilters: (filters: Partial<AITrialFilters>) => void;
  resetAITrialFilters: () => void;
  setCurrentAITrial: (trial: AITrial | null) => void;
  updateAITrial: (id: string, updates: Partial<AITrial>) => void;
  removeAITrial: (id: string) => void;
  
  // UI Actions
  setActiveTab: (tab: string) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  
  // Reset
  reset: () => void;
}

export type DataLifecycleStore = DataLifecycleState & DataLifecycleActions;

// ============================================================================
// Initial State
// ============================================================================

const initialPagination: Pagination = {
  page: 1,
  pageSize: 10,
  total: 0,
};

const initialState: DataLifecycleState = {
  // Temp Data
  tempDataList: [],
  tempDataPagination: { ...initialPagination },
  tempDataFilters: {},
  currentTempData: null,
  
  // Sample Library
  sampleList: [],
  samplePagination: { ...initialPagination },
  sampleFilters: {},
  currentSample: null,
  
  // Reviews
  reviewList: [],
  reviewPagination: { ...initialPagination },
  reviewFilters: {},
  currentReview: null,
  
  // Annotation Tasks
  annotationTaskList: [],
  annotationTaskPagination: { ...initialPagination },
  annotationTaskFilters: {},
  currentAnnotationTask: null,
  
  // Enhancement Jobs
  enhancementList: [],
  enhancementPagination: { ...initialPagination },
  enhancementFilters: {},
  currentEnhancement: null,
  
  // AI Trials
  aiTrialList: [],
  aiTrialPagination: { ...initialPagination },
  aiTrialFilters: {},
  currentAITrial: null,
  
  // UI State
  activeTab: 'tempData',
  isLoading: false,
  error: null,
};

// ============================================================================
// Store
// ============================================================================

export const useDataLifecycleStore = create<DataLifecycleStore>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      ...initialState,

      // Temp Data Actions
      setTempDataList: (list, total) => set((state) => ({
        tempDataList: list,
        tempDataPagination: { ...state.tempDataPagination, total },
      }), false, 'setTempDataList'),
      
      setTempDataFilters: (filters) => set((state) => ({
        tempDataFilters: { ...state.tempDataFilters, ...filters },
        tempDataPagination: { ...state.tempDataPagination, page: 1 },
      }), false, 'setTempDataFilters'),
      
      resetTempDataFilters: () => set({
        tempDataFilters: {},
        tempDataPagination: { ...get().tempDataPagination, page: 1 },
      }, false, 'resetTempDataFilters'),
      
      setCurrentTempData: (data) => set({
        currentTempData: data,
      }, false, 'setCurrentTempData'),
      
      updateTempData: (id, updates) => set((state) => ({
        tempDataList: state.tempDataList.map((item) =>
          item.id === id ? { ...item, ...updates } : item
        ),
        currentTempData: state.currentTempData?.id === id
          ? { ...state.currentTempData, ...updates }
          : state.currentTempData,
      }), false, 'updateTempData'),
      
      removeTempData: (id) => set((state) => ({
        tempDataList: state.tempDataList.filter((item) => item.id !== id),
        currentTempData: state.currentTempData?.id === id ? null : state.currentTempData,
      }), false, 'removeTempData'),

      // Sample Library Actions
      setSampleList: (list, total) => set((state) => ({
        sampleList: list,
        samplePagination: { ...state.samplePagination, total },
      }), false, 'setSampleList'),
      
      setSampleFilters: (filters) => set((state) => ({
        sampleFilters: { ...state.sampleFilters, ...filters },
        samplePagination: { ...state.samplePagination, page: 1 },
      }), false, 'setSampleFilters'),
      
      resetSampleFilters: () => set({
        sampleFilters: {},
        samplePagination: { ...get().samplePagination, page: 1 },
      }, false, 'resetSampleFilters'),
      
      setCurrentSample: (sample) => set({
        currentSample: sample,
      }, false, 'setCurrentSample'),
      
      updateSample: (id, updates) => set((state) => ({
        sampleList: state.sampleList.map((item) =>
          item.id === id ? { ...item, ...updates } : item
        ),
        currentSample: state.currentSample?.id === id
          ? { ...state.currentSample, ...updates }
          : state.currentSample,
      }), false, 'updateSample'),
      
      removeSample: (id) => set((state) => ({
        sampleList: state.sampleList.filter((item) => item.id !== id),
        currentSample: state.currentSample?.id === id ? null : state.currentSample,
      }), false, 'removeSample'),

      // Review Actions
      setReviewList: (list, total) => set((state) => ({
        reviewList: list,
        reviewPagination: { ...state.reviewPagination, total },
      }), false, 'setReviewList'),
      
      setReviewFilters: (filters) => set((state) => ({
        reviewFilters: { ...state.reviewFilters, ...filters },
        reviewPagination: { ...state.reviewPagination, page: 1 },
      }), false, 'setReviewFilters'),
      
      resetReviewFilters: () => set({
        reviewFilters: {},
        reviewPagination: { ...get().reviewPagination, page: 1 },
      }, false, 'resetReviewFilters'),
      
      setCurrentReview: (review) => set({
        currentReview: review,
      }, false, 'setCurrentReview'),
      
      updateReview: (id, updates) => set((state) => ({
        reviewList: state.reviewList.map((item) =>
          item.id === id ? { ...item, ...updates } : item
        ),
        currentReview: state.currentReview?.id === id
          ? { ...state.currentReview, ...updates }
          : state.currentReview,
      }), false, 'updateReview'),
      
      removeReview: (id) => set((state) => ({
        reviewList: state.reviewList.filter((item) => item.id !== id),
        currentReview: state.currentReview?.id === id ? null : state.currentReview,
      }), false, 'removeReview'),

      // Annotation Task Actions
      setAnnotationTaskList: (list, total) => set((state) => ({
        annotationTaskList: list,
        annotationTaskPagination: { ...state.annotationTaskPagination, total },
      }), false, 'setAnnotationTaskList'),
      
      setAnnotationTaskFilters: (filters) => set((state) => ({
        annotationTaskFilters: { ...state.annotationTaskFilters, ...filters },
        annotationTaskPagination: { ...state.annotationTaskPagination, page: 1 },
      }), false, 'setAnnotationTaskFilters'),
      
      resetAnnotationTaskFilters: () => set({
        annotationTaskFilters: {},
        annotationTaskPagination: { ...get().annotationTaskPagination, page: 1 },
      }, false, 'resetAnnotationTaskFilters'),
      
      setCurrentAnnotationTask: (task) => set({
        currentAnnotationTask: task,
      }, false, 'setCurrentAnnotationTask'),
      
      updateAnnotationTask: (id, updates) => set((state) => ({
        annotationTaskList: state.annotationTaskList.map((item) =>
          item.id === id ? { ...item, ...updates } : item
        ),
        currentAnnotationTask: state.currentAnnotationTask?.id === id
          ? { ...state.currentAnnotationTask, ...updates }
          : state.currentAnnotationTask,
      }), false, 'updateAnnotationTask'),
      
      removeAnnotationTask: (id) => set((state) => ({
        annotationTaskList: state.annotationTaskList.filter((item) => item.id !== id),
        currentAnnotationTask: state.currentAnnotationTask?.id === id ? null : state.currentAnnotationTask,
      }), false, 'removeAnnotationTask'),

      // Enhancement Actions
      setEnhancementList: (list, total) => set((state) => ({
        enhancementList: list,
        enhancementPagination: { ...state.enhancementPagination, total },
      }), false, 'setEnhancementList'),
      
      setEnhancementFilters: (filters) => set((state) => ({
        enhancementFilters: { ...state.enhancementFilters, ...filters },
        enhancementPagination: { ...state.enhancementPagination, page: 1 },
      }), false, 'setEnhancementFilters'),
      
      resetEnhancementFilters: () => set({
        enhancementFilters: {},
        enhancementPagination: { ...get().enhancementPagination, page: 1 },
      }, false, 'resetEnhancementFilters'),
      
      setCurrentEnhancement: (job) => set({
        currentEnhancement: job,
      }, false, 'setCurrentEnhancement'),
      
      updateEnhancement: (id, updates) => set((state) => ({
        enhancementList: state.enhancementList.map((item) =>
          item.id === id ? { ...item, ...updates } : item
        ),
        currentEnhancement: state.currentEnhancement?.id === id
          ? { ...state.currentEnhancement, ...updates }
          : state.currentEnhancement,
      }), false, 'updateEnhancement'),
      
      removeEnhancement: (id) => set((state) => ({
        enhancementList: state.enhancementList.filter((item) => item.id !== id),
        currentEnhancement: state.currentEnhancement?.id === id ? null : state.currentEnhancement,
      }), false, 'removeEnhancement'),

      // AI Trial Actions
      setAITrialList: (list, total) => set((state) => ({
        aiTrialList: list,
        aiTrialPagination: { ...state.aiTrialPagination, total },
      }), false, 'setAITrialList'),
      
      setAITrialFilters: (filters) => set((state) => ({
        aiTrialFilters: { ...state.aiTrialFilters, ...filters },
        aiTrialPagination: { ...state.aiTrialPagination, page: 1 },
      }), false, 'setAITrialFilters'),
      
      resetAITrialFilters: () => set({
        aiTrialFilters: {},
        aiTrialPagination: { ...get().aiTrialPagination, page: 1 },
      }, false, 'resetAITrialFilters'),
      
      setCurrentAITrial: (trial) => set({
        currentAITrial: trial,
      }, false, 'setCurrentAITrial'),
      
      updateAITrial: (id, updates) => set((state) => ({
        aiTrialList: state.aiTrialList.map((item) =>
          item.id === id ? { ...item, ...updates } : item
        ),
        currentAITrial: state.currentAITrial?.id === id
          ? { ...state.currentAITrial, ...updates }
          : state.currentAITrial,
      }), false, 'updateAITrial'),
      
      removeAITrial: (id) => set((state) => ({
        aiTrialList: state.aiTrialList.filter((item) => item.id !== id),
        currentAITrial: state.currentAITrial?.id === id ? null : state.currentAITrial,
      }), false, 'removeAITrial'),

      // UI Actions
      setActiveTab: (tab) => set({
        activeTab: tab,
      }, false, 'setActiveTab'),
      
      setLoading: (isLoading) => set({
        isLoading,
      }, false, 'setLoading'),
      
      setError: (error) => set({
        error,
      }, false, 'setError'),
      
      clearError: () => set({
        error: null,
      }, false, 'clearError'),

      // Reset
      reset: () => set(initialState, false, 'reset'),
    })),
    { name: 'DataLifecycleStore' }
  )
);

// ============================================================================
// Selectors (for optimized re-renders)
// ============================================================================

export const dataLifecycleSelectors = {
  // Temp Data selectors
  getTempDataByState: (state: DataLifecycleStore, targetState: string) =>
    state.tempDataList.filter((item) => item.state === targetState),
  
  getTempDataCount: (state: DataLifecycleStore) => state.tempDataList.length,
  
  // Sample selectors
  getSamplesByQuality: (state: DataLifecycleStore, minScore: number) =>
    state.sampleList.filter((item) => item.quality_score >= minScore),
  
  getSampleCount: (state: DataLifecycleStore) => state.sampleList.length,
  
  // Review selectors
  getPendingReviews: (state: DataLifecycleStore) =>
    state.reviewList.filter((item) => item.status === 'pending'),
  
  getReviewCount: (state: DataLifecycleStore) => state.reviewList.length,
  
  // Annotation Task selectors
  getTasksByStatus: (state: DataLifecycleStore, status: string) =>
    state.annotationTaskList.filter((item) => item.status === status),
  
  getTaskCount: (state: DataLifecycleStore) => state.annotationTaskList.length,
  
  // Enhancement selectors
  getEnhancementsByStatus: (state: DataLifecycleStore, status: string) =>
    state.enhancementList.filter((item) => item.status === status),
  
  getEnhancementCount: (state: DataLifecycleStore) => state.enhancementList.length,
  
  // AI Trial selectors
  getTrialsByStatus: (state: DataLifecycleStore, status: string) =>
    state.aiTrialList.filter((item) => item.status === status),
  
  getTrialCount: (state: DataLifecycleStore) => state.aiTrialList.length,
  
  // Summary statistics
  getSummaryStats: (state: DataLifecycleStore) => ({
    tempDataCount: state.tempDataList.length,
    sampleCount: state.sampleList.length,
    pendingReviews: state.reviewList.filter((r) => r.status === 'pending').length,
    pendingTasks: state.annotationTaskList.filter((t) => t.status === 'created').length,
    runningEnhancements: state.enhancementList.filter((e) => e.status === 'running').length,
    runningTrials: state.aiTrialList.filter((t) => t.status === 'running').length,
  }),
};

export default useDataLifecycleStore;