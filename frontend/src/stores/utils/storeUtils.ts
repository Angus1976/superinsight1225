/**
 * Store Utilities
 * 
 * Common utilities and patterns for Zustand stores.
 * Provides type-safe helpers for state management.
 */
import type { StoreApi, UseBoundStore } from 'zustand';

// ============================================================================
// Types
// ============================================================================

/**
 * Generic loading state interface
 */
export interface LoadingState {
  isLoading: boolean;
  isRefreshing?: boolean;
  loadingKeys?: Set<string>;
}

/**
 * Generic error state interface
 */
export interface ErrorState {
  error: string | null;
  errorCode?: string;
  errorDetails?: Record<string, unknown>;
}

/**
 * Generic pagination state interface
 */
export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

/**
 * Generic filter state interface
 */
export interface FilterState<T = Record<string, unknown>> {
  filters: T;
  activeFilterCount: number;
}

/**
 * Generic selection state interface
 */
export interface SelectionState<T = string> {
  selectedIds: T[];
  isAllSelected: boolean;
}

// ============================================================================
// Selector Helpers
// ============================================================================

/**
 * Creates a shallow selector for optimized re-renders
 * Use this when selecting multiple values from a store
 * 
 * @example
 * const { tasks, isLoading } = useTaskStore(
 *   useShallow(state => ({
 *     tasks: state.tasks,
 *     isLoading: state.isLoading,
 *   }))
 * );
 * 
 * Note: useShallow should be used directly in components, not wrapped.
 * This function is provided for documentation purposes.
 */
export function createShallowSelector<T, R>(selector: (state: T) => R) {
  // Note: useShallow is a hook and should be used directly in components
  // This wrapper is for non-hook contexts where shallow comparison is needed
  return selector;
}

/**
 * Creates a memoized selector that only updates when dependencies change
 * 
 * @example
 * const filteredTasks = useTaskStore(
 *   createMemoizedSelector(
 *     state => state.tasks,
 *     state => state.filters,
 *     (tasks, filters) => tasks.filter(t => matchesFilters(t, filters))
 *   )
 * );
 */
export function createMemoizedSelector<T, A, B, R>(
  selectorA: (state: T) => A,
  selectorB: (state: T) => B,
  combiner: (a: A, b: B) => R
): (state: T) => R {
  let lastA: A;
  let lastB: B;
  let lastResult: R;

  return (state: T) => {
    const a = selectorA(state);
    const b = selectorB(state);

    if (a !== lastA || b !== lastB) {
      lastA = a;
      lastB = b;
      lastResult = combiner(a, b);
    }

    return lastResult;
  };
}

// ============================================================================
// Action Helpers
// ============================================================================

/**
 * Creates a loading action wrapper that handles loading state
 * 
 * @example
 * const fetchTasks = withLoading(
 *   async () => {
 *     const tasks = await api.getTasks();
 *     set({ tasks });
 *   },
 *   (isLoading) => set({ isLoading })
 * );
 */
export function withLoading<T extends (...args: unknown[]) => Promise<unknown>>(
  action: T,
  setLoading: (isLoading: boolean) => void
): T {
  return (async (...args: Parameters<T>) => {
    setLoading(true);
    try {
      return await action(...args);
    } finally {
      setLoading(false);
    }
  }) as T;
}

/**
 * Creates an error-handling action wrapper
 * 
 * @example
 * const fetchTasks = withErrorHandling(
 *   async () => {
 *     const tasks = await api.getTasks();
 *     set({ tasks });
 *   },
 *   (error) => set({ error: error.message })
 * );
 */
export function withErrorHandling<T extends (...args: unknown[]) => Promise<unknown>>(
  action: T,
  setError: (error: string | null) => void
): T {
  return (async (...args: Parameters<T>) => {
    setError(null);
    try {
      return await action(...args);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'An error occurred';
      setError(message);
      throw error;
    }
  }) as T;
}

// ============================================================================
// State Helpers
// ============================================================================

/**
 * Creates initial pagination state
 */
export function createPaginationState(
  pageSize: number = 20,
  page: number = 1
): PaginationState {
  return {
    page,
    pageSize,
    total: 0,
  };
}

/**
 * Creates initial selection state
 */
export function createSelectionState<T = string>(): SelectionState<T> {
  return {
    selectedIds: [],
    isAllSelected: false,
  };
}

/**
 * Calculates pagination info
 */
export function getPaginationInfo(pagination: PaginationState) {
  const { page, pageSize, total } = pagination;
  const totalPages = Math.ceil(total / pageSize);
  const hasNextPage = page < totalPages;
  const hasPrevPage = page > 1;
  const startIndex = (page - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, total);

  return {
    totalPages,
    hasNextPage,
    hasPrevPage,
    startIndex,
    endIndex,
    currentRange: `${startIndex + 1}-${endIndex}`,
  };
}

// ============================================================================
// Reset Helpers
// ============================================================================

/**
 * Creates a reset function that preserves certain keys
 * 
 * @example
 * const reset = createPartialReset(initialState, ['preferences']);
 */
export function createPartialReset<T extends Record<string, unknown>>(
  initialState: T,
  preserveKeys: (keyof T)[]
): (currentState: T) => T {
  return (currentState: T) => {
    const preserved = preserveKeys.reduce((acc, key) => {
      acc[key] = currentState[key];
      return acc;
    }, {} as Partial<T>);

    return { ...initialState, ...preserved };
  };
}

// ============================================================================
// Subscription Helpers
// ============================================================================

/**
 * Creates a subscription to store changes with cleanup
 * 
 * @example
 * useEffect(() => {
 *   return subscribeToStore(
 *     useTaskStore,
 *     state => state.tasks,
 *     (tasks) => console.log('Tasks changed:', tasks)
 *   );
 * }, []);
 */
export function subscribeToStore<T, S>(
  store: UseBoundStore<StoreApi<T>>,
  selector: (state: T) => S,
  callback: (value: S, prevValue: S) => void
): () => void {
  return store.subscribe((state, prevState) => {
    const value = selector(state);
    const prevValue = selector(prevState);
    if (value !== prevValue) {
      callback(value, prevValue);
    }
  });
}

// ============================================================================
// Batch Update Helpers
// ============================================================================

/**
 * Batches multiple state updates into a single update
 * Useful for reducing re-renders when updating multiple values
 * 
 * @example
 * batchUpdate(set, {
 *   tasks: newTasks,
 *   isLoading: false,
 *   error: null,
 * });
 */
export function batchUpdate<T>(
  set: (partial: Partial<T>) => void,
  updates: Partial<T>
): void {
  set(updates);
}

// ============================================================================
// Type Guards
// ============================================================================

/**
 * Type guard for checking if a value is a valid pagination state
 */
export function isPaginationState(value: unknown): value is PaginationState {
  return (
    typeof value === 'object' &&
    value !== null &&
    'page' in value &&
    'pageSize' in value &&
    'total' in value
  );
}

/**
 * Type guard for checking if a value is a valid selection state
 */
export function isSelectionState<T>(value: unknown): value is SelectionState<T> {
  return (
    typeof value === 'object' &&
    value !== null &&
    'selectedIds' in value &&
    'isAllSelected' in value &&
    Array.isArray((value as SelectionState<T>).selectedIds)
  );
}
