/**
 * Tests for SecurityAuditLogger
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  SecurityAuditLogger,
  createDefaultAuditConfig,
  getGlobalSecurityAuditLogger,
  initializeGlobalSecurityAuditLogger,
  type AuditLogConfig,
  type SecurityAuditEvent,
  type AuditQuery,
} from './SecurityAuditLogger';

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};

Object.defineProperty(global, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
});

// Mock fetch
global.fetch = vi.fn();

// Mock navigator
Object.defineProperty(global, 'navigator', {
  value: {
    userAgent: 'test-user-agent',
  },
  writable: true,
});

// Mock console
Object.defineProperty(global, 'console', {
  value: {
    log: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
  writable: true,
});

describe('SecurityAuditLogger', () => {
  let logger: SecurityAuditLogger;
  let config: AuditLogConfig;
  let eventHandlers: SecurityAuditEvent[];

  beforeEach(() => {
    config = createDefaultAuditConfig();
    logger = new SecurityAuditLogger(config);
    eventHandlers = [];

    // Setup event handler
    logger.onEvent((event) => {
      eventHandlers.push(event);
    });

    // Reset mocks
    vi.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue(null);
  });

  afterEach(() => {
    logger.cleanup();
  });

  describe('initialization', () => {
    it('should initialize successfully', async () => {
      await logger.initialize();
      
      expect(logger.isReady()).toBe(true);
    });

    it('should load existing logs from localStorage', async () => {
      const existingLogs = [
        {
          id: 'test-1',
          type: 'authentication',
          action: 'login',
          timestamp: Date.now(),
          success: true,
          riskLevel: 'low',
        },
      ];
      
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify(existingLogs));
      
      await logger.initialize();
      
      const events = logger.queryEvents();
      expect(events).toHaveLength(2); // Existing log + initialization event
      expect(events.some(e => e.id === 'test-1')).toBe(true);
    });

    it('should handle corrupted localStorage data', async () => {
      mockLocalStorage.getItem.mockReturnValue('invalid-json');
      
      await logger.initialize();
      
      expect(logger.isReady()).toBe(true);
      expect(console.warn).toHaveBeenCalledWith(
        'Failed to load audit log from local storage:',
        expect.any(Error)
      );
    });

    it('should clean up old logs during initialization', async () => {
      const oldTimestamp = Date.now() - (100 * 24 * 60 * 60 * 1000); // 100 days ago
      const recentTimestamp = Date.now() - (1 * 24 * 60 * 60 * 1000); // 1 day ago
      
      const existingLogs = [
        {
          id: 'old-log',
          type: 'authentication',
          action: 'login',
          timestamp: oldTimestamp,
          success: true,
          riskLevel: 'low',
        },
        {
          id: 'recent-log',
          type: 'authentication',
          action: 'login',
          timestamp: recentTimestamp,
          success: true,
          riskLevel: 'low',
        },
      ];
      
      mockLocalStorage.getItem.mockReturnValue(JSON.stringify(existingLogs));
      
      await logger.initialize();
      
      const events = logger.queryEvents();
      expect(events).toHaveLength(2); // Recent log + initialization event
      expect(events.some(e => e.id === 'recent-log')).toBe(true);
      expect(events.some(e => e.id === 'old-log')).toBe(false);
    });

    it('should not initialize twice', async () => {
      await logger.initialize();
      await logger.initialize();
      
      expect(logger.isReady()).toBe(true);
    });
  });

  describe('event logging', () => {
    beforeEach(async () => {
      await logger.initialize();
    });

    it('should log events with all required fields', async () => {
      await logger.logEvent({
        type: 'authentication',
        action: 'login_attempt',
        success: true,
        riskLevel: 'low',
      });
      
      const events = logger.queryEvents();
      expect(events).toHaveLength(2); // Including initialization event
      
      const loginEvent = events.find(e => e.action === 'login_attempt');
      expect(loginEvent).toBeDefined();
      expect(loginEvent!.id).toBeDefined();
      expect(loginEvent!.timestamp).toBeDefined();
      expect(loginEvent!.userAgent).toBe('test-user-agent');
    });

    it('should save to localStorage when enabled', async () => {
      config.enableLocalStorage = true;
      logger = new SecurityAuditLogger(config);
      await logger.initialize();
      
      await logger.logEvent({
        type: 'authentication',
        action: 'test',
        success: true,
        riskLevel: 'low',
      });
      
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'iframe_security_audit_log',
        expect.any(String)
      );
    });

    it('should send to remote endpoint when enabled', async () => {
      config.enableRemoteLogging = true;
      config.remoteEndpoint = 'https://api.example.com/audit';
      logger = new SecurityAuditLogger(config);
      await logger.initialize();
      
      (global.fetch as any).mockResolvedValue({ ok: true });
      
      await logger.logEvent({
        type: 'authentication',
        action: 'test',
        success: true,
        riskLevel: 'low',
      });
      
      expect(global.fetch).toHaveBeenCalledWith(
        'https://api.example.com/audit',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.any(String),
        })
      );
    });

    it('should handle remote logging errors gracefully', async () => {
      config.enableRemoteLogging = true;
      config.remoteEndpoint = 'https://api.example.com/audit';
      logger = new SecurityAuditLogger(config);
      await logger.initialize();
      
      (global.fetch as any).mockRejectedValue(new Error('Network error'));
      
      await logger.logEvent({
        type: 'authentication',
        action: 'test',
        success: true,
        riskLevel: 'low',
      });
      
      expect(console.warn).toHaveBeenCalledWith(
        'Failed to send audit event to remote endpoint:',
        expect.any(Error)
      );
    });

    it('should log to console when enabled', async () => {
      config.enableConsoleLogging = true;
      logger = new SecurityAuditLogger(config);
      await logger.initialize();
      
      await logger.logEvent({
        type: 'authentication',
        action: 'test',
        success: true,
        riskLevel: 'high',
      });
      
      expect(console.error).toHaveBeenCalledWith(
        expect.stringContaining('[AUDIT] authentication:test - SUCCESS'),
        expect.any(Object)
      );
    });

    it('should enforce max log size', async () => {
      config.maxLogSize = 3;
      logger = new SecurityAuditLogger(config);
      await logger.initialize();
      
      // Log more events than max size
      for (let i = 0; i < 5; i++) {
        await logger.logEvent({
          type: 'authentication',
          action: `test-${i}`,
          success: true,
          riskLevel: 'low',
        });
      }
      
      const events = logger.queryEvents();
      expect(events.length).toBeLessThanOrEqual(3);
    });
  });

  describe('specialized logging methods', () => {
    beforeEach(async () => {
      await logger.initialize();
    });

    it('should log authentication events', async () => {
      await logger.logAuthentication('login', true, { userId: 'user123' });
      
      const events = logger.queryEvents({ type: 'authentication' });
      expect(events).toHaveLength(1);
      expect(events[0].action).toBe('login');
      expect(events[0].success).toBe(true);
      expect(events[0].riskLevel).toBe('low');
    });

    it('should log failed authentication with high risk', async () => {
      await logger.logAuthentication('login', false);
      
      const events = logger.queryEvents({ type: 'authentication' });
      expect(events).toHaveLength(1);
      expect(events[0].success).toBe(false);
      expect(events[0].riskLevel).toBe('high');
    });

    it('should log authorization events', async () => {
      await logger.logAuthorization('access_resource', '/api/data', true, 'user123');
      
      const events = logger.queryEvents({ type: 'authorization' });
      expect(events).toHaveLength(1);
      expect(events[0].resource).toBe('/api/data');
      expect(events[0].userId).toBe('user123');
    });

    it('should log data access events', async () => {
      await logger.logDataAccess('read', '/api/sensitive', 'user123', { count: 10 });
      
      const events = logger.queryEvents({ type: 'data_access' });
      expect(events).toHaveLength(1);
      expect(events[0].resource).toBe('/api/sensitive');
      expect(events[0].details).toEqual({ count: 10 });
    });

    it('should log encryption events', async () => {
      await logger.logEncryption('encrypt_data', true, { algorithm: 'AES-256' });
      
      const events = logger.queryEvents({ type: 'encryption' });
      expect(events).toHaveLength(1);
      expect(events[0].action).toBe('encrypt_data');
      expect(events[0].details).toEqual({ algorithm: 'AES-256' });
    });

    it('should log policy violations', async () => {
      await logger.logPolicyViolation('csp_violation', { directive: 'script-src' });
      
      const events = logger.queryEvents({ type: 'policy_violation' });
      expect(events).toHaveLength(1);
      expect(events[0].success).toBe(false);
      expect(events[0].riskLevel).toBe('critical');
    });

    it('should log configuration changes', async () => {
      await logger.logConfigurationChange('update_security_policy', { policy: 'CSP' });
      
      const events = logger.queryEvents({ type: 'configuration_change' });
      expect(events).toHaveLength(2); // Including initialization event
      
      const updateEvent = events.find(e => e.action === 'update_security_policy');
      expect(updateEvent).toBeDefined();
      expect(updateEvent!.riskLevel).toBe('medium');
    });
  });

  describe('event querying', () => {
    beforeEach(async () => {
      await logger.initialize();
      
      // Add test events
      await logger.logAuthentication('login', true);
      await logger.logAuthentication('logout', true);
      await logger.logAuthorization('access', '/api/data', false);
      await logger.logDataAccess('read', '/api/sensitive', 'user123');
    });

    it('should query all events', () => {
      const events = logger.queryEvents();
      expect(events.length).toBeGreaterThan(0);
    });

    it('should filter by event type', () => {
      const authEvents = logger.queryEvents({ type: 'authentication' });
      expect(authEvents).toHaveLength(2);
      expect(authEvents.every(e => e.type === 'authentication')).toBe(true);
    });

    it('should filter by action', () => {
      const loginEvents = logger.queryEvents({ action: 'login' });
      expect(loginEvents).toHaveLength(1);
      expect(loginEvents[0].action).toBe('login');
    });

    it('should filter by success status', () => {
      const failedEvents = logger.queryEvents({ success: false });
      expect(failedEvents).toHaveLength(1);
      expect(failedEvents[0].success).toBe(false);
    });

    it('should filter by user ID', () => {
      const userEvents = logger.queryEvents({ userId: 'user123' });
      expect(userEvents).toHaveLength(1);
      expect(userEvents[0].userId).toBe('user123');
    });

    it('should filter by time range', () => {
      const now = Date.now();
      const oneHourAgo = now - (60 * 60 * 1000);
      
      const recentEvents = logger.queryEvents({
        startTime: oneHourAgo,
        endTime: now,
      });
      
      expect(recentEvents.length).toBeGreaterThan(0);
      expect(recentEvents.every(e => e.timestamp >= oneHourAgo && e.timestamp <= now)).toBe(true);
    });

    it('should apply pagination', () => {
      const firstPage = logger.queryEvents({ limit: 2, offset: 0 });
      const secondPage = logger.queryEvents({ limit: 2, offset: 2 });
      
      expect(firstPage).toHaveLength(2);
      expect(secondPage.length).toBeGreaterThanOrEqual(0);
      
      // Should not have overlapping events
      const firstPageIds = firstPage.map(e => e.id);
      const secondPageIds = secondPage.map(e => e.id);
      const overlap = firstPageIds.filter(id => secondPageIds.includes(id));
      expect(overlap).toHaveLength(0);
    });

    it('should sort events by timestamp (newest first)', () => {
      const events = logger.queryEvents();
      
      for (let i = 1; i < events.length; i++) {
        expect(events[i - 1].timestamp).toBeGreaterThanOrEqual(events[i].timestamp);
      }
    });
  });

  describe('audit summary', () => {
    beforeEach(async () => {
      await logger.initialize();
      
      // Add test events with different characteristics
      await logger.logAuthentication('login', true);
      await logger.logAuthentication('login', false);
      await logger.logAuthorization('access', '/api/data', true);
      await logger.logPolicyViolation('csp_violation', {});
    });

    it('should generate summary statistics', () => {
      const summary = logger.getSummary();
      
      expect(summary.totalEvents).toBeGreaterThan(0);
      expect(summary.successfulEvents).toBeGreaterThan(0);
      expect(summary.failedEvents).toBeGreaterThan(0);
      expect(summary.totalEvents).toBe(summary.successfulEvents + summary.failedEvents);
    });

    it('should calculate risk distribution', () => {
      const summary = logger.getSummary();
      
      expect(summary.riskDistribution).toHaveProperty('low');
      expect(summary.riskDistribution).toHaveProperty('medium');
      expect(summary.riskDistribution).toHaveProperty('high');
      expect(summary.riskDistribution).toHaveProperty('critical');
      
      const totalRisk = Object.values(summary.riskDistribution).reduce((a, b) => a + b, 0);
      expect(totalRisk).toBe(summary.totalEvents);
    });

    it('should calculate type distribution', () => {
      const summary = logger.getSummary();
      
      expect(summary.typeDistribution).toHaveProperty('authentication');
      expect(summary.typeDistribution).toHaveProperty('authorization');
      expect(summary.typeDistribution).toHaveProperty('policy_violation');
      
      const totalTypes = Object.values(summary.typeDistribution).reduce((a, b) => a + b, 0);
      expect(totalTypes).toBe(summary.totalEvents);
    });

    it('should calculate time range', () => {
      const summary = logger.getSummary();
      
      expect(summary.timeRange.start).toBeGreaterThan(0);
      expect(summary.timeRange.end).toBeGreaterThan(0);
      expect(summary.timeRange.end).toBeGreaterThanOrEqual(summary.timeRange.start);
    });
  });

  describe('log export', () => {
    beforeEach(async () => {
      await logger.initialize();
      await logger.logAuthentication('login', true);
    });

    it('should export as JSON', () => {
      const exported = logger.exportLog('json');
      
      expect(() => JSON.parse(exported)).not.toThrow();
      
      const parsed = JSON.parse(exported);
      expect(Array.isArray(parsed)).toBe(true);
      expect(parsed.length).toBeGreaterThan(0);
    });

    it('should export as CSV', () => {
      const exported = logger.exportLog('csv');
      
      expect(typeof exported).toBe('string');
      expect(exported).toContain('id,type,action');
      
      const lines = exported.split('\n');
      expect(lines.length).toBeGreaterThan(1); // Header + data
    });

    it('should handle empty export', () => {
      const emptyLogger = new SecurityAuditLogger(config);
      
      const jsonExport = emptyLogger.exportLog('json');
      expect(jsonExport).toBe('[]');
      
      const csvExport = emptyLogger.exportLog('csv');
      expect(csvExport).toBe('');
    });

    it('should export with query filters', () => {
      const exported = logger.exportLog('json', { type: 'authentication' });
      
      const parsed = JSON.parse(exported);
      expect(parsed.every((event: SecurityAuditEvent) => event.type === 'authentication')).toBe(true);
    });
  });

  describe('log management', () => {
    beforeEach(async () => {
      await logger.initialize();
      await logger.logAuthentication('login', true);
    });

    it('should clear audit log', async () => {
      expect(logger.queryEvents()).toHaveLength(2); // Including initialization event
      
      await logger.clearLog();
      
      const events = logger.queryEvents();
      expect(events).toHaveLength(1); // Only the clear log event
      expect(events[0].action).toBe('audit_log_cleared');
    });

    it('should remove localStorage data when clearing', async () => {
      await logger.clearLog();
      
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('iframe_security_audit_log');
    });
  });

  describe('event handlers', () => {
    beforeEach(async () => {
      await logger.initialize();
    });

    it('should notify event handlers', async () => {
      await logger.logAuthentication('login', true);
      
      expect(eventHandlers.length).toBeGreaterThan(0);
      
      const loginEvent = eventHandlers.find(e => e.action === 'login');
      expect(loginEvent).toBeDefined();
    });

    it('should remove event handlers', async () => {
      const handler = vi.fn();
      const removeHandler = logger.onEvent(handler);
      
      await logger.logAuthentication('login', true);
      expect(handler).toHaveBeenCalledTimes(1);
      
      removeHandler();
      await logger.logAuthentication('logout', true);
      expect(handler).toHaveBeenCalledTimes(1); // Should not be called again
    });

    it('should handle errors in event handlers gracefully', async () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error');
      });
      
      logger.onEvent(errorHandler);
      
      await logger.logAuthentication('login', true);
      
      expect(console.error).toHaveBeenCalledWith(
        'Error in audit event handler:',
        expect.any(Error)
      );
    });
  });

  describe('configuration management', () => {
    it('should update configuration', () => {
      const newConfig = {
        maxLogSize: 5000,
        enableConsoleLogging: true,
      };
      
      logger.updateConfig(newConfig);
      
      const currentConfig = logger.getConfig();
      expect(currentConfig.maxLogSize).toBe(5000);
      expect(currentConfig.enableConsoleLogging).toBe(true);
    });

    it('should get current configuration', () => {
      const currentConfig = logger.getConfig();
      expect(currentConfig).toEqual(config);
    });
  });

  describe('cleanup', () => {
    it('should cleanup resources', async () => {
      await logger.initialize();
      expect(logger.isReady()).toBe(true);
      
      logger.cleanup();
      expect(logger.isReady()).toBe(false);
    });
  });
});

describe('createDefaultAuditConfig', () => {
  it('should create default configuration', () => {
    const config = createDefaultAuditConfig();
    
    expect(config.maxLogSize).toBe(10000);
    expect(config.retentionDays).toBe(90);
    expect(config.enableRemoteLogging).toBe(false);
    expect(config.enableLocalStorage).toBe(true);
    expect(config.logLevel).toBe('info');
    expect(config.enableEncryption).toBe(false);
  });

  it('should set console logging based on environment', () => {
    const originalEnv = process.env.NODE_ENV;
    
    process.env.NODE_ENV = 'development';
    const devConfig = createDefaultAuditConfig();
    expect(devConfig.enableConsoleLogging).toBe(true);
    
    process.env.NODE_ENV = 'production';
    const prodConfig = createDefaultAuditConfig();
    expect(prodConfig.enableConsoleLogging).toBe(false);
    
    process.env.NODE_ENV = originalEnv;
  });
});

describe('global audit logger', () => {
  afterEach(() => {
    // Reset global instance
    (globalThis as any).globalSecurityAuditLogger = null;
  });

  it('should get global instance', () => {
    const logger1 = getGlobalSecurityAuditLogger();
    const logger2 = getGlobalSecurityAuditLogger();
    
    expect(logger1).toBe(logger2); // Should be the same instance
  });

  it('should initialize global instance', async () => {
    const customConfig = {
      maxLogSize: 5000,
    };
    
    const logger = await initializeGlobalSecurityAuditLogger(customConfig);
    
    expect(logger.isReady()).toBe(true);
    expect(logger.getConfig().maxLogSize).toBe(5000);
  });
});