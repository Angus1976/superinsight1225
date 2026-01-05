/**
 * ErrorHandler - Comprehensive error handling and recovery for iframe integration
 * Handles loading errors, communication errors, permission errors, and automatic recovery
 */

import type {
  IframeStatus,
  BridgeStatus,
  Message,
  Response,
  AnnotationContext,
  Permission,
} from './types';
import { IframeStatus as IframeStatusEnum, BridgeStatus as BridgeStatusEnum } from './types';

export enum ErrorType {
  LOADING_ERROR = 'loading_error',
  COMMUNICATION_ERROR = 'communication_error',
  PERMISSION_ERROR = 'permission_error',
  TIMEOUT_ERROR = 'timeout_error',
  NETWORK_ERROR = 'network_error',
  SECURITY_ERROR = 'security_error',
  VALIDATION_ERROR = 'validation_error',
  SYSTEM_ERROR = 'system_error',
}

export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export enum RecoveryAction {
  RETRY = 'retry',
  RETRY_WITH_BACKOFF = 'retry_with_backoff',
  RELOAD_IFRAME = 'reload_iframe',
  RECONNECT_BRIDGE = 'reconnect_bridge',
  REFRESH_PERMISSIONS = 'refresh_permissions',
  FALLBACK_MODE = 'fallback_mode',
  MANUAL_INTERVENTION = 'manual_intervention',
  ABORT_OPERATION = 'abort_operation',
}

export interface ErrorInfo {
  id: string;
  type: ErrorType;
  severity: ErrorSeverity;
  message: string;
  details?: Record<string, unknown>;
  timestamp: number;
  source: 'iframe' | 'bridge' | 'permission' | 'system';
  context?: AnnotationContext;
  stackTrace?: string;
  retryCount: number;
  maxRetries: number;
  recoveryAction: RecoveryAction;
  resolved: boolean;
}

export interface ErrorHandlerConfig {
  maxRetries?: number;
  retryDelay?: number;
  backoffMultiplier?: number;
  maxBackoffDelay?: number;
  enableAutoRecovery?: boolean;
  enableLogging?: boolean;
  logLevel?: 'debug' | 'info' | 'warn' | 'error';
  onError?: (error: ErrorInfo) => void;
  onRecovery?: (error: ErrorInfo, success: boolean) => void;
}

export interface RecoveryStrategy {
  canHandle(error: ErrorInfo): boolean;
  execute(error: ErrorInfo): Promise<boolean>;
  getEstimatedTime(): number;
  getDescription(): string;
}

export class ErrorHandler {
  private config: Required<ErrorHandlerConfig>;
  private errorHistory: ErrorInfo[] = [];
  private activeErrors: Map<string, ErrorInfo> = new Map();
  private recoveryStrategies: Map<RecoveryAction, RecoveryStrategy> = new Map();
  private errorCounter: number = 0;
  private isRecovering: boolean = false;

  constructor(config: ErrorHandlerConfig = {}) {
    this.config = {
      maxRetries: config.maxRetries || 3,
      retryDelay: config.retryDelay || 1000,
      backoffMultiplier: config.backoffMultiplier || 2,
      maxBackoffDelay: config.maxBackoffDelay || 30000,
      enableAutoRecovery: config.enableAutoRecovery !== false,
      enableLogging: config.enableLogging !== false,
      logLevel: config.logLevel || 'error',
      onError: config.onError || (() => {}),
      onRecovery: config.onRecovery || (() => {}),
    };

    this.initializeRecoveryStrategies();
  }

  /**
   * Handle loading errors (iframe load failures, timeouts, network issues)
   */
  handleLoadingError(
    error: Error | string,
    context?: {
      url?: string;
      timeout?: number;
      retryCount?: number;
      iframeStatus?: IframeStatus;
    }
  ): ErrorInfo {
    const errorMessage = typeof error === 'string' ? error : error.message;
    const stackTrace = typeof error === 'object' ? error.stack : undefined;

    let errorType = ErrorType.LOADING_ERROR;
    let severity = ErrorSeverity.MEDIUM;
    let recoveryAction = RecoveryAction.RETRY;

    // Determine specific error type and recovery action
    if (errorMessage.includes('timeout')) {
      errorType = ErrorType.TIMEOUT_ERROR;
      recoveryAction = RecoveryAction.RETRY_WITH_BACKOFF;
    } else if (errorMessage.includes('network') || errorMessage.includes('fetch')) {
      errorType = ErrorType.NETWORK_ERROR;
      severity = ErrorSeverity.HIGH;
      recoveryAction = RecoveryAction.RETRY_WITH_BACKOFF;
    } else if (errorMessage.includes('security') || errorMessage.includes('cors')) {
      errorType = ErrorType.SECURITY_ERROR;
      severity = ErrorSeverity.HIGH;
      recoveryAction = RecoveryAction.MANUAL_INTERVENTION;
    }

    const errorInfo: ErrorInfo = {
      id: this.generateErrorId(),
      type: errorType,
      severity,
      message: errorMessage,
      details: context,
      timestamp: Date.now(),
      source: 'iframe',
      stackTrace,
      retryCount: context?.retryCount || 0,
      maxRetries: this.config.maxRetries,
      recoveryAction,
      resolved: false,
    };

    return this.processError(errorInfo);
  }

  /**
   * Handle communication errors (PostMessage failures, bridge issues)
   */
  handleCommunicationError(
    error: Error | string,
    context?: {
      message?: Message;
      response?: Response;
      bridgeStatus?: BridgeStatus;
      retryCount?: number;
    }
  ): ErrorInfo {
    const errorMessage = typeof error === 'string' ? error : error.message;
    const stackTrace = typeof error === 'object' ? error.stack : undefined;

    let errorType = ErrorType.COMMUNICATION_ERROR;
    let severity = ErrorSeverity.MEDIUM;
    let recoveryAction = RecoveryAction.RECONNECT_BRIDGE;

    // Determine specific error type and recovery action
    if (errorMessage.includes('timeout')) {
      errorType = ErrorType.TIMEOUT_ERROR;
      recoveryAction = RecoveryAction.RETRY_WITH_BACKOFF;
    } else if (errorMessage.includes('signature') || errorMessage.includes('validation')) {
      errorType = ErrorType.SECURITY_ERROR;
      severity = ErrorSeverity.HIGH;
      recoveryAction = RecoveryAction.MANUAL_INTERVENTION;
    } else if (context?.bridgeStatus === BridgeStatusEnum.DISCONNECTED) {
      severity = ErrorSeverity.HIGH;
      recoveryAction = RecoveryAction.RECONNECT_BRIDGE;
    }

    const errorInfo: ErrorInfo = {
      id: this.generateErrorId(),
      type: errorType,
      severity,
      message: errorMessage,
      details: context,
      timestamp: Date.now(),
      source: 'bridge',
      stackTrace,
      retryCount: context?.retryCount || 0,
      maxRetries: this.config.maxRetries,
      recoveryAction,
      resolved: false,
    };

    return this.processError(errorInfo);
  }

  /**
   * Handle permission errors (access denied, insufficient permissions)
   */
  handlePermissionError(
    error: Error | string,
    context?: {
      action?: string;
      resource?: string;
      requiredPermissions?: Permission[];
      currentPermissions?: Permission[];
      userId?: string;
    }
  ): ErrorInfo {
    const errorMessage = typeof error === 'string' ? error : error.message;
    const stackTrace = typeof error === 'object' ? error.stack : undefined;

    let severity = ErrorSeverity.MEDIUM;
    let recoveryAction = RecoveryAction.REFRESH_PERMISSIONS;

    // Determine severity based on context
    if (context?.action === 'admin' || context?.resource === 'system') {
      severity = ErrorSeverity.HIGH;
    }

    const errorInfo: ErrorInfo = {
      id: this.generateErrorId(),
      type: ErrorType.PERMISSION_ERROR,
      severity,
      message: errorMessage,
      details: context,
      timestamp: Date.now(),
      source: 'permission',
      stackTrace,
      retryCount: 0,
      maxRetries: 1, // Permission errors usually don't benefit from retries
      recoveryAction,
      resolved: false,
    };

    return this.processError(errorInfo);
  }

  /**
   * Handle system errors (unexpected errors, crashes)
   */
  handleSystemError(
    error: Error | string,
    context?: {
      component?: string;
      operation?: string;
      state?: Record<string, unknown>;
    }
  ): ErrorInfo {
    const errorMessage = typeof error === 'string' ? error : error.message;
    const stackTrace = typeof error === 'object' ? error.stack : undefined;

    const errorInfo: ErrorInfo = {
      id: this.generateErrorId(),
      type: ErrorType.SYSTEM_ERROR,
      severity: ErrorSeverity.CRITICAL,
      message: errorMessage,
      details: context,
      timestamp: Date.now(),
      source: 'system',
      stackTrace,
      retryCount: 0,
      maxRetries: this.config.maxRetries,
      recoveryAction: RecoveryAction.RELOAD_IFRAME,
      resolved: false,
    };

    return this.processError(errorInfo);
  }

  /**
   * Attempt automatic recovery for an error
   */
  async attemptRecovery(errorId: string): Promise<boolean> {
    const error = this.activeErrors.get(errorId);
    if (!error || this.isRecovering) {
      return false;
    }

    if (error.retryCount >= error.maxRetries) {
      this.log('warn', `Max retries exceeded for error ${errorId}`);
      return false;
    }

    this.isRecovering = true;
    error.retryCount++;

    try {
      const strategy = this.recoveryStrategies.get(error.recoveryAction);
      if (!strategy) {
        this.log('error', `No recovery strategy found for action: ${error.recoveryAction}`);
        return false;
      }

      if (!strategy.canHandle(error)) {
        this.log('warn', `Recovery strategy cannot handle error: ${errorId}`);
        return false;
      }

      this.log('info', `Attempting recovery for error ${errorId} using ${error.recoveryAction}`);

      const success = await strategy.execute(error);
      
      if (success) {
        error.resolved = true;
        this.activeErrors.delete(errorId);
        this.log('info', `Successfully recovered from error ${errorId}`);
      } else {
        this.log('warn', `Recovery failed for error ${errorId}`);
      }

      this.config.onRecovery(error, success);
      return success;

    } catch (recoveryError) {
      this.log('error', `Recovery attempt failed for error ${errorId}:`, recoveryError);
      return false;
    } finally {
      this.isRecovering = false;
    }
  }

  /**
   * Get error by ID
   */
  getError(errorId: string): ErrorInfo | undefined {
    return this.activeErrors.get(errorId) || 
           this.errorHistory.find(e => e.id === errorId);
  }

  /**
   * Get all active errors
   */
  getActiveErrors(): ErrorInfo[] {
    return Array.from(this.activeErrors.values());
  }

  /**
   * Get error history
   */
  getErrorHistory(limit?: number): ErrorInfo[] {
    return limit ? this.errorHistory.slice(-limit) : [...this.errorHistory];
  }

  /**
   * Clear resolved errors from history
   */
  clearResolvedErrors(): void {
    this.errorHistory = this.errorHistory.filter(error => !error.resolved);
  }

  /**
   * Get error statistics
   */
  getErrorStats(): {
    totalErrors: number;
    activeErrors: number;
    resolvedErrors: number;
    errorsByType: Record<ErrorType, number>;
    errorsBySeverity: Record<ErrorSeverity, number>;
  } {
    const errorsByType = {} as Record<ErrorType, number>;
    const errorsBySeverity = {} as Record<ErrorSeverity, number>;

    // Initialize counters
    Object.values(ErrorType).forEach(type => {
      errorsByType[type] = 0;
    });
    Object.values(ErrorSeverity).forEach(severity => {
      errorsBySeverity[severity] = 0;
    });

    // Count errors
    this.errorHistory.forEach(error => {
      errorsByType[error.type]++;
      errorsBySeverity[error.severity]++;
    });

    return {
      totalErrors: this.errorHistory.length,
      activeErrors: this.activeErrors.size,
      resolvedErrors: this.errorHistory.filter(e => e.resolved).length,
      errorsByType,
      errorsBySeverity,
    };
  }

  /**
   * Process error and trigger recovery if enabled
   */
  private processError(error: ErrorInfo): ErrorInfo {
    // Add to active errors and history
    this.activeErrors.set(error.id, error);
    this.errorHistory.push(error);

    // Log error
    this.log('error', `Error ${error.id}: ${error.message}`, error);

    // Trigger error callback
    this.config.onError(error);

    // Attempt automatic recovery if enabled
    if (this.config.enableAutoRecovery && error.retryCount < error.maxRetries) {
      // Use setTimeout to avoid blocking
      setTimeout(() => {
        this.attemptRecovery(error.id);
      }, this.calculateRetryDelay(error.retryCount));
    }

    return error;
  }

  /**
   * Calculate retry delay with exponential backoff
   */
  private calculateRetryDelay(retryCount: number): number {
    const delay = this.config.retryDelay * Math.pow(this.config.backoffMultiplier, retryCount);
    return Math.min(delay, this.config.maxBackoffDelay);
  }

  /**
   * Generate unique error ID
   */
  private generateErrorId(): string {
    return `error_${Date.now()}_${++this.errorCounter}`;
  }

  /**
   * Log message based on configured log level
   */
  private log(level: 'debug' | 'info' | 'warn' | 'error', message: string, ...args: unknown[]): void {
    if (!this.config.enableLogging) return;

    const levels = ['debug', 'info', 'warn', 'error'];
    const configLevel = levels.indexOf(this.config.logLevel);
    const messageLevel = levels.indexOf(level);

    if (messageLevel >= configLevel) {
      console[level](`[ErrorHandler] ${message}`, ...args);
    }
  }

  /**
   * Initialize recovery strategies
   */
  private initializeRecoveryStrategies(): void {
    // Retry strategy
    this.recoveryStrategies.set(RecoveryAction.RETRY, {
      canHandle: (error) => error.retryCount < error.maxRetries,
      execute: async () => {
        // Simple retry - implementation depends on context
        return true;
      },
      getEstimatedTime: () => 1000,
      getDescription: () => 'Retry operation immediately',
    });

    // Retry with backoff strategy
    this.recoveryStrategies.set(RecoveryAction.RETRY_WITH_BACKOFF, {
      canHandle: (error) => error.retryCount < error.maxRetries,
      execute: async (error) => {
        const delay = this.calculateRetryDelay(error.retryCount);
        await new Promise(resolve => setTimeout(resolve, delay));
        return true;
      },
      getEstimatedTime: () => this.config.retryDelay,
      getDescription: () => 'Retry operation with exponential backoff',
    });

    // Reload iframe strategy
    this.recoveryStrategies.set(RecoveryAction.RELOAD_IFRAME, {
      canHandle: () => true,
      execute: async () => {
        // Implementation would trigger iframe reload
        return true;
      },
      getEstimatedTime: () => 5000,
      getDescription: () => 'Reload iframe container',
    });

    // Reconnect bridge strategy
    this.recoveryStrategies.set(RecoveryAction.RECONNECT_BRIDGE, {
      canHandle: () => true,
      execute: async () => {
        // Implementation would reconnect PostMessage bridge
        return true;
      },
      getEstimatedTime: () => 2000,
      getDescription: () => 'Reconnect communication bridge',
    });

    // Refresh permissions strategy
    this.recoveryStrategies.set(RecoveryAction.REFRESH_PERMISSIONS, {
      canHandle: () => true,
      execute: async () => {
        // Implementation would refresh user permissions
        return true;
      },
      getEstimatedTime: () => 3000,
      getDescription: () => 'Refresh user permissions',
    });
  }
}