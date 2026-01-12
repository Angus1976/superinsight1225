/**
 * Store Type Definitions
 * 
 * Strict type definitions for Zustand stores and state management.
 * These types ensure type safety for all store interactions.
 */

import type { StateCreator, StoreApi, UseBoundStore } from 'zustand';

// ============================================================================
// Store Utility Types
// ============================================================================

/** Extract state type from a store */
export type ExtractState<S> = S extends UseBoundStore<StoreApi<infer T>> ? T : never;

/** Extract actions from a store state */
export type ExtractActions<T> = {
  [K in keyof T as T[K] extends (...args: unknown[]) => unknown ? K : never]: T[K];
};

/** Extract data (non-action) properties from a store state */
export type ExtractData<T> = {
  [K in keyof T as T[K] extends (...args: unknown[]) => unknown ? never : K]: T[K];
};

/** Create a selector type for a store */
export type StoreSelector<TState, TSelected> = (state: TState) => TSelected;

/** Create a shallow selector type */
export type ShallowSelector<TState, TSelected extends object> = (state: TState) => TSelected;

// ============================================================================
// Store State Patterns
// ============================================================================

/** Base loading state */
export interface LoadingState {
  isLoading: boolean;
  isRefreshing?: boolean;
}

/** Base error state */
export interface ErrorState {
  error: string | null;
}

/** Base async state */
export interface AsyncState extends LoadingState, ErrorState {}

/** Entity state (for normalized data) */
export interface EntityState<T extends { id: string }> {
  ids: string[];
  entities: Record<string, T>;
}

/** List state with pagination */
export interface ListState<T> extends AsyncState {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

/** Selection state */
export interface SelectionState<T = string> {
  selectedIds: T[];
  isAllSelected: boolean;
}

/** Filter state */
export interface FilterState<T = Record<string, unknown>> {
  filters: T;
  activeFilterCount: number;
}

/** Sort state */
export interface SortState {
  sortField: string;
  sortOrder: 'asc' | 'desc';
}

// ============================================================================
// Store Action Patterns
// ============================================================================

/** Base loading actions */
export interface LoadingActions {
  setLoading: (isLoading: boolean) => void;
  setRefreshing?: (isRefreshing: boolean) => void;
}

/** Base error actions */
export interface ErrorActions {
  setError: (error: string | null) => void;
  clearError: () => void;
}

/** Base async actions */
export interface AsyncActions extends LoadingActions, ErrorActions {}

/** Entity actions */
export interface EntityActions<T extends { id: string }> {
  setEntities: (entities: T[]) => void;
  addEntity: (entity: T) => void;
  updateEntity: (id: string, updates: Partial<T>) => void;
  removeEntity: (id: string) => void;
  clearEntities: () => void;
}

/** List actions */
export interface ListActions<T> extends AsyncActions {
  setItems: (items: T[]) => void;
  addItem: (item: T) => void;
  updateItem: (index: number, item: T) => void;
  removeItem: (index: number) => void;
  clearItems: () => void;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  setTotal: (total: number) => void;
}

/** Selection actions */
export interface SelectionActions<T = string> {
  select: (id: T) => void;
  deselect: (id: T) => void;
  toggle: (id: T) => void;
  selectAll: (ids: T[]) => void;
  deselectAll: () => void;
  isSelected: (id: T) => boolean;
}

/** Filter actions */
export interface FilterActions<T = Record<string, unknown>> {
  setFilters: (filters: Partial<T>) => void;
  setFilter: <K extends keyof T>(key: K, value: T[K]) => void;
  clearFilter: <K extends keyof T>(key: K) => void;
  clearAllFilters: () => void;
}

/** Sort actions */
export interface SortActions {
  setSort: (field: string, order?: 'asc' | 'desc') => void;
  toggleSort: (field: string) => void;
  clearSort: () => void;
}

// ============================================================================
// Store Slice Types
// ============================================================================

/** Create a store slice type */
export type StoreSlice<T, U = T> = StateCreator<
  U,
  [['zustand/devtools', never], ['zustand/persist', unknown]],
  [],
  T
>;

/** Create a store slice without middleware */
export type SimpleStoreSlice<T, U = T> = StateCreator<U, [], [], T>;

/** Combine multiple slices */
export type CombinedSlices<T extends Record<string, unknown>> = {
  [K in keyof T]: T[K];
}[keyof T];

// ============================================================================
// Store Middleware Types
// ============================================================================

/** Persist options */
export interface PersistOptions<T> {
  name: string;
  storage?: 'localStorage' | 'sessionStorage';
  partialize?: (state: T) => Partial<T>;
  version?: number;
  migrate?: (persistedState: unknown, version: number) => T;
}

/** Devtools options */
export interface DevtoolsOptions {
  name?: string;
  enabled?: boolean;
  anonymousActionType?: string;
}

// ============================================================================
// Store Hook Types
// ============================================================================

/** Store hook with selector */
export type UseStoreWithSelector<TState> = {
  <TSelected>(selector: StoreSelector<TState, TSelected>): TSelected;
  (): TState;
};

/** Store hook with shallow selector */
export type UseStoreWithShallowSelector<TState> = {
  <TSelected extends object>(selector: ShallowSelector<TState, TSelected>): TSelected;
  (): TState;
};

// ============================================================================
// Specific Store Types
// ============================================================================

/** Auth store state */
export interface AuthStoreState {
  user: import('./auth').User | null;
  token: string | null;
  currentTenant: import('./auth').Tenant | null;
  currentWorkspace: import('./auth').Workspace | null;
  workspaces: import('./auth').Workspace[];
  isAuthenticated: boolean;
}

/** Auth store actions */
export interface AuthStoreActions {
  setAuth: (
    user: import('./auth').User,
    token: string,
    tenant?: import('./auth').Tenant,
    workspace?: import('./auth').Workspace
  ) => void;
  setUser: (user: import('./auth').User) => void;
  setTenant: (tenant: import('./auth').Tenant) => void;
  setWorkspace: (workspace: import('./auth').Workspace) => void;
  setWorkspaces: (workspaces: import('./auth').Workspace[]) => void;
  clearAuth: () => void;
}

/** Auth store type */
export type AuthStore = AuthStoreState & AuthStoreActions;

/** Task store state */
export interface TaskStoreState extends AsyncState {
  tasks: import('./task').Task[];
  currentTask: import('./task').Task | null;
  stats: import('./task').TaskStats | null;
  filters: TaskFilters;
  pagination: TaskPagination;
  sort: TaskSort;
  selection: SelectionState;
}

/** Task filters */
export interface TaskFilters {
  status?: import('./task').TaskStatus;
  priority?: import('./task').TaskPriority;
  assigneeId?: string;
  search?: string;
  tags?: string[];
  dateRange?: [string, string];
}

/** Task pagination */
export interface TaskPagination {
  page: number;
  pageSize: number;
  total: number;
}

/** Task sort */
export interface TaskSort {
  field: string;
  order: 'asc' | 'desc';
}

/** Task store actions */
export interface TaskStoreActions extends AsyncActions, SelectionActions {
  setTasks: (tasks: import('./task').Task[]) => void;
  setCurrentTask: (task: import('./task').Task | null) => void;
  setStats: (stats: import('./task').TaskStats | null) => void;
  updateTask: (id: string, updates: Partial<import('./task').Task>) => void;
  removeTask: (id: string) => void;
  addTask: (task: import('./task').Task) => void;
  setFilters: (filters: Partial<TaskFilters>) => void;
  resetFilters: () => void;
  setPagination: (pagination: Partial<TaskPagination>) => void;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  setSort: (sort: TaskSort) => void;
  reset: () => void;
}

/** Task store type */
export type TaskStore = TaskStoreState & TaskStoreActions;

/** Dashboard store state */
export interface DashboardStoreState extends AsyncState {
  summary: import('./dashboard').DashboardSummary | null;
  annotationEfficiency: import('./dashboard').AnnotationEfficiency | null;
  userActivity: import('./dashboard').UserActivityMetrics | null;
  alerts: DashboardAlert[];
  quickStats: import('./dashboard').MetricCardData[];
  preferences: DashboardPreferences;
  lastUpdated: string | null;
}

/** Dashboard alert */
export interface DashboardAlert {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actionUrl?: string;
}

/** Dashboard preferences */
export interface DashboardPreferences {
  timeRange: '1h' | '6h' | '24h' | '7d' | '30d' | 'custom';
  customDateRange?: [string, string];
  viewMode: 'overview' | 'detailed' | 'compact';
  refreshInterval: number;
  widgets: DashboardWidget[];
  showAlerts: boolean;
  autoRefresh: boolean;
}

/** Dashboard widget */
export interface DashboardWidget {
  id: string;
  type: 'metric' | 'chart' | 'table' | 'progress';
  title: string;
  visible: boolean;
  order: number;
  size: 'small' | 'medium' | 'large';
}

/** Dashboard store actions */
export interface DashboardStoreActions extends AsyncActions {
  setSummary: (summary: import('./dashboard').DashboardSummary | null) => void;
  setAnnotationEfficiency: (data: import('./dashboard').AnnotationEfficiency | null) => void;
  setUserActivity: (data: import('./dashboard').UserActivityMetrics | null) => void;
  setQuickStats: (stats: import('./dashboard').MetricCardData[]) => void;
  addAlert: (alert: Omit<DashboardAlert, 'id' | 'timestamp' | 'read'>) => void;
  markAlertRead: (id: string) => void;
  markAllAlertsRead: () => void;
  removeAlert: (id: string) => void;
  clearAlerts: () => void;
  setTimeRange: (range: DashboardPreferences['timeRange']) => void;
  setCustomDateRange: (range: [string, string]) => void;
  setViewMode: (mode: DashboardPreferences['viewMode']) => void;
  setRefreshInterval: (interval: number) => void;
  toggleAutoRefresh: () => void;
  toggleAlerts: () => void;
  updateWidget: (id: string, updates: Partial<DashboardWidget>) => void;
  reorderWidgets: (widgets: DashboardWidget[]) => void;
  resetPreferences: () => void;
  setLastUpdated: (timestamp: string) => void;
  reset: () => void;
}

/** Dashboard store type */
export type DashboardStore = DashboardStoreState & DashboardStoreActions;

/** Notification store state */
export interface NotificationStoreState {
  notifications: Notification[];
  isOpen: boolean;
  preferences: NotificationPreferences;
  isConnected: boolean;
  lastSyncTime: string | null;
}

/** Notification */
export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  category: 'system' | 'task' | 'quality' | 'billing' | 'security' | 'general';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  dismissed: boolean;
  actionUrl?: string;
  actionLabel?: string;
  metadata?: Record<string, unknown>;
  expiresAt?: string;
}

/** Notification preferences */
export interface NotificationPreferences {
  enableSound: boolean;
  enableDesktop: boolean;
  showBadge: boolean;
  categories: Record<Notification['category'], boolean>;
  priorities: Record<Notification['priority'], boolean>;
  quietHours: {
    enabled: boolean;
    start: string;
    end: string;
  };
}

/** Notification store actions */
export interface NotificationStoreActions {
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read' | 'dismissed'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  dismiss: (id: string) => void;
  dismissAll: () => void;
  removeNotification: (id: string) => void;
  clearExpired: () => void;
  setOpen: (isOpen: boolean) => void;
  toggle: () => void;
  setPreferences: (preferences: Partial<NotificationPreferences>) => void;
  toggleCategory: (category: Notification['category']) => void;
  togglePriority: (priority: Notification['priority']) => void;
  setQuietHours: (quietHours: NotificationPreferences['quietHours']) => void;
  resetPreferences: () => void;
  setConnected: (isConnected: boolean) => void;
  setLastSyncTime: (time: string) => void;
  reset: () => void;
}

/** Notification store type */
export type NotificationStore = NotificationStoreState & NotificationStoreActions;

// ============================================================================
// Store Selector Helpers
// ============================================================================

/** Create a typed selector */
export const createSelector = <TState, TSelected>(
  selector: StoreSelector<TState, TSelected>
): StoreSelector<TState, TSelected> => selector;

/** Create a memoized selector */
export const createMemoizedSelector = <TState, TDeps extends unknown[], TSelected>(
  deps: (...args: TDeps) => StoreSelector<TState, unknown>[],
  combiner: (...values: unknown[]) => TSelected
): ((...args: TDeps) => StoreSelector<TState, TSelected>) => {
  return (...args: TDeps) => {
    const selectors = deps(...args);
    return (state: TState) => {
      const values = selectors.map(selector => selector(state));
      return combiner(...values);
    };
  };
};

// ============================================================================
// Store Initial State Helpers
// ============================================================================

/** Create initial async state */
export const createInitialAsyncState = (): AsyncState => ({
  isLoading: false,
  error: null,
});

/** Create initial list state */
export const createInitialListState = <T>(): ListState<T> => ({
  ...createInitialAsyncState(),
  items: [],
  total: 0,
  page: 1,
  pageSize: 20,
  hasMore: false,
});

/** Create initial selection state */
export const createInitialSelectionState = <T = string>(): SelectionState<T> => ({
  selectedIds: [],
  isAllSelected: false,
});

/** Create initial entity state */
export const createInitialEntityState = <T extends { id: string }>(): EntityState<T> => ({
  ids: [],
  entities: {},
});
