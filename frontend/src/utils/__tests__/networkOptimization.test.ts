/**
 * Network Optimization Utilities Tests
 * 
 * Tests for network request optimization utilities.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  calculateBackoffDelay,
  defaultRetryCondition,
  executeWithRetry,
  batchRequests,
  getNetworkStatus,
  isSlowNetwork,
  getAdaptiveTimeout,
  createAdaptiveRequestConfig,
  requestCancellationManager,
  requestMetricsCollector,
  MAX_CONCURRENT_REQUESTS,
  DEFAULT_RETRY_ATTEMPTS,
  BASE_RETRY_DELAY,
  MAX_RETRY_DELAY,
  SLOW_NETWORK_TIMEOUT,
  FAST_NETWORK_TIMEOUT,
} from '../networkOptimization';
import type { AxiosError, AxiosResponse } from 'axios';

describe('Network Optimization Utilities', () => {
  beforeEach(() => {
    // Reset state before each test
    requestMetricsCollector.reset();
    requestCancellationManager.cancelAll();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Constants', () => {
    it('should have correct max concurrent requests', () => {
      expect(MAX_CONCURRENT_REQUESTS).toBe(6);
    });

    it('should have correct default retry attempts', () => {
      expect(DEFAULT_RETRY_ATTEMPTS).toBe(3);
    });

    it('should have correct base retry delay', () => {
      expect(BASE_RETRY_DELAY).toBe(1000);
    });

    it('should have correct max retry delay', () => {
      expect(MAX_RETRY_DELAY).toBe(30000);
    });

    it('should have correct slow network timeout', () => {
      expect(SLOW_NETWORK_TIMEOUT).toBe(10000);
    });

    it('should have correct fast network timeout', () => {
      expect(FAST_NETWORK_TIMEOUT).toBe(5000);
    });
  });

  describe('calculateBackoffDelay', () => {
    it('should calculate exponential delay for first attempt', () => {
      const delay = calculateBackoffDelay(0, 1000, 30000);
      // First attempt: 1000 * 2^0 = 1000, plus jitter (0-30%)
      expect(delay).toBeGreaterThanOrEqual(1000);
      expect(delay).toBeLessThanOrEqual(1300);
    });

    it('should calculate exponential delay for second attempt', () => {
      const delay = calculateBackoffDelay(1, 1000, 30000);
      // Second attempt: 1000 * 2^1 = 2000, plus jitter (0-30%)
      expect(delay).toBeGreaterThanOrEqual(2000);
      expect(delay).toBeLessThanOrEqual(2600);
    });

    it('should calculate exponential delay for third attempt', () => {
      const delay = calculateBackoffDelay(2, 1000, 30000);
      // Third attempt: 1000 * 2^2 = 4000, plus jitter (0-30%)
      expect(delay).toBeGreaterThanOrEqual(4000);
      expect(delay).toBeLessThanOrEqual(5200);
    });

    it('should cap delay at max delay', () => {
      const delay = calculateBackoffDelay(10, 1000, 5000);
      // 1000 * 2^10 = 1024000, but capped at 5000
      expect(delay).toBeLessThanOrEqual(5000);
    });

    it('should use default values when not provided', () => {
      const delay = calculateBackoffDelay(0);
      expect(delay).toBeGreaterThanOrEqual(BASE_RETRY_DELAY);
    });
  });

  describe('defaultRetryCondition', () => {
    it('should retry on network errors (no response)', () => {
      const error = { response: undefined } as AxiosError;
      expect(defaultRetryCondition(error)).toBe(true);
    });

    it('should retry on 500 server error', () => {
      const error = { response: { status: 500 } } as AxiosError;
      expect(defaultRetryCondition(error)).toBe(true);
    });

    it('should retry on 502 bad gateway', () => {
      const error = { response: { status: 502 } } as AxiosError;
      expect(defaultRetryCondition(error)).toBe(true);
    });

    it('should retry on 503 service unavailable', () => {
      const error = { response: { status: 503 } } as AxiosError;
      expect(defaultRetryCondition(error)).toBe(true);
    });

    it('should retry on 429 too many requests', () => {
      const error = { response: { status: 429 } } as AxiosError;
      expect(defaultRetryCondition(error)).toBe(true);
    });

    it('should not retry on 400 bad request', () => {
      const error = { response: { status: 400 } } as AxiosError;
      expect(defaultRetryCondition(error)).toBe(false);
    });

    it('should not retry on 401 unauthorized', () => {
      const error = { response: { status: 401 } } as AxiosError;
      expect(defaultRetryCondition(error)).toBe(false);
    });

    it('should not retry on 404 not found', () => {
      const error = { response: { status: 404 } } as AxiosError;
      expect(defaultRetryCondition(error)).toBe(false);
    });
  });

  describe('executeWithRetry', () => {
    it('should return result on successful request', async () => {
      const mockResponse = { data: 'success', status: 200 } as AxiosResponse;
      const requestFn = vi.fn().mockResolvedValue(mockResponse);

      const result = await executeWithRetry(requestFn, { maxRetries: 3 });

      expect(result).toEqual(mockResponse);
      expect(requestFn).toHaveBeenCalledTimes(1);
    });

    it('should retry on failure and succeed', async () => {
      const mockResponse = { data: 'success', status: 200 } as AxiosResponse;
      const requestFn = vi.fn()
        .mockRejectedValueOnce({ response: { status: 500 } })
        .mockResolvedValueOnce(mockResponse);

      const result = await executeWithRetry(requestFn, { 
        maxRetries: 3,
        baseDelay: 10, // Short delay for testing
      });

      expect(result).toEqual(mockResponse);
      expect(requestFn).toHaveBeenCalledTimes(2);
    });

    it('should throw after max retries exceeded', async () => {
      const error = { response: { status: 500 } } as AxiosError;
      const requestFn = vi.fn().mockRejectedValue(error);

      await expect(
        executeWithRetry(requestFn, { 
          maxRetries: 2,
          baseDelay: 10,
        })
      ).rejects.toEqual(error);

      expect(requestFn).toHaveBeenCalledTimes(3); // Initial + 2 retries
    });

    it('should not retry when condition returns false', async () => {
      const error = { response: { status: 400 } } as AxiosError;
      const requestFn = vi.fn().mockRejectedValue(error);

      await expect(
        executeWithRetry(requestFn, { 
          maxRetries: 3,
          retryCondition: () => false,
        })
      ).rejects.toEqual(error);

      expect(requestFn).toHaveBeenCalledTimes(1);
    });
  });

  describe('batchRequests', () => {
    it('should execute all requests successfully', async () => {
      const mockExecutor = vi.fn().mockImplementation((config) => 
        Promise.resolve({ data: config.url, status: 200 } as AxiosResponse)
      );

      const results = await batchRequests(mockExecutor, {
        requests: [
          { key: 'req1', config: { url: '/api/1' } },
          { key: 'req2', config: { url: '/api/2' } },
          { key: 'req3', config: { url: '/api/3' } },
        ],
      });

      expect(results).toHaveLength(3);
      expect(results.every(r => r.success)).toBe(true);
      expect(mockExecutor).toHaveBeenCalledTimes(3);
    });

    it('should handle partial failures', async () => {
      const mockExecutor = vi.fn()
        .mockResolvedValueOnce({ data: 'success1', status: 200 })
        .mockRejectedValueOnce(new Error('Failed'))
        .mockResolvedValueOnce({ data: 'success3', status: 200 });

      const results = await batchRequests(mockExecutor, {
        requests: [
          { key: 'req1', config: { url: '/api/1' } },
          { key: 'req2', config: { url: '/api/2' } },
          { key: 'req3', config: { url: '/api/3' } },
        ],
        stopOnError: false,
      });

      expect(results).toHaveLength(3);
      expect(results[0].success).toBe(true);
      expect(results[1].success).toBe(false);
      expect(results[2].success).toBe(true);
    });

    it('should stop on error when configured', async () => {
      const mockExecutor = vi.fn()
        .mockResolvedValueOnce({ data: 'success1', status: 200 })
        .mockRejectedValueOnce(new Error('Failed'));

      await expect(
        batchRequests(mockExecutor, {
          requests: [
            { key: 'req1', config: { url: '/api/1' } },
            { key: 'req2', config: { url: '/api/2' } },
            { key: 'req3', config: { url: '/api/3' } },
          ],
          maxConcurrent: 1,
          stopOnError: true,
        })
      ).rejects.toThrow('Failed');
    });

    it('should call progress callback', async () => {
      const mockExecutor = vi.fn().mockResolvedValue({ data: 'success', status: 200 });
      const onProgress = vi.fn();

      await batchRequests(mockExecutor, {
        requests: [
          { key: 'req1', config: { url: '/api/1' } },
          { key: 'req2', config: { url: '/api/2' } },
        ],
        onProgress,
      });

      expect(onProgress).toHaveBeenCalledWith(1, 2);
      expect(onProgress).toHaveBeenCalledWith(2, 2);
    });

    it('should respect max concurrent limit', async () => {
      let concurrentCount = 0;
      let maxConcurrent = 0;

      const mockExecutor = vi.fn().mockImplementation(async () => {
        concurrentCount++;
        maxConcurrent = Math.max(maxConcurrent, concurrentCount);
        await new Promise(resolve => setTimeout(resolve, 10));
        concurrentCount--;
        return { data: 'success', status: 200 };
      });

      await batchRequests(mockExecutor, {
        requests: Array.from({ length: 10 }, (_, i) => ({
          key: `req${i}`,
          config: { url: `/api/${i}` },
        })),
        maxConcurrent: 3,
      });

      expect(maxConcurrent).toBeLessThanOrEqual(3);
    });
  });

  describe('getNetworkStatus', () => {
    it('should return online status', () => {
      const status = getNetworkStatus();
      expect(status).toHaveProperty('online');
      expect(typeof status.online).toBe('boolean');
    });

    it('should return effective type', () => {
      const status = getNetworkStatus();
      expect(status).toHaveProperty('effectiveType');
    });

    it('should return downlink', () => {
      const status = getNetworkStatus();
      expect(status).toHaveProperty('downlink');
      expect(typeof status.downlink).toBe('number');
    });

    it('should return rtt', () => {
      const status = getNetworkStatus();
      expect(status).toHaveProperty('rtt');
      expect(typeof status.rtt).toBe('number');
    });
  });

  describe('isSlowNetwork', () => {
    it('should return boolean', () => {
      const result = isSlowNetwork();
      expect(typeof result).toBe('boolean');
    });
  });

  describe('getAdaptiveTimeout', () => {
    it('should return a number', () => {
      const timeout = getAdaptiveTimeout();
      expect(typeof timeout).toBe('number');
      expect(timeout).toBeGreaterThan(0);
    });

    it('should return either slow or fast timeout', () => {
      const timeout = getAdaptiveTimeout();
      expect([SLOW_NETWORK_TIMEOUT, FAST_NETWORK_TIMEOUT]).toContain(timeout);
    });
  });

  describe('createAdaptiveRequestConfig', () => {
    it('should add timeout to config', () => {
      const config = createAdaptiveRequestConfig({ url: '/api/test' });
      expect(config.timeout).toBeDefined();
      expect(config.timeout).toBeGreaterThan(0);
    });

    it('should add priority header', () => {
      const config = createAdaptiveRequestConfig(
        { url: '/api/test' },
        { priority: 'high' }
      );
      expect(config.headers?.['X-Request-Priority']).toBe('high');
    });

    it('should preserve original config', () => {
      const config = createAdaptiveRequestConfig({
        url: '/api/test',
        method: 'POST',
        data: { foo: 'bar' },
      });
      expect(config.url).toBe('/api/test');
      expect(config.method).toBe('POST');
      expect(config.data).toEqual({ foo: 'bar' });
    });
  });

  describe('requestCancellationManager', () => {
    it('should create abort controller', () => {
      const controller = requestCancellationManager.create('test-request');
      expect(controller).toBeInstanceOf(AbortController);
    });

    it('should cancel request', () => {
      requestCancellationManager.create('test-request');
      const result = requestCancellationManager.cancel('test-request');
      expect(result).toBe(true);
    });

    it('should return false when cancelling non-existent request', () => {
      const result = requestCancellationManager.cancel('non-existent');
      expect(result).toBe(false);
    });

    it('should cancel requests by prefix', () => {
      requestCancellationManager.create('user-1');
      requestCancellationManager.create('user-2');
      requestCancellationManager.create('task-1');

      const cancelled = requestCancellationManager.cancelByPrefix('user-');
      expect(cancelled).toBe(2);
    });

    it('should cancel all requests', () => {
      requestCancellationManager.create('req-1');
      requestCancellationManager.create('req-2');
      requestCancellationManager.create('req-3');

      const cancelled = requestCancellationManager.cancelAll();
      expect(cancelled).toBe(3);
      expect(requestCancellationManager.getActiveCount()).toBe(0);
    });

    it('should track active count', () => {
      expect(requestCancellationManager.getActiveCount()).toBe(0);
      
      requestCancellationManager.create('req-1');
      expect(requestCancellationManager.getActiveCount()).toBe(1);
      
      requestCancellationManager.create('req-2');
      expect(requestCancellationManager.getActiveCount()).toBe(2);
      
      requestCancellationManager.complete('req-1');
      expect(requestCancellationManager.getActiveCount()).toBe(1);
    });
  });

  describe('requestMetricsCollector', () => {
    it('should record successful requests', () => {
      requestMetricsCollector.recordSuccess(100);
      const metrics = requestMetricsCollector.getMetrics();
      
      expect(metrics.totalRequests).toBe(1);
      expect(metrics.successfulRequests).toBe(1);
      expect(metrics.averageResponseTime).toBe(100);
    });

    it('should record failed requests', () => {
      requestMetricsCollector.recordFailure();
      const metrics = requestMetricsCollector.getMetrics();
      
      expect(metrics.totalRequests).toBe(1);
      expect(metrics.failedRequests).toBe(1);
    });

    it('should record cancelled requests', () => {
      requestMetricsCollector.recordCancellation();
      const metrics = requestMetricsCollector.getMetrics();
      
      expect(metrics.totalRequests).toBe(1);
      expect(metrics.cancelledRequests).toBe(1);
    });

    it('should record retries', () => {
      requestMetricsCollector.recordRetry();
      requestMetricsCollector.recordRetry();
      const metrics = requestMetricsCollector.getMetrics();
      
      expect(metrics.retryCount).toBe(2);
    });

    it('should calculate average response time', () => {
      requestMetricsCollector.recordSuccess(100);
      requestMetricsCollector.recordSuccess(200);
      requestMetricsCollector.recordSuccess(300);
      
      const metrics = requestMetricsCollector.getMetrics();
      expect(metrics.averageResponseTime).toBe(200);
    });

    it('should reset metrics', () => {
      requestMetricsCollector.recordSuccess(100);
      requestMetricsCollector.recordFailure();
      requestMetricsCollector.reset();
      
      const metrics = requestMetricsCollector.getMetrics();
      expect(metrics.totalRequests).toBe(0);
      expect(metrics.successfulRequests).toBe(0);
      expect(metrics.failedRequests).toBe(0);
    });
  });
});
