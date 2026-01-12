/**
 * Memory Optimization Hooks
 * 
 * React hooks for monitoring and optimizing memory usage.
 * Provides real-time memory tracking, leak detection, and optimization utilities.
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  MemoryMonitor,
  MemorySample,
  MemoryReport,
  MemoryStatus,
  MemoryTrend,
  MemoryLeakDetection,
  getCurrentMemorySample,
  getMemoryStatus,
  formatMemorySize,
  MEMORY_BUDGET,
} from '@/utils/memoryOptimization';

/**
 * Hook result for useMemoryMonitor
 */
export interface UseMemoryMonitorResult {
  /** Current memory sample */
  current: MemorySample | null;
  /** Memory status (good, warning, critical) */
  status: MemoryStatus;
  /** Memory trend analysis */
  trend: MemoryTrend | null;
  /** Memory leak detection result */
  leakDetection: MemoryLeakDetection | null;
  /** Historical samples */
  history: MemorySample[];
  /** Recommendations for optimization */
  recommendations: string[];
  /** Whether memory API is available */
  isSupported: boolean;
  /** Refresh memory data */
  refresh: () => void;
  /** Clear history */
  clearHistory: () => void;
}

/**
 * Hook for monitoring memory usage
 */
export function useMemoryMonitor(options: {
  /** Sample interval in milliseconds */
  sampleInterval?: number;
  /** Maximum number of samples to keep */
  maxSamples?: number;
  /** Whether to auto-start monitoring */
  autoStart?: boolean;
} = {}): UseMemoryMonitorResult {
  const {
    sampleInterval = 5000,
    maxSamples = 100,
    autoStart = true,
  } = options;

  const [report, setReport] = useState<MemoryReport>({
    current: null,
    status: 'good',
    trend: null,
    leakDetection: null,
    history: [],
    recommendations: [],
  });

  const monitorRef = useRef<MemoryMonitor | null>(null);

  // Check if memory API is supported
  const isSupported = useMemo(() => {
    if (!('memory' in performance)) return false;
    const mem = (performance as any).memory;
    return mem && typeof mem.usedJSHeapSize === 'number';
  }, []);

  // Initialize monitor
  useEffect(() => {
    if (!isSupported) return;

    monitorRef.current = new MemoryMonitor({ sampleInterval, maxSamples });

    if (autoStart) {
      monitorRef.current.start();
    }

    // Subscribe to updates
    const unsubscribe = monitorRef.current.subscribe(() => {
      if (monitorRef.current) {
        setReport(monitorRef.current.generateReport());
      }
    });

    // Initial report
    setReport(monitorRef.current.generateReport());

    return () => {
      unsubscribe();
      if (monitorRef.current) {
        monitorRef.current.destroy();
        monitorRef.current = null;
      }
    };
  }, [isSupported, sampleInterval, maxSamples, autoStart]);

  // Refresh callback
  const refresh = useCallback(() => {
    if (monitorRef.current) {
      setReport(monitorRef.current.generateReport());
    }
  }, []);

  // Clear history callback
  const clearHistory = useCallback(() => {
    if (monitorRef.current) {
      monitorRef.current.clear();
      setReport(monitorRef.current.generateReport());
    }
  }, []);

  return {
    ...report,
    isSupported,
    refresh,
    clearHistory,
  };
}

/**
 * Hook for simple memory usage display
 */
export function useMemoryUsage(): {
  usedMB: number;
  totalMB: number;
  limitMB: number;
  usagePercent: number;
  status: MemoryStatus;
  formatted: string;
  isSupported: boolean;
} {
  const [memory, setMemory] = useState({
    usedMB: 0,
    totalMB: 0,
    limitMB: 0,
    usagePercent: 0,
    status: 'good' as MemoryStatus,
    formatted: '0 MB',
  });

  const isSupported = useMemo(() => {
    if (!('memory' in performance)) return false;
    const mem = (performance as any).memory;
    return mem && typeof mem.usedJSHeapSize === 'number';
  }, []);

  useEffect(() => {
    if (!isSupported) return;

    const updateMemory = () => {
      const sample = getCurrentMemorySample();
      if (sample) {
        const usedMB = sample.usedJSHeapSize / (1024 * 1024);
        const totalMB = sample.totalJSHeapSize / (1024 * 1024);
        const limitMB = sample.jsHeapSizeLimit / (1024 * 1024);

        setMemory({
          usedMB: Math.round(usedMB * 100) / 100,
          totalMB: Math.round(totalMB * 100) / 100,
          limitMB: Math.round(limitMB * 100) / 100,
          usagePercent: Math.round(sample.usagePercentage * 100) / 100,
          status: getMemoryStatus(sample),
          formatted: formatMemorySize(sample.usedJSHeapSize),
        });
      }
    };

    updateMemory();
    const interval = setInterval(updateMemory, 5000);

    return () => clearInterval(interval);
  }, [isSupported]);

  return { ...memory, isSupported };
}

/**
 * Hook for detecting memory leaks in a component
 */
export function useMemoryLeakDetector(componentName: string): {
  isLeaking: boolean;
  confidence: number;
  message: string;
} {
  const [result, setResult] = useState({
    isLeaking: false,
    confidence: 0,
    message: 'Monitoring...',
  });

  const samplesRef = useRef<number[]>([]);
  const mountTimeRef = useRef(Date.now());

  useEffect(() => {
    // Check if memory API is supported
    const isSupported = 'memory' in performance && 
      (performance as any).memory && 
      typeof (performance as any).memory.usedJSHeapSize === 'number';
    
    if (!isSupported) {
      setResult({
        isLeaking: false,
        confidence: 0,
        message: 'Memory API not supported',
      });
      return;
    }

    const checkMemory = () => {
      const sample = getCurrentMemorySample();
      if (!sample) return;

      samplesRef.current.push(sample.usedJSHeapSize);

      // Keep only last 20 samples
      if (samplesRef.current.length > 20) {
        samplesRef.current.shift();
      }

      // Need at least 5 samples to analyze
      if (samplesRef.current.length < 5) {
        setResult({
          isLeaking: false,
          confidence: 0,
          message: 'Collecting samples...',
        });
        return;
      }

      // Analyze trend
      const samples = samplesRef.current;
      let increasingCount = 0;

      for (let i = 1; i < samples.length; i++) {
        if (samples[i] > samples[i - 1]) {
          increasingCount++;
        }
      }

      const confidence = (increasingCount / (samples.length - 1)) * 100;
      const isLeaking = confidence > 80;

      const firstSample = samples[0];
      const lastSample = samples[samples.length - 1];
      const growth = lastSample - firstSample;
      const growthMB = growth / (1024 * 1024);

      let message: string;
      if (isLeaking) {
        message = `⚠️ ${componentName}: Memory grew by ${growthMB.toFixed(2)}MB`;
      } else if (confidence > 50) {
        message = `📊 ${componentName}: Memory trending up (${confidence.toFixed(0)}% confidence)`;
      } else {
        message = `✅ ${componentName}: Memory stable`;
      }

      setResult({ isLeaking, confidence, message });
    };

    const interval = setInterval(checkMemory, 3000);
    checkMemory();

    return () => {
      clearInterval(interval);
      
      // Log final analysis in development
      if (import.meta.env.DEV && samplesRef.current.length > 0) {
        const duration = Date.now() - mountTimeRef.current;
        const samples = samplesRef.current;
        const growth = samples[samples.length - 1] - samples[0];
        
        if (growth > 1024 * 1024) { // More than 1MB growth
          console.log(
            `[Memory] ${componentName} unmounted after ${(duration / 1000).toFixed(1)}s, ` +
            `memory change: ${formatMemorySize(growth)}`
          );
        }
      }
    };
  }, [componentName]);

  return result;
}

/**
 * Hook for cleanup on unmount to prevent memory leaks
 */
export function useCleanup(cleanup: () => void): void {
  const cleanupRef = useRef(cleanup);
  cleanupRef.current = cleanup;

  useEffect(() => {
    return () => {
      cleanupRef.current();
    };
  }, []);
}

/**
 * Hook for managing disposable resources
 */
export function useDisposable<T extends { dispose?: () => void; destroy?: () => void }>(
  factory: () => T,
  deps: React.DependencyList = []
): T {
  const resourceRef = useRef<T | null>(null);

  useEffect(() => {
    resourceRef.current = factory();

    return () => {
      if (resourceRef.current) {
        if (typeof resourceRef.current.dispose === 'function') {
          resourceRef.current.dispose();
        } else if (typeof resourceRef.current.destroy === 'function') {
          resourceRef.current.destroy();
        }
        resourceRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return resourceRef.current as T;
}

/**
 * Hook for tracking component memory footprint
 */
export function useMemoryFootprint(componentName: string): {
  mountMemory: number;
  currentMemory: number;
  delta: number;
  formatted: string;
} {
  const mountMemoryRef = useRef<number>(0);
  const [footprint, setFootprint] = useState({
    mountMemory: 0,
    currentMemory: 0,
    delta: 0,
    formatted: '0 B',
  });

  useEffect(() => {
    const sample = getCurrentMemorySample();
    if (sample) {
      mountMemoryRef.current = sample.usedJSHeapSize;
      setFootprint({
        mountMemory: sample.usedJSHeapSize,
        currentMemory: sample.usedJSHeapSize,
        delta: 0,
        formatted: '0 B',
      });
    }

    const interval = setInterval(() => {
      const currentSample = getCurrentMemorySample();
      if (currentSample) {
        const delta = currentSample.usedJSHeapSize - mountMemoryRef.current;
        setFootprint({
          mountMemory: mountMemoryRef.current,
          currentMemory: currentSample.usedJSHeapSize,
          delta,
          formatted: formatMemorySize(Math.abs(delta)),
        });
      }
    }, 5000);

    return () => {
      clearInterval(interval);
      
      // Log memory delta on unmount in development
      if (import.meta.env.DEV) {
        const finalSample = getCurrentMemorySample();
        if (finalSample && mountMemoryRef.current > 0) {
          const delta = finalSample.usedJSHeapSize - mountMemoryRef.current;
          if (Math.abs(delta) > 512 * 1024) { // More than 512KB change
            console.log(
              `[Memory] ${componentName} footprint: ${delta > 0 ? '+' : ''}${formatMemorySize(delta)}`
            );
          }
        }
      }
    };
  }, [componentName]);

  return footprint;
}

/**
 * Hook for memory-aware data loading
 */
export function useMemoryAwareLoader<T>(
  loader: () => Promise<T>,
  options: {
    /** Memory threshold in MB to pause loading */
    memoryThreshold?: number;
    /** Retry delay when memory is high */
    retryDelay?: number;
  } = {}
): {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
  isMemoryConstrained: boolean;
  retry: () => void;
} {
  const { memoryThreshold = MEMORY_BUDGET.warning, retryDelay = 5000 } = options;

  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [isMemoryConstrained, setIsMemoryConstrained] = useState(false);

  const load = useCallback(async () => {
    // Check memory before loading
    const sample = getCurrentMemorySample();
    if (sample) {
      const usedMB = sample.usedJSHeapSize / (1024 * 1024);
      if (usedMB > memoryThreshold) {
        setIsMemoryConstrained(true);
        // Retry after delay
        setTimeout(load, retryDelay);
        return;
      }
    }

    setIsMemoryConstrained(false);
    setIsLoading(true);
    setError(null);

    try {
      const result = await loader();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [loader, memoryThreshold, retryDelay]);

  useEffect(() => {
    load();
  }, [load]);

  return {
    data,
    isLoading,
    error,
    isMemoryConstrained,
    retry: load,
  };
}
