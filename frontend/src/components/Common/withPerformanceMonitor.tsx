/**
 * withPerformanceMonitor HOC
 * 
 * Higher-Order Component that wraps components with performance monitoring
 * to ensure render time stays under 100ms budget.
 */

import React, { memo, useRef, useEffect, ComponentType, forwardRef } from 'react';

// Render time budget in milliseconds
const RENDER_TIME_BUDGET = 100;

interface PerformanceMonitorOptions {
  /** Component display name for logging */
  displayName?: string;
  /** Custom render time budget in ms */
  budget?: number;
  /** Enable console logging */
  enableLogging?: boolean;
  /** Enable React.memo optimization */
  enableMemo?: boolean;
  /** Custom comparison function for memo */
  arePropsEqual?: (prevProps: any, nextProps: any) => boolean;
}

interface RenderStats {
  renderCount: number;
  totalRenderTime: number;
  maxRenderTime: number;
  minRenderTime: number;
  lastRenderTime: number;
}

// Global stats store
const componentStats = new Map<string, RenderStats>();

/**
 * Get component render statistics
 */
export function getComponentStats(componentName: string): RenderStats | undefined {
  return componentStats.get(componentName);
}

/**
 * Get all component statistics
 */
export function getAllComponentStats(): Map<string, RenderStats> {
  return new Map(componentStats);
}

/**
 * Clear all component statistics
 */
export function clearComponentStats(): void {
  componentStats.clear();
}

/**
 * Higher-Order Component for performance monitoring
 */
export function withPerformanceMonitor<P extends object>(
  WrappedComponent: ComponentType<P>,
  options: PerformanceMonitorOptions = {}
): ComponentType<P> {
  const {
    displayName = WrappedComponent.displayName || WrappedComponent.name || 'Component',
    budget = RENDER_TIME_BUDGET,
    enableLogging = import.meta.env.DEV,
    enableMemo = true,
    arePropsEqual,
  } = options;

  // Initialize stats for this component
  if (!componentStats.has(displayName)) {
    componentStats.set(displayName, {
      renderCount: 0,
      totalRenderTime: 0,
      maxRenderTime: 0,
      minRenderTime: Infinity,
      lastRenderTime: 0,
    });
  }

  const PerformanceMonitoredComponent = forwardRef<any, P>((props, ref) => {
    const renderStartRef = useRef<number>(performance.now());
    
    // Mark render start
    renderStartRef.current = performance.now();

    useEffect(() => {
      // Measure render time after paint
      const measureRender = () => {
        const renderTime = performance.now() - renderStartRef.current;
        
        // Update stats
        const stats = componentStats.get(displayName)!;
        stats.renderCount += 1;
        stats.totalRenderTime += renderTime;
        stats.lastRenderTime = renderTime;
        stats.maxRenderTime = Math.max(stats.maxRenderTime, renderTime);
        stats.minRenderTime = Math.min(stats.minRenderTime, renderTime);

        // Log performance
        if (enableLogging) {
          const isWithinBudget = renderTime <= budget;
          const budgetUsage = (renderTime / budget) * 100;

          if (!isWithinBudget) {
            console.warn(
              `%c[Perf] ✗ ${displayName}: ${renderTime.toFixed(2)}ms exceeds ${budget}ms budget`,
              'color: red; font-weight: bold;'
            );
          } else if (budgetUsage >= 80) {
            console.log(
              `%c[Perf] ⚠ ${displayName}: ${renderTime.toFixed(2)}ms (${budgetUsage.toFixed(0)}% of budget)`,
              'color: orange;'
            );
          }
        }
      };

      requestAnimationFrame(() => {
        requestAnimationFrame(measureRender);
      });
    });

    // Pass ref to wrapped component if it accepts refs
    const componentProps = ref ? { ...props, ref } : props;
    return <WrappedComponent {...(componentProps as P)} />;
  });

  PerformanceMonitoredComponent.displayName = `withPerformanceMonitor(${displayName})`;

  // Apply memo optimization if enabled
  if (enableMemo) {
    return memo(PerformanceMonitoredComponent, arePropsEqual) as ComponentType<P>;
  }

  return PerformanceMonitoredComponent as ComponentType<P>;
}

/**
 * Create a memoized component with shallow comparison
 */
export function createOptimizedComponent<P extends object>(
  Component: ComponentType<P>,
  displayName?: string
): React.MemoExoticComponent<ComponentType<P>> {
  const MemoizedComponent = memo(Component);
  MemoizedComponent.displayName = displayName || Component.displayName || Component.name;
  return MemoizedComponent;
}

/**
 * Deep comparison function for complex props
 */
export function deepPropsEqual<P extends object>(prevProps: P, nextProps: P): boolean {
  const prevKeys = Object.keys(prevProps) as Array<keyof P>;
  const nextKeys = Object.keys(nextProps) as Array<keyof P>;

  if (prevKeys.length !== nextKeys.length) {
    return false;
  }

  for (const key of prevKeys) {
    const prevValue = prevProps[key];
    const nextValue = nextProps[key];

    // Handle functions - compare by reference
    if (typeof prevValue === 'function' && typeof nextValue === 'function') {
      if (prevValue !== nextValue) {
        return false;
      }
      continue;
    }

    // Handle arrays
    if (Array.isArray(prevValue) && Array.isArray(nextValue)) {
      if (prevValue.length !== nextValue.length) {
        return false;
      }
      for (let i = 0; i < prevValue.length; i++) {
        if (prevValue[i] !== nextValue[i]) {
          return false;
        }
      }
      continue;
    }

    // Handle objects (shallow comparison for nested objects)
    if (
      typeof prevValue === 'object' &&
      prevValue !== null &&
      typeof nextValue === 'object' &&
      nextValue !== null
    ) {
      const prevObjKeys = Object.keys(prevValue);
      const nextObjKeys = Object.keys(nextValue);
      
      if (prevObjKeys.length !== nextObjKeys.length) {
        return false;
      }
      
      for (const objKey of prevObjKeys) {
        if ((prevValue as any)[objKey] !== (nextValue as any)[objKey]) {
          return false;
        }
      }
      continue;
    }

    // Primitive comparison
    if (prevValue !== nextValue) {
      return false;
    }
  }

  return true;
}

/**
 * Shallow props comparison (default React.memo behavior)
 */
export function shallowPropsEqual<P extends object>(prevProps: P, nextProps: P): boolean {
  const prevKeys = Object.keys(prevProps) as Array<keyof P>;
  const nextKeys = Object.keys(nextProps) as Array<keyof P>;

  if (prevKeys.length !== nextKeys.length) {
    return false;
  }

  for (const key of prevKeys) {
    if (prevProps[key] !== nextProps[key]) {
      return false;
    }
  }

  return true;
}

export default withPerformanceMonitor;
