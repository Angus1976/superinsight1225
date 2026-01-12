/**
 * Store Hooks
 * 
 * Custom hooks for common store patterns and optimized selectors.
 * These hooks provide a clean API for accessing store state.
 */
import { useCallback, useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useAuthStore } from '../authStore';
import { useUIStore } from '../uiStore';
import { useTaskStore, taskSelectors } from '../taskStore';
import { useDashboardStore, dashboardSelectors } from '../dashboardStore';
import { useNotificationStore, notificationSelectors } from '../notificationStore';
import type { TaskStatus } from '@/types';

// ============================================================================
// Auth Hooks
// ============================================================================

/**
 * Hook for accessing current user and authentication state
 */
export function useCurrentUser() {
  return useAuthStore(
    useShallow((state) => ({
      user: state.user,
      isAuthenticated: state.isAuthenticated,
      currentTenant: state.currentTenant,
      currentWorkspace: state.currentWorkspace,
    }))
  );
}

/**
 * Hook for tenant and workspace management
 */
export function useTenantWorkspace() {
  return useAuthStore(
    useShallow((state) => ({
      currentTenant: state.currentTenant,
      currentWorkspace: state.currentWorkspace,
      workspaces: state.workspaces,
      setTenant: state.setTenant,
      setWorkspace: state.setWorkspace,
      setWorkspaces: state.setWorkspaces,
    }))
  );
}

/**
 * Hook for auth actions
 */
export function useAuthActions() {
  return useAuthStore(
    useShallow((state) => ({
      setAuth: state.setAuth,
      setUser: state.setUser,
      clearAuth: state.clearAuth,
    }))
  );
}

// ============================================================================
// UI Hooks
// ============================================================================

/**
 * Hook for theme management
 */
export function useTheme() {
  return useUIStore(
    useShallow((state) => ({
      theme: state.theme,
      setTheme: state.setTheme,
      toggleTheme: state.toggleTheme,
    }))
  );
}

/**
 * Hook for language management
 */
export function useLanguage() {
  return useUIStore(
    useShallow((state) => ({
      language: state.language,
      setLanguage: state.setLanguage,
    }))
  );
}

/**
 * Hook for sidebar state
 */
export function useSidebar() {
  return useUIStore(
    useShallow((state) => ({
      collapsed: state.sidebarCollapsed,
      setCollapsed: state.setSidebarCollapsed,
      toggle: state.toggleSidebar,
    }))
  );
}

/**
 * Hook for global loading state
 */
export function useGlobalLoading() {
  return useUIStore(
    useShallow((state) => ({
      loading: state.loading,
      setLoading: state.setLoading,
    }))
  );
}

// ============================================================================
// Task Hooks
// ============================================================================

/**
 * Hook for task list with filters and pagination
 */
export function useTaskList() {
  const state = useTaskStore(
    useShallow((state) => ({
      tasks: state.tasks,
      filters: state.filters,
      pagination: state.pagination,
      sort: state.sort,
      isLoading: state.isLoading,
      error: state.error,
    }))
  );

  const actions = useTaskStore(
    useShallow((state) => ({
      setTasks: state.setTasks,
      setFilters: state.setFilters,
      resetFilters: state.resetFilters,
      setPagination: state.setPagination,
      setPage: state.setPage,
      setPageSize: state.setPageSize,
      setSort: state.setSort,
      setLoading: state.setLoading,
      setError: state.setError,
    }))
  );

  const hasActiveFilters = useTaskStore(taskSelectors.hasActiveFilters);

  return {
    ...state,
    ...actions,
    hasActiveFilters,
  };
}

/**
 * Hook for task selection
 */
export function useTaskSelection() {
  const selection = useTaskStore((state) => state.selection);
  const tasks = useTaskStore((state) => state.tasks);
  
  const actions = useTaskStore(
    useShallow((state) => ({
      selectTask: state.selectTask,
      deselectTask: state.deselectTask,
      selectAll: state.selectAll,
      deselectAll: state.deselectAll,
      toggleSelection: state.toggleSelection,
    }))
  );

  const selectedTasks = useMemo(
    () => tasks.filter((task) => selection.selectedIds.includes(task.id)),
    [tasks, selection.selectedIds]
  );

  const isSelected = useCallback(
    (id: string) => selection.selectedIds.includes(id),
    [selection.selectedIds]
  );

  return {
    ...selection,
    ...actions,
    selectedTasks,
    isSelected,
    selectedCount: selection.selectedIds.length,
  };
}

/**
 * Hook for current task detail
 */
export function useCurrentTask() {
  return useTaskStore(
    useShallow((state) => ({
      task: state.currentTask,
      isLoading: state.isLoadingTask,
      setCurrentTask: state.setCurrentTask,
      updateTask: state.updateTask,
      setLoadingTask: state.setLoadingTask,
    }))
  );
}

/**
 * Hook for task statistics
 */
export function useTaskStats() {
  const stats = useTaskStore((state) => state.stats);
  const isLoading = useTaskStore((state) => state.isLoadingStats);
  const setStats = useTaskStore((state) => state.setStats);
  const setLoadingStats = useTaskStore((state) => state.setLoadingStats);
  
  const completionPercentage = useTaskStore(taskSelectors.getCompletionPercentage);

  return {
    stats,
    isLoading,
    setStats,
    setLoadingStats,
    completionPercentage,
  };
}

/**
 * Hook for tasks by status
 */
export function useTasksByStatus(status: TaskStatus) {
  return useTaskStore(
    useCallback((state) => taskSelectors.getTasksByStatus(state, status), [status])
  );
}

// ============================================================================
// Dashboard Hooks
// ============================================================================

/**
 * Hook for dashboard data
 */
export function useDashboardData() {
  return useDashboardStore(
    useShallow((state) => ({
      summary: state.summary,
      annotationEfficiency: state.annotationEfficiency,
      userActivity: state.userActivity,
      quickStats: state.quickStats,
      isLoading: state.isLoading,
      isRefreshing: state.isRefreshing,
      lastUpdated: state.lastUpdated,
      error: state.error,
    }))
  );
}

/**
 * Hook for dashboard preferences
 */
export function useDashboardPreferences() {
  const preferences = useDashboardStore((state) => state.preferences);
  
  const actions = useDashboardStore(
    useShallow((state) => ({
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

  const visibleWidgets = useDashboardStore(dashboardSelectors.getVisibleWidgets);
  const timeRangeHours = useDashboardStore(dashboardSelectors.getTimeRangeHours);

  return {
    ...preferences,
    ...actions,
    visibleWidgets,
    timeRangeHours,
  };
}

/**
 * Hook for dashboard alerts
 */
export function useDashboardAlerts() {
  const alerts = useDashboardStore((state) => state.alerts);
  
  const actions = useDashboardStore(
    useShallow((state) => ({
      addAlert: state.addAlert,
      markAlertRead: state.markAlertRead,
      markAllAlertsRead: state.markAllAlertsRead,
      removeAlert: state.removeAlert,
      clearAlerts: state.clearAlerts,
    }))
  );

  const unreadCount = useDashboardStore(dashboardSelectors.getUnreadAlertsCount);

  return {
    alerts,
    ...actions,
    unreadCount,
  };
}

// ============================================================================
// Notification Hooks
// ============================================================================

/**
 * Hook for notifications
 */
export function useNotifications() {
  const state = useNotificationStore(
    useShallow((state) => ({
      notifications: state.notifications,
      isOpen: state.isOpen,
      isConnected: state.isConnected,
    }))
  );

  const actions = useNotificationStore(
    useShallow((state) => ({
      addNotification: state.addNotification,
      markAsRead: state.markAsRead,
      markAllAsRead: state.markAllAsRead,
      dismiss: state.dismiss,
      dismissAll: state.dismissAll,
      removeNotification: state.removeNotification,
      setOpen: state.setOpen,
      toggle: state.toggle,
    }))
  );

  const unreadCount = useNotificationStore(notificationSelectors.getUnreadCount);
  const visibleNotifications = useNotificationStore(notificationSelectors.getVisibleNotifications);
  const hasUnreadUrgent = useNotificationStore(notificationSelectors.hasUnreadUrgent);

  return {
    ...state,
    ...actions,
    unreadCount,
    visibleNotifications,
    hasUnreadUrgent,
  };
}

/**
 * Hook for notification preferences
 */
export function useNotificationPreferences() {
  const preferences = useNotificationStore((state) => state.preferences);
  
  const actions = useNotificationStore(
    useShallow((state) => ({
      setPreferences: state.setPreferences,
      toggleCategory: state.toggleCategory,
      togglePriority: state.togglePriority,
      setQuietHours: state.setQuietHours,
      resetPreferences: state.resetPreferences,
    }))
  );

  return {
    ...preferences,
    ...actions,
  };
}

// ============================================================================
// Combined Hooks
// ============================================================================

/**
 * Hook for app-wide state summary
 */
export function useAppState() {
  const { isAuthenticated, currentTenant, currentWorkspace } = useCurrentUser();
  const { theme, language } = useUIStore(
    useShallow((state) => ({
      theme: state.theme,
      language: state.language,
    }))
  );
  const notificationCount = useNotificationStore(notificationSelectors.getUnreadCount);

  return {
    isAuthenticated,
    currentTenant,
    currentWorkspace,
    theme,
    language,
    notificationCount,
  };
}

/**
 * Hook for resetting all stores (useful for logout)
 */
export function useResetAllStores() {
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const resetTasks = useTaskStore((state) => state.reset);
  const resetDashboard = useDashboardStore((state) => state.reset);
  const resetNotifications = useNotificationStore((state) => state.reset);

  return useCallback(() => {
    clearAuth();
    resetTasks();
    resetDashboard();
    resetNotifications();
  }, [clearAuth, resetTasks, resetDashboard, resetNotifications]);
}
