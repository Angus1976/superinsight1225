/**
 * Dashboard Store
 * 
 * Centralized state management for dashboard data and UI preferences.
 * Handles real-time data updates and dashboard customization.
 */
import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';
import type { 
  DashboardSummary, 
  AnnotationEfficiency, 
  UserActivityMetrics,
  MetricCardData,
} from '@/types';

// ============================================================================
// Types
// ============================================================================

export type DashboardTimeRange = '1h' | '6h' | '24h' | '7d' | '30d' | 'custom';
export type DashboardViewMode = 'overview' | 'detailed' | 'compact';
export type RefreshInterval = 0 | 30000 | 60000 | 300000; // 0 = disabled

export interface DashboardWidget {
  id: string;
  type: 'metric' | 'chart' | 'table' | 'progress';
  title: string;
  visible: boolean;
  order: number;
  size: 'small' | 'medium' | 'large';
}

export interface DashboardPreferences {
  timeRange: DashboardTimeRange;
  customDateRange?: [string, string];
  viewMode: DashboardViewMode;
  refreshInterval: RefreshInterval;
  widgets: DashboardWidget[];
  showAlerts: boolean;
  autoRefresh: boolean;
}

interface DashboardState {
  // Data
  summary: DashboardSummary | null;
  annotationEfficiency: AnnotationEfficiency | null;
  userActivity: UserActivityMetrics | null;
  alerts: DashboardAlert[];
  quickStats: MetricCardData[];
  
  // UI State
  preferences: DashboardPreferences;
  lastUpdated: string | null;
  
  // Loading States
  isLoading: boolean;
  isRefreshing: boolean;
  
  // Error States
  error: string | null;
}

export interface DashboardAlert {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actionUrl?: string;
}

interface DashboardActions {
  // Data Actions
  setSummary: (summary: DashboardSummary | null) => void;
  setAnnotationEfficiency: (data: AnnotationEfficiency | null) => void;
  setUserActivity: (data: UserActivityMetrics | null) => void;
  setQuickStats: (stats: MetricCardData[]) => void;
  
  // Alert Actions
  addAlert: (alert: Omit<DashboardAlert, 'id' | 'timestamp' | 'read'>) => void;
  markAlertRead: (id: string) => void;
  markAllAlertsRead: () => void;
  removeAlert: (id: string) => void;
  clearAlerts: () => void;
  
  // Preference Actions
  setTimeRange: (range: DashboardTimeRange) => void;
  setCustomDateRange: (range: [string, string]) => void;
  setViewMode: (mode: DashboardViewMode) => void;
  setRefreshInterval: (interval: RefreshInterval) => void;
  toggleAutoRefresh: () => void;
  toggleAlerts: () => void;
  updateWidget: (id: string, updates: Partial<DashboardWidget>) => void;
  reorderWidgets: (widgets: DashboardWidget[]) => void;
  resetPreferences: () => void;
  
  // Loading Actions
  setLoading: (isLoading: boolean) => void;
  setRefreshing: (isRefreshing: boolean) => void;
  setLastUpdated: (timestamp: string) => void;
  
  // Error Actions
  setError: (error: string | null) => void;
  clearError: () => void;
  
  // Reset
  reset: () => void;
}

export type DashboardStore = DashboardState & DashboardActions;

// ============================================================================
// Initial State
// ============================================================================

const defaultWidgets: DashboardWidget[] = [
  { id: 'total-tasks', type: 'metric', title: '总任务数', visible: true, order: 0, size: 'small' },
  { id: 'completion-rate', type: 'metric', title: '完成率', visible: true, order: 1, size: 'small' },
  { id: 'active-users', type: 'metric', title: '活跃用户', visible: true, order: 2, size: 'small' },
  { id: 'quality-score', type: 'metric', title: '质量评分', visible: true, order: 3, size: 'small' },
  { id: 'efficiency-chart', type: 'chart', title: '标注效率趋势', visible: true, order: 4, size: 'large' },
  { id: 'activity-chart', type: 'chart', title: '用户活动', visible: true, order: 5, size: 'medium' },
  { id: 'progress-overview', type: 'progress', title: '项目进度', visible: true, order: 6, size: 'medium' },
  { id: 'recent-tasks', type: 'table', title: '最近任务', visible: true, order: 7, size: 'large' },
];

const initialPreferences: DashboardPreferences = {
  timeRange: '24h',
  customDateRange: undefined,
  viewMode: 'overview',
  refreshInterval: 60000,
  widgets: defaultWidgets,
  showAlerts: true,
  autoRefresh: true,
};

const initialState: DashboardState = {
  summary: null,
  annotationEfficiency: null,
  userActivity: null,
  alerts: [],
  quickStats: [],
  preferences: initialPreferences,
  lastUpdated: null,
  isLoading: false,
  isRefreshing: false,
  error: null,
};

// ============================================================================
// Store
// ============================================================================

export const useDashboardStore = create<DashboardStore>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        // Data Actions
        setSummary: (summary) => set({ summary }, false, 'setSummary'),
        
        setAnnotationEfficiency: (data) => set({ annotationEfficiency: data }, false, 'setAnnotationEfficiency'),
        
        setUserActivity: (data) => set({ userActivity: data }, false, 'setUserActivity'),
        
        setQuickStats: (stats) => set({ quickStats: stats }, false, 'setQuickStats'),

        // Alert Actions
        addAlert: (alert) => set((state) => ({
          alerts: [
            {
              ...alert,
              id: `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
              timestamp: new Date().toISOString(),
              read: false,
            },
            ...state.alerts,
          ].slice(0, 50), // Keep max 50 alerts
        }), false, 'addAlert'),
        
        markAlertRead: (id) => set((state) => ({
          alerts: state.alerts.map((alert) =>
            alert.id === id ? { ...alert, read: true } : alert
          ),
        }), false, 'markAlertRead'),
        
        markAllAlertsRead: () => set((state) => ({
          alerts: state.alerts.map((alert) => ({ ...alert, read: true })),
        }), false, 'markAllAlertsRead'),
        
        removeAlert: (id) => set((state) => ({
          alerts: state.alerts.filter((alert) => alert.id !== id),
        }), false, 'removeAlert'),
        
        clearAlerts: () => set({ alerts: [] }, false, 'clearAlerts'),

        // Preference Actions
        setTimeRange: (range) => set((state) => ({
          preferences: { ...state.preferences, timeRange: range },
        }), false, 'setTimeRange'),
        
        setCustomDateRange: (range) => set((state) => ({
          preferences: { 
            ...state.preferences, 
            timeRange: 'custom',
            customDateRange: range,
          },
        }), false, 'setCustomDateRange'),
        
        setViewMode: (mode) => set((state) => ({
          preferences: { ...state.preferences, viewMode: mode },
        }), false, 'setViewMode'),
        
        setRefreshInterval: (interval) => set((state) => ({
          preferences: { ...state.preferences, refreshInterval: interval },
        }), false, 'setRefreshInterval'),
        
        toggleAutoRefresh: () => set((state) => ({
          preferences: { ...state.preferences, autoRefresh: !state.preferences.autoRefresh },
        }), false, 'toggleAutoRefresh'),
        
        toggleAlerts: () => set((state) => ({
          preferences: { ...state.preferences, showAlerts: !state.preferences.showAlerts },
        }), false, 'toggleAlerts'),
        
        updateWidget: (id, updates) => set((state) => ({
          preferences: {
            ...state.preferences,
            widgets: state.preferences.widgets.map((widget) =>
              widget.id === id ? { ...widget, ...updates } : widget
            ),
          },
        }), false, 'updateWidget'),
        
        reorderWidgets: (widgets) => set((state) => ({
          preferences: { ...state.preferences, widgets },
        }), false, 'reorderWidgets'),
        
        resetPreferences: () => set((state) => ({
          preferences: initialPreferences,
        }), false, 'resetPreferences'),

        // Loading Actions
        setLoading: (isLoading) => set({ isLoading }, false, 'setLoading'),
        setRefreshing: (isRefreshing) => set({ isRefreshing }, false, 'setRefreshing'),
        setLastUpdated: (timestamp) => set({ lastUpdated: timestamp }, false, 'setLastUpdated'),

        // Error Actions
        setError: (error) => set({ error }, false, 'setError'),
        clearError: () => set({ error: null }, false, 'clearError'),

        // Reset
        reset: () => set({ ...initialState, preferences: get().preferences }, false, 'reset'),
      }),
      {
        name: 'dashboard-storage',
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          preferences: state.preferences,
        }),
      }
    ),
    { name: 'DashboardStore' }
  )
);

// ============================================================================
// Selectors
// ============================================================================

export const dashboardSelectors = {
  // Get unread alerts count
  getUnreadAlertsCount: (state: DashboardStore) =>
    state.alerts.filter((alert) => !alert.read).length,
  
  // Get visible widgets
  getVisibleWidgets: (state: DashboardStore) =>
    state.preferences.widgets
      .filter((widget) => widget.visible)
      .sort((a, b) => a.order - b.order),
  
  // Get time range in hours
  getTimeRangeHours: (state: DashboardStore): number => {
    const { timeRange } = state.preferences;
    switch (timeRange) {
      case '1h': return 1;
      case '6h': return 6;
      case '24h': return 24;
      case '7d': return 168;
      case '30d': return 720;
      default: return 24;
    }
  },
  
  // Check if data is stale
  isDataStale: (state: DashboardStore, maxAgeMs: number = 300000) => {
    if (!state.lastUpdated) return true;
    const lastUpdate = new Date(state.lastUpdated).getTime();
    return Date.now() - lastUpdate > maxAgeMs;
  },
  
  // Get alerts by type
  getAlertsByType: (state: DashboardStore, type: DashboardAlert['type']) =>
    state.alerts.filter((alert) => alert.type === type),
};
