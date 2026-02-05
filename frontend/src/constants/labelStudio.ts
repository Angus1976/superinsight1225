/**
 * Label Studio 相关常量
 * 
 * 集中管理 Label Studio 集成相关的配置和常量
 */

/**
 * Label Studio 语言映射
 * 前端语言代码 -> Label Studio 语言代码
 */
export const LABEL_STUDIO_LANGUAGE_MAP: Record<string, string> = {
  'zh': 'zh-cn',
  'zh-CN': 'zh-cn',
  'zh-TW': 'zh-tw',
  'en': 'en',
  'en-US': 'en',
  'en-GB': 'en',
} as const;

/**
 * 默认 Label Studio 语言
 */
export const LABEL_STUDIO_DEFAULT_LANGUAGE = 'zh-cn';

/**
 * Label Studio 默认 URL
 */
export const LABEL_STUDIO_DEFAULT_URL = 'http://localhost:8080';

/**
 * Label Studio URL 端点
 */
export const LABEL_STUDIO_ENDPOINTS = {
  /** 数据管理器 - 显示任务列表 */
  DATA_MANAGER: '/data',
  /** 项目设置 */
  SETTINGS: '/settings',
  /** 用户登录 */
  LOGIN: '/user/login',
  /** 项目仪表盘 (不推荐使用) */
  DASHBOARD: '',
} as const;

/**
 * Label Studio 错误类型
 */
export const LABEL_STUDIO_ERROR_TYPES = {
  NOT_FOUND: 'not_found',
  AUTH: 'auth',
  NETWORK: 'network',
  SERVICE: 'service',
  UNKNOWN: 'unknown',
} as const;

export type LabelStudioErrorType = typeof LABEL_STUDIO_ERROR_TYPES[keyof typeof LABEL_STUDIO_ERROR_TYPES];

/**
 * Label Studio 同步状态
 */
export const LABEL_STUDIO_SYNC_STATUS = {
  SYNCED: 'synced',
  PENDING: 'pending',
  FAILED: 'failed',
  NOT_SYNCED: 'not_synced',
} as const;

export type LabelStudioSyncStatus = typeof LABEL_STUDIO_SYNC_STATUS[keyof typeof LABEL_STUDIO_SYNC_STATUS];

/**
 * Label Studio 窗口打开选项
 */
export const LABEL_STUDIO_WINDOW_OPTIONS = 'noopener,noreferrer';

/**
 * Label Studio API 路径
 */
export const LABEL_STUDIO_API_PATHS = {
  PROJECTS: '/api/label-studio/projects',
  PROJECT: (id: number | string) => `/api/label-studio/projects/${id}`,
  PROJECT_TASKS: (id: number | string) => `/api/label-studio/projects/${id}/tasks`,
  PROJECT_EXPORT: (id: number | string) => `/api/label-studio/projects/${id}/export`,
  ANNOTATIONS: (id: number | string) => `/api/label-studio/annotations/${id}`,
  TASK_ANNOTATIONS: (projectId: number | string, taskId: number | string) => 
    `/api/label-studio/projects/${projectId}/tasks/${taskId}/annotations`,
} as const;

/**
 * 标注类型
 */
export const ANNOTATION_TYPES = {
  TEXT_CLASSIFICATION: 'text_classification',
  NER: 'ner',
  SENTIMENT: 'sentiment',
  IMAGE_CLASSIFICATION: 'image_classification',
  OBJECT_DETECTION: 'object_detection',
} as const;

export type AnnotationType = typeof ANNOTATION_TYPES[keyof typeof ANNOTATION_TYPES];
