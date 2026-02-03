/**
 * Label Studio Logger 单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { labelStudioLogger, createLabelStudioLogger } from '../labelStudioLogger';

describe('labelStudioLogger', () => {
  let consoleSpy: {
    log: ReturnType<typeof vi.spyOn>;
    debug: ReturnType<typeof vi.spyOn>;
    warn: ReturnType<typeof vi.spyOn>;
    error: ReturnType<typeof vi.spyOn>;
  };

  beforeEach(() => {
    consoleSpy = {
      log: vi.spyOn(console, 'log').mockImplementation(() => {}),
      debug: vi.spyOn(console, 'debug').mockImplementation(() => {}),
      warn: vi.spyOn(console, 'warn').mockImplementation(() => {}),
      error: vi.spyOn(console, 'error').mockImplementation(() => {}),
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('generateRequestId', () => {
    it('should generate unique request IDs', () => {
      const id1 = labelStudioLogger.generateRequestId();
      const id2 = labelStudioLogger.generateRequestId();

      expect(id1).not.toBe(id2);
      expect(id1).toMatch(/^ls-[a-z0-9]+-[a-z0-9]+$/);
      expect(id2).toMatch(/^ls-[a-z0-9]+-[a-z0-9]+$/);
    });

    it('should start with "ls-" prefix', () => {
      const id = labelStudioLogger.generateRequestId();
      expect(id.startsWith('ls-')).toBe(true);
    });
  });

  describe('log methods', () => {
    it('should log info messages with timestamp', () => {
      labelStudioLogger.info('Test message');

      expect(consoleSpy.log).toHaveBeenCalled();
      const logCall = consoleSpy.log.mock.calls[0][0];
      expect(logCall).toContain('[LabelStudio]');
      expect(logCall).toContain('[INFO]');
      expect(logCall).toContain('Test message');
      // Check timestamp format (ISO 8601)
      expect(logCall).toMatch(/\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
    });

    it('should log debug messages', () => {
      labelStudioLogger.debug('Debug message');

      expect(consoleSpy.debug).toHaveBeenCalled();
      const logCall = consoleSpy.debug.mock.calls[0][0];
      expect(logCall).toContain('[DEBUG]');
    });

    it('should log warn messages', () => {
      labelStudioLogger.warn('Warning message');

      expect(consoleSpy.warn).toHaveBeenCalled();
      const logCall = consoleSpy.warn.mock.calls[0][0];
      expect(logCall).toContain('[WARN]');
    });

    it('should log error messages', () => {
      labelStudioLogger.error('Error message');

      expect(consoleSpy.error).toHaveBeenCalled();
      const logCall = consoleSpy.error.mock.calls[0][0];
      expect(logCall).toContain('[ERROR]');
    });

    it('should include request ID when provided', () => {
      const requestId = 'ls-test-0001';
      labelStudioLogger.info('Test message', undefined, requestId);

      const logCall = consoleSpy.log.mock.calls[0][0];
      expect(logCall).toContain(`[${requestId}]`);
    });

    it('should include data when provided', () => {
      const data = { projectId: 123, taskId: 456 };
      labelStudioLogger.info('Test message', data);

      expect(consoleSpy.log).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ data })
      );
    });
  });

  describe('operation logging', () => {
    it('should log operation start and return request ID', () => {
      const requestId = labelStudioLogger.startOperation('Test Operation', { key: 'value' });

      expect(requestId).toMatch(/^ls-/);
      expect(consoleSpy.log).toHaveBeenCalled();
      const logCall = consoleSpy.log.mock.calls[0][0];
      expect(logCall).toContain('Test Operation - START');
    });

    it('should log operation end with success', () => {
      const requestId = 'ls-test-0001';
      labelStudioLogger.endOperation('Test Operation', requestId, true);

      expect(consoleSpy.log).toHaveBeenCalled();
      const logCall = consoleSpy.log.mock.calls[0][0];
      expect(logCall).toContain('Test Operation - END - SUCCESS');
      expect(logCall).toContain(requestId);
    });

    it('should log operation end with failure', () => {
      const requestId = 'ls-test-0001';
      labelStudioLogger.endOperation('Test Operation', requestId, false);

      expect(consoleSpy.error).toHaveBeenCalled();
      const logCall = consoleSpy.error.mock.calls[0][0];
      expect(logCall).toContain('Test Operation - END - FAILED');
    });
  });

  describe('specialized logging methods', () => {
    it('should log window open operation', () => {
      const requestId = labelStudioLogger.logWindowOpen(123, 'http://localhost:8080/projects/123/data', 456);

      expect(requestId).toMatch(/^ls-/);
      expect(consoleSpy.log).toHaveBeenCalled();
      const logCall = consoleSpy.log.mock.calls[0][0];
      expect(logCall).toContain('Open Label Studio Window - START');
    });

    it('should log project create operation', () => {
      const requestId = labelStudioLogger.logProjectCreate('task-1', 'Test Task');

      expect(requestId).toMatch(/^ls-/);
      expect(consoleSpy.log).toHaveBeenCalled();
    });

    it('should log API calls', () => {
      labelStudioLogger.logApiCall('GET', '/api/projects', 'ls-test-0001');

      expect(consoleSpy.log).toHaveBeenCalled();
      const logCall = consoleSpy.log.mock.calls[0][0];
      expect(logCall).toContain('API Call: GET /api/projects');
    });

    it('should log API responses', () => {
      labelStudioLogger.logApiResponse('GET', '/api/projects', 200, 'ls-test-0001');

      expect(consoleSpy.log).toHaveBeenCalled();
      const logCall = consoleSpy.log.mock.calls[0][0];
      expect(logCall).toContain('API Response: GET /api/projects - 200');
    });

    it('should log API error responses', () => {
      labelStudioLogger.logApiResponse('GET', '/api/projects', 500, 'ls-test-0001');

      expect(consoleSpy.error).toHaveBeenCalled();
      const logCall = consoleSpy.error.mock.calls[0][0];
      expect(logCall).toContain('API Response: GET /api/projects - 500');
    });

    it('should log sync operations', () => {
      labelStudioLogger.logSync('start', { taskCount: 10 });
      expect(consoleSpy.log.mock.calls[0][0]).toContain('Sync Started');

      labelStudioLogger.logSync('progress', { current: 5, total: 10 });
      expect(consoleSpy.log.mock.calls[1][0]).toContain('Sync Progress');

      labelStudioLogger.logSync('complete', { successCount: 10 });
      expect(consoleSpy.log.mock.calls[2][0]).toContain('Sync Completed');

      labelStudioLogger.logSync('error', { error: 'Network error' });
      expect(consoleSpy.error).toHaveBeenCalled();
    });

    it('should log errors with stack trace', () => {
      const error = new Error('Test error');
      labelStudioLogger.logError('Test Operation', error, 'ls-test-0001');

      expect(consoleSpy.error).toHaveBeenCalled();
      const logData = consoleSpy.error.mock.calls[0][1];
      expect(logData.data.error).toBe('Test error');
      expect(logData.data.stack).toBeDefined();
    });
  });

  describe('createLabelStudioLogger', () => {
    it('should create a new logger instance with custom config', () => {
      const customLogger = createLabelStudioLogger({
        moduleName: 'CustomModule',
        minLevel: 'warn',
      });

      const config = customLogger.getConfig();
      expect(config.moduleName).toBe('CustomModule');
      expect(config.minLevel).toBe('warn');
    });

    it('should respect minLevel configuration', () => {
      const customLogger = createLabelStudioLogger({
        minLevel: 'warn',
      });

      customLogger.debug('Debug message');
      customLogger.info('Info message');
      customLogger.warn('Warn message');

      // debug and info should not be logged
      expect(consoleSpy.debug).not.toHaveBeenCalled();
      expect(consoleSpy.log).not.toHaveBeenCalled();
      // warn should be logged
      expect(consoleSpy.warn).toHaveBeenCalled();
    });
  });
});
