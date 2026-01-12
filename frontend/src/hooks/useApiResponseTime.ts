/**
 * useApiResponseTime Hook
 * 
 * Tracks and enforces API response time to ensure < 500ms target.
 * Provides real-time feedback on API performance.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import {
  apiPerformanceMonitor,
  requestCache,
  API_RESPONSE_BUDGET,
  API_WARNING_THRESHOLD,
  type ApiPerformanceMetrics,
} from '@/utils/apiPerformance';

export interface UseApiResponseTimeResult {
  /** Latest API metrics */
  latestMetrics: ApiPerformanceMetrics | null;
  /** All recorded metrics */
  allMetrics: ApiPerformanceMetrics[];
  /** Performance summary */
  summary: {
    totalCalls: number;
    withinBudget: number;
    exceedingBudget: number;
    averageResponseTime: number;
    cacheHitRate: number;
    slowestEndpoints: Array<{ endpoint: string; avgTime: number }>;
  };
  /** Whether API performance is healthy */
  isHealthy: boolean;
  /** Clear all metrics */
  clearMetrics: () => void;
  /** Clear cache */
  clearCache: () => void;
  /** Invalidate specific cache entry */
  invalidateCache: (pattern: string | RegExp) => void;
}

/**
 * Hook to monitor API response times
 */
export function useApiResponseTime(): UseApiResponseTimeResult {
  const [latestMetrics, setLatestMetrics] = useState<ApiPerformanceMetrics | null>(null);
  const [allMetrics, setAllMetrics] = useState<ApiPerformanceMetrics[]>([]);
  const [summary, setSummary] = useState(apiPerformanceMonitor.getSummary());

  useEffect(() => {
    // Subscribe to metric updates
    const unsubscribe = apiPerformanceMonitor.subscribe((metrics) => {
      setLatestMetrics(metrics);
      setAllMetrics(apiPerformanceMonitor.getMetrics());
      setSummary(apiPerformanceMonitor.getSummary());
    });

    // Get initial metrics
    setAllMetrics(apiPerformanceMonitor.getMetrics());
    setSummary(apiPerformanceMonitor.getSummary());

    return unsubscribe;
  }, []);

  const clearMetrics = useCallback(() => {
    apiPerformanceMonitor.clear();
    setLatestMetrics(null);
    setAllMetrics([]);
    setSummary(apiPerformanceMonitor.getSummary());
  }, []);

  const clearCache = useCallback(() => {
    requestCache.clear();
  }, []);

  const invalidateCache = useCallback((pattern: string | RegExp) => {
    requestCache.invalidatePattern(pattern);
  }, []);

  // Consider healthy if > 90% of calls are within budget
  const isHealthy = summary.totalCalls === 0 || 
    (summary.withinBudget / summary.totalCalls) >= 0.9;

  return {
    latestMetrics,
    allMetrics,
    summary,
    isHealthy,
    clearMetrics,
    clearCache,
    invalidateCache,
  };
}

/**
 * Hook to track a specific API endpoint's performance
 */
export function useEndpointPerformance(endpoint: string): {
  metrics: ApiPerformanceMetrics[];
  averageResponseTime: number;
  isWithinBudget: boolean;
  callCount: number;
} {
  const [metrics, setMetrics] = useState<ApiPerformanceMetrics[]>([]);

  useEffect(() => {
    const unsubscribe = apiPerformanceMonitor.subscribe((newMetric) => {
      if (newMetric.endpoint.includes(endpoint)) {
        setMetrics(prev => [...prev.slice(-99), newMetric]);
      }
    });

    // Get existing metrics for this endpoint
    const existingMetrics = apiPerformanceMonitor.getMetrics()
      .filter(m => m.endpoint.includes(endpoint));
    setMetrics(existingMetrics);

    return unsubscribe;
  }, [endpoint]);

  const averageResponseTime = metrics.length > 0
    ? Math.round(metrics.reduce((sum, m) => sum + m.responseTime, 0) / metrics.length)
    : 0;

  const withinBudgetCount = metrics.filter(m => m.isWithinBudget).length;
  const isWithinBudget = metrics.length === 0 || withinBudgetCount === metrics.length;

  return {
    metrics,
    averageResponseTime,
    isWithinBudget,
    callCount: metrics.length,
  };
}

/**
 * Hook to measure a single API call
 */
export function useApiCallMeasurement(): {
  measure: <T>(
    name: string,
    apiCall: () => Promise<T>
  ) => Promise<{ data: T; responseTime: number; isWithinBudget: boolean }>;
  lastMeasurement: { name: string; responseTime: number; isWithinBudget: boolean } | null;
} {
  const [lastMeasurement, setLastMeasurement] = useState<{
    name: string;
    responseTime: number;
    isWithinBudget: boolean;
  } | null>(null);

  const measure = useCallback(async <T,>(
    name: string,
    apiCall: () => Promise<T>
  ): Promise<{ data: T; responseTime: number; isWithinBudget: boolean }> => {
    const startTime = performance.now();
    
    try {
      const data = await apiCall();
      const responseTime = Math.round(performance.now() - startTime);
      const isWithinBudget = responseTime <= API_RESPONSE_BUDGET;

      const measurement = { name, responseTime, isWithinBudget };
      setLastMeasurement(measurement);

      // Record to global monitor
      apiPerformanceMonitor.record({
        endpoint: name,
        method: 'GET',
        responseTime,
        isWithinBudget,
        timestamp: Date.now(),
        cached: false,
      });

      return { data, responseTime, isWithinBudget };
    } catch (error) {
      const responseTime = Math.round(performance.now() - startTime);
      
      apiPerformanceMonitor.record({
        endpoint: name,
        method: 'GET',
        responseTime,
        isWithinBudget: false,
        timestamp: Date.now(),
        cached: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      throw error;
    }
  }, []);

  return { measure, lastMeasurement };
}

/**
 * Hook to get API performance alerts
 */
export function useApiPerformanceAlerts(): {
  alerts: Array<{
    type: 'warning' | 'error';
    message: string;
    endpoint: string;
    timestamp: number;
  }>;
  clearAlerts: () => void;
} {
  const [alerts, setAlerts] = useState<Array<{
    type: 'warning' | 'error';
    message: string;
    endpoint: string;
    timestamp: number;
  }>>([]);

  useEffect(() => {
    const unsubscribe = apiPerformanceMonitor.subscribe((metrics) => {
      if (!metrics.isWithinBudget) {
        setAlerts(prev => [
          ...prev.slice(-49),
          {
            type: 'error',
            message: `API call to ${metrics.endpoint} exceeded budget: ${metrics.responseTime}ms > ${API_RESPONSE_BUDGET}ms`,
            endpoint: metrics.endpoint,
            timestamp: metrics.timestamp,
          },
        ]);
      } else if (metrics.responseTime > API_WARNING_THRESHOLD) {
        setAlerts(prev => [
          ...prev.slice(-49),
          {
            type: 'warning',
            message: `API call to ${metrics.endpoint} approaching budget: ${metrics.responseTime}ms`,
            endpoint: metrics.endpoint,
            timestamp: metrics.timestamp,
          },
        ]);
      }
    });

    return unsubscribe;
  }, []);

  const clearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  return { alerts, clearAlerts };
}

/**
 * Hook to prefetch API data
 */
export function useApiPrefetch(): {
  prefetch: (
    endpoint: string,
    fetchFn: () => Promise<unknown>,
    options?: { ttl?: number; priority?: 'high' | 'normal' | 'low' }
  ) => void;
  isPrefetching: boolean;
} {
  const [isPrefetching, setIsPrefetching] = useState(false);
  const prefetchingRef = useRef(new Set<string>());

  const prefetch = useCallback((
    endpoint: string,
    fetchFn: () => Promise<unknown>,
    options?: { ttl?: number; priority?: 'high' | 'normal' | 'low' }
  ) => {
    const { priority = 'low' } = options || {};

    // Avoid duplicate prefetches
    if (prefetchingRef.current.has(endpoint)) return;

    prefetchingRef.current.add(endpoint);
    setIsPrefetching(true);

    const doPrefetch = async () => {
      try {
        await fetchFn();
      } catch {
        // Silently fail - prefetch is optional
      } finally {
        prefetchingRef.current.delete(endpoint);
        setIsPrefetching(prefetchingRef.current.size > 0);
      }
    };

    if (priority === 'high') {
      doPrefetch();
    } else if ('requestIdleCallback' in window) {
      requestIdleCallback(() => doPrefetch(), { 
        timeout: priority === 'normal' ? 1000 : 5000 
      });
    } else {
      setTimeout(doPrefetch, priority === 'normal' ? 100 : 1000);
    }
  }, []);

  return { prefetch, isPrefetching };
}

export { API_RESPONSE_BUDGET, API_WARNING_THRESHOLD };
