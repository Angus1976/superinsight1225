// Task management hook with optimized data fetching
// Features:
// - Data caching with configurable stale time
// - Request deduplication via React Query
// - Pagination support for task lists
// - Lazy loading for task details
import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { message } from 'antd';
import { taskService } from '@/services/task';
import type { TaskListParams, CreateTaskPayload, UpdateTaskPayload, Task } from '@/types';

// Query keys for cache management and request deduplication
const QUERY_KEYS = {
  tasks: 'tasks',
  task: 'task',
  taskStats: 'taskStats',
  tasksPaginated: 'tasksPaginated',
  tasksInfinite: 'tasksInfinite',
} as const;

// Cache configuration constants
const CACHE_CONFIG = {
  // Task list cache: 30 seconds stale time, 5 minutes garbage collection
  taskList: {
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  },
  // Single task cache: 1 minute stale time, 10 minutes garbage collection
  taskDetail: {
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
  },
  // Task stats cache: 1 minute stale time
  taskStats: {
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
  },
} as const;

// Default pagination settings
const DEFAULT_PAGE_SIZE = 10;

/**
 * Hook for fetching task list with caching and request deduplication
 * React Query automatically deduplicates concurrent requests with the same query key
 */
export function useTasks(params: TaskListParams = {}) {
  return useQuery({
    // Query key includes params for proper cache invalidation
    queryKey: [QUERY_KEYS.tasks, params],
    queryFn: () => taskService.getList(params),
    // Data is considered fresh for 30 seconds
    staleTime: CACHE_CONFIG.taskList.staleTime,
    // Keep unused data in cache for 5 minutes
    gcTime: CACHE_CONFIG.taskList.gcTime,
    // Refetch on window focus for fresh data
    refetchOnWindowFocus: true,
    // Don't refetch on mount if data is fresh
    refetchOnMount: 'always',
  });
}

/**
 * Hook for paginated task list with optimized caching
 * Supports page-based pagination with prefetching
 */
export function useTasksPaginated(params: TaskListParams = {}) {
  const queryClient = useQueryClient();
  const page = params.page || 1;
  const pageSize = params.page_size || DEFAULT_PAGE_SIZE;

  const query = useQuery({
    queryKey: [QUERY_KEYS.tasksPaginated, { ...params, page, page_size: pageSize }],
    queryFn: () => taskService.getList({ ...params, page, page_size: pageSize }),
    staleTime: CACHE_CONFIG.taskList.staleTime,
    gcTime: CACHE_CONFIG.taskList.gcTime,
    // Keep previous data while fetching new page
    placeholderData: (previousData) => previousData,
  });

  // Prefetch next page for smoother pagination
  const prefetchNextPage = () => {
    if (query.data && page * pageSize < query.data.total) {
      queryClient.prefetchQuery({
        queryKey: [QUERY_KEYS.tasksPaginated, { ...params, page: page + 1, page_size: pageSize }],
        queryFn: () => taskService.getList({ ...params, page: page + 1, page_size: pageSize }),
        staleTime: CACHE_CONFIG.taskList.staleTime,
      });
    }
  };

  return {
    ...query,
    prefetchNextPage,
    pagination: {
      current: page,
      pageSize,
      total: query.data?.total || 0,
      hasNextPage: query.data ? page * pageSize < query.data.total : false,
      hasPreviousPage: page > 1,
    },
  };
}

/**
 * Hook for infinite scroll task list (lazy loading)
 * Loads more tasks as user scrolls
 */
export function useTasksInfinite(params: Omit<TaskListParams, 'page'> = {}) {
  const pageSize = params.page_size || DEFAULT_PAGE_SIZE;

  return useInfiniteQuery({
    queryKey: [QUERY_KEYS.tasksInfinite, params],
    queryFn: ({ pageParam = 1 }) => 
      taskService.getList({ ...params, page: pageParam, page_size: pageSize }),
    initialPageParam: 1,
    getNextPageParam: (lastPage, allPages) => {
      const totalFetched = allPages.length * pageSize;
      return totalFetched < lastPage.total ? allPages.length + 1 : undefined;
    },
    staleTime: CACHE_CONFIG.taskList.staleTime,
    gcTime: CACHE_CONFIG.taskList.gcTime,
  });
}

/**
 * Hook for fetching single task with lazy loading support
 * Only fetches when id is provided and enabled
 */
export function useTask(id: string, options?: { enabled?: boolean }) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: [QUERY_KEYS.task, id],
    queryFn: () => taskService.getById(id),
    // Only fetch when id is provided and explicitly enabled
    enabled: !!id && (options?.enabled !== false),
    // Longer stale time for individual tasks
    staleTime: CACHE_CONFIG.taskDetail.staleTime,
    gcTime: CACHE_CONFIG.taskDetail.gcTime,
    // Use cached data from task list if available
    initialData: () => {
      // Try to find task in cached task list
      const cachedLists = queryClient.getQueriesData<{ items: Task[] }>({
        queryKey: [QUERY_KEYS.tasks],
      });
      
      for (const [, data] of cachedLists) {
        const task = data?.items?.find((t) => t.id === id);
        if (task) return task;
      }
      return undefined;
    },
    // Mark initial data as stale to trigger background refetch
    initialDataUpdatedAt: 0,
  });
}

/**
 * Hook for lazy loading task details
 * Returns a function to trigger the fetch manually
 */
export function useLazyTask() {
  const queryClient = useQueryClient();

  const fetchTask = async (id: string): Promise<Task> => {
    return queryClient.fetchQuery({
      queryKey: [QUERY_KEYS.task, id],
      queryFn: () => taskService.getById(id),
      staleTime: CACHE_CONFIG.taskDetail.staleTime,
    });
  };

  const prefetchTask = (id: string) => {
    queryClient.prefetchQuery({
      queryKey: [QUERY_KEYS.task, id],
      queryFn: () => taskService.getById(id),
      staleTime: CACHE_CONFIG.taskDetail.staleTime,
    });
  };

  return { fetchTask, prefetchTask };
}

export function useTaskStats() {
  return useQuery({
    queryKey: [QUERY_KEYS.taskStats],
    queryFn: () => taskService.getStats(),
    staleTime: CACHE_CONFIG.taskStats.staleTime,
    gcTime: CACHE_CONFIG.taskStats.gcTime,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateTaskPayload) => taskService.create(payload),
    onSuccess: () => {
      // Invalidate all task-related queries
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasks] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasksPaginated] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasksInfinite] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.taskStats] });
      message.success('Task created successfully');
    },
    onError: () => {
      message.error('Failed to create task');
    },
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateTaskPayload }) =>
      taskService.update(id, payload),
    onSuccess: (data) => {
      // Invalidate list queries and specific task query
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasks] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasksPaginated] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasksInfinite] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.task, data.id] });
      message.success('Task updated successfully');
    },
    onError: () => {
      message.error('Failed to update task');
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => taskService.delete(id),
    onSuccess: () => {
      // Invalidate all task-related queries
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasks] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasksPaginated] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasksInfinite] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.taskStats] });
      message.success('Task deleted successfully');
    },
    onError: () => {
      message.error('Failed to delete task');
    },
  });
}

export function useAssignTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, userId }: { id: string; userId: string }) =>
      taskService.assign(id, userId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasks] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasksPaginated] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasksInfinite] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.task, data.id] });
      message.success('Task assigned successfully');
    },
    onError: () => {
      message.error('Failed to assign task');
    },
  });
}

export function useBatchDeleteTasks() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ids: string[]) => taskService.batchDelete(ids),
    onSuccess: () => {
      // Invalidate all task-related queries
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasks] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasksPaginated] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.tasksInfinite] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.taskStats] });
      message.success('Tasks deleted successfully');
    },
    onError: () => {
      message.error('Failed to delete tasks');
    },
  });
}
