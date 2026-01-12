/**
 * API Performance Utilities Tests
 * 
 * Tests for API response time optimization utilities.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  apiPerformanceMonitor,
  requestCache,
  requestDeduplicator,
  checkApiResponseBudget,
  isCacheableEndpoint,
  createOptimizedRequestConfig,
  API_RESPONSE_BUDGET,
  API_WARNING_THRESHOLD,
  DEFAULT_CACHE_TTL,
} from '../apiPerformance';

describe('API Performance Utilities', () => {
  beforeEach(() => {
    // Clear state before each test
    apiPerformanceMonitor.clear();
    requestCache.clear();
    requestDeduplicator.clear();
  });

  describe('checkApiResponseBudget', () => {
    it('should pass when response time is within budget', () => {
      const result = checkApiResponseBudget(300);
      
      expect(result.passed).toBe(true);
      expect(result.isWarning).toBe(false);
      expect(result.responseTime).toBe(300);
      expect(result.budget).toBe(API_RESPONSE_BUDGET);
    });

    it('should warn when response time approaches budget', () => {
      const result = checkApiResponseBudget(450);
      
      expect(result.passed).toBe(true);
      expect(result.isWarning).toBe(true);
    });

    it('should fail when response time exceeds budget', () => {
      const result = checkApiResponseBudget(600);
      
      expect(result.passed).toBe(false);
      expect(result.responseTime).toBe(600);
    });

    it('should calculate usage percentage correctly', () => {
      const result = checkApiResponseBudget(250);
      
      expect(result.usagePercent).toBe(50);
    });

    it('should use custom budget when provided', () => {
      const result = checkApiResponseBudget(300, 200);
      
      expect(result.passed).toBe(false);
      expect(result.budget).toBe(200);
    });
  });

  describe('apiPerformanceMonitor', () => {
    it('should record metrics', () => {
      apiPerformanceMonitor.record({
        endpoint: '/api/test',
        method: 'GET',
        responseTime: 200,
        isWithinBudget: true,
        timestamp: Date.now(),
        cached: false,
      });

      const metrics = apiPerformanceMonitor.getMetrics();
      expect(metrics).toHaveLength(1);
      expect(metrics[0].endpoint).toBe('/api/test');
    });

    it('should calculate summary correctly', () => {
      // Record some metrics
      apiPerformanceMonitor.record({
        endpoint: '/api/test1',
        method: 'GET',
        responseTime: 200,
        isWithinBudget: true,
        timestamp: Date.now(),
        cached: false,
      });
      
      apiPerformanceMonitor.record({
        endpoint: '/api/test2',
        method: 'GET',
        responseTime: 600,
        isWithinBudget: false,
        timestamp: Date.now(),
        cached: false,
      });
      
      apiPerformanceMonitor.record({
        endpoint: '/api/test3',
        method: 'GET',
        responseTime: 100,
        isWithinBudget: true,
        timestamp: Date.now(),
        cached: true,
      });

      const summary = apiPerformanceMonitor.getSummary();
      
      expect(summary.totalCalls).toBe(3);
      expect(summary.withinBudget).toBe(2);
      expect(summary.exceedingBudget).toBe(1);
      expect(summary.averageResponseTime).toBe(300);
      expect(summary.cacheHitRate).toBe(33);
    });

    it('should notify subscribers on new metrics', () => {
      const callback = vi.fn();
      const unsubscribe = apiPerformanceMonitor.subscribe(callback);

      apiPerformanceMonitor.record({
        endpoint: '/api/test',
        method: 'GET',
        responseTime: 200,
        isWithinBudget: true,
        timestamp: Date.now(),
        cached: false,
      });

      expect(callback).toHaveBeenCalledTimes(1);
      
      unsubscribe();
      
      apiPerformanceMonitor.record({
        endpoint: '/api/test2',
        method: 'GET',
        responseTime: 200,
        isWithinBudget: true,
        timestamp: Date.now(),
        cached: false,
      });

      expect(callback).toHaveBeenCalledTimes(1);
    });

    it('should clear metrics', () => {
      apiPerformanceMonitor.record({
        endpoint: '/api/test',
        method: 'GET',
        responseTime: 200,
        isWithinBudget: true,
        timestamp: Date.now(),
        cached: false,
      });

      apiPerformanceMonitor.clear();
      
      expect(apiPerformanceMonitor.getMetrics()).toHaveLength(0);
    });
  });

  describe('requestCache', () => {
    it('should cache and retrieve data', () => {
      const key = 'test-key';
      const data = { foo: 'bar' };
      
      requestCache.set(key, data);
      const cached = requestCache.get(key);
      
      expect(cached).toEqual(data);
    });

    it('should return null for non-existent keys', () => {
      const cached = requestCache.get('non-existent');
      
      expect(cached).toBeNull();
    });

    it('should expire entries after TTL', async () => {
      const key = 'test-key';
      const data = { foo: 'bar' };
      
      requestCache.set(key, data, 10); // 10ms TTL
      
      // Wait for expiration
      await new Promise(resolve => setTimeout(resolve, 20));
      
      const cached = requestCache.get(key);
      expect(cached).toBeNull();
    });

    it('should generate consistent cache keys', () => {
      const config1 = { method: 'GET', url: '/api/test', params: { id: 1 } };
      const config2 = { method: 'GET', url: '/api/test', params: { id: 1 } };
      
      const key1 = requestCache.generateKey(config1);
      const key2 = requestCache.generateKey(config2);
      
      expect(key1).toBe(key2);
    });

    it('should invalidate entries by pattern', () => {
      requestCache.set('GET:/api/users/1', { id: 1 });
      requestCache.set('GET:/api/users/2', { id: 2 });
      requestCache.set('GET:/api/tasks/1', { id: 1 });
      
      requestCache.invalidatePattern('/api/users');
      
      expect(requestCache.get('GET:/api/users/1')).toBeNull();
      expect(requestCache.get('GET:/api/users/2')).toBeNull();
      expect(requestCache.get('GET:/api/tasks/1')).not.toBeNull();
    });

    it('should clear all cache', () => {
      requestCache.set('key1', 'value1');
      requestCache.set('key2', 'value2');
      
      requestCache.clear();
      
      expect(requestCache.get('key1')).toBeNull();
      expect(requestCache.get('key2')).toBeNull();
    });
  });

  describe('requestDeduplicator', () => {
    it('should deduplicate concurrent requests', async () => {
      let callCount = 0;
      const requestFn = async () => {
        callCount++;
        await new Promise(resolve => setTimeout(resolve, 50));
        return { data: 'result' };
      };

      // Make concurrent requests
      const [result1, result2] = await Promise.all([
        requestDeduplicator.deduplicate('test-key', requestFn),
        requestDeduplicator.deduplicate('test-key', requestFn),
      ]);

      expect(callCount).toBe(1);
      expect(result1.data).toEqual({ data: 'result' });
      expect(result2.data).toEqual({ data: 'result' });
      expect(result1.deduplicated).toBe(false);
      expect(result2.deduplicated).toBe(true);
    });

    it('should not deduplicate sequential requests', async () => {
      let callCount = 0;
      const requestFn = async () => {
        callCount++;
        return { data: 'result' };
      };

      await requestDeduplicator.deduplicate('test-key', requestFn);
      await requestDeduplicator.deduplicate('test-key', requestFn);

      expect(callCount).toBe(2);
    });
  });

  describe('isCacheableEndpoint', () => {
    it('should identify cacheable endpoints', () => {
      const result = isCacheableEndpoint('/api/business-metrics/summary', 'GET');
      
      expect(result.cacheable).toBe(true);
      expect(result.ttl).toBeGreaterThan(0);
    });

    it('should not cache non-GET methods', () => {
      const result = isCacheableEndpoint('/api/business-metrics/summary', 'POST');
      
      expect(result.cacheable).toBe(false);
    });

    it('should not cache unknown endpoints', () => {
      const result = isCacheableEndpoint('/api/unknown/endpoint', 'GET');
      
      expect(result.cacheable).toBe(false);
    });
  });

  describe('createOptimizedRequestConfig', () => {
    it('should set appropriate timeout for high priority', () => {
      const config = createOptimizedRequestConfig(
        { url: '/api/test' },
        { priority: 'high' }
      );
      
      expect(config.timeout).toBeLessThanOrEqual(API_RESPONSE_BUDGET);
    });

    it('should set longer timeout for low priority', () => {
      const config = createOptimizedRequestConfig(
        { url: '/api/test' },
        { priority: 'low' }
      );
      
      expect(config.timeout).toBeGreaterThan(API_RESPONSE_BUDGET);
    });

    it('should add priority header', () => {
      const config = createOptimizedRequestConfig(
        { url: '/api/test' },
        { priority: 'high' }
      );
      
      expect(config.headers?.['X-Request-Priority']).toBe('high');
    });
  });

  describe('Constants', () => {
    it('should have correct API response budget', () => {
      expect(API_RESPONSE_BUDGET).toBe(500);
    });

    it('should have correct warning threshold', () => {
      expect(API_WARNING_THRESHOLD).toBe(400);
    });

    it('should have correct default cache TTL', () => {
      expect(DEFAULT_CACHE_TTL).toBe(30000);
    });
  });
});
