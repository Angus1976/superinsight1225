/**
 * Notification Store Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useNotificationStore, notificationSelectors } from '../notificationStore';

describe('notificationStore', () => {
  beforeEach(() => {
    useNotificationStore.getState().reset();
  });

  describe('initial state', () => {
    it('starts with empty notifications', () => {
      const { notifications } = useNotificationStore.getState();
      expect(notifications).toEqual([]);
    });

    it('starts with panel closed', () => {
      const { isOpen } = useNotificationStore.getState();
      expect(isOpen).toBe(false);
    });

    it('starts with default preferences', () => {
      const { preferences } = useNotificationStore.getState();
      expect(preferences.enableSound).toBe(true);
      expect(preferences.showBadge).toBe(true);
    });
  });

  describe('notification actions', () => {
    it('addNotification adds notification with generated id', () => {
      const { addNotification } = useNotificationStore.getState();
      
      addNotification({
        type: 'info',
        priority: 'normal',
        category: 'system',
        title: '测试通知',
        message: '这是一个测试通知',
      });
      
      const { notifications } = useNotificationStore.getState();
      expect(notifications.length).toBe(1);
      expect(notifications[0].title).toBe('测试通知');
      expect(notifications[0].id).toBeDefined();
      expect(notifications[0].read).toBe(false);
      expect(notifications[0].dismissed).toBe(false);
    });

    it('addNotification respects category preferences', () => {
      const { addNotification, toggleCategory } = useNotificationStore.getState();
      
      toggleCategory('billing'); // Disable billing notifications
      
      addNotification({
        type: 'info',
        priority: 'normal',
        category: 'billing',
        title: 'Billing',
        message: 'Test',
      });
      
      const { notifications } = useNotificationStore.getState();
      expect(notifications.length).toBe(0);
    });

    it('markAsRead marks notification as read', () => {
      const { addNotification, markAsRead } = useNotificationStore.getState();
      
      addNotification({
        type: 'info',
        priority: 'normal',
        category: 'system',
        title: 'Test',
        message: 'Test',
      });
      
      const notifId = useNotificationStore.getState().notifications[0].id;
      markAsRead(notifId);
      
      const { notifications } = useNotificationStore.getState();
      expect(notifications[0].read).toBe(true);
    });

    it('markAllAsRead marks all notifications as read', () => {
      const { addNotification, markAllAsRead } = useNotificationStore.getState();
      
      addNotification({ type: 'info', priority: 'normal', category: 'system', title: 'Test 1', message: 'Test' });
      addNotification({ type: 'info', priority: 'normal', category: 'system', title: 'Test 2', message: 'Test' });
      
      markAllAsRead();
      
      const { notifications } = useNotificationStore.getState();
      expect(notifications.every(n => n.read)).toBe(true);
    });

    it('dismiss marks notification as dismissed', () => {
      const { addNotification, dismiss } = useNotificationStore.getState();
      
      addNotification({
        type: 'info',
        priority: 'normal',
        category: 'system',
        title: 'Test',
        message: 'Test',
      });
      
      const notifId = useNotificationStore.getState().notifications[0].id;
      dismiss(notifId);
      
      const { notifications } = useNotificationStore.getState();
      expect(notifications[0].dismissed).toBe(true);
    });

    it('removeNotification removes notification', () => {
      const { addNotification, removeNotification } = useNotificationStore.getState();
      
      addNotification({
        type: 'info',
        priority: 'normal',
        category: 'system',
        title: 'Test',
        message: 'Test',
      });
      
      const notifId = useNotificationStore.getState().notifications[0].id;
      removeNotification(notifId);
      
      const { notifications } = useNotificationStore.getState();
      expect(notifications.length).toBe(0);
    });
  });

  describe('UI actions', () => {
    it('setOpen updates isOpen state', () => {
      const { setOpen } = useNotificationStore.getState();
      
      setOpen(true);
      expect(useNotificationStore.getState().isOpen).toBe(true);
      
      setOpen(false);
      expect(useNotificationStore.getState().isOpen).toBe(false);
    });

    it('toggle toggles isOpen state', () => {
      const { toggle } = useNotificationStore.getState();
      
      toggle();
      expect(useNotificationStore.getState().isOpen).toBe(true);
      
      toggle();
      expect(useNotificationStore.getState().isOpen).toBe(false);
    });
  });

  describe('preference actions', () => {
    it('toggleCategory toggles category preference', () => {
      const { toggleCategory } = useNotificationStore.getState();
      
      const initialValue = useNotificationStore.getState().preferences.categories.billing;
      toggleCategory('billing');
      
      const { preferences } = useNotificationStore.getState();
      expect(preferences.categories.billing).toBe(!initialValue);
    });

    it('togglePriority toggles priority preference', () => {
      const { togglePriority } = useNotificationStore.getState();
      
      const initialValue = useNotificationStore.getState().preferences.priorities.low;
      togglePriority('low');
      
      const { preferences } = useNotificationStore.getState();
      expect(preferences.priorities.low).toBe(!initialValue);
    });

    it('setQuietHours updates quiet hours', () => {
      const { setQuietHours } = useNotificationStore.getState();
      
      setQuietHours({
        enabled: true,
        start: '23:00',
        end: '07:00',
      });
      
      const { preferences } = useNotificationStore.getState();
      expect(preferences.quietHours.enabled).toBe(true);
      expect(preferences.quietHours.start).toBe('23:00');
    });
  });

  describe('selectors', () => {
    it('getUnreadCount returns correct count', () => {
      const { addNotification, markAsRead } = useNotificationStore.getState();
      
      addNotification({ type: 'info', priority: 'normal', category: 'system', title: 'Test 1', message: 'Test' });
      addNotification({ type: 'info', priority: 'normal', category: 'system', title: 'Test 2', message: 'Test' });
      
      const notifId = useNotificationStore.getState().notifications[0].id;
      markAsRead(notifId);
      
      const count = notificationSelectors.getUnreadCount(useNotificationStore.getState());
      expect(count).toBe(1);
    });

    it('getVisibleNotifications excludes dismissed', () => {
      const { addNotification, dismiss } = useNotificationStore.getState();
      
      addNotification({ type: 'info', priority: 'normal', category: 'system', title: 'Test 1', message: 'Test' });
      addNotification({ type: 'info', priority: 'normal', category: 'system', title: 'Test 2', message: 'Test' });
      
      const notifId = useNotificationStore.getState().notifications[0].id;
      dismiss(notifId);
      
      const visible = notificationSelectors.getVisibleNotifications(useNotificationStore.getState());
      expect(visible.length).toBe(1);
    });

    it('hasUnreadUrgent returns true for unread urgent notifications', () => {
      const { addNotification } = useNotificationStore.getState();
      
      expect(notificationSelectors.hasUnreadUrgent(useNotificationStore.getState())).toBe(false);
      
      addNotification({ type: 'error', priority: 'urgent', category: 'security', title: 'Urgent', message: 'Test' });
      
      expect(notificationSelectors.hasUnreadUrgent(useNotificationStore.getState())).toBe(true);
    });

    it('getByCategory filters by category', () => {
      const { addNotification } = useNotificationStore.getState();
      
      addNotification({ type: 'info', priority: 'normal', category: 'system', title: 'System', message: 'Test' });
      addNotification({ type: 'info', priority: 'normal', category: 'task', title: 'Task', message: 'Test' });
      
      const systemNotifs = notificationSelectors.getByCategory(useNotificationStore.getState(), 'system');
      expect(systemNotifs.length).toBe(1);
      expect(systemNotifs[0].category).toBe('system');
    });
  });
});
