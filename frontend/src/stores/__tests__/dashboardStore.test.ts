/**
 * Dashboard Store Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useDashboardStore, dashboardSelectors } from '../dashboardStore';
import type { DashboardSummary } from '@/types';

describe('dashboardStore', () => {
  const mockSummary: DashboardSummary = {
    business_metrics: {
      annotation_efficiency: {
        period_hours: 24,
        data_points: 24,
        trends: [],
        summary: {
          avg_annotations_per_hour: 50,
          avg_quality_score: 0.85,
          avg_completion_rate: 0.75,
          avg_revision_rate: 0.1,
        },
      },
    },
    system_performance: {
      active_requests: 10,
      avg_request_duration: {},
      database_performance: {},
      ai_performance: {},
    },
    generated_at: '2025-01-01T00:00:00Z',
  };

  beforeEach(() => {
    useDashboardStore.getState().reset();
  });

  describe('initial state', () => {
    it('starts with null summary', () => {
      const { summary } = useDashboardStore.getState();
      expect(summary).toBeNull();
    });

    it('starts with default preferences', () => {
      const { preferences } = useDashboardStore.getState();
      expect(preferences.timeRange).toBe('24h');
      expect(preferences.viewMode).toBe('overview');
      expect(preferences.autoRefresh).toBe(true);
    });

    it('starts with empty alerts', () => {
      const { alerts } = useDashboardStore.getState();
      expect(alerts).toEqual([]);
    });
  });

  describe('data actions', () => {
    it('setSummary updates summary', () => {
      const { setSummary } = useDashboardStore.getState();
      
      setSummary(mockSummary);
      
      const { summary } = useDashboardStore.getState();
      expect(summary).toEqual(mockSummary);
    });

    it('setLastUpdated updates timestamp', () => {
      const { setLastUpdated } = useDashboardStore.getState();
      const timestamp = '2025-01-01T12:00:00Z';
      
      setLastUpdated(timestamp);
      
      const { lastUpdated } = useDashboardStore.getState();
      expect(lastUpdated).toBe(timestamp);
    });
  });

  describe('alert actions', () => {
    it('addAlert adds alert with generated id and timestamp', () => {
      const { addAlert } = useDashboardStore.getState();
      
      addAlert({
        type: 'warning',
        title: '测试警告',
        message: '这是一个测试警告',
      });
      
      const { alerts } = useDashboardStore.getState();
      expect(alerts.length).toBe(1);
      expect(alerts[0].title).toBe('测试警告');
      expect(alerts[0].id).toBeDefined();
      expect(alerts[0].timestamp).toBeDefined();
      expect(alerts[0].read).toBe(false);
    });

    it('markAlertRead marks alert as read', () => {
      const { addAlert, markAlertRead } = useDashboardStore.getState();
      
      addAlert({ type: 'info', title: 'Test', message: 'Test' });
      const alertId = useDashboardStore.getState().alerts[0].id;
      
      markAlertRead(alertId);
      
      const { alerts } = useDashboardStore.getState();
      expect(alerts[0].read).toBe(true);
    });

    it('markAllAlertsRead marks all alerts as read', () => {
      const { addAlert, markAllAlertsRead } = useDashboardStore.getState();
      
      addAlert({ type: 'info', title: 'Test 1', message: 'Test' });
      addAlert({ type: 'warning', title: 'Test 2', message: 'Test' });
      
      markAllAlertsRead();
      
      const { alerts } = useDashboardStore.getState();
      expect(alerts.every(a => a.read)).toBe(true);
    });

    it('clearAlerts removes all alerts', () => {
      const { addAlert, clearAlerts } = useDashboardStore.getState();
      
      addAlert({ type: 'info', title: 'Test', message: 'Test' });
      clearAlerts();
      
      const { alerts } = useDashboardStore.getState();
      expect(alerts).toEqual([]);
    });
  });

  describe('preference actions', () => {
    it('setTimeRange updates time range', () => {
      const { setTimeRange } = useDashboardStore.getState();
      
      setTimeRange('7d');
      
      const { preferences } = useDashboardStore.getState();
      expect(preferences.timeRange).toBe('7d');
    });

    it('setViewMode updates view mode', () => {
      const { setViewMode } = useDashboardStore.getState();
      
      setViewMode('detailed');
      
      const { preferences } = useDashboardStore.getState();
      expect(preferences.viewMode).toBe('detailed');
    });

    it('toggleAutoRefresh toggles auto refresh', () => {
      const { toggleAutoRefresh } = useDashboardStore.getState();
      
      const initialValue = useDashboardStore.getState().preferences.autoRefresh;
      toggleAutoRefresh();
      
      const { preferences } = useDashboardStore.getState();
      expect(preferences.autoRefresh).toBe(!initialValue);
    });

    it('updateWidget updates specific widget', () => {
      const { updateWidget } = useDashboardStore.getState();
      
      updateWidget('total-tasks', { visible: false });
      
      const { preferences } = useDashboardStore.getState();
      const widget = preferences.widgets.find(w => w.id === 'total-tasks');
      expect(widget?.visible).toBe(false);
    });
  });

  describe('selectors', () => {
    it('getUnreadAlertsCount returns correct count', () => {
      const { addAlert, markAlertRead } = useDashboardStore.getState();
      
      addAlert({ type: 'info', title: 'Test 1', message: 'Test' });
      addAlert({ type: 'info', title: 'Test 2', message: 'Test' });
      
      const alertId = useDashboardStore.getState().alerts[0].id;
      markAlertRead(alertId);
      
      const count = dashboardSelectors.getUnreadAlertsCount(useDashboardStore.getState());
      expect(count).toBe(1);
    });

    it('getVisibleWidgets returns sorted visible widgets', () => {
      const { updateWidget } = useDashboardStore.getState();
      
      updateWidget('total-tasks', { visible: false });
      
      const visibleWidgets = dashboardSelectors.getVisibleWidgets(useDashboardStore.getState());
      expect(visibleWidgets.find(w => w.id === 'total-tasks')).toBeUndefined();
    });

    it('getTimeRangeHours returns correct hours', () => {
      const { setTimeRange } = useDashboardStore.getState();
      
      setTimeRange('7d');
      
      const hours = dashboardSelectors.getTimeRangeHours(useDashboardStore.getState());
      expect(hours).toBe(168); // 7 * 24
    });
  });
});
