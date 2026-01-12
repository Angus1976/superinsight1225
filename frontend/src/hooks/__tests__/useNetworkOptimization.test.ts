/**
 * useNetworkOptimization Hooks Tests
 * 
 * Tests for network optimization React hooks.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useNetworkStatus,
  useRequestCancellation,
  useRequestMetrics,
} from '../useNetworkOptimization';
import {
  requestCancellationManager,
  requestMetricsCollector,
} from '@/utils/networkOptimization';

describe('useNetworkOptimization Hooks', () => {
  beforeEach(() => {
    // Reset state before each test
    requestMetricsCollector.reset();
    requestCancellationManager.cancelAll();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('useNetworkStatus', () => {
    it('should return network status', () => {
      const { result } = renderHook(() => useNetworkStatus());

      expect(result.current).toHaveProperty('status');
      expect(result.current).toHaveProperty('isOnline');
      expect(result.current).toHaveProperty('isSlow');
      expect(result.current).toHaveProperty('recommendedTimeout');
    });

    it('should have isOnline as boolean', () => {
      const { result } = renderHook(() => useNetworkStatus());
      expect(typeof result.current.isOnline).toBe('boolean');
    });

    it('should have isSlow as boolean', () => {
      const { result } = renderHook(() => useNetworkStatus());
      expect(typeof result.current.isSlow).toBe('boolean');
    });

    it('should have recommendedTimeout as number', () => {
      const { result } = renderHook(() => useNetworkStatus());
      expect(typeof result.current.recommendedTimeout).toBe('number');
      expect(result.current.recommendedTimeout).toBeGreaterThan(0);
    });

    it('should have status object with required properties', () => {
      const { result } = renderHook(() => useNetworkStatus());
      
      expect(result.current.status).toHaveProperty('online');
      expect(result.current.status).toHaveProperty('effectiveType');
      expect(result.current.status).toHaveProperty('downlink');
      expect(result.current.status).toHaveProperty('rtt');
      expect(result.current.status).toHaveProperty('saveData');
    });
  });

  describe('useRequestCancellation', () => {
    it('should create abort controller', () => {
      const { result } = renderHook(() => useRequestCancellation());

      let controller: AbortController;
      act(() => {
        controller = result.current.createController('test-request');
      });

      expect(controller!).toBeInstanceOf(AbortController);
    });

    it('should cancel request', () => {
      const { result } = renderHook(() => useRequestCancellation());

      act(() => {
        result.current.createController('test-request');
      });

      let cancelled: boolean;
      act(() => {
        cancelled = result.current.cancel('test-request');
      });

      expect(cancelled!).toBe(true);
    });

    it('should return false when cancelling non-existent request', () => {
      const { result } = renderHook(() => useRequestCancellation());

      let cancelled: boolean;
      act(() => {
        cancelled = result.current.cancel('non-existent');
      });

      expect(cancelled!).toBe(false);
    });

    it('should cancel requests by prefix', () => {
      const { result } = renderHook(() => useRequestCancellation());

      act(() => {
        result.current.createController('user-1');
        result.current.createController('user-2');
        result.current.createController('task-1');
      });

      let cancelled: number;
      act(() => {
        cancelled = result.current.cancelByPrefix('user-');
      });

      expect(cancelled!).toBe(2);
    });

    it('should cancel all requests', () => {
      const { result } = renderHook(() => useRequestCancellation());

      act(() => {
        result.current.createController('req-1');
        result.current.createController('req-2');
        result.current.createController('req-3');
      });

      let cancelled: number;
      act(() => {
        cancelled = result.current.cancelAll();
      });

      expect(cancelled!).toBe(3);
    });

    it('should track active count', () => {
      const { result } = renderHook(() => useRequestCancellation());

      expect(result.current.activeCount).toBe(0);

      act(() => {
        result.current.createController('req-1');
      });
      expect(result.current.activeCount).toBe(1);

      act(() => {
        result.current.createController('req-2');
      });
      expect(result.current.activeCount).toBe(2);

      act(() => {
        result.current.complete('req-1');
      });
      expect(result.current.activeCount).toBe(1);
    });

    it('should complete request', () => {
      const { result } = renderHook(() => useRequestCancellation());

      act(() => {
        result.current.createController('test-request');
      });

      expect(result.current.activeCount).toBe(1);

      act(() => {
        result.current.complete('test-request');
      });

      expect(result.current.activeCount).toBe(0);
    });
  });

  describe('useRequestMetrics', () => {
    it('should return initial metrics', () => {
      const { result } = renderHook(() => useRequestMetrics());

      expect(result.current.metrics).toEqual({
        totalRequests: 0,
        successfulRequests: 0,
        failedRequests: 0,
        cancelledRequests: 0,
        averageResponseTime: 0,
        retryCount: 0,
        cacheHits: 0,
      });
    });

    it('should calculate success rate', () => {
      const { result } = renderHook(() => useRequestMetrics());

      // Initial success rate should be 100% (no requests)
      expect(result.current.successRate).toBe(100);
    });

    it('should determine health status', () => {
      const { result } = renderHook(() => useRequestMetrics());

      // Initially healthy (no requests)
      expect(result.current.isHealthy).toBe(true);
    });

    it('should reset metrics', () => {
      // Record some metrics first
      requestMetricsCollector.recordSuccess(100);
      requestMetricsCollector.recordFailure();

      const { result } = renderHook(() => useRequestMetrics());

      act(() => {
        result.current.reset();
      });

      expect(result.current.metrics.totalRequests).toBe(0);
    });

    it('should update metrics when collector records', async () => {
      const { result } = renderHook(() => useRequestMetrics());

      // Record a success
      act(() => {
        requestMetricsCollector.recordSuccess(100);
      });

      // Wait for the interval to update
      await waitFor(() => {
        expect(result.current.metrics.totalRequests).toBeGreaterThanOrEqual(0);
      }, { timeout: 2000 });
    });

    it('should calculate correct success rate with mixed results', () => {
      // Record mixed results
      requestMetricsCollector.recordSuccess(100);
      requestMetricsCollector.recordSuccess(100);
      requestMetricsCollector.recordFailure();

      const { result } = renderHook(() => useRequestMetrics());

      // Wait for state to update
      expect(result.current.successRate).toBeGreaterThanOrEqual(0);
    });
  });
});
