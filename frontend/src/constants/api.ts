// API endpoint constants

export const API_ENDPOINTS = {
  // Authentication
  AUTH: {
    LOGIN: '/api/auth/login',
    LOGOUT: '/api/auth/logout',
    REGISTER: '/api/auth/register',
    CURRENT_USER: '/api/auth/me',
    REFRESH: '/api/auth/refresh',
    SWITCH_TENANT: '/api/auth/switch-tenant',
    FORGOT_PASSWORD: '/api/auth/forgot-password',
    RESET_PASSWORD: '/api/auth/reset-password',
  },

  // Label Studio
  LABEL_STUDIO: {
    PROJECTS: '/api/label-studio/projects',
    PROJECT_BY_ID: (id: string) => `/api/label-studio/projects/${id}`,
    TASKS: (projectId: string) => `/api/label-studio/projects/${projectId}/tasks`,
    ANNOTATIONS: (projectId: string, taskId: string) =>
      `/api/label-studio/projects/${projectId}/tasks/${taskId}/annotations`,
    // New endpoints for annotation workflow fix
    ENSURE_PROJECT: '/api/label-studio/projects/ensure',
    VALIDATE_PROJECT: (id: string) => `/api/label-studio/projects/${id}/validate`,
    IMPORT_TASKS: (projectId: string) => `/api/label-studio/projects/${projectId}/import-tasks`,
    AUTH_URL: (projectId: string) => `/api/label-studio/projects/${projectId}/auth-url`,
    SYNC_ANNOTATIONS: (projectId: string) => `/api/label-studio/projects/${projectId}/sync-annotations`,
  },

  // Label Studio Workspaces (Enterprise)
  LS_WORKSPACES: {
    BASE: '/api/ls-workspaces',
    BY_ID: (id: string) => `/api/ls-workspaces/${id}`,
    MEMBERS: (id: string) => `/api/ls-workspaces/${id}/members`,
    MEMBER_BY_ID: (workspaceId: string, userId: string) => `/api/ls-workspaces/${workspaceId}/members/${userId}`,
    PERMISSIONS: (id: string) => `/api/ls-workspaces/${id}/permissions`,
    PROJECTS: (id: string) => `/api/ls-workspaces/${id}/projects`,
    PROJECT_BY_ID: (workspaceId: string, projectId: string) => `/api/ls-workspaces/${workspaceId}/projects/${projectId}`,
  },

  // Users
  USERS: {
    BASE: '/api/security/users',
    BY_ID: (id: string) => `/api/security/users/${id}`,
    ROLE: (id: string) => `/api/security/users/${id}/role`,
  },

  // Business metrics
  METRICS: {
    SUMMARY: '/api/business-metrics/summary',
    ANNOTATION_EFFICIENCY: '/api/business-metrics/annotation-efficiency',
    USER_ACTIVITY: '/api/business-metrics/user-activity',
    AI_MODELS: '/api/business-metrics/ai-models',
    PROJECTS: '/api/business-metrics/projects',
  },

  // Admin
  ADMIN: {
    TENANTS: '/api/auth/tenants',
    TENANT_BY_ID: (id: string) => `/api/auth/tenants/${id}`,
  },

  // Workspaces
  WORKSPACES: {
    BASE: '/api/workspaces',
    BY_ID: (id: string) => `/api/workspaces/${id}`,
    MEMBERS: (id: string) => `/api/workspaces/${id}/members`,
    SWITCH: '/api/workspaces/switch',
    MY_WORKSPACES: '/api/workspaces/my',
  },

  // Billing
  BILLING: {
    RECORDS: (tenantId: string) => `/api/billing/records/${tenantId}`,
    ANALYSIS: (tenantId: string) => `/api/billing/analysis/${tenantId}`,
    TRENDS: (tenantId: string) => `/api/billing/analytics/trends/${tenantId}`,
  },

  // Quality
  QUALITY: {
    DASHBOARD: '/api/quality/dashboard/summary',
    RULES: '/api/quality/rules',
    ISSUES: '/api/quality/issues',
    RUN_ALL: '/api/quality/rules/run-all',
    STATS: '/api/quality/stats',
  },

  // Security / Audit
  SECURITY: {
    AUDIT_LOGS: '/api/security/audit-logs',
    AUDIT_SUMMARY: '/api/security/audit/summary',
    PERMISSIONS: '/api/security/permissions',
    IP_WHITELIST: '/api/security/ip-whitelist',
    EVENTS: '/api/security/events',
    EXPORT_LOGS: '/api/security/audit-logs/export',
    BLOCKED_IPS: '/api/security/blocked-ips',
    SESSIONS: '/api/security/sessions',
    STATS: '/api/security/stats',
  },

  // Data Augmentation
  AUGMENTATION: {
    JOBS: '/api/augmentation/jobs',
    SAMPLES: '/api/augmentation/samples',
    UPLOAD: '/api/augmentation/upload',
    STATS: '/api/augmentation/stats',
  },

  // Tasks
  TASKS: {
    BASE: '/api/tasks',
    BY_ID: (id: string) => `/api/tasks/${id}`,
    STATS: '/api/tasks/stats',
    ASSIGN: (id: string) => `/api/tasks/${id}/assign`,
    BATCH: '/api/tasks/batch',
  },

  // Datalake/Warehouse
  DATALAKE: {
    SOURCES: '/api/v1/datalake/sources',
    SOURCE_BY_ID: (id: string) => `/api/v1/datalake/sources/${id}`,
    TEST_CONNECTION: (id: string) => `/api/v1/datalake/sources/${id}/test`,
    DATABASES: (id: string) => `/api/v1/datalake/sources/${id}/databases`,
    TABLES: (id: string) => `/api/v1/datalake/sources/${id}/tables`,
    DASHBOARD_OVERVIEW: '/api/v1/datalake/dashboard/overview',
    DASHBOARD_HEALTH: '/api/v1/datalake/dashboard/health',
    VOLUME_TRENDS: '/api/v1/datalake/dashboard/volume-trends',
    QUERY_PERFORMANCE: '/api/v1/datalake/dashboard/query-performance',
    DATA_FLOW: '/api/v1/datalake/dashboard/data-flow',
  },

  // System
  SYSTEM: {
    HEALTH: '/health',
    STATUS: '/system/status',
    METRICS: '/system/metrics',
    SERVICES: '/system/services',
  },

  // LLM Configuration
  LLM_CONFIGS: {
    BASE: '/api/llm-configs',
    BY_ID: (id: string) => `/api/llm-configs/${id}`,
    TEST: (id: string) => `/api/llm-configs/${id}/test`,
  },

  // Applications
  APPLICATIONS: {
    BASE: '/api/applications',
    BY_CODE: (code: string) => `/api/applications/${code}`,
  },

  // LLM Bindings
  LLM_BINDINGS: {
    BASE: '/api/llm-bindings',
    BY_ID: (id: string) => `/api/llm-bindings/${id}`,
  },
} as const;
