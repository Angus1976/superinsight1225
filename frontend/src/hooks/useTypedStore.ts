/**
 * Type-Safe Store Hooks
 * 
 * Provides type-safe hooks for accessing Zustand stores with proper typing.
 * These hooks ensure compile-time type safety for all store interactions.
 */

import { useCallback, useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useAuthStore } from '@/stores/authStore';
import { useTaskStore, taskSelectors } from '@/stores/taskStore';
import { useDashboardStore, dashboardSelectors } from '@/stores/dashboardStore';
import { useNotificationStore, notificationSelectors } from '@/stores/notificationStore';
import type { 
  AuthStore,
  TaskStore,
  DashboardStore,
  NotificationStore,
  StoreSelector,
} from '@/types/store';
import type { TaskStatus } from '@/types/task';

// ============================================================================
// Generic Store Hook Utilities
// ============================================================================

/**
 * Create a type-safe selector hook for any store
 */
export function createTypedSelector<TState>() {
  return function useTypedSelector<TSelected>(
    useStore: (selector: StoreSelector<TState, TSelected>) => TSelected,
    selector: StoreSelector<TState, TSelected>
  ): TSelected {
    return useStore(selector);
  };
}

/**
 * Create a type-safe shallow selector hook for any store
 */
export function createTypedShallowSelector<TState>() {
  return function useTypedShallowSelector<TSelected extends object>(
    useStore: (selector: StoreSelector<TState, TSelected>) => TSelected,
    selector: StoreSelector<TState, TSelected>
  ): TSelected {
    return useStore(useShallow(selector));
  };
}

// ============================================================================
// Auth Store Hooks
// ============================================================================

/**
 * Type-safe hook for auth store state
 */
export function useAuthState() {
  return useAuthStore(
    useShallow((state) => ({
      user: state.user,
      token: state.token,
      currentTenant: state.currentTenant,
      currentWorkspace: state.currentWorkspace,
      workspaces: state.workspaces,
      isAuthenticated: state.isAuthenticated,
    }))
  );
}

/**
 * Type-safe hook for auth store actions
 */
export function useAuthActions() {
  return useAuthStore(
    useShallow((state) => ({
      setAuth: state.setAuth,
      setUser: state.setUser,
      setTenant: state.setTenant,
      setWorkspace: state.setWorkspace,
      setWorkspaces: state.setWorkspaces,
      clearAuth: state.clearAuth,
    }))
  );
}

/**
 * Type-safe hook for current user
 */
export function useCurrentUser() {
  return useAuthStore((state) => state.user);
}

/**
 * Type-safe hook for current tenant
 */
export function useCurrentTenant() {
  return useAuthStore((state) => state.currentTenant);
}

/**
 * Type-safe hook for current workspace
 */
export function useCurrentWorkspace() {
  return useAuthStore((state) => state.currentWorkspace);
}

/**
 * Type-safe hook for authentication status
 */
export function useIsAuthenticated() {
  return useAuthStore((state) => state.isAuthenticated);
}

// ============================================================================
// Task Store Hooks
// ============================================================================

/**
 * Type-safe hook for task store state
 */
export function useTaskState() {
  return useTaskStore(
    useShallow((state) => ({
      tasks: state.tasks,
      currentTask: state.currentTask,
      stats: state.stats,
      filters: state.filters,
      pagination: state.pagination,
      sort: state.sort,
      selection: state.selection,
      isLoading: state.isLoading,
      error: state.error,
    }))
  );
}

/**
 * Type-safe hook for task store actions
 */
export function useTaskActions() {
  return useTaskStore(
    useShallow((state) => ({
      setTasks: state.setTasks,
      setCurrentTask: state.setCurrentTask,
      setStats: state.setStats,
      updateTask: state.updateTask,
      removeTask: state.removeTask,
      addTask: state.addTask,
      setFilters: state.setFilters,
      resetFilters: state.resetFilters,
      setPagination: state.setPagination,
      setPage: state.setPage,
      setPageSize: state.setPageSize,
      setSort: state.setSort,
      selectTask: state.selectTask,
      deselectTask: state.deselectTask,
      selectAll: state.selectAll,
      deselectAll: state.deselectAll,
      toggleSelection: state.toggleSelection,
      setLoading: state.setLoading,
      setError: state.setError,
      clearError: state.clearError,
      reset: state.reset,
    }))
  );
}

/**
 * Type-safe hook for task list
 */
export function useTaskList() {
  return useTaskStore((state) => state.tasks);
}

/**
 * Type-safe hook for current task
 */
export function useCurrentTask() {
  return useTaskStore((state) => state.currentTask);
}

/**
 * Type-safe hook for task stats
 */
export function useTaskStats() {
  return useTaskStore((state) => state.stats);
}

/**
 * Type-safe hook for task filters
 */
export function useTaskFilters() {
  return useTaskStore(
    useShallow((state) => ({
      filters: state.filters,
      setFilters: state.setFilters,
      resetFilters: state.resetFilters,
      hasActiveFilters: taskSelectors.hasActiveFilters(state),
    }))
  );
}

/**
 * Type-safe hook for task pagination
 */
export function useTaskPagination() {
  return useTaskStore(
    useShallow((state) => ({
      pagination: state.pagination,
      setPagination: state.setPagination,
      setPage: state.setPage,
      setPageSize: state.setPageSize,
    }))
  );
}

/**
 * Type-safe hook for task selection
 */
export function useTaskSelection() {
  const store = useTaskStore();
  
  return useMemo(() => ({
    selectedIds: store.selection.selectedIds,
    isAllSelected: store.selection.isAllSelected,
    selectedTasks: taskSelectors.getSelectedTasks(store),
    selectTask: store.selectTask,
    deselectTask: store.deselectTask,
    selectAll: store.selectAll,
    deselectAll: store.deselectAll,
    toggleSelection: store.toggleSelection,
    isSelected: (id: string) => taskSelectors.isTaskSelected(store, id),
  }), [store]);
}

/**
 * Type-safe hook for tasks by status
 */
export function useTasksByStatus(status: TaskStatus) {
  const store = useTaskStore();
  return useMemo(() => taskSelectors.getTasksByStatus(store, status), [store, status]);
}

/**
 * Type-safe hook for task completion percentage
 */
export function useTaskCompletionPercentage() {
  const store = useTaskStore();
  return useMemo(() => taskSelectors.getCompletionPercentage(store), [store]);
}

// ============================================================================
// Dashboard Store Hooks
// ============================================================================

/**
 * Type-safe hook for dashboard store state
 */
export function useDashboardState() {
  return useDashboardStore(
    useShallow((state) => ({
      summary: state.summary,
      annotationEfficiency: state.annotationEfficiency,
      userActivity: state.userActivity,
      alerts: state.alerts,
      quickStats: state.quickStats,
      preferences: state.preferences,
      lastUpdated: state.lastUpdated,
      isLoading: state.isLoading,
      isRefreshing: state.isRefreshing,
      error: state.error,
    }))
  );
}

/**
 * Type-safe hook for dashboard store actions
 */
export function useDashboardActions() {
  return useDashboardStore(
    useShallow((state) => ({
      setSummary: state.setSummary,
      setAnnotationEfficiency: state.setAnnotationEfficiency,
      setUserActivity: state.setUserActivity,
      setQuickStats: state.setQuickStats,
      addAlert: state.addAlert,
      markAlertRead: state.markAlertRead,
      markAllAlertsRead: state.markAllAlertsRead,
      removeAlert: state.removeAlert,
      clearAlerts: state.clearAlerts,
      setTimeRange: state.setTimeRange,
      setCustomDateRange: state.setCustomDateRange,
      setViewMode: state.setViewMode,
      setRefreshInterval: state.setRefreshInterval,
      toggleAutoRefresh: state.toggleAutoRefresh,
      toggleAlerts: state.toggleAlerts,
      updateWidget: state.updateWidget,
      reorderWidgets: state.reorderWidgets,
      resetPreferences: state.resetPreferences,
      setLoading: state.setLoading,
      setRefreshing: state.setRefreshing,
      setLastUpdated: state.setLastUpdated,
      setError: state.setError,
      clearError: state.clearError,
      reset: state.reset,
    }))
  );
}

/**
 * Type-safe hook for dashboard summary
 */
export function useDashboardSummary() {
  return useDashboardStore((state) => state.summary);
}

/**
 * Type-safe hook for dashboard alerts
 */
export function useDashboardAlerts() {
  const store = useDashboardStore();
  
  return useMemo(() => ({
    alerts: store.alerts,
    unreadCount: dashboardSelectors.getUnreadAlertsCount(store),
    addAlert: store.addAlert,
    markAlertRead: store.markAlertRead,
    markAllAlertsRead: store.markAllAlertsRead,
    removeAlert: store.removeAlert,
    clearAlerts: store.clearAlerts,
  }), [store]);
}

/**
 * Type-safe hook for dashboard preferences
 */
export function useDashboardPreferences() {
  return useDashboardStore(
    useShallow((state) => ({
      preferences: state.preferences,
      setTimeRange: state.setTimeRange,
      setCustomDateRange: state.setCustomDateRange,
      setViewMode: state.setViewMode,
      setRefreshInterval: state.setRefreshInterval,
      toggleAutoRefresh: state.toggleAutoRefresh,
      toggleAlerts: state.toggleAlerts,
      updateWidget: state.updateWidget,
      reorderWidgets: state.reorderWidgets,
      resetPreferences: state.resetPreferences,
    }))
  );
}

/**
 * Type-safe hook for visible dashboard widgets
 */
export function useVisibleWidgets() {
  const store = useDashboardStore();
  return useMemo(() => dashboardSelectors.getVisibleWidgets(store), [store]);
}

/**
 * Type-safe hook for dashboard data staleness
 */
export function useIsDashboardDataStale(maxAgeMs: number = 300000) {
  const store = useDashboardStore();
  return useMemo(() => dashboardSelectors.isDataStale(store, maxAgeMs), [store, maxAgeMs]);
}

// ============================================================================
// Notification Store Hooks
// ============================================================================

/**
 * Type-safe hook for notification store state
 */
export function useNotificationState() {
  return useNotificationStore(
    useShallow((state) => ({
      notifications: state.notifications,
      isOpen: state.isOpen,
      preferences: state.preferences,
      isConnected: state.isConnected,
      lastSyncTime: state.lastSyncTime,
    }))
  );
}

/**
 * Type-safe hook for notification store actions
 */
export function useNotificationActions() {
  return useNotificationStore(
    useShallow((state) => ({
      addNotification: state.addNotification,
      markAsRead: state.markAsRead,
      markAllAsRead: state.markAllAsRead,
      dismiss: state.dismiss,
      dismissAll: state.dismissAll,
      removeNotification: state.removeNotification,
      clearExpired: state.clearExpired,
      setOpen: state.setOpen,
      toggle: state.toggle,
      setPreferences: state.setPreferences,
      toggleCategory: state.toggleCategory,
      togglePriority: state.togglePriority,
      setQuietHours: state.setQuietHours,
      resetPreferences: state.resetPreferences,
      setConnected: state.setConnected,
      setLastSyncTime: state.setLastSyncTime,
      reset: state.reset,
    }))
  );
}

/**
 * Type-safe hook for notification list
 */
export function useNotificationList() {
  const store = useNotificationStore();
  return useMemo(() => notificationSelectors.getVisibleNotifications(store), [store]);
}

/**
 * Type-safe hook for unread notification count
 */
export function useUnreadNotificationCount() {
  const store = useNotificationStore();
  return useMemo(() => notificationSelectors.getUnreadCount(store), [store]);
}

/**
 * Type-safe hook for urgent notifications
 */
export function useUrgentNotifications() {
  const store = useNotificationStore();
  return useMemo(() => ({
    urgent: notificationSelectors.getUrgent(store),
    hasUnreadUrgent: notificationSelectors.hasUnreadUrgent(store),
  }), [store]);
}

/**
 * Type-safe hook for notification preferences
 */
export function useNotificationPreferences() {
  return useNotificationStore(
    useShallow((state) => ({
      preferences: state.preferences,
      setPreferences: state.setPreferences,
      toggleCategory: state.toggleCategory,
      togglePriority: state.togglePriority,
      setQuietHours: state.setQuietHours,
      resetPreferences: state.resetPreferences,
    }))
  );
}

/**
 * Type-safe hook for notification panel state
 */
export function useNotificationPanel() {
  return useNotificationStore(
    useShallow((state) => ({
      isOpen: state.isOpen,
      setOpen: state.setOpen,
      toggle: state.toggle,
    }))
  );
}

// ============================================================================
// Combined Hooks
// ============================================================================

/**
 * Type-safe hook for tenant context
 */
export function useTenantContext() {
  const { currentTenant, currentWorkspace } = useAuthState();
  
  return useMemo(() => ({
    tenantId: currentTenant?.id,
    tenantName: currentTenant?.name,
    workspaceId: currentWorkspace?.id,
    workspaceName: currentWorkspace?.name,
    hasTenant: !!currentTenant,
    hasWorkspace: !!currentWorkspace,
  }), [currentTenant, currentWorkspace]);
}

/**
 * Type-safe hook for loading states across stores
 */
export function useGlobalLoadingState() {
  const taskLoading = useTaskStore((state) => state.isLoading);
  const dashboardLoading = useDashboardStore((state) => state.isLoading);
  
  return useMemo(() => ({
    isTaskLoading: taskLoading,
    isDashboardLoading: dashboardLoading,
    isAnyLoading: taskLoading || dashboardLoading,
  }), [taskLoading, dashboardLoading]);
}

/**
 * Type-safe hook for error states across stores
 */
export function useGlobalErrorState() {
  const taskError = useTaskStore((state) => state.error);
  const dashboardError = useDashboardStore((state) => state.error);
  
  return useMemo(() => ({
    taskError,
    dashboardError,
    hasAnyError: !!(taskError || dashboardError),
    errors: [taskError, dashboardError].filter(Boolean) as string[],
  }), [taskError, dashboardError]);
}
