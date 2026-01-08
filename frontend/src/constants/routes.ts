// Route path constants

export const ROUTES = {
  // Public routes
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',

  // Protected routes
  HOME: '/',
  DASHBOARD: '/dashboard',

  // Task management (Phase 2)
  TASKS: '/tasks',
  TASK_DETAIL: '/tasks/:id',
  TASK_CREATE: '/tasks/create',
  TASK_ANNOTATE: '/tasks/:id/annotate',

  // Billing (Phase 2)
  BILLING: '/billing',
  BILLING_DETAIL: '/billing/:id',

  // Settings
  SETTINGS: '/settings',
  PROFILE: '/settings/profile',

  // Admin
  ADMIN: '/admin',
  ADMIN_TENANTS: '/admin/tenants',
  ADMIN_USERS: '/admin/users',

  // Data Augmentation
  AUGMENTATION: '/augmentation',

  // Quality Management
  QUALITY: '/quality',

  // Security Audit
  SECURITY: '/security',

  // Data Sync
  DATA_SYNC: '/data-sync',

  // Error pages
  NOT_FOUND: '/404',
  FORBIDDEN: '/403',
  SERVER_ERROR: '/500',
} as const;

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES];
