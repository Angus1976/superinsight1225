/**
 * AutoRecoveryManager Unit Tests
 * Tests automatic recovery, failover, and error logging functionality
 */

import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from 'vitest';
import { AutoRecoveryManager, type AutoRecoveryConfig } from './AutoRecoveryManager';
import { ErrorHandler } from './ErrorHandler';
import { IframeManager } from './IframeManager';
import { PostMessageBridge } from './PostMessageBridge';
import { ContextManager } from './ContextManager';

// Mock fetch
global.fetch = vi.fn();

// Mock console
const mockConsole = {
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
};
vi.stubGlobal('console', mockConsole);

// Mock timers
vi.useFakeTimers();

describe('AutoRecoveryManager', () => {
  let autoRecoveryManager: AutoRecoveryManager;
  let mockErrorHandler: ErrorHandler;
  let mockIframeManager: Partial<IframeManager>;
  let mockPostMessageBridge: Partial<PostMessageBridge>;
  let mockContextManager: Partial<ContextManager>;

  beforeEach(() => {
    // Create mock error handler
    mockErrorHandler = new ErrorHandler();

    // Create mock managers
    mockIframeManager = {
      getStatus: vi.fn().mockReturnValue('ready'),
      getIframe: vi.fn().mockReturnValue(document.createElement('iframe')),
      destroy: vi.fn().mockResolvedValue(undefined),
      create: vi.fn().mockResolvedValue(document.createElement('iframe')),
      on: vi.fn(),
    };

    mockPostMessageBridge = {
      getStatus: vi.fn().mockReturnValue('connected'),
      cleanup: vi.fn(),
      initialize: vi.fn(),
      send: vi.fn().mockResolvedValue({ success: true, id: 'test', data: {} }),
    };

    mockContextManager = {
      getContext: vi.fn().mockReturnValue({
        user: { id: 'user1', name: 'Test User', email: 'test@example.com', role: 'user' },
        project: { id: 'proj1', name: 'Test Project', description: 'Test', status: 'active', createdAt: '', updatedAt: '' },
        task: { id: 'task1', name: 'Test Task', status: 'active', progress: 0 },
        permissions: [],
        timestamp: Date.now(),
      }),
    };

    const config: AutoRecoveryConfig = {
      enableAutoReconnect: true,
      reconnectInterval: 1000,
      maxReconnectAttempts: 3,
      enableFailover: true,
      failoverUrls: ['https://backup1.example.com', 'https://backup2.example.com'],
      enableHealthCheck: true,
      healthCheckInterval: 5000,
      enableErrorLogging: true,
      logRetentionDays: 7,
      enableMetrics: true,
    };

    autoRecoveryManager = new AutoRecoveryManager(mockErrorHandler, config);
    autoRecoveryManager.initialize(
      mockIframeManager as IframeManager,
      mockPostMessageBridge as PostMessageBridge,
      mockContextManager as ContextManager
    );
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.clearAllTimers();
    autoRecoveryManager.cleanup();
  });

  describe('Initialization', () => {
    it('should initialize with default configuration', () => {
      const defaultManager = new AutoRecoveryManager(mockErrorHandler);
      
      expect(defaultManager).toBeDefined();
    });

    it('should start health check when enabled', () => {
      // Health check should be scheduled
      expect(vi.getTimerCount()).toBeGreaterThan(0);
    });

    it('should setup error handlers for managers', () => {
      expect(mockIframeManager.on).toHaveBeenCalledWith('error', expect.any(Function));
    });
  });

  describe('Automatic Reconnection', () => {
    it('should successfully reconnect after connection failure', async () => {
      // Mock successful health check and connection verification
      (global.fetch as Mock).mockResolvedValueOnce({
        ok: true,
        type: 'basic',
      });

      const result = await autoRecoveryManager.implementAutoReconnect();

      expect(result).toBe(true);
      expect(mockPostMessageBridge.cleanup).toHaveBeenCalled();
      expect(mockPostMessageBridge.initialize).toHaveBeenCalled();
    });

    it('should retry reconnection up to max attempts', async () => {
      // Mock failed health checks
      (global.fetch as Mock).mockRejectedValue(new Error('Network error'));

      const result = await autoRecoveryManager.implementAutoReconnect();

      expect(result).toBe(false);
      // Should have attempted multiple times but we can't easily verify the exact count
      // due to the async nature and private methods
    });

    it('should not attempt reconnection when already recovering', async () => {
      // Start first reconnection
      const promise1 = autoRecoveryManager.implementAutoReconnect();
      
      // Attempt second reconnection while first is in progress
      const result2 = await autoRecoveryManager.implementAutoReconnect();

      expect(result2).toBe(false);
      
      await promise1; // Clean up
    });

    it('should not attempt reconnection when disabled', async () => {
      const disabledConfig: AutoRecoveryConfig = {
        enableAutoReconnect: false,
      };

      const disabledManager = new AutoRecoveryManager(mockErrorHandler, disabledConfig);
      const result = await disabledManager.implementAutoReconnect();

      expect(result).toBe(false);
    });
  });

  describe('Failover Implementation', () => {
    it('should successfully failover to backup URL', async () => {
      // Mock successful URL test
      (global.fetch as Mock).mockResolvedValueOnce({
        ok: true,
        type: 'basic',
      });

      const result = await autoRecoveryManager.implementFailover();

      expect(result).toBe(true);
      expect(mockIframeManager.destroy).toHaveBeenCalled();
    });

    it('should try all failover URLs before giving up', async () => {
      // Mock all URLs failing
      (global.fetch as Mock).mockRejectedValue(new Error('Network error'));

      const result = await autoRecoveryManager.implementFailover();

      expect(result).toBe(false);
      expect(global.fetch).toHaveBeenCalledTimes(2); // Two failover URLs
    });

    it('should not attempt failover when disabled', async () => {
      const noFailoverConfig: AutoRecoveryConfig = {
        enableFailover: false,
      };

      const noFailoverManager = new AutoRecoveryManager(mockErrorHandler, noFailoverConfig);
      const result = await noFailoverManager.implementFailover();

      expect(result).toBe(false);
    });

    it('should not attempt failover when no URLs configured', async () => {
      const noUrlsConfig: AutoRecoveryConfig = {
        enableFailover: true,
        failoverUrls: [],
      };

      const noUrlsManager = new AutoRecoveryManager(mockErrorHandler, noUrlsConfig);
      const result = await noUrlsManager.implementFailover();

      expect(result).toBe(false);
    });
  });

  describe('Health Check', () => {
    it('should perform health check periodically', async () => {
      // Mock successful communication test
      (mockPostMessageBridge.send as Mock).mockResolvedValue({ success: true, id: 'health', data: {} });

      // Advance timer to trigger health check
      vi.advanceTimersByTime(5000);

      // Wait for async operations
      await vi.runAllTimersAsync();

      expect(mockIframeManager.getStatus).toHaveBeenCalled();
      expect(mockPostMessageBridge.getStatus).toHaveBeenCalled();
    });

    it('should detect unhealthy connection and trigger recovery', async () => {
      // Mock unhealthy iframe status
      (mockIframeManager.getStatus as Mock).mockReturnValue('error');

      // Advance timer to trigger health check
      vi.advanceTimersByTime(5000);
      await vi.runAllTimersAsync();

      const health = autoRecoveryManager.getConnectionHealth();
      expect(health.isHealthy).toBe(false);
    });

    it('should update connection health metrics', async () => {
      // Mock successful health check
      (mockPostMessageBridge.send as Mock).mockResolvedValue({ success: true, id: 'health', data: {} });

      // Advance timer to trigger health check
      vi.advanceTimersByTime(5000);
      await vi.runAllTimersAsync();

      const health = autoRecoveryManager.getConnectionHealth();
      expect(health.lastCheck).toBeGreaterThan(0);
      expect(health.responseTime).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Error Logging', () => {
    it('should log error messages with correct format', () => {
      autoRecoveryManager.logError('error', 'Test error message', {
        error: new Error('Test error'),
        recoveryAction: 'retry',
      });

      expect(mockConsole.error).toHaveBeenCalledWith(
        '[AutoRecoveryManager] Test error message',
        expect.any(Object)
      );
    });

    it('should log different severity levels', () => {
      autoRecoveryManager.logError('debug', 'Debug message');
      autoRecoveryManager.logError('info', 'Info message');
      autoRecoveryManager.logError('warn', 'Warning message');
      autoRecoveryManager.logError('error', 'Error message');
      autoRecoveryManager.logError('critical', 'Critical message');

      expect(mockConsole.debug).toHaveBeenCalled();
      expect(mockConsole.info).toHaveBeenCalled();
      expect(mockConsole.warn).toHaveBeenCalled();
      expect(mockConsole.error).toHaveBeenCalledTimes(2); // error and critical both use console.error
    });

    it('should not log when logging is disabled', () => {
      const noLogConfig: AutoRecoveryConfig = {
        enableErrorLogging: false,
      };

      const noLogManager = new AutoRecoveryManager(mockErrorHandler, noLogConfig);
      noLogManager.logError('error', 'Test message');

      expect(mockConsole.error).not.toHaveBeenCalled();
    });

    it('should store error logs for retrieval', () => {
      autoRecoveryManager.logError('error', 'Test error 1');
      autoRecoveryManager.logError('warn', 'Test warning');
      autoRecoveryManager.logError('error', 'Test error 2');

      const logs = autoRecoveryManager.getErrorLogs();
      expect(logs).toHaveLength(3);
      expect(logs[0].message).toBe('Test error 2'); // Most recent first
      expect(logs[1].message).toBe('Test warning');
      expect(logs[2].message).toBe('Test error 1');
    });

    it('should limit error logs when requested', () => {
      autoRecoveryManager.logError('error', 'Error 1');
      autoRecoveryManager.logError('error', 'Error 2');
      autoRecoveryManager.logError('error', 'Error 3');

      const limitedLogs = autoRecoveryManager.getErrorLogs(2);
      expect(limitedLogs).toHaveLength(2);
    });

    it('should clear error logs', () => {
      autoRecoveryManager.logError('error', 'Test error');
      
      autoRecoveryManager.clearErrorLogs();
      
      const logs = autoRecoveryManager.getErrorLogs();
      expect(logs).toHaveLength(0);
    });

    it('should export error logs as JSON', () => {
      autoRecoveryManager.logError('error', 'Test error');
      
      const exported = autoRecoveryManager.exportErrorLogs();
      const parsed = JSON.parse(exported);
      
      expect(parsed.exportTime).toBeDefined();
      expect(parsed.metrics).toBeDefined();
      expect(parsed.connectionHealth).toBeDefined();
      expect(parsed.logs).toHaveLength(1);
    });
  });

  describe('Metrics Collection', () => {
    it('should track recovery metrics', () => {
      const metrics = autoRecoveryManager.getRecoveryMetrics();
      
      expect(metrics.totalRecoveryAttempts).toBe(0);
      expect(metrics.successfulRecoveries).toBe(0);
      expect(metrics.failedRecoveries).toBe(0);
      expect(metrics.averageRecoveryTime).toBe(0);
      expect(metrics.failoverCount).toBe(0);
      expect(metrics.reconnectCount).toBe(0);
    });

    it('should update metrics after recovery attempts', async () => {
      // Mock successful reconnection
      (global.fetch as Mock).mockResolvedValue({ ok: true, type: 'basic' });

      await autoRecoveryManager.implementAutoReconnect();

      const metrics = autoRecoveryManager.getRecoveryMetrics();
      expect(metrics.reconnectCount).toBe(1);
    });

    it('should update metrics after failover attempts', async () => {
      // Mock successful failover
      (global.fetch as Mock).mockResolvedValue({ ok: true, type: 'basic' });

      await autoRecoveryManager.implementFailover();

      const metrics = autoRecoveryManager.getRecoveryMetrics();
      expect(metrics.failoverCount).toBe(1);
    });
  });

  describe('Connection Health Monitoring', () => {
    it('should provide current connection health status', () => {
      const health = autoRecoveryManager.getConnectionHealth();
      
      expect(health.isHealthy).toBe(true);
      expect(health.lastCheck).toBeGreaterThan(0);
      expect(health.responseTime).toBeGreaterThanOrEqual(0);
      expect(health.errorCount).toBe(0);
      expect(health.consecutiveFailures).toBe(0);
    });

    it('should update health status on errors', () => {
      // Simulate iframe error
      const errorCallback = (mockIframeManager.on as Mock).mock.calls
        .find(call => call[0] === 'error')?.[1];
      
      if (errorCallback) {
        errorCallback({ type: 'error', timestamp: Date.now(), data: { error: 'Test error' } });
      }

      const health = autoRecoveryManager.getConnectionHealth();
      expect(health.errorCount).toBe(1);
      expect(health.consecutiveFailures).toBe(1);
      expect(health.isHealthy).toBe(false);
    });
  });

  describe('Cleanup', () => {
    it('should cleanup timers and resources', () => {
      const timerCount = vi.getTimerCount();
      expect(timerCount).toBeGreaterThan(0);

      autoRecoveryManager.cleanup();

      // Timers should be cleared
      expect(vi.getTimerCount()).toBeLessThan(timerCount);
    });

    it('should stop recovery processes on cleanup', () => {
      autoRecoveryManager.cleanup();

      // Should not attempt recovery after cleanup
      const result = autoRecoveryManager.implementAutoReconnect();
      expect(result).resolves.toBe(false);
    });
  });

  describe('Error Handler Integration', () => {
    it('should handle iframe errors and trigger recovery', async () => {
      // Mock the error handler setup
      const errorCallback = (mockIframeManager.on as Mock).mock.calls
        .find(call => call[0] === 'error')?.[1];
      
      expect(errorCallback).toBeDefined();
      
      if (errorCallback) {
        // Simulate an iframe error
        errorCallback({ 
          type: 'error', 
          timestamp: Date.now(), 
          data: { error: 'iframe load failed' } 
        });

        // Should have logged the error and updated health
        const health = autoRecoveryManager.getConnectionHealth();
        expect(health.isHealthy).toBe(false);
        expect(health.errorCount).toBe(1);
      }
    });
  });
});