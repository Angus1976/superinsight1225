/**
 * Network Request Optimization Utilities
 * 
 * Provides advanced network optimization features including:
 * - Request batching for efficient API calls
 * - Retry logic with exponential backoff
 * - Request prioritization queue
 * - Network status detection and adaptive loading
 * - Request cancellation support
 * - Connection pooling simulation
 */

import type { AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';

// ============================================
// Constants and Configuration
// ============================================

/** Maximum concurrent requests */
export const MAX_CONCURRENT_REQUESTS = 6;

/** Default retry attempts */
export const DEFAULT_RETRY_ATTEMPTS = 3;

/** Base delay for exponential backoff (ms) */
export const BASE_RETRY_DELAY = 1000;

/** Maximum retry delay (ms) */
export const MAX_RETRY_DELAY = 30000;

/** Request timeout for slow networks (ms) */
export const SLOW_NETWORK_TIMEOUT = 10000;

/** Request timeout for fast networks (ms) */
export const FAST_NETWORK_TIMEOUT = 5000;

// ============================================
// Types and Interfaces
// ============================================

export type RequestPriority = 'critical' | 'high' | 'normal' | 'low' | 'background';

export interface QueuedRequest<T = unknown> {
  id: string;
  config: AxiosRequestConfig;
  priority: RequestPriority;
  timestamp: number;
  retryCount: number;
  maxRetries: number;
  resolve: (value: AxiosResponse<T>) => void;
  reject: (error: Error) => void;
  abortController?: AbortController;
}

export interface NetworkStatus {
  online: boolean;
  effectiveType: 'slow-2g' | '2g' | '3g' | '4g' | 'unknown';
  downlink: number;
  rtt: number;
  saveData: boolean;
}

export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  retryCondition?: (error: AxiosError) => boolean;
}

export interface BatchRequestConfig<T> {
  requests: Array<{
    key: string;
    config: AxiosRequestConfig;
    priority?: RequestPriority;
  }>;
  maxConcurrent?: number;
  stopOnError?: boolean;
  onProgress?: (completed: number, total: number) => void;
}

export interface BatchRequestResult<T> {
  key: string;
  success: boolean;
  data?: T;
  error?: Error;
  duration: number;
}

// ============================================
// Network Status Detection
// ============================================

/**
 * Get current network status
 */
export function getNetworkStatus(): NetworkStatus {
  const defaultStatus: NetworkStatus = {
    online: navigator.onLine,
    effectiveType: 'unknown',
    downlink: 10,
    rtt: 50,
    saveData: false,
  };

  if ('connection' in navigator) {
    const connection = (navigator as Navigator & {
      connection: {
        effectiveType: string;
        downlink: number;
        rtt: number;
        saveData: boolean;
      };
    }).connection;

    return {
      online: navigator.onLine,
      effectiveType: connection.effectiveType as NetworkStatus['effectiveType'],
      downlink: connection.downlink,
      rtt: connection.rtt,
      saveData: connection.saveData,
    };
  }

  return defaultStatus;
}

/**
 * Check if network is slow
 */
export function isSlowNetwork(): boolean {
  const status = getNetworkStatus();
  return (
    status.effectiveType === 'slow-2g' ||
    status.effectiveType === '2g' ||
    status.rtt > 500 ||
    status.downlink < 1
  );
}

/**
 * Get adaptive timeout based on network conditions
 */
export function getAdaptiveTimeout(): number {
  return isSlowNetwork() ? SLOW_NETWORK_TIMEOUT : FAST_NETWORK_TIMEOUT;
}

// ============================================
// Network Status Observer
// ============================================

type NetworkStatusCallback = (status: NetworkStatus) => void;

class NetworkStatusObserver {
  private callbacks: Set<NetworkStatusCallback> = new Set();
  private currentStatus: NetworkStatus;

  constructor() {
    this.currentStatus = getNetworkStatus();
    this.setupListeners();
  }

  private setupListeners(): void {
    // Online/offline events
    window.addEventListener('online', () => this.updateStatus());
    window.addEventListener('offline', () => this.updateStatus());

    // Connection change events
    if ('connection' in navigator) {
      const connection = (navigator as Navigator & {
        connection: {
          addEventListener: (type: string, listener: () => void) => void;
        };
      }).connection;
      connection.addEventListener('change', () => this.updateStatus());
    }
  }

  private updateStatus(): void {
    this.currentStatus = getNetworkStatus();
    this.callbacks.forEach(callback => callback(this.currentStatus));
  }

  subscribe(callback: NetworkStatusCallback): () => void {
    this.callbacks.add(callback);
    // Immediately call with current status
    callback(this.currentStatus);
    return () => this.callbacks.delete(callback);
  }

  getStatus(): NetworkStatus {
    return this.currentStatus;
  }
}

export const networkStatusObserver = new NetworkStatusObserver();

// ============================================
// Retry Logic with Exponential Backoff
// ============================================

/**
 * Calculate delay for exponential backoff
 */
export function calculateBackoffDelay(
  attempt: number,
  baseDelay: number = BASE_RETRY_DELAY,
  maxDelay: number = MAX_RETRY_DELAY
): number {
  // Exponential backoff with jitter
  const exponentialDelay = baseDelay * Math.pow(2, attempt);
  const jitter = Math.random() * 0.3 * exponentialDelay; // 0-30% jitter
  return Math.min(exponentialDelay + jitter, maxDelay);
}

/**
 * Default retry condition - retry on network errors and 5xx responses
 */
export function defaultRetryCondition(error: AxiosError): boolean {
  // Retry on network errors
  if (!error.response) {
    return true;
  }

  // Retry on 5xx server errors
  const status = error.response.status;
  if (status >= 500 && status < 600) {
    return true;
  }

  // Retry on 429 Too Many Requests
  if (status === 429) {
    return true;
  }

  // Don't retry on client errors (4xx except 429)
  return false;
}

/**
 * Execute request with retry logic
 */
export async function executeWithRetry<T>(
  requestFn: () => Promise<AxiosResponse<T>>,
  config: Partial<RetryConfig> = {}
): Promise<AxiosResponse<T>> {
  const {
    maxRetries = DEFAULT_RETRY_ATTEMPTS,
    baseDelay = BASE_RETRY_DELAY,
    maxDelay = MAX_RETRY_DELAY,
    retryCondition = defaultRetryCondition,
  } = config;

  let lastError: AxiosError | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await requestFn();
    } catch (error) {
      lastError = error as AxiosError;

      // Check if we should retry
      if (attempt < maxRetries && retryCondition(lastError)) {
        const delay = calculateBackoffDelay(attempt, baseDelay, maxDelay);
        
        if (import.meta.env.DEV) {
          console.log(
            `[Network] Retry attempt ${attempt + 1}/${maxRetries} after ${Math.round(delay)}ms`
          );
        }

        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        throw lastError;
      }
    }
  }

  throw lastError;
}

// ============================================
// Request Priority Queue
// ============================================

const PRIORITY_WEIGHTS: Record<RequestPriority, number> = {
  critical: 5,
  high: 4,
  normal: 3,
  low: 2,
  background: 1,
};

class RequestPriorityQueue {
  private queue: QueuedRequest[] = [];
  private activeRequests = 0;
  private maxConcurrent: number;
  private requestExecutor: (config: AxiosRequestConfig) => Promise<AxiosResponse>;

  constructor(
    executor: (config: AxiosRequestConfig) => Promise<AxiosResponse>,
    maxConcurrent: number = MAX_CONCURRENT_REQUESTS
  ) {
    this.requestExecutor = executor;
    this.maxConcurrent = maxConcurrent;
  }

  /**
   * Add request to queue
   */
  enqueue<T>(
    config: AxiosRequestConfig,
    priority: RequestPriority = 'normal',
    maxRetries: number = DEFAULT_RETRY_ATTEMPTS
  ): Promise<AxiosResponse<T>> {
    return new Promise((resolve, reject) => {
      const abortController = new AbortController();
      
      const request: QueuedRequest<T> = {
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        config: {
          ...config,
          signal: abortController.signal,
        },
        priority,
        timestamp: Date.now(),
        retryCount: 0,
        maxRetries,
        resolve: resolve as (value: AxiosResponse<unknown>) => void,
        reject,
        abortController,
      };

      this.queue.push(request);
      this.sortQueue();
      this.processQueue();
    });
  }

  /**
   * Sort queue by priority and timestamp
   */
  private sortQueue(): void {
    this.queue.sort((a, b) => {
      const priorityDiff = PRIORITY_WEIGHTS[b.priority] - PRIORITY_WEIGHTS[a.priority];
      if (priorityDiff !== 0) return priorityDiff;
      return a.timestamp - b.timestamp; // FIFO for same priority
    });
  }

  /**
   * Process queued requests
   */
  private async processQueue(): Promise<void> {
    while (this.queue.length > 0 && this.activeRequests < this.maxConcurrent) {
      const request = this.queue.shift();
      if (!request) continue;

      this.activeRequests++;
      this.executeRequest(request).finally(() => {
        this.activeRequests--;
        this.processQueue();
      });
    }
  }

  /**
   * Execute a single request with retry logic
   */
  private async executeRequest(request: QueuedRequest): Promise<void> {
    try {
      const response = await executeWithRetry(
        () => this.requestExecutor(request.config),
        { maxRetries: request.maxRetries - request.retryCount }
      );
      request.resolve(response);
    } catch (error) {
      request.reject(error as Error);
    }
  }

  /**
   * Cancel a specific request
   */
  cancel(requestId: string): boolean {
    const index = this.queue.findIndex(r => r.id === requestId);
    if (index !== -1) {
      const request = this.queue[index];
      request.abortController?.abort();
      request.reject(new Error('Request cancelled'));
      this.queue.splice(index, 1);
      return true;
    }
    return false;
  }

  /**
   * Cancel all requests with a specific priority
   */
  cancelByPriority(priority: RequestPriority): number {
    let cancelled = 0;
    this.queue = this.queue.filter(request => {
      if (request.priority === priority) {
        request.abortController?.abort();
        request.reject(new Error('Request cancelled'));
        cancelled++;
        return false;
      }
      return true;
    });
    return cancelled;
  }

  /**
   * Cancel all pending requests
   */
  cancelAll(): number {
    const count = this.queue.length;
    this.queue.forEach(request => {
      request.abortController?.abort();
      request.reject(new Error('Request cancelled'));
    });
    this.queue = [];
    return count;
  }

  /**
   * Get queue statistics
   */
  getStats(): {
    queueLength: number;
    activeRequests: number;
    maxConcurrent: number;
    byPriority: Record<RequestPriority, number>;
  } {
    const byPriority: Record<RequestPriority, number> = {
      critical: 0,
      high: 0,
      normal: 0,
      low: 0,
      background: 0,
    };

    this.queue.forEach(request => {
      byPriority[request.priority]++;
    });

    return {
      queueLength: this.queue.length,
      activeRequests: this.activeRequests,
      maxConcurrent: this.maxConcurrent,
      byPriority,
    };
  }
}

// Factory function to create queue with custom executor
export function createRequestQueue(
  executor: (config: AxiosRequestConfig) => Promise<AxiosResponse>,
  maxConcurrent?: number
): RequestPriorityQueue {
  return new RequestPriorityQueue(executor, maxConcurrent);
}

// ============================================
// Request Batching
// ============================================

/**
 * Execute multiple requests in batches with concurrency control
 */
export async function batchRequests<T>(
  executor: (config: AxiosRequestConfig) => Promise<AxiosResponse<T>>,
  config: BatchRequestConfig<T>
): Promise<BatchRequestResult<T>[]> {
  const {
    requests,
    maxConcurrent = MAX_CONCURRENT_REQUESTS,
    stopOnError = false,
    onProgress,
  } = config;

  const results: BatchRequestResult<T>[] = [];
  let completed = 0;

  // Process in batches
  for (let i = 0; i < requests.length; i += maxConcurrent) {
    const batch = requests.slice(i, i + maxConcurrent);
    
    const batchPromises = batch.map(async (req) => {
      const startTime = performance.now();
      
      try {
        const response = await executor(req.config);
        const duration = performance.now() - startTime;
        
        completed++;
        onProgress?.(completed, requests.length);
        
        return {
          key: req.key,
          success: true,
          data: response.data,
          duration,
        } as BatchRequestResult<T>;
      } catch (error) {
        const duration = performance.now() - startTime;
        
        completed++;
        onProgress?.(completed, requests.length);
        
        if (stopOnError) {
          throw error;
        }
        
        return {
          key: req.key,
          success: false,
          error: error as Error,
          duration,
        } as BatchRequestResult<T>;
      }
    });

    const batchResults = await Promise.all(batchPromises);
    results.push(...batchResults);
  }

  return results;
}

// ============================================
// Request Cancellation Manager
// ============================================

class RequestCancellationManager {
  private controllers: Map<string, AbortController> = new Map();

  /**
   * Create a new abort controller for a request
   */
  create(requestId: string): AbortController {
    // Cancel existing request with same ID
    this.cancel(requestId);
    
    const controller = new AbortController();
    this.controllers.set(requestId, controller);
    return controller;
  }

  /**
   * Get abort signal for a request
   */
  getSignal(requestId: string): AbortSignal | undefined {
    return this.controllers.get(requestId)?.signal;
  }

  /**
   * Cancel a specific request
   */
  cancel(requestId: string): boolean {
    const controller = this.controllers.get(requestId);
    if (controller) {
      controller.abort();
      this.controllers.delete(requestId);
      return true;
    }
    return false;
  }

  /**
   * Cancel multiple requests by prefix
   */
  cancelByPrefix(prefix: string): number {
    let cancelled = 0;
    for (const [id, controller] of this.controllers.entries()) {
      if (id.startsWith(prefix)) {
        controller.abort();
        this.controllers.delete(id);
        cancelled++;
      }
    }
    return cancelled;
  }

  /**
   * Cancel all requests
   */
  cancelAll(): number {
    const count = this.controllers.size;
    for (const controller of this.controllers.values()) {
      controller.abort();
    }
    this.controllers.clear();
    return count;
  }

  /**
   * Remove completed request
   */
  complete(requestId: string): void {
    this.controllers.delete(requestId);
  }

  /**
   * Get active request count
   */
  getActiveCount(): number {
    return this.controllers.size;
  }
}

export const requestCancellationManager = new RequestCancellationManager();

// ============================================
// Adaptive Request Configuration
// ============================================

/**
 * Create request config adapted to network conditions
 */
export function createAdaptiveRequestConfig(
  baseConfig: AxiosRequestConfig,
  options?: {
    priority?: RequestPriority;
    enableCompression?: boolean;
  }
): AxiosRequestConfig {
  const networkStatus = getNetworkStatus();
  const { priority = 'normal', enableCompression = true } = options || {};

  const adaptedConfig: AxiosRequestConfig = {
    ...baseConfig,
    timeout: getAdaptiveTimeout(),
    headers: {
      ...baseConfig.headers,
      'X-Request-Priority': priority,
    },
  };

  // Enable compression for slow networks
  if (enableCompression && isSlowNetwork()) {
    adaptedConfig.headers = {
      ...adaptedConfig.headers,
      'Accept-Encoding': 'gzip, deflate, br',
    };
  }

  // Reduce payload for save-data mode
  if (networkStatus.saveData) {
    adaptedConfig.headers = {
      ...adaptedConfig.headers,
      'Save-Data': 'on',
    };
  }

  return adaptedConfig;
}

// ============================================
// Connection Keep-Alive Management
// ============================================

/**
 * Preflight request to warm up connection
 */
export async function warmupConnection(
  baseUrl: string,
  executor: (config: AxiosRequestConfig) => Promise<AxiosResponse>
): Promise<boolean> {
  try {
    await executor({
      method: 'HEAD',
      url: `${baseUrl}/health`,
      timeout: 5000,
    });
    return true;
  } catch {
    return false;
  }
}

// ============================================
// Request Metrics Collection
// ============================================

export interface RequestMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  cancelledRequests: number;
  averageResponseTime: number;
  retryCount: number;
  cacheHits: number;
}

class RequestMetricsCollector {
  private metrics: RequestMetrics = {
    totalRequests: 0,
    successfulRequests: 0,
    failedRequests: 0,
    cancelledRequests: 0,
    averageResponseTime: 0,
    retryCount: 0,
    cacheHits: 0,
  };
  private responseTimes: number[] = [];
  private maxSamples = 1000;

  recordSuccess(responseTime: number): void {
    this.metrics.totalRequests++;
    this.metrics.successfulRequests++;
    this.addResponseTime(responseTime);
  }

  recordFailure(): void {
    this.metrics.totalRequests++;
    this.metrics.failedRequests++;
  }

  recordCancellation(): void {
    this.metrics.totalRequests++;
    this.metrics.cancelledRequests++;
  }

  recordRetry(): void {
    this.metrics.retryCount++;
  }

  recordCacheHit(): void {
    this.metrics.cacheHits++;
  }

  private addResponseTime(time: number): void {
    this.responseTimes.push(time);
    if (this.responseTimes.length > this.maxSamples) {
      this.responseTimes.shift();
    }
    this.updateAverageResponseTime();
  }

  private updateAverageResponseTime(): void {
    if (this.responseTimes.length === 0) {
      this.metrics.averageResponseTime = 0;
      return;
    }
    const sum = this.responseTimes.reduce((a, b) => a + b, 0);
    this.metrics.averageResponseTime = Math.round(sum / this.responseTimes.length);
  }

  getMetrics(): RequestMetrics {
    return { ...this.metrics };
  }

  reset(): void {
    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      cancelledRequests: 0,
      averageResponseTime: 0,
      retryCount: 0,
      cacheHits: 0,
    };
    this.responseTimes = [];
  }
}

export const requestMetricsCollector = new RequestMetricsCollector();

// ============================================
// Initialize Network Optimizations
// ============================================

export function initNetworkOptimizations(): void {
  // Log network status changes in development
  if (import.meta.env.DEV) {
    networkStatusObserver.subscribe((status) => {
      console.log('[Network] Status changed:', status);
    });
  }

  // Periodic metrics logging in development
  if (import.meta.env.DEV) {
    setInterval(() => {
      const metrics = requestMetricsCollector.getMetrics();
      if (metrics.totalRequests > 0) {
        console.log('[Network] Request metrics:', metrics);
      }
    }, 60000);
  }
}
