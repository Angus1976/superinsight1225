/**
 * API Performance Optimization Utilities
 * 
 * Provides utilities for optimizing API response time to achieve < 500ms target.
 * Includes request caching, deduplication, timeout management, and performance monitoring.
 */

import type { AxiosRequestConfig, AxiosResponse } from 'axios';

// API response time budget in milliseconds
export const API_RESPONSE_BUDGET = 500;

// Warning threshold (80% of budget)
export const API_WARNING_THRESHOLD = 400;

// Cache configuration
export const DEFAULT_CACHE_TTL = 30000; // 30 seconds
export const MAX_CACHE_SIZE = 100;

/**
 * API performance metrics interface
 */
export interface ApiPerformanceMetrics {
  endpoint: string;
  method: string;
  responseTime: number;
  isWithinBudget: boolean;
  timestamp: number;
  cached: boolean;
  status?: number;
  error?: string;
}

/**
 * Cache entry interface
 */
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
  hits: number;
}

/**
 * Pending request interface for deduplication
 */
interface PendingRequest<T> {
  promise: Promise<T>;
  timestamp: number;
}

/**
 * API Performance Monitor class
 * Tracks and reports API response times
 */
class ApiPerformanceMonitor {
  private metrics: ApiPerformanceMetrics[] = [];
  private maxMetrics = 1000;
  private subscribers: Set<(metrics: ApiPerformanceMetrics) => void> = new Set();

  /**
   * Record an API call metric
   */
  record(metric: ApiPerformanceMetrics): void {
    this.metrics.push(metric);
    
    // Keep only recent metrics
    if (this.metrics.length > this.maxMetrics) {
      this.metrics = this.metrics.slice(-this.maxMetrics);
    }

    // Notify subscribers
    this.subscribers.forEach(callback => callback(metric));

    // Log in development
    if (import.meta.env.DEV) {
      this.logMetric(metric);
    }
  }

  /**
   * Log metric to console in development
   */
  private logMetric(metric: ApiPerformanceMetrics): void {
    const status = metric.isWithinBudget ? '✓' : '✗';
    const cacheStatus = metric.cached ? ' (cached)' : '';
    const color = metric.isWithinBudget 
      ? (metric.responseTime > API_WARNING_THRESHOLD ? 'orange' : 'green')
      : 'red';

    if (!metric.isWithinBudget) {
      console.warn(
        `%c[API] ${status} ${metric.method} ${metric.endpoint}: ${metric.responseTime}ms${cacheStatus}`,
        `color: ${color}; font-weight: bold;`
      );
    } else if (metric.responseTime > API_WARNING_THRESHOLD) {
      console.log(
        `%c[API] ${status} ${metric.method} ${metric.endpoint}: ${metric.responseTime}ms${cacheStatus}`,
        `color: ${color};`
      );
    }
  }

  /**
   * Subscribe to metric updates
   */
  subscribe(callback: (metrics: ApiPerformanceMetrics) => void): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  /**
   * Get all recorded metrics
   */
  getMetrics(): ApiPerformanceMetrics[] {
    return [...this.metrics];
  }

  /**
   * Get metrics summary
   */
  getSummary(): {
    totalCalls: number;
    withinBudget: number;
    exceedingBudget: number;
    averageResponseTime: number;
    cacheHitRate: number;
    slowestEndpoints: Array<{ endpoint: string; avgTime: number }>;
  } {
    if (this.metrics.length === 0) {
      return {
        totalCalls: 0,
        withinBudget: 0,
        exceedingBudget: 0,
        averageResponseTime: 0,
        cacheHitRate: 0,
        slowestEndpoints: [],
      };
    }

    const withinBudget = this.metrics.filter(m => m.isWithinBudget).length;
    const cachedCalls = this.metrics.filter(m => m.cached).length;
    const totalResponseTime = this.metrics.reduce((sum, m) => sum + m.responseTime, 0);

    // Group by endpoint for slowest analysis
    const endpointTimes = new Map<string, number[]>();
    this.metrics.forEach(m => {
      if (!endpointTimes.has(m.endpoint)) {
        endpointTimes.set(m.endpoint, []);
      }
      endpointTimes.get(m.endpoint)!.push(m.responseTime);
    });

    const endpointAverages = Array.from(endpointTimes.entries())
      .map(([endpoint, times]) => ({
        endpoint,
        avgTime: Math.round(times.reduce((a, b) => a + b, 0) / times.length),
      }))
      .sort((a, b) => b.avgTime - a.avgTime)
      .slice(0, 5);

    return {
      totalCalls: this.metrics.length,
      withinBudget,
      exceedingBudget: this.metrics.length - withinBudget,
      averageResponseTime: Math.round(totalResponseTime / this.metrics.length),
      cacheHitRate: Math.round((cachedCalls / this.metrics.length) * 100),
      slowestEndpoints: endpointAverages,
    };
  }

  /**
   * Clear all metrics
   */
  clear(): void {
    this.metrics = [];
  }
}

// Global performance monitor instance
export const apiPerformanceMonitor = new ApiPerformanceMonitor();

/**
 * Request Cache class
 * Caches API responses to reduce redundant requests
 */
class RequestCache {
  private cache = new Map<string, CacheEntry<unknown>>();
  private maxSize = MAX_CACHE_SIZE;

  /**
   * Generate cache key from request config
   */
  generateKey(config: AxiosRequestConfig): string {
    const { method = 'GET', url = '', params, data } = config;
    const paramsStr = params ? JSON.stringify(params) : '';
    const dataStr = data ? JSON.stringify(data) : '';
    return `${method.toUpperCase()}:${url}:${paramsStr}:${dataStr}`;
  }

  /**
   * Get cached response
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key) as CacheEntry<T> | undefined;
    
    if (!entry) return null;

    // Check if expired
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }

    // Update hit count
    entry.hits += 1;
    return entry.data;
  }

  /**
   * Set cached response
   */
  set<T>(key: string, data: T, ttl: number = DEFAULT_CACHE_TTL): void {
    // Evict oldest entries if cache is full
    if (this.cache.size >= this.maxSize) {
      const oldestKey = this.cache.keys().next().value;
      if (oldestKey) {
        this.cache.delete(oldestKey);
      }
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
      hits: 0,
    });
  }

  /**
   * Invalidate cache entry
   */
  invalidate(key: string): void {
    this.cache.delete(key);
  }

  /**
   * Invalidate cache entries matching a pattern
   */
  invalidatePattern(pattern: string | RegExp): void {
    const regex = typeof pattern === 'string' ? new RegExp(pattern) : pattern;
    
    for (const key of this.cache.keys()) {
      if (regex.test(key)) {
        this.cache.delete(key);
      }
    }
  }

  /**
   * Clear all cache
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Get cache statistics
   */
  getStats(): {
    size: number;
    maxSize: number;
    entries: Array<{ key: string; hits: number; age: number }>;
  } {
    const entries = Array.from(this.cache.entries()).map(([key, entry]) => ({
      key,
      hits: entry.hits,
      age: Date.now() - entry.timestamp,
    }));

    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      entries,
    };
  }
}

// Global request cache instance
export const requestCache = new RequestCache();

/**
 * Request Deduplicator class
 * Prevents duplicate concurrent requests to the same endpoint
 */
class RequestDeduplicator {
  private pendingRequests = new Map<string, PendingRequest<unknown>>();
  private requestTimeout = 30000; // 30 seconds max pending time

  /**
   * Get or create a pending request
   */
  async deduplicate<T>(
    key: string,
    requestFn: () => Promise<T>
  ): Promise<{ data: T; deduplicated: boolean }> {
    // Check for existing pending request
    const pending = this.pendingRequests.get(key) as PendingRequest<T> | undefined;
    
    if (pending && Date.now() - pending.timestamp < this.requestTimeout) {
      return { data: await pending.promise, deduplicated: true };
    }

    // Create new request
    const promise = requestFn();
    this.pendingRequests.set(key, { promise, timestamp: Date.now() });

    try {
      const data = await promise;
      return { data, deduplicated: false };
    } finally {
      // Clean up after request completes
      this.pendingRequests.delete(key);
    }
  }

  /**
   * Clear all pending requests
   */
  clear(): void {
    this.pendingRequests.clear();
  }

  /**
   * Get pending request count
   */
  getPendingCount(): number {
    return this.pendingRequests.size;
  }
}

// Global request deduplicator instance
export const requestDeduplicator = new RequestDeduplicator();

/**
 * Check if API response time is within budget
 */
export function checkApiResponseBudget(
  responseTime: number,
  budget: number = API_RESPONSE_BUDGET
): {
  passed: boolean;
  isWarning: boolean;
  responseTime: number;
  budget: number;
  usagePercent: number;
} {
  const usagePercent = (responseTime / budget) * 100;

  return {
    passed: responseTime <= budget,
    isWarning: responseTime > API_WARNING_THRESHOLD && responseTime <= budget,
    responseTime: Math.round(responseTime),
    budget,
    usagePercent: Math.round(usagePercent),
  };
}

/**
 * Create optimized request configuration
 */
export function createOptimizedRequestConfig(
  config: AxiosRequestConfig,
  options?: {
    timeout?: number;
    priority?: 'high' | 'normal' | 'low';
  }
): AxiosRequestConfig {
  const { timeout = API_RESPONSE_BUDGET, priority = 'normal' } = options || {};

  // Adjust timeout based on priority
  const adjustedTimeout = {
    high: Math.min(timeout, API_RESPONSE_BUDGET),
    normal: timeout,
    low: timeout * 2,
  }[priority];

  return {
    ...config,
    timeout: adjustedTimeout,
    headers: {
      ...config.headers,
      // Add priority hint header
      'X-Request-Priority': priority,
    },
  };
}

/**
 * Cacheable endpoints configuration
 * Define which endpoints should be cached and for how long
 */
export const CACHEABLE_ENDPOINTS: Record<string, { ttl: number; methods: string[] }> = {
  '/api/business-metrics/summary': { ttl: 60000, methods: ['GET'] },
  '/api/business-metrics/annotation-efficiency': { ttl: 30000, methods: ['GET'] },
  '/api/business-metrics/user-activity': { ttl: 30000, methods: ['GET'] },
  '/api/business-metrics/ai-models': { ttl: 60000, methods: ['GET'] },
  '/api/business-metrics/projects': { ttl: 30000, methods: ['GET'] },
  '/api/quality/dashboard/summary': { ttl: 30000, methods: ['GET'] },
  '/api/quality/stats': { ttl: 30000, methods: ['GET'] },
  '/api/tasks/stats': { ttl: 15000, methods: ['GET'] },
  '/api/security/stats': { ttl: 60000, methods: ['GET'] },
  '/api/workspaces/my': { ttl: 60000, methods: ['GET'] },
  '/auth/tenants': { ttl: 120000, methods: ['GET'] },
  '/system/status': { ttl: 10000, methods: ['GET'] },
};

/**
 * Check if endpoint is cacheable
 */
export function isCacheableEndpoint(
  url: string,
  method: string
): { cacheable: boolean; ttl: number } {
  // Normalize URL (remove query params for matching)
  const normalizedUrl = url.split('?')[0];
  
  for (const [pattern, config] of Object.entries(CACHEABLE_ENDPOINTS)) {
    if (normalizedUrl.includes(pattern) && config.methods.includes(method.toUpperCase())) {
      return { cacheable: true, ttl: config.ttl };
    }
  }

  return { cacheable: false, ttl: 0 };
}

/**
 * Measure API call performance
 */
export async function measureApiCall<T>(
  endpoint: string,
  method: string,
  requestFn: () => Promise<AxiosResponse<T>>,
  options?: {
    useCache?: boolean;
    useDeduplication?: boolean;
    cacheTtl?: number;
  }
): Promise<{ data: T; metrics: ApiPerformanceMetrics }> {
  const { useCache = true, useDeduplication = true, cacheTtl } = options || {};
  const startTime = performance.now();
  
  // Generate cache key
  const cacheKey = `${method.toUpperCase()}:${endpoint}`;
  
  // Check cache first
  if (useCache && method.toUpperCase() === 'GET') {
    const cached = requestCache.get<T>(cacheKey);
    if (cached !== null) {
      const responseTime = performance.now() - startTime;
      const metrics: ApiPerformanceMetrics = {
        endpoint,
        method: method.toUpperCase(),
        responseTime: Math.round(responseTime),
        isWithinBudget: true,
        timestamp: Date.now(),
        cached: true,
      };
      apiPerformanceMonitor.record(metrics);
      return { data: cached, metrics };
    }
  }

  try {
    let response: AxiosResponse<T>;
    let deduplicated = false;

    if (useDeduplication && method.toUpperCase() === 'GET') {
      const result = await requestDeduplicator.deduplicate(cacheKey, requestFn);
      response = { data: result.data } as AxiosResponse<T>;
      deduplicated = result.deduplicated;
    } else {
      response = await requestFn();
    }

    const responseTime = performance.now() - startTime;
    const budgetCheck = checkApiResponseBudget(responseTime);

    const metrics: ApiPerformanceMetrics = {
      endpoint,
      method: method.toUpperCase(),
      responseTime: Math.round(responseTime),
      isWithinBudget: budgetCheck.passed,
      timestamp: Date.now(),
      cached: deduplicated,
      status: response.status,
    };

    apiPerformanceMonitor.record(metrics);

    // Cache successful GET responses
    if (useCache && method.toUpperCase() === 'GET' && !deduplicated) {
      const { cacheable, ttl } = isCacheableEndpoint(endpoint, method);
      if (cacheable) {
        requestCache.set(cacheKey, response.data, cacheTtl || ttl);
      }
    }

    return { data: response.data, metrics };
  } catch (error) {
    const responseTime = performance.now() - startTime;
    
    const metrics: ApiPerformanceMetrics = {
      endpoint,
      method: method.toUpperCase(),
      responseTime: Math.round(responseTime),
      isWithinBudget: false,
      timestamp: Date.now(),
      cached: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };

    apiPerformanceMonitor.record(metrics);
    throw error;
  }
}

/**
 * Batch multiple API requests for efficiency
 */
export async function batchApiRequests<T>(
  requests: Array<{
    endpoint: string;
    method: string;
    requestFn: () => Promise<AxiosResponse<T>>;
  }>,
  options?: {
    maxConcurrent?: number;
    stopOnError?: boolean;
  }
): Promise<Array<{ data: T | null; error?: Error; metrics: ApiPerformanceMetrics }>> {
  const { maxConcurrent = 5, stopOnError = false } = options || {};
  const results: Array<{ data: T | null; error?: Error; metrics: ApiPerformanceMetrics }> = [];

  // Process in batches
  for (let i = 0; i < requests.length; i += maxConcurrent) {
    const batch = requests.slice(i, i + maxConcurrent);
    
    const batchResults = await Promise.all(
      batch.map(async (req) => {
        try {
          const result = await measureApiCall(req.endpoint, req.method, req.requestFn);
          return { data: result.data, metrics: result.metrics };
        } catch (error) {
          if (stopOnError) throw error;
          return {
            data: null,
            error: error instanceof Error ? error : new Error('Unknown error'),
            metrics: {
              endpoint: req.endpoint,
              method: req.method,
              responseTime: 0,
              isWithinBudget: false,
              timestamp: Date.now(),
              cached: false,
              error: error instanceof Error ? error.message : 'Unknown error',
            },
          };
        }
      })
    );

    results.push(...batchResults);
  }

  return results;
}

/**
 * Prefetch API data for anticipated user actions
 */
export function prefetchApiData(
  endpoint: string,
  requestFn: () => Promise<AxiosResponse<unknown>>,
  options?: { ttl?: number; priority?: 'high' | 'normal' | 'low' }
): void {
  const { ttl, priority = 'low' } = options || {};

  // Use requestIdleCallback for low priority prefetching
  const prefetch = async () => {
    try {
      await measureApiCall(endpoint, 'GET', requestFn, { cacheTtl: ttl });
    } catch {
      // Silently fail - prefetch is optional
    }
  };

  if (priority === 'high') {
    prefetch();
  } else if ('requestIdleCallback' in window) {
    requestIdleCallback(() => prefetch(), { timeout: priority === 'normal' ? 1000 : 5000 });
  } else {
    setTimeout(prefetch, priority === 'normal' ? 100 : 1000);
  }
}

/**
 * Initialize API performance optimizations
 */
export function initApiPerformanceOptimizations(): void {
  // Log summary periodically in development
  if (import.meta.env.DEV) {
    setInterval(() => {
      const summary = apiPerformanceMonitor.getSummary();
      if (summary.totalCalls > 0) {
        console.log('[API Performance Summary]', {
          totalCalls: summary.totalCalls,
          withinBudget: `${summary.withinBudget}/${summary.totalCalls}`,
          avgResponseTime: `${summary.averageResponseTime}ms`,
          cacheHitRate: `${summary.cacheHitRate}%`,
        });
      }
    }, 60000); // Every minute
  }
}
