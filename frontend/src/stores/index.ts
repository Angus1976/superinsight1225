/**
 * Store Exports
 * 
 * Central export point for all Zustand stores, hooks, and utilities.
 * 
 * Architecture Overview:
 * - authStore: Authentication, user, tenant, and workspace state
 * - uiStore: UI preferences (theme, language, sidebar)
 * - taskStore: Task management state with filters, pagination, selection
 * - dashboardStore: Dashboard data and preferences
 * - notificationStore: System notifications and preferences
 * 
 * Usage Patterns:
 * 1. Direct store access: useTaskStore(state => state.tasks)
 * 2. Custom hooks: useTaskList(), useCurrentUser()
 * 3. Selectors: taskSelectors.getFilteredCount(state)
 */

// ============================================================================
// Core Stores
// ============================================================================
export * from './authStore';
export * from './uiStore';
export * from './taskStore';
export * from './dashboardStore';
export * from './notificationStore';

// ============================================================================
// Store Hooks
// ============================================================================
export * from './hooks/useStoreHooks';

// ============================================================================
// Store Utilities
// ============================================================================
export * from './utils/storeUtils';
