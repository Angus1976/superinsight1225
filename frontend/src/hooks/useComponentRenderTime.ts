/**
 * useComponentRenderTime Hook
 * 
 * Tracks and enforces component rendering time to ensure < 100ms target.
 * Provides real-time feedback on component render performance.
 */

import { useEffect, useRef, useCallback, useState } from 'react';

// Component render time budget in milliseconds
const RENDER_TIME_BUDGET = 100;

// Warning threshold (80% of budget)
const WARNING_THRESHOLD = 80;

export interface RenderMetrics {
  componentName: string;
  renderTime: number;
  isWithinBudget: boolean;
  renderCount: number;
  averageRenderTime: number;
  maxRenderTime: number;
  minRenderTime: number;
  timestamp: number;
}

export interface UseComponentRenderTimeOptions {
  /** Component name for logging */
  componentName: string;
  /** Custom budget in ms (default: 100ms) */
  budget?: number;
  /** Enable console logging in development */
  enableLogging?: boolean;
  /** Callback when render exceeds budget */
  onBudgetExceeded?: (metrics: RenderMetrics) => void;
}

// Global metrics store for aggregation
const globalMetricsStore = new Map<string, RenderMetrics[]>();

/**
 * Hook to track component render time
 */
export function useComponentRenderTime(options: UseComponentRenderTimeOptions): RenderMetrics | null {
  const {
    componentName,
    budget = RENDER_TIME_BUDGET,
    enableLogging = import.meta.env.DEV,
    onBudgetExceeded,
  } = options;

  const startTimeRef = useRef<number>(performance.now());
  const renderCountRef = useRef<number>(0);
  const renderTimesRef = useRef<number[]>([]);
  const [metrics, setMetrics] = useState<RenderMetrics | null>(null);

  // Mark render start
  startTimeRef.current = performance.now();
  renderCountRef.current += 1;

  useEffect(() => {
    // Measure render time after component mounts/updates
    const measureRenderTime = () => {
      const renderTime = performance.now() - startTimeRef.current;
      renderTimesRef.current.push(renderTime);

      // Keep only last 100 measurements
      if (renderTimesRef.current.length > 100) {
        renderTimesRef.current.shift();
      }

      const times = renderTimesRef.current;
      const newMetrics: RenderMetrics = {
        componentName,
        renderTime: Math.round(renderTime * 100) / 100,
        isWithinBudget: renderTime <= budget,
        renderCount: renderCountRef.current,
        averageRenderTime: Math.round((times.reduce((a, b) => a + b, 0) / times.length) * 100) / 100,
        maxRenderTime: Math.round(Math.max(...times) * 100) / 100,
        minRenderTime: Math.round(Math.min(...times) * 100) / 100,
        timestamp: Date.now(),
      };

      setMetrics(newMetrics);

      // Store in global metrics
      if (!globalMetricsStore.has(componentName)) {
        globalMetricsStore.set(componentName, []);
      }
      const componentMetrics = globalMetricsStore.get(componentName)!;
      componentMetrics.push(newMetrics);
      if (componentMetrics.length > 50) {
        componentMetrics.shift();
      }

      // Log in development
      if (enableLogging) {
        const status = newMetrics.isWithinBudget ? '✓' : '✗';
        const warningLevel = (renderTime / budget) * 100;
        
        if (!newMetrics.isWithinBudget) {
          console.warn(
            `%c[Render] ${status} ${componentName}: ${newMetrics.renderTime}ms (budget: ${budget}ms)`,
            'color: red; font-weight: bold;'
          );
        } else if (warningLevel >= WARNING_THRESHOLD) {
          console.log(
            `%c[Render] ${status} ${componentName}: ${newMetrics.renderTime}ms (${warningLevel.toFixed(0)}% of budget)`,
            'color: orange; font-weight: bold;'
          );
        } else if (import.meta.env.DEV && renderCountRef.current <= 2) {
          // Only log first few renders in dev to avoid noise
          console.log(
            `%c[Render] ${status} ${componentName}: ${newMetrics.renderTime}ms`,
            'color: green;'
          );
        }
      }

      // Callback for budget exceeded
      if (!newMetrics.isWithinBudget && onBudgetExceeded) {
        onBudgetExceeded(newMetrics);
      }
    };

    // Use requestAnimationFrame to measure after paint
    requestAnimationFrame(() => {
      requestAnimationFrame(measureRenderTime);
    });
  });

  return metrics;
}

/**
 * Get all component render metrics
 */
export function getAllRenderMetrics(): Map<string, RenderMetrics[]> {
  return new Map(globalMetricsStore);
}

/**
 * Get render metrics summary for all components
 */
export function getRenderMetricsSummary(): {
  totalComponents: number;
  componentsWithinBudget: number;
  componentsExceedingBudget: number;
  averageRenderTime: number;
  slowestComponents: Array<{ name: string; avgTime: number }>;
} {
  const components = Array.from(globalMetricsStore.entries());
  
  let totalRenderTime = 0;
  let totalRenders = 0;
  const componentAverages: Array<{ name: string; avgTime: number }> = [];
  let withinBudget = 0;
  let exceedingBudget = 0;

  components.forEach(([name, metrics]) => {
    if (metrics.length === 0) return;
    
    const avgTime = metrics.reduce((sum, m) => sum + m.renderTime, 0) / metrics.length;
    componentAverages.push({ name, avgTime });
    totalRenderTime += avgTime;
    totalRenders += 1;

    if (avgTime <= RENDER_TIME_BUDGET) {
      withinBudget += 1;
    } else {
      exceedingBudget += 1;
    }
  });

  // Sort by average time descending
  componentAverages.sort((a, b) => b.avgTime - a.avgTime);

  return {
    totalComponents: components.length,
    componentsWithinBudget: withinBudget,
    componentsExceedingBudget: exceedingBudget,
    averageRenderTime: totalRenders > 0 ? Math.round((totalRenderTime / totalRenders) * 100) / 100 : 0,
    slowestComponents: componentAverages.slice(0, 5),
  };
}

/**
 * Clear all render metrics
 */
export function clearRenderMetrics(): void {
  globalMetricsStore.clear();
}

/**
 * Hook to track render performance with automatic cleanup
 */
export function useRenderProfiler(componentName: string): void {
  const renderStartRef = useRef<number>(0);
  
  // Mark render start
  renderStartRef.current = performance.now();

  useEffect(() => {
    const renderTime = performance.now() - renderStartRef.current;
    
    if (import.meta.env.DEV && renderTime > RENDER_TIME_BUDGET) {
      console.warn(
        `[Performance Warning] ${componentName} render took ${renderTime.toFixed(2)}ms (budget: ${RENDER_TIME_BUDGET}ms)`
      );
    }
  });
}

export { RENDER_TIME_BUDGET, WARNING_THRESHOLD };
