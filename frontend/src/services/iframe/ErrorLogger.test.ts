/**
 * ErrorLogger Unit Tests
 * Tests structured logging, log aggregation, and error analytics
 */

import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from 'vitest';
import { ErrorLogger, LogLevel, type LoggerConfig, type ErrorAggregation } from './ErrorLogger';
import { ErrorType, ErrorSeverity, type ErrorInfo } from './ErrorHandler';

// Mock fetch
global.fetch = vi.fn();

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
vi.stubGlobal('localStorage', mockLocalStorage);

// Mock console
const mockConsole = {
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
};
vi.stubGlobal('console', mockConsole);

// Mock navigator
vi.stubGlobal('navigator', {
  userAgent: 'Mozilla/5.0 (Test Browser)',
});

// Mock window.location
vi.stubGlobal('window', {
  location: {
    href: 'https://test.example.com/page',
  },
});

describe('ErrorLogger', () => {
  let errorLogger: ErrorLogger;

  beforeEach(() => {
    const config: LoggerConfig = {
      enableConsoleLogging: true,
      enableLocalStorage: true,
      enableRemoteLogging: false,
      maxLocalStorageEntries: 100,
      logLevel: LogLevel.DEBUG,
      enableStructuredLogging: true,
      enableErrorAggregation: true,
      aggregationWindow: 300000,
      enablePerformanceLogging: true,
    };

    errorLogger = new ErrorLogger(config);
    errorLogger.setUserId('test_user_123');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Logging', () => {
    it('should log debug messages', () => {
      errorLogger.debug('test_category', 'Debug message', { key: 'value' });

      expect(mockConsole.debug).toHaveBeenCalledWith(
        expect.stringContaining('[DEBUG] [test_category] Debug message'),
        { key: 'value' }
      );
    });

    it('should log info messages', () => {
      errorLogger.info('test_category', 'Info message', { key: 'value' });

      expect(mockConsole.info).toHaveBeenCalledWith(
        expect.stringContaining('[INFO] [test_category] Info message'),
        { key: 'value' }
      );
    });

    it('should log warning messages', () => {
      errorLogger.warn('test_category', 'Warning message', { key: 'value' });

      expect(mockConsole.warn).toHaveBeenCalledWith(
        expect.stringContaining('[WARN] [test_category] Warning message'),
        { key: 'value' }
      );
    });

    it('should log error messages with Error objects', () => {
      const error = new Error('Test error');
      errorLogger.error('test_category', 'Error message', error, { key: 'value' });

      expect(mockConsole.error).toHaveBeenCalledWith(
        expect.stringContaining('[ERROR] [test_category] Error message'),
        expect.objectContaining({
          key: 'value',
          errorName: 'Error',
          errorMessage: 'Test error',
          stackTrace: expect.any(String),
        }),
        expect.any(String)
      );
    });

    it('should log error messages with ErrorInfo objects', () => {
      const errorInfo: ErrorInfo = {
        id: 'error_123',
        type: ErrorType.LOADING_ERROR,
        severity: ErrorSeverity.HIGH,
        message: 'Loading failed',
        timestamp: Date.now(),
        source: 'iframe',
        retryCount: 1,
        maxRetries: 3,
        recoveryAction: 'retry',
        resolved: false,
      };

      errorLogger.error('test_category', 'Error message', errorInfo, { key: 'value' });

      expect(mockConsole.error).toHaveBeenCalledWith(
        expect.stringContaining('[ERROR] [test_category] Error message'),
        expect.objectContaining({
          key: 'value',
          errorInfo,
        }),
        undefined
      );
    });

    it('should log critical messages', () => {
      const error = new Error('Critical error');
      errorLogger.critical('test_category', 'Critical message', error);

      expect(mockConsole.error).toHaveBeenCalledWith(
        expect.stringContaining('[CRITICAL] [test_category] Critical message'),
        expect.any(Object),
        expect.any(String)
      );
    });
  });

  describe('Log Level Filtering', () => {
    it('should respect log level configuration', () => {
      const warnConfig: LoggerConfig = {
        logLevel: LogLevel.WARN,
      };

      const warnLogger = new ErrorLogger(warnConfig);

      warnLogger.debug('test', 'Debug message');
      warnLogger.info('test', 'Info message');
      warnLogger.warn('test', 'Warning message');
      warnLogger.error('test', 'Error message');

      expect(mockConsole.debug).not.toHaveBeenCalled();
      expect(mockConsole.info).not.toHaveBeenCalled();
      expect(mockConsole.warn).toHaveBeenCalled();
      expect(mockConsole.error).toHaveBeenCalled();
    });

    it('should disable console logging when configured', () => {
      const noConsoleConfig: LoggerConfig = {
        enableConsoleLogging: false,
      };

      const noConsoleLogger = new ErrorLogger(noConsoleConfig);
      noConsoleLogger.error('test', 'Error message');

      expect(mockConsole.error).not.toHaveBeenCalled();
    });
  });

  describe('Performance Logging', () => {
    it('should log performance metrics', () => {
      errorLogger.logPerformance('test_operation', 1500, true, undefined, { key: 'value' });

      const metrics = errorLogger.getPerformanceMetrics();
      expect(metrics).toHaveLength(1);
      expect(metrics[0].operation).toBe('test_operation');
      expect(metrics[0].duration).toBe(1500);
      expect(metrics[0].success).toBe(true);
      expect(metrics[0].metadata).toEqual({ key: 'value' });
    });

    it('should log warning for slow operations', () => {
      errorLogger.logPerformance('slow_operation', 6000, true);

      expect(mockConsole.warn).toHaveBeenCalledWith(
        expect.stringContaining('Slow operation: slow_operation'),
        expect.objectContaining({
          duration: 6000,
          success: true,
        })
      );
    });

    it('should log warning for failed operations', () => {
      errorLogger.logPerformance('failed_operation', 1000, false, ErrorType.NETWORK_ERROR);

      expect(mockConsole.warn).toHaveBeenCalledWith(
        expect.stringContaining('Slow operation: failed_operation'),
        expect.objectContaining({
          duration: 1000,
          success: false,
          errorType: ErrorType.NETWORK_ERROR,
        })
      );
    });

    it('should not log performance when disabled', () => {
      const noPerfConfig: LoggerConfig = {
        enablePerformanceLogging: false,
      };

      const noPerfLogger = new ErrorLogger(noPerfConfig);
      noPerfLogger.logPerformance('test_operation', 1000, true);

      const metrics = noPerfLogger.getPerformanceMetrics();
      expect(metrics).toHaveLength(0);
    });
  });

  describe('Log Retrieval', () => {
    beforeEach(() => {
      errorLogger.debug('category1', 'Debug message');
      errorLogger.info('category1', 'Info message');
      errorLogger.warn('category2', 'Warning message');
      errorLogger.error('category2', 'Error message');
      errorLogger.critical('category3', 'Critical message');
    });

    it('should get logs by level', () => {
      const errorLogs = errorLogger.getLogsByLevel(LogLevel.ERROR);
      expect(errorLogs).toHaveLength(2); // ERROR and CRITICAL

      const warnLogs = errorLogger.getLogsByLevel(LogLevel.WARN);
      expect(warnLogs).toHaveLength(3); // WARN, ERROR, and CRITICAL
    });

    it('should get logs by level with limit', () => {
      const limitedLogs = errorLogger.getLogsByLevel(LogLevel.INFO, 2);
      expect(limitedLogs).toHaveLength(2);
    });

    it('should get logs by category', () => {
      const category1Logs = errorLogger.getLogsByCategory('category1');
      expect(category1Logs).toHaveLength(2);

      const category2Logs = errorLogger.getLogsByCategory('category2');
      expect(category2Logs).toHaveLength(2);
    });

    it('should get logs by category with limit', () => {
      const limitedCategoryLogs = errorLogger.getLogsByCategory('category1', 1);
      expect(limitedCategoryLogs).toHaveLength(1);
    });

    it('should get logs by time range', () => {
      const now = Date.now();
      const oneHourAgo = now - (60 * 60 * 1000);
      
      const recentLogs = errorLogger.getLogsByTimeRange(oneHourAgo, now);
      expect(recentLogs).toHaveLength(5); // All logs should be recent
      
      const futureLogs = errorLogger.getLogsByTimeRange(now + 1000, now + 2000);
      expect(futureLogs).toHaveLength(0);
    });
  });

  describe('Error Aggregation', () => {
    it('should aggregate similar errors', () => {
      const errorInfo1: ErrorInfo = {
        id: 'error_1',
        type: ErrorType.LOADING_ERROR,
        severity: ErrorSeverity.MEDIUM,
        message: 'Failed to load',
        timestamp: Date.now(),
        source: 'iframe',
        retryCount: 0,
        maxRetries: 3,
        recoveryAction: 'retry',
        resolved: false,
        context: { userId: 'user1' },
      };

      const errorInfo2: ErrorInfo = {
        ...errorInfo1,
        id: 'error_2',
        timestamp: Date.now() + 1000,
        context: { userId: 'user2' },
      };

      errorLogger.error('test', 'Error 1', errorInfo1);
      errorLogger.error('test', 'Error 2', errorInfo2);

      const aggregations = errorLogger.getErrorAggregations();
      expect(aggregations).toHaveLength(1);
      
      const aggregation = aggregations[0];
      expect(aggregation.count).toBe(2);
      expect(aggregation.errorType).toBe(ErrorType.LOADING_ERROR);
      expect(aggregation.affectedUsers.size).toBe(2);
      expect(aggregation.affectedUsers.has('user1')).toBe(true);
      expect(aggregation.affectedUsers.has('user2')).toBe(true);
    });

    it('should not aggregate when disabled', () => {
      const noAggregationConfig: LoggerConfig = {
        enableErrorAggregation: false,
      };

      const noAggregationLogger = new ErrorLogger(noAggregationConfig);
      
      const errorInfo: ErrorInfo = {
        id: 'error_1',
        type: ErrorType.LOADING_ERROR,
        severity: ErrorSeverity.MEDIUM,
        message: 'Failed to load',
        timestamp: Date.now(),
        source: 'iframe',
        retryCount: 0,
        maxRetries: 3,
        recoveryAction: 'retry',
        resolved: false,
      };

      noAggregationLogger.error('test', 'Error', errorInfo);

      const aggregations = noAggregationLogger.getErrorAggregations();
      expect(aggregations).toHaveLength(0);
    });
  });

  describe('Performance Summary', () => {
    beforeEach(() => {
      errorLogger.logPerformance('operation1', 1000, true);
      errorLogger.logPerformance('operation2', 2000, true);
      errorLogger.logPerformance('operation3', 3000, false, ErrorType.TIMEOUT_ERROR);
      errorLogger.logPerformance('operation4', 4000, false, ErrorType.NETWORK_ERROR);
    });

    it('should calculate performance summary correctly', () => {
      const summary = errorLogger.getPerformanceSummary();

      expect(summary.totalOperations).toBe(4);
      expect(summary.successfulOperations).toBe(2);
      expect(summary.failedOperations).toBe(2);
      expect(summary.averageDuration).toBe(2500); // (1000 + 2000 + 3000 + 4000) / 4
      expect(summary.slowestOperation?.duration).toBe(4000);
      expect(summary.errorsByType[ErrorType.TIMEOUT_ERROR]).toBe(1);
      expect(summary.errorsByType[ErrorType.NETWORK_ERROR]).toBe(1);
    });

    it('should handle empty performance metrics', () => {
      const emptyLogger = new ErrorLogger();
      const summary = emptyLogger.getPerformanceSummary();

      expect(summary.totalOperations).toBe(0);
      expect(summary.successfulOperations).toBe(0);
      expect(summary.failedOperations).toBe(0);
      expect(summary.averageDuration).toBe(0);
      expect(summary.slowestOperation).toBeNull();
    });
  });

  describe('Local Storage', () => {
    it('should save logs to localStorage', () => {
      errorLogger.info('test', 'Test message');

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'iframe_error_logs',
        expect.any(String)
      );
    });

    it('should save performance metrics to localStorage', () => {
      errorLogger.logPerformance('test_op', 1000, true);

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'iframe_performance_metrics',
        expect.any(String)
      );
    });

    it('should load logs from localStorage on initialization', () => {
      const savedLogs = JSON.stringify([
        {
          id: 'log_1',
          timestamp: Date.now(),
          level: LogLevel.INFO,
          category: 'test',
          message: 'Saved message',
        },
      ]);

      mockLocalStorage.getItem.mockReturnValue(savedLogs);

      const newLogger = new ErrorLogger({ enableLocalStorage: true });
      const logs = newLogger.getLogsByLevel(LogLevel.DEBUG);

      expect(logs).toHaveLength(1);
      expect(logs[0].message).toBe('Saved message');
    });

    it('should not use localStorage when disabled', () => {
      const noStorageConfig: LoggerConfig = {
        enableLocalStorage: false,
      };

      const noStorageLogger = new ErrorLogger(noStorageConfig);
      noStorageLogger.info('test', 'Test message');

      expect(mockLocalStorage.setItem).not.toHaveBeenCalled();
    });
  });

  describe('Remote Logging', () => {
    it('should flush logs to remote endpoint', async () => {
      const remoteConfig: LoggerConfig = {
        enableRemoteLogging: true,
        remoteEndpoint: 'https://api.example.com/logs',
      };

      const remoteLogger = new ErrorLogger(remoteConfig);
      remoteLogger.info('test', 'Test message');

      (global.fetch as Mock).mockResolvedValue({
        ok: true,
        status: 200,
      });

      const result = await remoteLogger.flushLogs();

      expect(result).toBe(true);
      expect(global.fetch).toHaveBeenCalledWith(
        'https://api.example.com/logs',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: expect.any(String),
        })
      );
    });

    it('should handle remote logging failures', async () => {
      const remoteConfig: LoggerConfig = {
        enableRemoteLogging: true,
        remoteEndpoint: 'https://api.example.com/logs',
      };

      const remoteLogger = new ErrorLogger(remoteConfig);

      (global.fetch as Mock).mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      const result = await remoteLogger.flushLogs();

      expect(result).toBe(false);
    });

    it('should not flush when remote logging is disabled', async () => {
      const result = await errorLogger.flushLogs();

      expect(result).toBe(false);
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  describe('Log Export and Management', () => {
    it('should export logs as JSON', () => {
      errorLogger.info('test', 'Test message');
      errorLogger.logPerformance('test_op', 1000, true);

      const exported = errorLogger.exportLogs();
      const parsed = JSON.parse(exported);

      expect(parsed.exportTime).toBeDefined();
      expect(parsed.sessionId).toBeDefined();
      expect(parsed.userId).toBe('test_user_123');
      expect(parsed.logs).toHaveLength(1);
      expect(parsed.performanceMetrics).toHaveLength(1);
    });

    it('should clear all logs', () => {
      errorLogger.info('test', 'Test message');
      errorLogger.logPerformance('test_op', 1000, true);

      errorLogger.clearLogs();

      const logs = errorLogger.getLogsByLevel(LogLevel.DEBUG);
      const metrics = errorLogger.getPerformanceMetrics();
      const aggregations = errorLogger.getErrorAggregations();

      expect(logs).toHaveLength(0);
      expect(metrics).toHaveLength(0);
      expect(aggregations).toHaveLength(0);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('iframe_error_logs');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('iframe_performance_metrics');
    });
  });

  describe('User Context', () => {
    it('should include user ID in log entries', () => {
      errorLogger.setUserId('new_user_456');
      errorLogger.info('test', 'Test message');

      const logs = errorLogger.getLogsByLevel(LogLevel.DEBUG);
      expect(logs[0].userId).toBe('new_user_456');
    });

    it('should include session ID in log entries', () => {
      errorLogger.info('test', 'Test message');

      const logs = errorLogger.getLogsByLevel(LogLevel.DEBUG);
      expect(logs[0].sessionId).toMatch(/^session_\d+_[a-z0-9]+$/);
    });

    it('should include correlation ID in log entries', () => {
      errorLogger.info('test', 'Test message');

      const logs = errorLogger.getLogsByLevel(LogLevel.DEBUG);
      expect(logs[0].correlationId).toMatch(/^corr_\d+_[a-z0-9]+$/);
    });
  });
});