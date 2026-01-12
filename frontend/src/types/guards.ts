/**
 * Type Guards and Runtime Type Checking
 * 
 * Comprehensive type guards for runtime type validation.
 * These functions help ensure type safety at runtime boundaries.
 */

import type { 
  User, 
  Tenant, 
  Workspace, 
  Permission,
  LoginResponse,
} from './auth';
import type { 
  Task, 
  TaskStatus, 
  TaskPriority, 
  AnnotationType,
} from './task';
import type { 
  DashboardSummary, 
  BusinessMetrics, 
  SystemPerformance,
} from './dashboard';
import type { 
  ApiResponse, 
  ApiError, 
  PaginatedResponse,
} from './api';
import type { 
  QualityRule, 
  QualityIssue,
} from './quality';
import type { 
  BillingRecord, 
  BillingItem,
} from './billing';
import type { 
  AuditLog, 
  SecurityEvent,
} from './security';
import type { 
  Notification,
  NotificationType,
  NotificationPriority,
  NotificationCategory,
} from '../stores/notificationStore';

// ============================================================================
// Primitive Type Guards
// ============================================================================

/** Check if value is a non-empty string */
export const isNonEmptyString = (value: unknown): value is string => {
  return typeof value === 'string' && value.trim().length > 0;
};

/** Check if value is a positive number */
export const isPositiveNumber = (value: unknown): value is number => {
  return typeof value === 'number' && !isNaN(value) && value > 0;
};

/** Check if value is a non-negative number */
export const isNonNegativeNumber = (value: unknown): value is number => {
  return typeof value === 'number' && !isNaN(value) && value >= 0;
};

/** Check if value is a valid integer */
export const isInteger = (value: unknown): value is number => {
  return typeof value === 'number' && Number.isInteger(value);
};

/** Check if value is a valid date */
export const isValidDate = (value: unknown): value is Date => {
  return value instanceof Date && !isNaN(value.getTime());
};

/** Check if value is a valid ISO date string */
export const isISODateString = (value: unknown): value is string => {
  if (typeof value !== 'string') return false;
  const date = new Date(value);
  return !isNaN(date.getTime()) && value.includes('T');
};

/** Check if value is a valid email */
export const isValidEmail = (value: unknown): value is string => {
  if (typeof value !== 'string') return false;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(value);
};

/** Check if value is a valid URL */
export const isValidURL = (value: unknown): value is string => {
  if (typeof value !== 'string') return false;
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
};

/** Check if value is a valid UUID */
export const isValidUUID = (value: unknown): value is string => {
  if (typeof value !== 'string') return false;
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(value);
};

// ============================================================================
// Auth Type Guards
// ============================================================================

/** Check if value is a valid User */
export const isUser = (value: unknown): value is User => {
  if (!value || typeof value !== 'object') return false;
  const user = value as Record<string, unknown>;
  return (
    typeof user.username === 'string' &&
    typeof user.email === 'string' &&
    typeof user.role === 'string'
  );
};

/** Check if value is a valid Tenant */
export const isTenant = (value: unknown): value is Tenant => {
  if (!value || typeof value !== 'object') return false;
  const tenant = value as Record<string, unknown>;
  return (
    typeof tenant.id === 'string' &&
    typeof tenant.name === 'string'
  );
};

/** Check if value is a valid Workspace */
export const isWorkspace = (value: unknown): value is Workspace => {
  if (!value || typeof value !== 'object') return false;
  const workspace = value as Record<string, unknown>;
  return (
    typeof workspace.id === 'string' &&
    typeof workspace.name === 'string' &&
    typeof workspace.tenant_id === 'string'
  );
};

/** Check if value is a valid Permission */
export const isPermission = (value: unknown): value is Permission => {
  if (!value || typeof value !== 'object') return false;
  const permission = value as Record<string, unknown>;
  return (
    typeof permission.id === 'string' &&
    typeof permission.user_id === 'string' &&
    typeof permission.project_id === 'string' &&
    typeof permission.permission_type === 'string'
  );
};

/** Check if value is a valid LoginResponse */
export const isLoginResponse = (value: unknown): value is LoginResponse => {
  if (!value || typeof value !== 'object') return false;
  const response = value as Record<string, unknown>;
  return (
    typeof response.access_token === 'string' &&
    typeof response.token_type === 'string' &&
    isUser(response.user)
  );
};

// ============================================================================
// Task Type Guards
// ============================================================================

/** Valid task statuses */
const TASK_STATUSES: TaskStatus[] = ['pending', 'in_progress', 'completed', 'cancelled'];

/** Valid task priorities */
const TASK_PRIORITIES: TaskPriority[] = ['low', 'medium', 'high', 'urgent'];

/** Valid annotation types */
const ANNOTATION_TYPES: AnnotationType[] = ['text_classification', 'ner', 'sentiment', 'qa', 'custom'];

/** Check if value is a valid TaskStatus */
export const isTaskStatus = (value: unknown): value is TaskStatus => {
  return typeof value === 'string' && TASK_STATUSES.includes(value as TaskStatus);
};

/** Check if value is a valid TaskPriority */
export const isTaskPriority = (value: unknown): value is TaskPriority => {
  return typeof value === 'string' && TASK_PRIORITIES.includes(value as TaskPriority);
};

/** Check if value is a valid AnnotationType */
export const isAnnotationType = (value: unknown): value is AnnotationType => {
  return typeof value === 'string' && ANNOTATION_TYPES.includes(value as AnnotationType);
};

/** Check if value is a valid Task */
export const isTask = (value: unknown): value is Task => {
  if (!value || typeof value !== 'object') return false;
  const task = value as Record<string, unknown>;
  return (
    typeof task.id === 'string' &&
    typeof task.name === 'string' &&
    isTaskStatus(task.status) &&
    isTaskPriority(task.priority) &&
    isAnnotationType(task.annotation_type) &&
    typeof task.created_by === 'string' &&
    typeof task.created_at === 'string' &&
    typeof task.updated_at === 'string' &&
    typeof task.progress === 'number' &&
    typeof task.total_items === 'number' &&
    typeof task.completed_items === 'number' &&
    typeof task.tenant_id === 'string'
  );
};

/** Check if value is a valid Task array */
export const isTaskArray = (value: unknown): value is Task[] => {
  return Array.isArray(value) && value.every(isTask);
};

// ============================================================================
// Dashboard Type Guards
// ============================================================================

/** Check if value is a valid BusinessMetrics */
export const isBusinessMetrics = (value: unknown): value is BusinessMetrics => {
  if (!value || typeof value !== 'object') return false;
  // BusinessMetrics has optional properties, so we just check it's an object
  return true;
};

/** Check if value is a valid SystemPerformance */
export const isSystemPerformance = (value: unknown): value is SystemPerformance => {
  if (!value || typeof value !== 'object') return false;
  const perf = value as Record<string, unknown>;
  return (
    typeof perf.active_requests === 'number' &&
    typeof perf.avg_request_duration === 'object' &&
    typeof perf.database_performance === 'object' &&
    typeof perf.ai_performance === 'object'
  );
};

/** Check if value is a valid DashboardSummary */
export const isDashboardSummary = (value: unknown): value is DashboardSummary => {
  if (!value || typeof value !== 'object') return false;
  const summary = value as Record<string, unknown>;
  return (
    isBusinessMetrics(summary.business_metrics) &&
    isSystemPerformance(summary.system_performance) &&
    typeof summary.generated_at === 'string'
  );
};

// ============================================================================
// API Response Type Guards
// ============================================================================

/** Check if value is a valid ApiResponse */
export const isApiResponse = <T>(
  value: unknown,
  dataGuard?: (data: unknown) => data is T
): value is ApiResponse<T> => {
  if (!value || typeof value !== 'object') return false;
  const response = value as Record<string, unknown>;
  const hasValidStructure = (
    typeof response.success === 'boolean' &&
    'data' in response
  );
  if (!hasValidStructure) return false;
  if (dataGuard && response.data !== undefined) {
    return dataGuard(response.data);
  }
  return true;
};

/** Check if value is a valid ApiError */
export const isApiError = (value: unknown): value is ApiError => {
  if (!value || typeof value !== 'object') return false;
  const error = value as Record<string, unknown>;
  return (
    typeof error.error === 'string' &&
    typeof error.message === 'string' &&
    typeof error.status_code === 'number'
  );
};

/** Check if value is a valid PaginatedResponse */
export const isPaginatedResponse = <T>(
  value: unknown,
  itemGuard?: (item: unknown) => item is T
): value is PaginatedResponse<T> => {
  if (!value || typeof value !== 'object') return false;
  const response = value as Record<string, unknown>;
  const hasValidStructure = (
    Array.isArray(response.items) &&
    typeof response.total === 'number' &&
    typeof response.page === 'number' &&
    typeof response.page_size === 'number' &&
    typeof response.total_pages === 'number'
  );
  if (!hasValidStructure) return false;
  if (itemGuard) {
    return (response.items as unknown[]).every(itemGuard);
  }
  return true;
};

// ============================================================================
// Quality Type Guards
// ============================================================================

/** Check if value is a valid QualityRule */
export const isQualityRule = (value: unknown): value is QualityRule => {
  if (!value || typeof value !== 'object') return false;
  const rule = value as Record<string, unknown>;
  return (
    typeof rule.id === 'string' &&
    typeof rule.name === 'string' &&
    typeof rule.type === 'string' &&
    typeof rule.description === 'string' &&
    typeof rule.enabled === 'boolean' &&
    typeof rule.severity === 'string' &&
    typeof rule.violations_count === 'number'
  );
};

/** Check if value is a valid QualityIssue */
export const isQualityIssue = (value: unknown): value is QualityIssue => {
  if (!value || typeof value !== 'object') return false;
  const issue = value as Record<string, unknown>;
  return (
    typeof issue.id === 'string' &&
    typeof issue.rule_id === 'string' &&
    typeof issue.rule_name === 'string' &&
    typeof issue.task_id === 'string' &&
    typeof issue.task_name === 'string' &&
    typeof issue.severity === 'string' &&
    typeof issue.description === 'string' &&
    typeof issue.status === 'string' &&
    typeof issue.created_at === 'string'
  );
};

// ============================================================================
// Billing Type Guards
// ============================================================================

/** Check if value is a valid BillingItem */
export const isBillingItem = (value: unknown): value is BillingItem => {
  if (!value || typeof value !== 'object') return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.id === 'string' &&
    typeof item.description === 'string' &&
    typeof item.quantity === 'number' &&
    typeof item.unit_price === 'number' &&
    typeof item.amount === 'number' &&
    typeof item.category === 'string'
  );
};

/** Check if value is a valid BillingRecord */
export const isBillingRecord = (value: unknown): value is BillingRecord => {
  if (!value || typeof value !== 'object') return false;
  const record = value as Record<string, unknown>;
  return (
    typeof record.id === 'string' &&
    typeof record.tenant_id === 'string' &&
    typeof record.period_start === 'string' &&
    typeof record.period_end === 'string' &&
    typeof record.total_amount === 'number' &&
    typeof record.status === 'string' &&
    Array.isArray(record.items) &&
    (record.items as unknown[]).every(isBillingItem) &&
    typeof record.created_at === 'string' &&
    typeof record.due_date === 'string'
  );
};

// ============================================================================
// Security Type Guards
// ============================================================================

/** Check if value is a valid AuditLog */
export const isAuditLog = (value: unknown): value is AuditLog => {
  if (!value || typeof value !== 'object') return false;
  const log = value as Record<string, unknown>;
  return (
    typeof log.id === 'string' &&
    typeof log.user_id === 'string' &&
    typeof log.user_name === 'string' &&
    typeof log.action === 'string' &&
    typeof log.resource === 'string' &&
    typeof log.ip_address === 'string' &&
    typeof log.user_agent === 'string' &&
    typeof log.status === 'string' &&
    typeof log.created_at === 'string'
  );
};

/** Check if value is a valid SecurityEvent */
export const isSecurityEvent = (value: unknown): value is SecurityEvent => {
  if (!value || typeof value !== 'object') return false;
  const event = value as Record<string, unknown>;
  return (
    typeof event.id === 'string' &&
    typeof event.type === 'string' &&
    typeof event.severity === 'string' &&
    typeof event.description === 'string' &&
    typeof event.resolved === 'boolean' &&
    typeof event.created_at === 'string'
  );
};

// ============================================================================
// Notification Type Guards
// ============================================================================

/** Valid notification types */
const NOTIFICATION_TYPES: NotificationType[] = ['info', 'success', 'warning', 'error'];

/** Valid notification priorities */
const NOTIFICATION_PRIORITIES: NotificationPriority[] = ['low', 'normal', 'high', 'urgent'];

/** Valid notification categories */
const NOTIFICATION_CATEGORIES: NotificationCategory[] = ['system', 'task', 'quality', 'billing', 'security', 'general'];

/** Check if value is a valid NotificationType */
export const isNotificationType = (value: unknown): value is NotificationType => {
  return typeof value === 'string' && NOTIFICATION_TYPES.includes(value as NotificationType);
};

/** Check if value is a valid NotificationPriority */
export const isNotificationPriority = (value: unknown): value is NotificationPriority => {
  return typeof value === 'string' && NOTIFICATION_PRIORITIES.includes(value as NotificationPriority);
};

/** Check if value is a valid NotificationCategory */
export const isNotificationCategory = (value: unknown): value is NotificationCategory => {
  return typeof value === 'string' && NOTIFICATION_CATEGORIES.includes(value as NotificationCategory);
};

/** Check if value is a valid Notification */
export const isNotification = (value: unknown): value is Notification => {
  if (!value || typeof value !== 'object') return false;
  const notification = value as Record<string, unknown>;
  return (
    typeof notification.id === 'string' &&
    isNotificationType(notification.type) &&
    isNotificationPriority(notification.priority) &&
    isNotificationCategory(notification.category) &&
    typeof notification.title === 'string' &&
    typeof notification.message === 'string' &&
    typeof notification.timestamp === 'string' &&
    typeof notification.read === 'boolean' &&
    typeof notification.dismissed === 'boolean'
  );
};

// ============================================================================
// Utility Type Guards
// ============================================================================

/** Check if value is a non-empty array */
export const isNonEmptyArray = <T>(value: unknown): value is [T, ...T[]] => {
  return Array.isArray(value) && value.length > 0;
};

/** Check if value is a plain object */
export const isPlainObject = (value: unknown): value is Record<string, unknown> => {
  return (
    typeof value === 'object' &&
    value !== null &&
    !Array.isArray(value) &&
    Object.prototype.toString.call(value) === '[object Object]'
  );
};

/** Check if value has a specific property */
export const hasProperty = <K extends string>(
  value: unknown,
  key: K
): value is Record<K, unknown> => {
  return isPlainObject(value) && key in value;
};

/** Check if value has all specified properties */
export const hasProperties = <K extends string>(
  value: unknown,
  keys: K[]
): value is Record<K, unknown> => {
  return isPlainObject(value) && keys.every(key => key in value);
};

/** Create a type guard for a specific value */
export const isExactValue = <T extends string | number | boolean>(
  expected: T
) => (value: unknown): value is T => {
  return value === expected;
};

/** Create a type guard for one of multiple values */
export const isOneOf = <T extends string | number | boolean>(
  values: readonly T[]
) => (value: unknown): value is T => {
  return values.includes(value as T);
};

// ============================================================================
// Assertion Functions
// ============================================================================

/** Assert that a value is defined */
export function assertDefined<T>(
  value: T | undefined | null,
  message = 'Value is undefined or null'
): asserts value is T {
  if (value === undefined || value === null) {
    throw new Error(message);
  }
}

/** Assert that a value is a string */
export function assertString(
  value: unknown,
  message = 'Value is not a string'
): asserts value is string {
  if (typeof value !== 'string') {
    throw new Error(message);
  }
}

/** Assert that a value is a number */
export function assertNumber(
  value: unknown,
  message = 'Value is not a number'
): asserts value is number {
  if (typeof value !== 'number' || isNaN(value)) {
    throw new Error(message);
  }
}

/** Assert that a value is an array */
export function assertArray<T>(
  value: unknown,
  message = 'Value is not an array'
): asserts value is T[] {
  if (!Array.isArray(value)) {
    throw new Error(message);
  }
}

/** Assert that a value passes a type guard */
export function assertType<T>(
  value: unknown,
  guard: (value: unknown) => value is T,
  message = 'Value does not match expected type'
): asserts value is T {
  if (!guard(value)) {
    throw new Error(message);
  }
}
