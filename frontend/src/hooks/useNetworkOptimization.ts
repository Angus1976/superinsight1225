/**
 * useNetworkOptimization Hook
 * 
 * Provides React hooks for network optimization features including:
 * - Network status monitoring
 * - Adaptive request configuration
 * - Request cancellation
 * - Batch request execution
 * - Retry logic
 */

import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import type { AxiosRequestConfig, AxiosResponse } from 'axios';
import {
  networkStatusObserver,
  requestCancellationManager,
  requestMetricsCollector,
  batchRequests,
  executeWithRetry,
  createAdaptiveRequestConfig,
  isSlowNetwork,
  getAdaptiveTimeout,
  type NetworkStatus,
  type RequestPriority,
  type BatchRequestResult,
  type RetryConfig,
  type RequestMetrics,
} from '@/utils/networkOptimization';
import apiClient from '@/services/api/client';

// ============================================
// useNetworkStatus Hook
// ============================================

export interface UseNetworkStatusResult {
  /** Current network status */
  status: NetworkStatus;
  /** Whether the network is online */
  isOnline: boolean;
  /** Whether the network is slow */
  isSlow: boolean;
  /** Recommended timeout for requests */
  recommendedTimeout: number;
}

/**
 * Hook to monitor network status
 */
export function useNetworkStatus(): UseNetworkStatusResult {
  const [status, setStatus] = useState<NetworkStatus>(networkStatusObserver.getStatus());

  useEffect(() => {
    const unsubscribe = networkStatusObserver.subscribe(setStatus);
    return unsubscribe;
  }, []);

  return {
    status,
    isOnline: status.online,
    isSlow: isSlowNetwork(),
    recommendedTimeout: getAdaptiveTimeout(),
  };
}

// ============================================
// useRequestCancellation Hook
// ============================================

export interface UseRequestCancellationResult {
  /** Create abort controller for a request */
  createController: (requestId: string) => AbortController;
  /** Cancel a specific request */
  cancel: (requestId: string) => boolean;
  /** Cancel requests by prefix */
  cancelByPrefix: (prefix: string) => number;
  /** Cancel all requests */
  cancelAll: () => number;
  /** Mark request as complete */
  complete: (requestId: string) => void;
  /** Number of active requests */
  activeCount: number;
}

/**
 * Hook for managing request cancellation
 */
export function useRequestCancellation(): UseRequestCancellationResult {
  const [activeCount, setActiveCount] = useState(requestCancellationManager.getActiveCount());

  const updateCount = useCallback(() => {
    setActiveCount(requestCancellationManager.getActiveCount());
  }, []);

  const createController = useCallback((requestId: string) => {
    const controller = requestCancellationManager.create(requestId);
    updateCount();
    return controller;
  }, [updateCount]);

  const cancel = useCallback((requestId: string) => {
    const result = requestCancellationManager.cancel(requestId);
    updateCount();
    return result;
  }, [updateCount]);

  const cancelByPrefix = useCallback((prefix: string) => {
    const count = requestCancellationManager.cancelByPrefix(prefix);
    updateCount();
    return count;
  }, [updateCount]);

  const cancelAll = useCallback(() => {
    const count = requestCancellationManager.cancelAll();
    updateCount();
    return count;
  }, [updateCount]);

  const complete = useCallback((requestId: string) => {
    requestCancellationManager.complete(requestId);
    updateCount();
  }, [updateCount]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Don't cancel all on unmount - let other components manage their requests
    };
  }, []);

  return {
    createController,
    cancel,
    cancelByPrefix,
    cancelAll,
    complete,
    activeCount,
  };
}

// ============================================
// useCancellableRequest Hook
// ============================================

export interface UseCancellableRequestResult<T> {
  /** Execute the request */
  execute: () => Promise<T | null>;
  /** Cancel the current request */
  cancel: () => void;
  /** Whether request is in progress */
  isLoading: boolean;
  /** Request data */
  data: T | null;
  /** Request error */
  error: Error | null;
}

/**
 * Hook for making cancellable requests
 */
export function useCancellableRequest<T>(
  requestFn: (signal: AbortSignal) => Promise<T>,
  requestId: string
): UseCancellableRequestResult<T> {
  const [isLoading, setIsLoading] = useState(false);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const execute = useCallback(async () => {
    // Cancel any existing request
    abortControllerRef.current?.abort();
    
    // Create new controller
    abortControllerRef.current = requestCancellationManager.create(requestId);
    
    setIsLoading(true);
    setError(null);

    try {
      const result = await requestFn(abortControllerRef.current.signal);
      setData(result);
      requestCancellationManager.complete(requestId);
      return result;
    } catch (err) {
      if ((err as Error).name === 'AbortError' || (err as Error).name === 'CanceledError') {
        // Request was cancelled, don't update state
        return null;
      }
      setError(err as Error);
      requestCancellationManager.complete(requestId);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [requestFn, requestId]);

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort();
    requestCancellationManager.cancel(requestId);
    setIsLoading(false);
  }, [requestId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      requestCancellationManager.cancel(requestId);
    };
  }, [requestId]);

  return {
    execute,
    cancel,
    isLoading,
    data,
    error,
  };
}

// ============================================
// useBatchRequests Hook
// ============================================

export interface UseBatchRequestsResult<T> {
  /** Execute batch requests */
  execute: (
    requests: Array<{
      key: string;
      config: AxiosRequestConfig;
      priority?: RequestPriority;
    }>
  ) => Promise<BatchRequestResult<T>[]>;
  /** Whether batch is in progress */
  isLoading: boolean;
  /** Batch results */
  results: BatchRequestResult<T>[];
  /** Progress (0-100) */
  progress: number;
  /** Cancel batch */
  cancel: () => void;
}

/**
 * Hook for executing batch requests
 */
export function useBatchRequests<T>(
  options?: {
    maxConcurrent?: number;
    stopOnError?: boolean;
  }
): UseBatchRequestsResult<T> {
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<BatchRequestResult<T>[]>([]);
  const [progress, setProgress] = useState(0);
  const cancelledRef = useRef(false);

  const execute = useCallback(async (
    requests: Array<{
      key: string;
      config: AxiosRequestConfig;
      priority?: RequestPriority;
    }>
  ) => {
    cancelledRef.current = false;
    setIsLoading(true);
    setProgress(0);
    setResults([]);

    try {
      const batchResults = await batchRequests<T>(
        (config) => apiClient.request<T>(config),
        {
          requests,
          maxConcurrent: options?.maxConcurrent,
          stopOnError: options?.stopOnError,
          onProgress: (completed, total) => {
            if (!cancelledRef.current) {
              setProgress(Math.round((completed / total) * 100));
            }
          },
        }
      );

      if (!cancelledRef.current) {
        setResults(batchResults);
      }
      return batchResults;
    } finally {
      if (!cancelledRef.current) {
        setIsLoading(false);
      }
    }
  }, [options?.maxConcurrent, options?.stopOnError]);

  const cancel = useCallback(() => {
    cancelledRef.current = true;
    setIsLoading(false);
  }, []);

  return {
    execute,
    isLoading,
    results,
    progress,
    cancel,
  };
}

// ============================================
// useRetryRequest Hook
// ============================================

export interface UseRetryRequestResult<T> {
  /** Execute request with retry */
  execute: () => Promise<T | null>;
  /** Whether request is in progress */
  isLoading: boolean;
  /** Request data */
  data: T | null;
  /** Request error */
  error: Error | null;
  /** Current retry attempt */
  retryAttempt: number;
}

/**
 * Hook for making requests with automatic retry
 */
export function useRetryRequest<T>(
  requestFn: () => Promise<AxiosResponse<T>>,
  retryConfig?: Partial<RetryConfig>
): UseRetryRequestResult<T> {
  const [isLoading, setIsLoading] = useState(false);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [retryAttempt, setRetryAttempt] = useState(0);

  const execute = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setRetryAttempt(0);

    try {
      const response = await executeWithRetry(requestFn, {
        ...retryConfig,
        retryCondition: (err) => {
          setRetryAttempt(prev => prev + 1);
          requestMetricsCollector.recordRetry();
          return retryConfig?.retryCondition?.(err) ?? true;
        },
      });
      
      setData(response.data);
      requestMetricsCollector.recordSuccess(0); // Response time tracked elsewhere
      return response.data;
    } catch (err) {
      setError(err as Error);
      requestMetricsCollector.recordFailure();
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [requestFn, retryConfig]);

  return {
    execute,
    isLoading,
    data,
    error,
    retryAttempt,
  };
}

// ============================================
// useAdaptiveRequest Hook
// ============================================

export interface UseAdaptiveRequestResult<T> {
  /** Execute adaptive request */
  execute: (config: AxiosRequestConfig) => Promise<T | null>;
  /** Whether request is in progress */
  isLoading: boolean;
  /** Request data */
  data: T | null;
  /** Request error */
  error: Error | null;
  /** Network status */
  networkStatus: NetworkStatus;
}

/**
 * Hook for making requests that adapt to network conditions
 */
export function useAdaptiveRequest<T>(
  priority: RequestPriority = 'normal'
): UseAdaptiveRequestResult<T> {
  const [isLoading, setIsLoading] = useState(false);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const { status: networkStatus } = useNetworkStatus();

  const execute = useCallback(async (config: AxiosRequestConfig) => {
    setIsLoading(true);
    setError(null);

    try {
      const adaptedConfig = createAdaptiveRequestConfig(config, { priority });
      const response = await apiClient.request<T>(adaptedConfig);
      setData(response.data);
      return response.data;
    } catch (err) {
      setError(err as Error);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [priority]);

  return {
    execute,
    isLoading,
    data,
    error,
    networkStatus,
  };
}

// ============================================
// useRequestMetrics Hook
// ============================================

export interface UseRequestMetricsResult {
  /** Current metrics */
  metrics: RequestMetrics;
  /** Reset metrics */
  reset: () => void;
  /** Success rate percentage */
  successRate: number;
  /** Is performance healthy */
  isHealthy: boolean;
}

/**
 * Hook for monitoring request metrics
 */
export function useRequestMetrics(): UseRequestMetricsResult {
  const [metrics, setMetrics] = useState<RequestMetrics>(requestMetricsCollector.getMetrics());

  // Update metrics periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(requestMetricsCollector.getMetrics());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const reset = useCallback(() => {
    requestMetricsCollector.reset();
    setMetrics(requestMetricsCollector.getMetrics());
  }, []);

  const successRate = useMemo(() => {
    if (metrics.totalRequests === 0) return 100;
    return Math.round((metrics.successfulRequests / metrics.totalRequests) * 100);
  }, [metrics.totalRequests, metrics.successfulRequests]);

  const isHealthy = useMemo(() => {
    return successRate >= 90 && metrics.averageResponseTime < 500;
  }, [successRate, metrics.averageResponseTime]);

  return {
    metrics,
    reset,
    successRate,
    isHealthy,
  };
}

// ============================================
// useOfflineQueue Hook
// ============================================

interface QueuedOfflineRequest {
  id: string;
  config: AxiosRequestConfig;
  timestamp: number;
}

export interface UseOfflineQueueResult {
  /** Queue a request for when online */
  queue: (config: AxiosRequestConfig) => string;
  /** Process queued requests */
  processQueue: () => Promise<void>;
  /** Clear the queue */
  clearQueue: () => void;
  /** Number of queued requests */
  queueLength: number;
  /** Whether currently processing */
  isProcessing: boolean;
}

/**
 * Hook for queuing requests when offline
 */
export function useOfflineQueue(): UseOfflineQueueResult {
  const [queuedRequests, setQueuedRequests] = useState<QueuedOfflineRequest[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const { isOnline } = useNetworkStatus();

  const queue = useCallback((config: AxiosRequestConfig): string => {
    const id = `offline-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setQueuedRequests(prev => [...prev, { id, config, timestamp: Date.now() }]);
    return id;
  }, []);

  const processQueue = useCallback(async () => {
    if (!isOnline || queuedRequests.length === 0 || isProcessing) return;

    setIsProcessing(true);
    const toProcess = [...queuedRequests];
    setQueuedRequests([]);

    for (const request of toProcess) {
      try {
        await apiClient.request(request.config);
      } catch (error) {
        // Re-queue failed requests
        setQueuedRequests(prev => [...prev, request]);
      }
    }

    setIsProcessing(false);
  }, [isOnline, queuedRequests, isProcessing]);

  const clearQueue = useCallback(() => {
    setQueuedRequests([]);
  }, []);

  // Auto-process when coming back online
  useEffect(() => {
    if (isOnline && queuedRequests.length > 0) {
      processQueue();
    }
  }, [isOnline, queuedRequests.length, processQueue]);

  return {
    queue,
    processQueue,
    clearQueue,
    queueLength: queuedRequests.length,
    isProcessing,
  };
}
