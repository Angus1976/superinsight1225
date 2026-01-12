/**
 * Error Types for User-Friendly Error Handling
 * 
 * Comprehensive error type definitions for consistent error handling
 * across the application with i18n support and actionable recovery options.
 */

// Error severity levels
export type ErrorSeverity = 'info' | 'warning' | 'error' | 'critical';

// Error categories for classification
export type ErrorCategory = 
  | 'network'      // Network connectivity issues
  | 'auth'         // Authentication/authorization errors
  | 'validation'   // Form/input validation errors
  | 'server'       // Server-side errors
  | 'client'       // Client-side errors
  | 'timeout'      // Request timeout errors
  | 'permission'   // Permission denied errors
  | 'notFound'     // Resource not found errors
  | 'conflict'     // Data conflict errors
  | 'rateLimit'    // Rate limiting errors
  | 'maintenance'  // System maintenance errors
  | 'unknown';     // Unknown errors

// HTTP status code to error category mapping
export const HTTP_STATUS_CATEGORY_MAP: Record<number, ErrorCategory> = {
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

// Recovery action types
export type RecoveryAction = 
  | 'retry'        // Retry the failed operation
  | 'refresh'      // Refresh the page
  | 'login'        // Redirect to login
  | 'goBack'       // Go back to previous page
  | 'goHome'       // Go to home page
  | 'contact'      // Contact support
  | 'dismiss'      // Dismiss the error
  | 'custom';      // Custom action

// Recovery action configuration
export interface RecoveryActionConfig {
  type: RecoveryAction;
  label: string;
  icon?: string;
  primary?: boolean;
  handler?: () => void | Promise<void>;
}

// Structured error interface
export interface AppError {
  // Core error information
  id: string;                    // Unique error ID for tracking
  code: string;                  // Error code (e.g., 'AUTH_001')
  message: string;               // User-friendly message
  technicalMessage?: string;     // Technical details (for debugging)
  
  // Classification
  category: ErrorCategory;
  severity: ErrorSeverity;
  
  // HTTP context (if applicable)
  statusCode?: number;
  endpoint?: string;
  method?: string;
  
  // Recovery options
  recoveryActions: RecoveryActionConfig[];
  canRetry: boolean;
  retryCount?: number;
  maxRetries?: number;
  
  // Additional context
  timestamp: number;
  context?: Record<string, unknown>;
  fieldErrors?: FieldError[];    // For validation errors
  
  // Tracking
  reported?: boolean;            // Whether error was reported to monitoring
  dismissed?: boolean;           // Whether user dismissed the error
}

// Field-level validation error
export interface FieldError {
  field: string;
  message: string;
  code?: string;
  value?: unknown;
}

// Error notification options
export interface ErrorNotificationOptions {
  duration?: number;             // Auto-dismiss duration (ms), 0 for persistent
  position?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight';
  showIcon?: boolean;
  closable?: boolean;
  showActions?: boolean;
  onClose?: () => void;
}

// Error boundary fallback props
export interface ErrorFallbackProps {
  error: AppError;
  resetError: () => void;
  retryOperation?: () => void;
}

// Error handler configuration
export interface ErrorHandlerConfig {
  // Global settings
  enableNotifications: boolean;
  enableLogging: boolean;
  enableReporting: boolean;
  
  // Retry settings
  defaultMaxRetries: number;
  retryDelay: number;
  retryBackoffMultiplier: number;
  
  // Notification settings
  defaultNotificationDuration: number;
  notificationPosition: ErrorNotificationOptions['position'];
  
  // Custom handlers
  onError?: (error: AppError) => void;
  onRecovery?: (error: AppError, action: RecoveryAction) => void;
}

// Default error handler configuration
export const DEFAULT_ERROR_CONFIG: ErrorHandlerConfig = {
  enableNotifications: true,
  enableLogging: true,
  enableReporting: true,
  defaultMaxRetries: 3,
  retryDelay: 1000,
  retryBackoffMultiplier: 2,
  defaultNotificationDuration: 5000,
  notificationPosition: 'topRight',
};

// Error code prefixes by category
export const ERROR_CODE_PREFIXES: Record<ErrorCategory, string> = {
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
