/**
 * Error Handler Utilities
 * 
 * Comprehensive error handling utilities for transforming, classifying,
 * and managing errors throughout the application.
 */

import { AxiosError } from 'axios';
import type {
  AppError,
  ErrorCategory,
  ErrorSeverity,
  RecoveryActionConfig,
  FieldError,
  HTTP_STATUS_CATEGORY_MAP,
  ERROR_CODE_PREFIXES,
} from '@/types/error';

// Generate unique error ID
const generateErrorId = (): string => {
  return `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

// Get error category from HTTP status code
export const getErrorCategory = (statusCode?: number): ErrorCategory => {
  if (!statusCode) return 'unknown';
  
  const categoryMap: Record<number, ErrorCategory> = {
    400: 'validation',
    401: 'auth',
    403: 'permission',
    404: 'notFound',
    408: 'timeout',
    409: 'conflict',
    422: 'validation',
    429: 'rateLimit',
    500: 'server',
    502: 'server',
    503: 'maintenance',
    504: 'timeout',
  };
  
  return categoryMap[statusCode] || (statusCode >= 500 ? 'server' : 'unknown');
};

// Get error severity based on category
export const getErrorSeverity = (category: ErrorCategory): ErrorSeverity => {
  const severityMap: Record<ErrorCategory, ErrorSeverity> = {
    network: 'error',
    auth: 'warning',
    validation: 'warning',
    server: 'error',
    client: 'error',
    timeout: 'warning',
    permission: 'warning',
    notFound: 'info',
    conflict: 'warning',
    rateLimit: 'warning',
    maintenance: 'info',
    unknown: 'error',
  };
  return severityMap[category];
};

// Generate error code
export const generateErrorCode = (category: ErrorCategory, statusCode?: number): string => {
  const prefixes: Record<ErrorCategory, string> = {
    network: 'NET',
    auth: 'AUTH',
    validation: 'VAL',
    server: 'SRV',
    client: 'CLT',
    timeout: 'TMO',
    permission: 'PRM',
    notFound: 'NF',
    conflict: 'CNF',
    rateLimit: 'RL',
    maintenance: 'MNT',
    unknown: 'UNK',
  };
  
  const prefix = prefixes[category];
  const code = statusCode || Math.floor(Math.random() * 900) + 100;
  return `${prefix}_${code}`;
};

// Get default recovery actions based on error category
export const getDefaultRecoveryActions = (category: ErrorCategory): RecoveryActionConfig[] => {
  const actionsMap: Record<ErrorCategory, RecoveryActionConfig[]> = {
    network: [
      { type: 'retry', label: 'error.actions.retry', primary: true },
      { type: 'refresh', label: 'error.actions.refresh' },
    ],
    auth: [
      { type: 'login', label: 'error.actions.login', primary: true },
    ],
    validation: [
      { type: 'dismiss', label: 'error.actions.dismiss', primary: true },
    ],
    server: [
      { type: 'retry', label: 'error.actions.retry', primary: true },
      { type: 'contact', label: 'error.actions.contact' },
    ],
    client: [
      { type: 'refresh', label: 'error.actions.refresh', primary: true },
      { type: 'goHome', label: 'error.actions.goHome' },
    ],
    timeout: [
      { type: 'retry', label: 'error.actions.retry', primary: true },
      { type: 'dismiss', label: 'error.actions.dismiss' },
    ],
    permission: [
      { type: 'goBack', label: 'error.actions.goBack', primary: true },
      { type: 'contact', label: 'error.actions.contact' },
    ],
    notFound: [
      { type: 'goBack', label: 'error.actions.goBack', primary: true },
      { type: 'goHome', label: 'error.actions.goHome' },
    ],
    conflict: [
      { type: 'refresh', label: 'error.actions.refresh', primary: true },
      { type: 'dismiss', label: 'error.actions.dismiss' },
    ],
    rateLimit: [
      { type: 'retry', label: 'error.actions.retryLater', primary: true },
    ],
    maintenance: [
      { type: 'refresh', label: 'error.actions.refresh', primary: true },
    ],
    unknown: [
      { type: 'retry', label: 'error.actions.retry', primary: true },
      { type: 'contact', label: 'error.actions.contact' },
    ],
  };
  return actionsMap[category];
};

// Check if error is retryable
export const isRetryableError = (category: ErrorCategory): boolean => {
  const retryableCategories: ErrorCategory[] = [
    'network',
    'server',
    'timeout',
    'rateLimit',
  ];
  return retryableCategories.includes(category);
};

// Parse field errors from API response
export const parseFieldErrors = (data: unknown): FieldError[] => {
  if (!data || typeof data !== 'object') return [];
  
  const errors: FieldError[] = [];
  const errorData = data as Record<string, unknown>;
  
  // Handle different API error formats
  if (Array.isArray(errorData.errors)) {
    for (const err of errorData.errors) {
      if (typeof err === 'object' && err !== null) {
        const fieldErr = err as Record<string, unknown>;
        errors.push({
          field: String(fieldErr.field || fieldErr.loc?.[1] || 'unknown'),
          message: String(fieldErr.message || fieldErr.msg || 'Invalid value'),
          code: fieldErr.code as string | undefined,
          value: fieldErr.value,
        });
      }
    }
  } else if (errorData.detail && Array.isArray(errorData.detail)) {
    // FastAPI validation error format
    for (const err of errorData.detail) {
      if (typeof err === 'object' && err !== null) {
        const fieldErr = err as Record<string, unknown>;
        const loc = fieldErr.loc as string[] | undefined;
        errors.push({
          field: loc ? loc[loc.length - 1] : 'unknown',
          message: String(fieldErr.msg || 'Invalid value'),
          code: fieldErr.type as string | undefined,
        });
      }
    }
  }
  
  return errors;
};

// Transform Axios error to AppError
export const transformAxiosError = (error: AxiosError): AppError => {
  const statusCode = error.response?.status;
  const category = getErrorCategory(statusCode);
  const severity = getErrorSeverity(category);
  const responseData = error.response?.data as Record<string, unknown> | undefined;
  
  // Extract message from response
  let message = 'error.messages.unknown';
  let technicalMessage = error.message;
  
  if (responseData) {
    if (typeof responseData.message === 'string') {
      technicalMessage = responseData.message;
    } else if (typeof responseData.detail === 'string') {
      technicalMessage = responseData.detail;
    } else if (typeof responseData.error === 'string') {
      technicalMessage = responseData.error;
    }
  }
  
  // Map to i18n message key based on category
  const messageKeyMap: Record<ErrorCategory, string> = {
    network: 'error.messages.network',
    auth: 'error.messages.auth',
    validation: 'error.messages.validation',
    server: 'error.messages.server',
    client: 'error.messages.client',
    timeout: 'error.messages.timeout',
    permission: 'error.messages.permission',
    notFound: 'error.messages.notFound',
    conflict: 'error.messages.conflict',
    rateLimit: 'error.messages.rateLimit',
    maintenance: 'error.messages.maintenance',
    unknown: 'error.messages.unknown',
  };
  message = messageKeyMap[category];
  
  // Handle network errors specifically
  if (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') {
    message = 'error.messages.network';
  }
  
  return {
    id: generateErrorId(),
    code: generateErrorCode(category, statusCode),
    message,
    technicalMessage,
    category,
    severity,
    statusCode,
    endpoint: error.config?.url,
    method: error.config?.method?.toUpperCase(),
    recoveryActions: getDefaultRecoveryActions(category),
    canRetry: isRetryableError(category),
    maxRetries: 3,
    retryCount: 0,
    timestamp: Date.now(),
    fieldErrors: parseFieldErrors(responseData),
    context: {
      url: error.config?.url,
      method: error.config?.method,
      responseData,
    },
  };
};

// Transform generic error to AppError
export const transformError = (error: unknown): AppError => {
  // Handle Axios errors
  if (error && typeof error === 'object' && 'isAxiosError' in error) {
    return transformAxiosError(error as AxiosError);
  }
  
  // Handle standard Error objects
  if (error instanceof Error) {
    return {
      id: generateErrorId(),
      code: generateErrorCode('client'),
      message: 'error.messages.client',
      technicalMessage: error.message,
      category: 'client',
      severity: 'error',
      recoveryActions: getDefaultRecoveryActions('client'),
      canRetry: false,
      timestamp: Date.now(),
      context: {
        name: error.name,
        stack: error.stack,
      },
    };
  }
  
  // Handle string errors
  if (typeof error === 'string') {
    return {
      id: generateErrorId(),
      code: generateErrorCode('unknown'),
      message: 'error.messages.unknown',
      technicalMessage: error,
      category: 'unknown',
      severity: 'error',
      recoveryActions: getDefaultRecoveryActions('unknown'),
      canRetry: false,
      timestamp: Date.now(),
    };
  }
  
  // Handle unknown errors
  return {
    id: generateErrorId(),
    code: generateErrorCode('unknown'),
    message: 'error.messages.unknown',
    technicalMessage: 'An unexpected error occurred',
    category: 'unknown',
    severity: 'error',
    recoveryActions: getDefaultRecoveryActions('unknown'),
    canRetry: false,
    timestamp: Date.now(),
    context: { originalError: error },
  };
};
