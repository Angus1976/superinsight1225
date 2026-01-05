/**
 * ErrorLogger - Advanced error logging system for iframe integration
 * Provides structured logging, log aggregation, and error analytics
 */

import type { ErrorInfo, ErrorType, ErrorSeverity } from './ErrorHandler';

export interface LoggerConfig {
  enableConsoleLogging?: boolean;
  enableLocalStorage?: boolean;
  enableRemoteLogging?: boolean;
  remoteEndpoint?: string;
  maxLocalStorageEntries?: number;
  logLevel?: LogLevel;
  enableStructuredLogging?: boolean;
  enableErrorAggregation?: boolean;
  aggregationWindow?: number;
  enablePerformanceLogging?: boolean;
}

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  CRITICAL = 4,
}

export interface LogEntry {
  id: string;
  timestamp: number;
  level: LogLevel;
  category: string;
  message: string;
  data?: Record<string, unknown>;
  error?: ErrorInfo;
  stackTrace?: string;
  userAgent?: string;
  url?: string;
  userId?: string;
  sessionId?: string;
  correlationId?: string;
}

export interface ErrorAggregation {
  errorType: ErrorType;
  count: number;
  firstOccurrence: number;
  lastOccurrence: number;
  affectedUsers: Set<string>;
  errorMessages: string[];
  severity: ErrorSeverity;
}

export interface PerformanceMetrics {
  timestamp: number;
  operation: string;
  duration: number;
  success: boolean;
  errorType?: ErrorType;
  metadata?: Record<string, unknown>;
}

export class ErrorLogger {
  private config: Required<LoggerConfig>;
  private logs: LogEntry[] = [];
  private errorAggregations: Map<string, ErrorAggregation> = new Map();
  private performanceMetrics: PerformanceMetrics[] = [];
  private logCounter: number = 0;
  private sessionId: string;
  private userId?: string;

  constructor(config: LoggerConfig = {}) {
    this.config = {
      enableConsoleLogging: config.enableConsoleLogging !== false,
      enableLocalStorage: config.enableLocalStorage !== false,
      enableRemoteLogging: config.enableRemoteLogging || false,
      remoteEndpoint: config.remoteEndpoint || '',
      maxLocalStorageEntries: config.maxLocalStorageEntries || 1000,
      logLevel: config.logLevel || LogLevel.INFO,
      enableStructuredLogging: config.enableStructuredLogging !== false,
      enableErrorAggregation: config.enableErrorAggregation !== false,
      aggregationWindow: config.aggregationWindow || 300000, // 5 minutes
      enablePerformanceLogging: config.enablePerformanceLogging || false,
    };

    this.sessionId = this.generateSessionId();
    this.initializeLogger();
  }

  /**
   * Set user ID for logging context
   */
  setUserId(userId: string): void {
    this.userId = userId;
  }

  /**
   * Log debug message
   */
  debug(category: string, message: string, data?: Record<string, unknown>): void {
    this.log(LogLevel.DEBUG, category, message, data);
  }

  /**
   * Log info message
   */
  info(category: string, message: string, data?: Record<string, unknown>): void {
    this.log(LogLevel.INFO, category, message, data);
  }

  /**
   * Log warning message
   */
  warn(category: string, message: string, data?: Record<string, unknown>): void {
    this.log(LogLevel.WARN, category, message, data);
  }

  /**
   * Log error message
   */
  error(category: string, message: string, error?: Error | ErrorInfo, data?: Record<string, unknown>): void {
    const logData = { ...data };
    
    if (error) {
      if (error instanceof Error) {
        logData.errorName = error.name;
        logData.errorMessage = error.message;
        logData.stackTrace = error.stack;
      } else {
        logData.errorInfo = error;
      }
    }

    this.log(LogLevel.ERROR, category, message, logData, error);
  }

  /**
   * Log critical error
   */
  critical(category: string, message: string, error?: Error | ErrorInfo, data?: Record<string, unknown>): void {
    const logData = { ...data };
    
    if (error) {
      if (error instanceof Error) {
        logData.errorName = error.name;
        logData.errorMessage = error.message;
        logData.stackTrace = error.stack;
      } else {
        logData.errorInfo = error;
      }
    }

    this.log(LogLevel.CRITICAL, category, message, logData, error);
  }

  /**
   * Log performance metrics
   */
  logPerformance(
    operation: string,
    duration: number,
    success: boolean,
    errorType?: ErrorType,
    metadata?: Record<string, unknown>
  ): void {
    if (!this.config.enablePerformanceLogging) return;

    const metric: PerformanceMetrics = {
      timestamp: Date.now(),
      operation,
      duration,
      success,
      errorType,
      metadata,
    };

    this.performanceMetrics.push(metric);

    // Keep only recent metrics
    const cutoff = Date.now() - (24 * 60 * 60 * 1000); // 24 hours
    this.performanceMetrics = this.performanceMetrics.filter(m => m.timestamp > cutoff);

    // Log performance issues
    if (!success || duration > 5000) {
      this.warn('performance', `Slow operation: ${operation}`, {
        duration,
        success,
        errorType,
        metadata,
      });
    }
  }

  /**
   * Get logs by level
   */
  getLogsByLevel(level: LogLevel, limit?: number): LogEntry[] {
    const filtered = this.logs.filter(log => log.level >= level);
    return limit ? filtered.slice(-limit) : filtered;
  }

  /**
   * Get logs by category
   */
  getLogsByCategory(category: string, limit?: number): LogEntry[] {
    const filtered = this.logs.filter(log => log.category === category);
    return limit ? filtered.slice(-limit) : filtered;
  }

  /**
   * Get logs by time range
   */
  getLogsByTimeRange(startTime: number, endTime: number): LogEntry[] {
    return this.logs.filter(log => 
      log.timestamp >= startTime && log.timestamp <= endTime
    );
  }

  /**
   * Get error aggregations
   */
  getErrorAggregations(): ErrorAggregation[] {
    return Array.from(this.errorAggregations.values());
  }

  /**
   * Get performance metrics
   */
  getPerformanceMetrics(): PerformanceMetrics[] {
    return [...this.performanceMetrics];
  }

  /**
   * Get performance summary
   */
  getPerformanceSummary(): {
    totalOperations: number;
    successfulOperations: number;
    failedOperations: number;
    averageDuration: number;
    slowestOperation: PerformanceMetrics | null;
    errorsByType: Record<string, number>;
  } {
    const total = this.performanceMetrics.length;
    const successful = this.performanceMetrics.filter(m => m.success).length;
    const failed = total - successful;
    
    const totalDuration = this.performanceMetrics.reduce((sum, m) => sum + m.duration, 0);
    const averageDuration = total > 0 ? totalDuration / total : 0;
    
    const slowest = this.performanceMetrics.reduce((slowest, current) => 
      !slowest || current.duration > slowest.duration ? current : slowest
    , null as PerformanceMetrics | null);

    const errorsByType: Record<string, number> = {};
    this.performanceMetrics.forEach(m => {
      if (m.errorType) {
        errorsByType[m.errorType] = (errorsByType[m.errorType] || 0) + 1;
      }
    });

    return {
      totalOperations: total,
      successfulOperations: successful,
      failedOperations: failed,
      averageDuration,
      slowestOperation: slowest,
      errorsByType,
    };
  }

  /**
   * Export logs as JSON
   */
  exportLogs(): string {
    return JSON.stringify({
      exportTime: new Date().toISOString(),
      sessionId: this.sessionId,
      userId: this.userId,
      config: this.config,
      logs: this.logs,
      errorAggregations: Array.from(this.errorAggregations.entries()),
      performanceMetrics: this.performanceMetrics,
    }, null, 2);
  }

  /**
   * Clear all logs
   */
  clearLogs(): void {
    this.logs = [];
    this.errorAggregations.clear();
    this.performanceMetrics = [];
    
    if (this.config.enableLocalStorage) {
      localStorage.removeItem('iframe_error_logs');
      localStorage.removeItem('iframe_performance_metrics');
    }
  }

  /**
   * Flush logs to remote endpoint
   */
  async flushLogs(): Promise<boolean> {
    if (!this.config.enableRemoteLogging || !this.config.remoteEndpoint) {
      return false;
    }

    try {
      const payload = {
        sessionId: this.sessionId,
        userId: this.userId,
        timestamp: Date.now(),
        logs: this.logs,
        errorAggregations: Array.from(this.errorAggregations.entries()),
        performanceMetrics: this.performanceMetrics,
      };

      const response = await fetch(this.config.remoteEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        this.info('logger', 'Logs flushed to remote endpoint successfully');
        return true;
      } else {
        this.error('logger', 'Failed to flush logs to remote endpoint', undefined, {
          status: response.status,
          statusText: response.statusText,
        });
        return false;
      }

    } catch (error) {
      this.error('logger', 'Error flushing logs to remote endpoint', error as Error);
      return false;
    }
  }

  /**
   * Core logging method
   */
  private log(
    level: LogLevel,
    category: string,
    message: string,
    data?: Record<string, unknown>,
    error?: Error | ErrorInfo
  ): void {
    if (level < this.config.logLevel) return;

    const logEntry: LogEntry = {
      id: this.generateLogId(),
      timestamp: Date.now(),
      level,
      category,
      message,
      data,
      userAgent: navigator.userAgent,
      url: window.location.href,
      userId: this.userId,
      sessionId: this.sessionId,
      correlationId: this.generateCorrelationId(),
    };

    // Add error information
    if (error) {
      if (error instanceof Error) {
        logEntry.stackTrace = error.stack;
      } else {
        logEntry.error = error;
        
        // Aggregate error if enabled
        if (this.config.enableErrorAggregation) {
          this.aggregateError(error);
        }
      }
    }

    this.logs.push(logEntry);

    // Console logging
    if (this.config.enableConsoleLogging) {
      this.logToConsole(logEntry);
    }

    // Local storage
    if (this.config.enableLocalStorage) {
      this.saveToLocalStorage();
    }

    // Cleanup old logs
    this.cleanupLogs();
  }

  /**
   * Log to console with appropriate formatting
   */
  private logToConsole(entry: LogEntry): void {
    const levelNames = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'];
    const levelName = levelNames[entry.level];
    const timestamp = new Date(entry.timestamp).toISOString();
    
    const prefix = `[${timestamp}] [${levelName}] [${entry.category}]`;
    const message = `${prefix} ${entry.message}`;

    switch (entry.level) {
      case LogLevel.DEBUG:
        console.debug(message, entry.data);
        break;
      case LogLevel.INFO:
        console.info(message, entry.data);
        break;
      case LogLevel.WARN:
        console.warn(message, entry.data);
        break;
      case LogLevel.ERROR:
      case LogLevel.CRITICAL:
        console.error(message, entry.data, entry.stackTrace);
        break;
    }
  }

  /**
   * Save logs to local storage
   */
  private saveToLocalStorage(): void {
    try {
      const recentLogs = this.logs.slice(-this.config.maxLocalStorageEntries);
      localStorage.setItem('iframe_error_logs', JSON.stringify(recentLogs));
      
      if (this.config.enablePerformanceLogging) {
        localStorage.setItem('iframe_performance_metrics', JSON.stringify(this.performanceMetrics));
      }
    } catch (error) {
      console.warn('Failed to save logs to localStorage:', error);
    }
  }

  /**
   * Load logs from local storage
   */
  private loadFromLocalStorage(): void {
    try {
      const savedLogs = localStorage.getItem('iframe_error_logs');
      if (savedLogs) {
        const parsedLogs = JSON.parse(savedLogs) as LogEntry[];
        this.logs = parsedLogs.filter(log => 
          Date.now() - log.timestamp < (7 * 24 * 60 * 60 * 1000) // 7 days
        );
      }

      if (this.config.enablePerformanceLogging) {
        const savedMetrics = localStorage.getItem('iframe_performance_metrics');
        if (savedMetrics) {
          const parsedMetrics = JSON.parse(savedMetrics) as PerformanceMetrics[];
          this.performanceMetrics = parsedMetrics.filter(metric =>
            Date.now() - metric.timestamp < (24 * 60 * 60 * 1000) // 24 hours
          );
        }
      }
    } catch (error) {
      console.warn('Failed to load logs from localStorage:', error);
    }
  }

  /**
   * Aggregate error for analysis
   */
  private aggregateError(error: ErrorInfo): void {
    const key = `${error.type}_${error.message}`;
    const existing = this.errorAggregations.get(key);

    if (existing) {
      existing.count++;
      existing.lastOccurrence = error.timestamp;
      if (error.context?.userId) {
        existing.affectedUsers.add(error.context.userId as string);
      }
      if (!existing.errorMessages.includes(error.message)) {
        existing.errorMessages.push(error.message);
      }
    } else {
      const aggregation: ErrorAggregation = {
        errorType: error.type,
        count: 1,
        firstOccurrence: error.timestamp,
        lastOccurrence: error.timestamp,
        affectedUsers: new Set(error.context?.userId ? [error.context.userId as string] : []),
        errorMessages: [error.message],
        severity: error.severity,
      };
      this.errorAggregations.set(key, aggregation);
    }

    // Clean up old aggregations
    const cutoff = Date.now() - this.config.aggregationWindow;
    for (const [key, aggregation] of this.errorAggregations.entries()) {
      if (aggregation.lastOccurrence < cutoff) {
        this.errorAggregations.delete(key);
      }
    }
  }

  /**
   * Clean up old logs
   */
  private cleanupLogs(): void {
    const maxEntries = this.config.maxLocalStorageEntries;
    if (this.logs.length > maxEntries) {
      this.logs = this.logs.slice(-maxEntries);
    }
  }

  /**
   * Initialize logger
   */
  private initializeLogger(): void {
    if (this.config.enableLocalStorage) {
      this.loadFromLocalStorage();
    }

    // Set up periodic log flushing
    if (this.config.enableRemoteLogging) {
      setInterval(() => {
        this.flushLogs();
      }, 60000); // Flush every minute
    }
  }

  /**
   * Generate unique log ID
   */
  private generateLogId(): string {
    return `log_${Date.now()}_${++this.logCounter}`;
  }

  /**
   * Generate session ID
   */
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Generate correlation ID for request tracing
   */
  private generateCorrelationId(): string {
    return `corr_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
  }
}