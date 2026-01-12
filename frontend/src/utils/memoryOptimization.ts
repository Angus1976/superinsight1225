/**
 * Memory Optimization Utilities
 * 
 * Provides utilities for monitoring and optimizing memory usage.
 * Includes memory leak detection, garbage collection hints, and memory budgets.
 */

// Memory budget configuration (in MB)
export const MEMORY_BUDGET = {
  warning: 100, // 100MB - warning threshold
  critical: 200, // 200MB - critical threshold
  max: 300, // 300MB - maximum allowed
};

// Memory sample for tracking
export interface MemorySample {
  timestamp: number;
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
  usagePercentage: number;
}

// Memory trend analysis
export interface MemoryTrend {
  direction: 'increasing' | 'decreasing' | 'stable';
  rate: number; // bytes per second
  samples: number;
  duration: number; // milliseconds
}

// Memory leak detection result
export interface MemoryLeakDetection {
  isLeaking: boolean;
  confidence: number; // 0-100
  trend: MemoryTrend;
  recommendation: string;
}

// Memory status
export type MemoryStatus = 'good' | 'warning' | 'critical';

// Memory report
export interface MemoryReport {
  current: MemorySample | null;
  status: MemoryStatus;
  trend: MemoryTrend | null;
  leakDetection: MemoryLeakDetection | null;
  history: MemorySample[];
  recommendations: string[];
}

/**
 * Memory Monitor class for tracking memory usage over time
 */
export class MemoryMonitor {
  private samples: MemorySample[] = [];
  private maxSamples: number;
  private sampleInterval: number;
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private listeners: Set<(sample: MemorySample) => void> = new Set();

  constructor(options: { maxSamples?: number; sampleInterval?: number } = {}) {
    this.maxSamples = options.maxSamples || 100;
    this.sampleInterval = options.sampleInterval || 5000; // 5 seconds
  }

  /**
   * Start monitoring memory usage
   */
  start(): void {
    if (this.intervalId) return;

    // Take initial sample
    this.takeSample();

    // Start periodic sampling
    this.intervalId = setInterval(() => {
      this.takeSample();
    }, this.sampleInterval);
  }

  /**
   * Stop monitoring memory usage
   */
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  /**
   * Take a memory sample
   */
  private takeSample(): void {
    const sample = getCurrentMemorySample();
    if (!sample) return;

    this.samples.push(sample);

    // Limit samples to maxSamples
    if (this.samples.length > this.maxSamples) {
      this.samples.shift();
    }

    // Notify listeners
    this.listeners.forEach(listener => listener(sample));
  }

  /**
   * Subscribe to memory updates
   */
  subscribe(listener: (sample: MemorySample) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Get current memory sample
   */
  getCurrentSample(): MemorySample | null {
    return this.samples.length > 0 ? this.samples[this.samples.length - 1] : null;
  }

  /**
   * Get all samples
   */
  getSamples(): MemorySample[] {
    return [...this.samples];
  }

  /**
   * Get memory trend
   */
  getTrend(): MemoryTrend | null {
    return analyzeMemoryTrend(this.samples);
  }

  /**
   * Detect memory leaks
   */
  detectLeaks(): MemoryLeakDetection | null {
    return detectMemoryLeak(this.samples);
  }

  /**
   * Generate memory report
   */
  generateReport(): MemoryReport {
    const current = this.getCurrentSample();
    const trend = this.getTrend();
    const leakDetection = this.detectLeaks();
    const status = getMemoryStatus(current);
    const recommendations = generateRecommendations(current, trend, leakDetection);

    return {
      current,
      status,
      trend,
      leakDetection,
      history: this.getSamples(),
      recommendations,
    };
  }

  /**
   * Clear all samples
   */
  clear(): void {
    this.samples = [];
  }

  /**
   * Destroy monitor and cleanup
   */
  destroy(): void {
    this.stop();
    this.clear();
    this.listeners.clear();
  }
}

/**
 * Get current memory sample
 */
export function getCurrentMemorySample(): MemorySample | null {
  if (!('memory' in performance)) {
    return null;
  }

  const memory = (performance as Performance & {
    memory?: {
      usedJSHeapSize: number;
      totalJSHeapSize: number;
      jsHeapSizeLimit: number;
    };
  }).memory;

  // Check if memory object exists and has required properties
  if (!memory || typeof memory.usedJSHeapSize !== 'number') {
    return null;
  }

  return {
    timestamp: Date.now(),
    usedJSHeapSize: memory.usedJSHeapSize,
    totalJSHeapSize: memory.totalJSHeapSize,
    jsHeapSizeLimit: memory.jsHeapSizeLimit,
    usagePercentage: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100,
  };
}

/**
 * Get memory status based on current usage
 */
export function getMemoryStatus(sample: MemorySample | null): MemoryStatus {
  if (!sample) return 'good';

  const usedMB = sample.usedJSHeapSize / (1024 * 1024);

  if (usedMB >= MEMORY_BUDGET.critical) {
    return 'critical';
  } else if (usedMB >= MEMORY_BUDGET.warning) {
    return 'warning';
  }
  return 'good';
}

/**
 * Analyze memory trend from samples
 */
export function analyzeMemoryTrend(samples: MemorySample[]): MemoryTrend | null {
  if (samples.length < 3) return null;

  const recentSamples = samples.slice(-10); // Use last 10 samples
  const firstSample = recentSamples[0];
  const lastSample = recentSamples[recentSamples.length - 1];

  const memoryChange = lastSample.usedJSHeapSize - firstSample.usedJSHeapSize;
  const timeChange = lastSample.timestamp - firstSample.timestamp;
  const rate = timeChange > 0 ? (memoryChange / timeChange) * 1000 : 0; // bytes per second

  let direction: 'increasing' | 'decreasing' | 'stable';
  const threshold = 1024; // 1KB/s threshold for stability

  if (Math.abs(rate) < threshold) {
    direction = 'stable';
  } else if (rate > 0) {
    direction = 'increasing';
  } else {
    direction = 'decreasing';
  }

  return {
    direction,
    rate,
    samples: recentSamples.length,
    duration: timeChange,
  };
}

/**
 * Detect potential memory leaks
 */
export function detectMemoryLeak(samples: MemorySample[]): MemoryLeakDetection | null {
  if (samples.length < 10) {
    return {
      isLeaking: false,
      confidence: 0,
      trend: { direction: 'stable', rate: 0, samples: samples.length, duration: 0 },
      recommendation: 'Not enough samples to detect memory leaks. Continue monitoring.',
    };
  }

  const trend = analyzeMemoryTrend(samples);
  if (!trend) return null;

  // Calculate confidence based on trend consistency
  let confidence = 0;
  let isLeaking = false;
  let recommendation = '';

  if (trend.direction === 'increasing') {
    // Check if memory is consistently increasing
    const recentSamples = samples.slice(-10);
    let increasingCount = 0;

    for (let i = 1; i < recentSamples.length; i++) {
      if (recentSamples[i].usedJSHeapSize > recentSamples[i - 1].usedJSHeapSize) {
        increasingCount++;
      }
    }

    confidence = (increasingCount / (recentSamples.length - 1)) * 100;

    // Consider it a leak if memory is increasing consistently and rate is significant
    const rateMBPerMinute = (trend.rate * 60) / (1024 * 1024);
    isLeaking = confidence > 70 && rateMBPerMinute > 1; // More than 1MB/minute

    if (isLeaking) {
      recommendation = `Memory is increasing at ${rateMBPerMinute.toFixed(2)}MB/min. Check for event listener leaks, uncleared intervals, or growing caches.`;
    } else if (confidence > 50) {
      recommendation = 'Memory usage is trending upward. Monitor closely for potential leaks.';
    } else {
      recommendation = 'Memory usage appears normal with some fluctuation.';
    }
  } else if (trend.direction === 'stable') {
    confidence = 0;
    recommendation = 'Memory usage is stable. No leaks detected.';
  } else {
    confidence = 0;
    recommendation = 'Memory usage is decreasing. Garbage collection is working effectively.';
  }

  return {
    isLeaking,
    confidence,
    trend,
    recommendation,
  };
}

/**
 * Generate recommendations based on memory analysis
 */
export function generateRecommendations(
  current: MemorySample | null,
  trend: MemoryTrend | null,
  leakDetection: MemoryLeakDetection | null
): string[] {
  const recommendations: string[] = [];

  if (!current) {
    recommendations.push('Memory API not available in this browser.');
    return recommendations;
  }

  const usedMB = current.usedJSHeapSize / (1024 * 1024);
  const status = getMemoryStatus(current);

  // Status-based recommendations
  if (status === 'critical') {
    recommendations.push('⚠️ Critical: Memory usage is very high. Consider refreshing the page.');
    recommendations.push('Clear unused data and close unnecessary tabs.');
  } else if (status === 'warning') {
    recommendations.push('⚡ Warning: Memory usage is elevated. Monitor for further increases.');
  }

  // Trend-based recommendations
  if (trend?.direction === 'increasing' && trend.rate > 10240) { // > 10KB/s
    recommendations.push('📈 Memory is growing rapidly. Check for memory leaks.');
  }

  // Leak detection recommendations
  if (leakDetection?.isLeaking) {
    recommendations.push('🔍 Potential memory leak detected. Review recent code changes.');
    recommendations.push('Check for: uncleared intervals, event listeners, growing arrays/objects.');
  }

  // General recommendations
  if (usedMB > 50) {
    recommendations.push('💡 Consider implementing virtualization for large lists.');
    recommendations.push('💡 Use React.memo() for expensive components.');
  }

  if (recommendations.length === 0) {
    recommendations.push('✅ Memory usage is healthy.');
  }

  return recommendations;
}

/**
 * Format bytes to human-readable string
 */
export function formatMemorySize(bytes: number): string {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Suggest garbage collection (hint only, not guaranteed)
 */
export function suggestGarbageCollection(): void {
  // Clear any weak references that might be holding memory
  if ('gc' in window && typeof (window as any).gc === 'function') {
    // Only available in Chrome with --expose-gc flag
    (window as any).gc();
  }
}

/**
 * Create a weak cache that allows garbage collection
 */
export function createWeakCache<K extends object, V>(): {
  get: (key: K) => V | undefined;
  set: (key: K, value: V) => void;
  has: (key: K) => boolean;
  delete: (key: K) => boolean;
} {
  const cache = new WeakMap<K, V>();

  return {
    get: (key: K) => cache.get(key),
    set: (key: K, value: V) => cache.set(key, value),
    has: (key: K) => cache.has(key),
    delete: (key: K) => cache.delete(key),
  };
}

/**
 * Create a size-limited cache with LRU eviction
 */
export function createLRUCache<K, V>(maxSize: number): {
  get: (key: K) => V | undefined;
  set: (key: K, value: V) => void;
  has: (key: K) => boolean;
  delete: (key: K) => boolean;
  clear: () => void;
  size: () => number;
} {
  const cache = new Map<K, V>();

  return {
    get: (key: K) => {
      const value = cache.get(key);
      if (value !== undefined) {
        // Move to end (most recently used)
        cache.delete(key);
        cache.set(key, value);
      }
      return value;
    },
    set: (key: K, value: V) => {
      if (cache.has(key)) {
        cache.delete(key);
      } else if (cache.size >= maxSize) {
        // Remove oldest (first) entry
        const firstKey = cache.keys().next().value;
        if (firstKey !== undefined) {
          cache.delete(firstKey);
        }
      }
      cache.set(key, value);
    },
    has: (key: K) => cache.has(key),
    delete: (key: K) => cache.delete(key),
    clear: () => cache.clear(),
    size: () => cache.size,
  };
}

// Global memory monitor instance
let globalMemoryMonitor: MemoryMonitor | null = null;

/**
 * Get or create global memory monitor
 */
export function getGlobalMemoryMonitor(): MemoryMonitor {
  if (!globalMemoryMonitor) {
    globalMemoryMonitor = new MemoryMonitor();
  }
  return globalMemoryMonitor;
}

/**
 * Initialize memory monitoring
 */
export function initMemoryMonitoring(): void {
  const monitor = getGlobalMemoryMonitor();
  monitor.start();

  // Log warnings in development
  if (import.meta.env.DEV) {
    monitor.subscribe((sample) => {
      const status = getMemoryStatus(sample);
      if (status === 'critical') {
        console.warn('[Memory] Critical memory usage:', formatMemorySize(sample.usedJSHeapSize));
      } else if (status === 'warning') {
        console.log('[Memory] Warning: elevated memory usage:', formatMemorySize(sample.usedJSHeapSize));
      }
    });
  }
}

/**
 * Cleanup memory monitoring
 */
export function cleanupMemoryMonitoring(): void {
  if (globalMemoryMonitor) {
    globalMemoryMonitor.destroy();
    globalMemoryMonitor = null;
  }
}
