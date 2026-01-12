/**
 * Notification Store
 * 
 * Centralized state management for system notifications and messages.
 * Supports real-time notifications, message center, and user preferences.
 */
import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';

// ============================================================================
// Types
// ============================================================================

export type NotificationType = 'info' | 'success' | 'warning' | 'error';
export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent';
export type NotificationCategory = 'system' | 'task' | 'quality' | 'billing' | 'security' | 'general';

export interface Notification {
  id: string;
  type: NotificationType;
  priority: NotificationPriority;
  category: NotificationCategory;
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

export interface NotificationPreferences {
  enableSound: boolean;
  enableDesktop: boolean;
  showBadge: boolean;
  categories: Record<NotificationCategory, boolean>;
  priorities: Record<NotificationPriority, boolean>;
  quietHours: {
    enabled: boolean;
    start: string; // HH:mm format
    end: string;
  };
}

interface NotificationState {
  // Data
  notifications: Notification[];
  
  // UI State
  isOpen: boolean;
  preferences: NotificationPreferences;
  
  // Connection State
  isConnected: boolean;
  lastSyncTime: string | null;
}

interface NotificationActions {
  // Notification Actions
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read' | 'dismissed'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  dismiss: (id: string) => void;
  dismissAll: () => void;
  removeNotification: (id: string) => void;
  clearExpired: () => void;
  
  // UI Actions
  setOpen: (isOpen: boolean) => void;
  toggle: () => void;
  
  // Preference Actions
  setPreferences: (preferences: Partial<NotificationPreferences>) => void;
  toggleCategory: (category: NotificationCategory) => void;
  togglePriority: (priority: NotificationPriority) => void;
  setQuietHours: (quietHours: NotificationPreferences['quietHours']) => void;
  resetPreferences: () => void;
  
  // Connection Actions
  setConnected: (isConnected: boolean) => void;
  setLastSyncTime: (time: string) => void;
  
  // Reset
  reset: () => void;
}

export type NotificationStore = NotificationState & NotificationActions;

// ============================================================================
// Initial State
// ============================================================================

const initialPreferences: NotificationPreferences = {
  enableSound: true,
  enableDesktop: false,
  showBadge: true,
  categories: {
    system: true,
    task: true,
    quality: true,
    billing: true,
    security: true,
    general: true,
  },
  priorities: {
    low: true,
    normal: true,
    high: true,
    urgent: true,
  },
  quietHours: {
    enabled: false,
    start: '22:00',
    end: '08:00',
  },
};

const initialState: NotificationState = {
  notifications: [],
  isOpen: false,
  preferences: initialPreferences,
  isConnected: false,
  lastSyncTime: null,
};

// ============================================================================
// Helpers
// ============================================================================

const generateId = () => `notif-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

const isInQuietHours = (preferences: NotificationPreferences): boolean => {
  if (!preferences.quietHours.enabled) return false;
  
  const now = new Date();
  const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
  const { start, end } = preferences.quietHours;
  
  if (start <= end) {
    return currentTime >= start && currentTime <= end;
  } else {
    // Quiet hours span midnight
    return currentTime >= start || currentTime <= end;
  }
};

// ============================================================================
// Store
// ============================================================================

export const useNotificationStore = create<NotificationStore>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        // Notification Actions
        addNotification: (notification) => {
          const state = get();
          const { preferences } = state;
          
          // Check if category is enabled
          if (!preferences.categories[notification.category]) return;
          
          // Check if priority is enabled
          if (!preferences.priorities[notification.priority]) return;
          
          // Check quiet hours (except for urgent notifications)
          if (notification.priority !== 'urgent' && isInQuietHours(preferences)) return;
          
          const newNotification: Notification = {
            ...notification,
            id: generateId(),
            timestamp: new Date().toISOString(),
            read: false,
            dismissed: false,
          };
          
          set((state) => ({
            notifications: [newNotification, ...state.notifications].slice(0, 100), // Keep max 100
          }), false, 'addNotification');
        },
        
        markAsRead: (id) => set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
        }), false, 'markAsRead'),
        
        markAllAsRead: () => set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, read: true })),
        }), false, 'markAllAsRead'),
        
        dismiss: (id) => set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, dismissed: true } : n
          ),
        }), false, 'dismiss'),
        
        dismissAll: () => set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, dismissed: true })),
        }), false, 'dismissAll'),
        
        removeNotification: (id) => set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        }), false, 'removeNotification'),
        
        clearExpired: () => set((state) => ({
          notifications: state.notifications.filter((n) => {
            if (!n.expiresAt) return true;
            return new Date(n.expiresAt) > new Date();
          }),
        }), false, 'clearExpired'),

        // UI Actions
        setOpen: (isOpen) => set({ isOpen }, false, 'setOpen'),
        toggle: () => set((state) => ({ isOpen: !state.isOpen }), false, 'toggle'),

        // Preference Actions
        setPreferences: (preferences) => set((state) => ({
          preferences: { ...state.preferences, ...preferences },
        }), false, 'setPreferences'),
        
        toggleCategory: (category) => set((state) => ({
          preferences: {
            ...state.preferences,
            categories: {
              ...state.preferences.categories,
              [category]: !state.preferences.categories[category],
            },
          },
        }), false, 'toggleCategory'),
        
        togglePriority: (priority) => set((state) => ({
          preferences: {
            ...state.preferences,
            priorities: {
              ...state.preferences.priorities,
              [priority]: !state.preferences.priorities[priority],
            },
          },
        }), false, 'togglePriority'),
        
        setQuietHours: (quietHours) => set((state) => ({
          preferences: { ...state.preferences, quietHours },
        }), false, 'setQuietHours'),
        
        resetPreferences: () => set({
          preferences: initialPreferences,
        }, false, 'resetPreferences'),

        // Connection Actions
        setConnected: (isConnected) => set({ isConnected }, false, 'setConnected'),
        setLastSyncTime: (time) => set({ lastSyncTime: time }, false, 'setLastSyncTime'),

        // Reset
        reset: () => set(initialState, false, 'reset'),
      }),
      {
        name: 'notification-storage',
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          preferences: state.preferences,
          notifications: state.notifications.slice(0, 20), // Persist only recent 20
        }),
      }
    ),
    { name: 'NotificationStore' }
  )
);

// ============================================================================
// Selectors
// ============================================================================

export const notificationSelectors = {
  // Get unread count
  getUnreadCount: (state: NotificationStore) =>
    state.notifications.filter((n) => !n.read && !n.dismissed).length,
  
  // Get visible notifications (not dismissed)
  getVisibleNotifications: (state: NotificationStore) =>
    state.notifications.filter((n) => !n.dismissed),
  
  // Get notifications by category
  getByCategory: (state: NotificationStore, category: NotificationCategory) =>
    state.notifications.filter((n) => n.category === category && !n.dismissed),
  
  // Get notifications by priority
  getByPriority: (state: NotificationStore, priority: NotificationPriority) =>
    state.notifications.filter((n) => n.priority === priority && !n.dismissed),
  
  // Get urgent notifications
  getUrgent: (state: NotificationStore) =>
    state.notifications.filter((n) => n.priority === 'urgent' && !n.read && !n.dismissed),
  
  // Check if has unread urgent
  hasUnreadUrgent: (state: NotificationStore) =>
    state.notifications.some((n) => n.priority === 'urgent' && !n.read && !n.dismissed),
  
  // Get recent notifications (last 24 hours)
  getRecent: (state: NotificationStore) => {
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    return state.notifications.filter((n) => n.timestamp > oneDayAgo && !n.dismissed);
  },
};
