/**
 * Task Management Store
 * 
 * Centralized state management for task-related data.
 * Uses Zustand with proper TypeScript typing and clear action patterns.
 */
import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import type { Task, TaskStatus, TaskPriority, TaskStats } from '@/types';

// ============================================================================
// Types
// ============================================================================

export interface TaskFilters {
  status?: TaskStatus;
  priority?: TaskPriority;
  assigneeId?: string;
  search?: string;
  tags?: string[];
  dateRange?: [string, string];
}

export interface TaskPagination {
  page: number;
  pageSize: number;
  total: number;
}

export interface TaskSortConfig {
  field: string;
  order: 'asc' | 'desc';
}

export interface TaskSelection {
  selectedIds: string[];
  isAllSelected: boolean;
}

interface TaskState {
  // Data
  tasks: Task[];
  currentTask: Task | null;
  stats: TaskStats | null;
  
  // UI State
  filters: TaskFilters;
  pagination: TaskPagination;
  sort: TaskSortConfig;
  selection: TaskSelection;
  
  // Loading States
  isLoading: boolean;
  isLoadingTask: boolean;
  isLoadingStats: boolean;
  
  // Error States
  error: string | null;
}

interface TaskActions {
  // Data Actions
  setTasks: (tasks: Task[]) => void;
  setCurrentTask: (task: Task | null) => void;
  setStats: (stats: TaskStats | null) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  removeTask: (id: string) => void;
  addTask: (task: Task) => void;
  
  // Filter Actions
  setFilters: (filters: Partial<TaskFilters>) => void;
  resetFilters: () => void;
  
  // Pagination Actions
  setPagination: (pagination: Partial<TaskPagination>) => void;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  
  // Sort Actions
  setSort: (sort: TaskSortConfig) => void;
  
  // Selection Actions
  selectTask: (id: string) => void;
  deselectTask: (id: string) => void;
  selectAll: () => void;
  deselectAll: () => void;
  toggleSelection: (id: string) => void;
  
  // Loading Actions
  setLoading: (isLoading: boolean) => void;
  setLoadingTask: (isLoading: boolean) => void;
  setLoadingStats: (isLoading: boolean) => void;
  
  // Error Actions
  setError: (error: string | null) => void;
  clearError: () => void;
  
  // Reset
  reset: () => void;
}

export type TaskStore = TaskState & TaskActions;

// ============================================================================
// Initial State
// ============================================================================

const initialFilters: TaskFilters = {
  status: undefined,
  priority: undefined,
  assigneeId: undefined,
  search: undefined,
  tags: undefined,
  dateRange: undefined,
};

const initialPagination: TaskPagination = {
  page: 1,
  pageSize: 20,
  total: 0,
};

const initialSort: TaskSortConfig = {
  field: 'created_at',
  order: 'desc',
};

const initialSelection: TaskSelection = {
  selectedIds: [],
  isAllSelected: false,
};

const initialState: TaskState = {
  tasks: [],
  currentTask: null,
  stats: null,
  filters: initialFilters,
  pagination: initialPagination,
  sort: initialSort,
  selection: initialSelection,
  isLoading: false,
  isLoadingTask: false,
  isLoadingStats: false,
  error: null,
};

// ============================================================================
// Store
// ============================================================================

export const useTaskStore = create<TaskStore>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      ...initialState,

      // Data Actions
      setTasks: (tasks) => set({ tasks, selection: initialSelection }, false, 'setTasks'),
      
      setCurrentTask: (task) => set({ currentTask: task }, false, 'setCurrentTask'),
      
      setStats: (stats) => set({ stats }, false, 'setStats'),
      
      updateTask: (id, updates) => set((state) => ({
        tasks: state.tasks.map((task) =>
          task.id === id ? { ...task, ...updates } : task
        ),
        currentTask: state.currentTask?.id === id
          ? { ...state.currentTask, ...updates }
          : state.currentTask,
      }), false, 'updateTask'),
      
      removeTask: (id) => set((state) => ({
        tasks: state.tasks.filter((task) => task.id !== id),
        currentTask: state.currentTask?.id === id ? null : state.currentTask,
        selection: {
          ...state.selection,
          selectedIds: state.selection.selectedIds.filter((selectedId) => selectedId !== id),
        },
      }), false, 'removeTask'),
      
      addTask: (task) => set((state) => ({
        tasks: [task, ...state.tasks],
        pagination: {
          ...state.pagination,
          total: state.pagination.total + 1,
        },
      }), false, 'addTask'),

      // Filter Actions
      setFilters: (filters) => set((state) => ({
        filters: { ...state.filters, ...filters },
        pagination: { ...state.pagination, page: 1 }, // Reset to first page on filter change
      }), false, 'setFilters'),
      
      resetFilters: () => set({
        filters: initialFilters,
        pagination: { ...get().pagination, page: 1 },
      }, false, 'resetFilters'),

      // Pagination Actions
      setPagination: (pagination) => set((state) => ({
        pagination: { ...state.pagination, ...pagination },
      }), false, 'setPagination'),
      
      setPage: (page) => set((state) => ({
        pagination: { ...state.pagination, page },
      }), false, 'setPage'),
      
      setPageSize: (pageSize) => set((state) => ({
        pagination: { ...state.pagination, pageSize, page: 1 },
      }), false, 'setPageSize'),

      // Sort Actions
      setSort: (sort) => set({ sort }, false, 'setSort'),

      // Selection Actions
      selectTask: (id) => set((state) => ({
        selection: {
          ...state.selection,
          selectedIds: [...state.selection.selectedIds, id],
          isAllSelected: state.selection.selectedIds.length + 1 === state.tasks.length,
        },
      }), false, 'selectTask'),
      
      deselectTask: (id) => set((state) => ({
        selection: {
          ...state.selection,
          selectedIds: state.selection.selectedIds.filter((selectedId) => selectedId !== id),
          isAllSelected: false,
        },
      }), false, 'deselectTask'),
      
      selectAll: () => set((state) => ({
        selection: {
          selectedIds: state.tasks.map((task) => task.id),
          isAllSelected: true,
        },
      }), false, 'selectAll'),
      
      deselectAll: () => set({
        selection: initialSelection,
      }, false, 'deselectAll'),
      
      toggleSelection: (id) => {
        const { selection } = get();
        if (selection.selectedIds.includes(id)) {
          get().deselectTask(id);
        } else {
          get().selectTask(id);
        }
      },

      // Loading Actions
      setLoading: (isLoading) => set({ isLoading }, false, 'setLoading'),
      setLoadingTask: (isLoadingTask) => set({ isLoadingTask }, false, 'setLoadingTask'),
      setLoadingStats: (isLoadingStats) => set({ isLoadingStats }, false, 'setLoadingStats'),

      // Error Actions
      setError: (error) => set({ error }, false, 'setError'),
      clearError: () => set({ error: null }, false, 'clearError'),

      // Reset
      reset: () => set(initialState, false, 'reset'),
    })),
    { name: 'TaskStore' }
  )
);

// ============================================================================
// Selectors (for optimized re-renders)
// ============================================================================

export const taskSelectors = {
  // Get filtered tasks count
  getFilteredCount: (state: TaskStore) => state.tasks.length,
  
  // Get selected tasks
  getSelectedTasks: (state: TaskStore) => 
    state.tasks.filter((task) => state.selection.selectedIds.includes(task.id)),
  
  // Check if a task is selected
  isTaskSelected: (state: TaskStore, id: string) => 
    state.selection.selectedIds.includes(id),
  
  // Get tasks by status
  getTasksByStatus: (state: TaskStore, status: TaskStatus) =>
    state.tasks.filter((task) => task.status === status),
  
  // Get completion percentage
  getCompletionPercentage: (state: TaskStore) => {
    if (!state.stats || state.stats.total === 0) return 0;
    return Math.round((state.stats.completed / state.stats.total) * 100);
  },
  
  // Check if has active filters
  hasActiveFilters: (state: TaskStore) => {
    const { filters } = state;
    return !!(
      filters.status ||
      filters.priority ||
      filters.assigneeId ||
      filters.search ||
      (filters.tags && filters.tags.length > 0) ||
      filters.dateRange
    );
  },
};
