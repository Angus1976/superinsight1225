/**
 * Performance Optimization Utilities
 * 
 * Provides utilities for optimizing page load time to achieve < 3 seconds target.
 * Includes resource preloading, lazy loading helpers, and performance monitoring.
 */

// Route prefetch configuration
interface PrefetchConfig {
  path: string;
  priority: 'high' | 'low';
}

// Resource hint types
type ResourceHintType = 'preload' | 'prefetch' | 'preconnect' | 'dns-prefetch';

/**
 * Add a resource hint to the document head
 */
export function addResourceHint(
  href: string,
  type: ResourceHintType,
  options?: {
    as?: string;
    crossOrigin?: 'anonymous' | 'use-credentials';
    type?: string;
  }
): void {
  // Check if hint already exists
  const existingHint = document.querySelector(`link[href="${href}"][rel="${type}"]`);
  if (existingHint) return;

  const link = document.createElement('link');
  link.rel = type;
  link.href = href;

  if (options?.as) link.setAttribute('as', options.as);
  if (options?.crossOrigin) link.crossOrigin = options.crossOrigin;
  if (options?.type) link.type = options.type;

  document.head.appendChild(link);
}

/**
 * Preload critical resources for faster page load
 */
export function preloadCriticalResources(): void {
  // Preconnect to API server
  addResourceHint('http://localhost:8000', 'preconnect', { crossOrigin: 'anonymous' });
  
  // DNS prefetch for common CDNs
  addResourceHint('https://fonts.googleapis.com', 'dns-prefetch');
  addResourceHint('https://cdn.jsdelivr.net', 'dns-prefetch');
}

/**
 * Prefetch route chunks based on user navigation patterns
 */
export function prefetchRouteChunks(routes: PrefetchConfig[]): void {
  // Use requestIdleCallback for non-critical prefetching
  const prefetch = () => {
    routes.forEach(({ path, priority }) => {
      if (priority === 'high') {
        // High priority routes are prefetched immediately
        import(/* @vite-ignore */ path).catch(() => {
          // Silently fail - prefetch is optional
        });
      } else {
        // Low priority routes are prefetched during idle time
        if ('requestIdleCallback' in window) {
          requestIdleCallback(() => {
            import(/* @vite-ignore */ path).catch(() => {});
          }, { timeout: 5000 });
        }
      }
    });
  };

  // Start prefetching after initial load
  if (document.readyState === 'complete') {
    prefetch();
  } else {
    window.addEventListener('load', prefetch);
  }
}

/**
 * Intersection Observer based lazy loading for components
 */
export function createLazyLoadObserver(
  callback: (entry: IntersectionObserverEntry) => void,
  options?: IntersectionObserverInit
): IntersectionObserver {
  return new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          callback(entry);
        }
      });
    },
    {
      rootMargin: '100px', // Start loading 100px before element is visible
      threshold: 0.1,
      ...options,
    }
  );
}

/**
 * Debounced scroll handler for performance
 */
export function createDebouncedScrollHandler(
  callback: () => void,
  delay: number = 100
): () => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  
  return () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(callback, delay);
  };
}

/**
 * Image lazy loading with placeholder
 */
export function lazyLoadImage(
  imgElement: HTMLImageElement,
  src: string,
  placeholder?: string
): void {
  if (placeholder) {
    imgElement.src = placeholder;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          imgElement.src = src;
          imgElement.classList.add('loaded');
          observer.unobserve(imgElement);
        }
      });
    },
    { rootMargin: '50px' }
  );

  observer.observe(imgElement);
}

/**
 * Performance budget checker
 */
export interface PerformanceBudget {
  maxLoadTime: number; // milliseconds
  maxBundleSize: number; // bytes
  maxImageSize: number; // bytes
}

const DEFAULT_BUDGET: PerformanceBudget = {
  maxLoadTime: 3000, // 3 seconds target
  maxBundleSize: 500 * 1024, // 500KB
  maxImageSize: 100 * 1024, // 100KB
};

export function checkPerformanceBudget(
  budget: Partial<PerformanceBudget> = {}
): { passed: boolean; violations: string[] } {
  const finalBudget = { ...DEFAULT_BUDGET, ...budget };
  const violations: string[] = [];

  // Check load time
  const loadTime = performance.now();
  if (loadTime > finalBudget.maxLoadTime) {
    violations.push(`Load time (${Math.round(loadTime)}ms) exceeds budget (${finalBudget.maxLoadTime}ms)`);
  }

  // Check resource sizes
  const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
  resources.forEach((resource) => {
    if (resource.transferSize > finalBudget.maxBundleSize) {
      violations.push(`Resource ${resource.name} (${Math.round(resource.transferSize / 1024)}KB) exceeds bundle budget`);
    }
  });

  return {
    passed: violations.length === 0,
    violations,
  };
}

/**
 * Memory usage monitor
 */
export function getMemoryUsage(): { usedJSHeapSize: number; totalJSHeapSize: number } | null {
  if ('memory' in performance) {
    const memory = (performance as Performance & { memory: { usedJSHeapSize: number; totalJSHeapSize: number } }).memory;
    return {
      usedJSHeapSize: memory.usedJSHeapSize,
      totalJSHeapSize: memory.totalJSHeapSize,
    };
  }
  return null;
}

/**
 * Network information for adaptive loading
 */
export function getNetworkInfo(): {
  effectiveType: string;
  downlink: number;
  rtt: number;
  saveData: boolean;
} | null {
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
      effectiveType: connection.effectiveType,
      downlink: connection.downlink,
      rtt: connection.rtt,
      saveData: connection.saveData,
    };
  }
  return null;
}

/**
 * Adaptive loading based on network conditions
 */
export function shouldReduceDataUsage(): boolean {
  const networkInfo = getNetworkInfo();
  if (!networkInfo) return false;

  // Reduce data on slow connections or when save-data is enabled
  return (
    networkInfo.saveData ||
    networkInfo.effectiveType === 'slow-2g' ||
    networkInfo.effectiveType === '2g'
  );
}

/**
 * Request idle callback polyfill
 */
export function requestIdleCallbackPolyfill(
  callback: IdleRequestCallback,
  options?: IdleRequestOptions
): number {
  if ('requestIdleCallback' in window) {
    return window.requestIdleCallback(callback, options);
  }
  
  // Fallback using setTimeout
  const timeoutId = setTimeout(() => {
    callback({
      didTimeout: false,
      timeRemaining: () => 50,
    });
  }, options?.timeout || 1);
  return timeoutId as unknown as number;
}

/**
 * Cancel idle callback polyfill
 */
export function cancelIdleCallbackPolyfill(handle: number): void {
  if ('cancelIdleCallback' in window) {
    window.cancelIdleCallback(handle);
  } else {
    clearTimeout(handle);
  }
}

/**
 * Defer non-critical work to idle time
 */
export function deferToIdle<T>(
  work: () => T,
  options?: { timeout?: number }
): Promise<T> {
  return new Promise((resolve) => {
    requestIdleCallbackPolyfill(
      () => {
        resolve(work());
      },
      { timeout: options?.timeout || 2000 }
    );
  });
}

/**
 * Batch DOM updates for better performance
 */
export function batchDOMUpdates(updates: Array<() => void>): void {
  requestAnimationFrame(() => {
    updates.forEach((update) => update());
  });
}

/**
 * Remove initial loader when app is ready
 */
export function removeInitialLoader(): void {
  const loader = document.getElementById('initial-loader');
  if (loader) {
    loader.classList.add('fade-out');
    setTimeout(() => loader.remove(), 300);
  }
}

/**
 * Initialize performance optimizations
 */
export function initPerformanceOptimizations(): void {
  // Preload critical resources
  preloadCriticalResources();
  
  // Remove initial loader
  removeInitialLoader();
  
  // Log performance metrics in development
  if (import.meta.env.DEV) {
    window.addEventListener('load', () => {
      const loadTime = performance.now();
      console.log(`[Performance] Total load time: ${Math.round(loadTime)}ms`);
      
      const budget = checkPerformanceBudget();
      if (!budget.passed) {
        console.warn('[Performance] Budget violations:', budget.violations);
      } else {
        console.log('[Performance] All budgets passed ✓');
      }
    });
  }
}


// ============================================
// Component Render Time Optimization Utilities
// ============================================

// Component render time budget (100ms)
export const COMPONENT_RENDER_BUDGET = 100;

/**
 * Component render budget configuration
 */
export interface ComponentRenderBudget {
  maxRenderTime: number; // milliseconds
  warningThreshold: number; // percentage of budget
}

const DEFAULT_RENDER_BUDGET: ComponentRenderBudget = {
  maxRenderTime: COMPONENT_RENDER_BUDGET,
  warningThreshold: 80,
};

/**
 * Check if component render time is within budget
 */
export function checkComponentRenderBudget(
  renderTime: number,
  budget: Partial<ComponentRenderBudget> = {}
): {
  passed: boolean;
  isWarning: boolean;
  renderTime: number;
  budget: number;
  usagePercent: number;
} {
  const finalBudget = { ...DEFAULT_RENDER_BUDGET, ...budget };
  const usagePercent = (renderTime / finalBudget.maxRenderTime) * 100;

  return {
    passed: renderTime <= finalBudget.maxRenderTime,
    isWarning: usagePercent >= finalBudget.warningThreshold && renderTime <= finalBudget.maxRenderTime,
    renderTime: Math.round(renderTime * 100) / 100,
    budget: finalBudget.maxRenderTime,
    usagePercent: Math.round(usagePercent * 100) / 100,
  };
}

/**
 * Throttle function for performance-critical operations
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false;
  
  return function (this: any, ...args: Parameters<T>) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}

/**
 * Debounce function for reducing render frequency
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  immediate: boolean = false
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return function (this: any, ...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      if (!immediate) func.apply(this, args);
    };

    const callNow = immediate && !timeout;
    
    if (timeout) {
      clearTimeout(timeout);
    }
    
    timeout = setTimeout(later, wait);
    
    if (callNow) {
      func.apply(this, args);
    }
  };
}

/**
 * Memoize function results for expensive computations
 */
export function memoize<T extends (...args: any[]) => any>(
  func: T,
  resolver?: (...args: Parameters<T>) => string
): T {
  const cache = new Map<string, ReturnType<T>>();

  return function (this: any, ...args: Parameters<T>): ReturnType<T> {
    const key = resolver ? resolver(...args) : JSON.stringify(args);
    
    if (cache.has(key)) {
      return cache.get(key)!;
    }
    
    const result = func.apply(this, args);
    cache.set(key, result);
    
    // Limit cache size to prevent memory leaks
    if (cache.size > 1000) {
      const firstKey = cache.keys().next().value;
      if (firstKey !== undefined) {
        cache.delete(firstKey);
      }
    }
    
    return result;
  } as T;
}

/**
 * Schedule work during idle time to avoid blocking renders
 */
export function scheduleIdleWork<T>(
  work: () => T,
  priority: 'high' | 'normal' | 'low' = 'normal'
): Promise<T> {
  const timeouts = {
    high: 100,
    normal: 1000,
    low: 5000,
  };

  return new Promise((resolve) => {
    if ('requestIdleCallback' in window) {
      requestIdleCallback(
        () => resolve(work()),
        { timeout: timeouts[priority] }
      );
    } else {
      // Fallback for browsers without requestIdleCallback
      setTimeout(() => resolve(work()), priority === 'high' ? 0 : 16);
    }
  });
}

/**
 * Chunk array processing to avoid blocking the main thread
 */
export async function processInChunks<T, R>(
  items: T[],
  processor: (item: T, index: number) => R,
  chunkSize: number = 100
): Promise<R[]> {
  const results: R[] = [];
  
  for (let i = 0; i < items.length; i += chunkSize) {
    const chunk = items.slice(i, i + chunkSize);
    
    // Process chunk
    const chunkResults = chunk.map((item, index) => processor(item, i + index));
    results.push(...chunkResults);
    
    // Yield to main thread between chunks
    if (i + chunkSize < items.length) {
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
  }
  
  return results;
}

/**
 * Virtual list helper for rendering large lists efficiently
 */
export function calculateVisibleRange(
  scrollTop: number,
  containerHeight: number,
  itemHeight: number,
  totalItems: number,
  overscan: number = 3
): { start: number; end: number; offsetY: number } {
  const start = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const end = Math.min(totalItems, start + visibleCount + overscan * 2);
  const offsetY = start * itemHeight;

  return { start, end, offsetY };
}

/**
 * Measure component render time
 */
export function measureRenderTime(componentName: string): {
  start: () => void;
  end: () => number;
} {
  let startTime = 0;

  return {
    start: () => {
      startTime = performance.now();
    },
    end: () => {
      const renderTime = performance.now() - startTime;
      
      if (import.meta.env.DEV) {
        const result = checkComponentRenderBudget(renderTime);
        
        if (!result.passed) {
          console.warn(
            `[Render] ✗ ${componentName}: ${result.renderTime}ms exceeds ${result.budget}ms budget`
          );
        } else if (result.isWarning) {
          console.log(
            `[Render] ⚠ ${componentName}: ${result.renderTime}ms (${result.usagePercent}% of budget)`
          );
        }
      }
      
      return renderTime;
    },
  };
}

/**
 * Create a performance-optimized event handler
 */
export function createOptimizedHandler<T extends (...args: any[]) => any>(
  handler: T,
  options: {
    throttle?: number;
    debounce?: number;
    leading?: boolean;
  } = {}
): (...args: Parameters<T>) => void {
  if (options.throttle) {
    return throttle(handler, options.throttle);
  }
  
  if (options.debounce) {
    return debounce(handler, options.debounce, options.leading);
  }
  
  return handler;
}
