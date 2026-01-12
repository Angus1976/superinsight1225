/**
 * usePageLoadTime Hook
 * 
 * Tracks and reports page load time to ensure < 3 second target.
 * Provides real-time feedback on page performance.
 */

import { useEffect, useState, useRef } from 'react';
import { useLocation } from 'react-router-dom';

interface PageLoadMetrics {
  loadTime: number;
  isWithinBudget: boolean;
  route: string;
  timestamp: number;
}

const LOAD_TIME_BUDGET = 3000; // 3 seconds target

/**
 * Hook to track page load time
 */
export function usePageLoadTime(): PageLoadMetrics | null {
  const location = useLocation();
  const [metrics, setMetrics] = useState<PageLoadMetrics | null>(null);
  const startTimeRef = useRef<number>(performance.now());
  const routeRef = useRef<string>(location.pathname);

  useEffect(() => {
    // Reset start time on route change
    startTimeRef.current = performance.now();
    routeRef.current = location.pathname;
  }, [location.pathname]);

  useEffect(() => {
    // Measure load time after component mounts
    const measureLoadTime = () => {
      const loadTime = performance.now() - startTimeRef.current;
      const newMetrics: PageLoadMetrics = {
        loadTime: Math.round(loadTime),
        isWithinBudget: loadTime <= LOAD_TIME_BUDGET,
        route: routeRef.current,
        timestamp: Date.now(),
      };

      setMetrics(newMetrics);

      // Log in development
      if (import.meta.env.DEV) {
        const status = newMetrics.isWithinBudget ? '✓' : '✗';
        const color = newMetrics.isWithinBudget ? 'green' : 'red';
        console.log(
          `%c[Page Load] ${status} ${newMetrics.route}: ${newMetrics.loadTime}ms`,
          `color: ${color}; font-weight: bold;`
        );
      }
    };

    // Use requestAnimationFrame to measure after paint
    requestAnimationFrame(() => {
      requestAnimationFrame(measureLoadTime);
    });
  }, [location.pathname]);

  return metrics;
}

/**
 * Hook to track navigation performance
 */
export function useNavigationTiming(): PerformanceNavigationTiming | null {
  const [timing, setTiming] = useState<PerformanceNavigationTiming | null>(null);

  useEffect(() => {
    const getTiming = () => {
      const entries = performance.getEntriesByType('navigation');
      if (entries.length > 0) {
        setTiming(entries[0] as PerformanceNavigationTiming);
      }
    };

    // Wait for navigation timing to be available
    if (document.readyState === 'complete') {
      getTiming();
    } else {
      window.addEventListener('load', getTiming);
      return () => window.removeEventListener('load', getTiming);
    }
  }, []);

  return timing;
}

/**
 * Get detailed page load breakdown
 */
export function getPageLoadBreakdown(): {
  dns: number;
  tcp: number;
  ttfb: number;
  download: number;
  domParsing: number;
  domInteractive: number;
  domComplete: number;
  total: number;
} | null {
  const entries = performance.getEntriesByType('navigation');
  if (entries.length === 0) return null;

  const timing = entries[0] as PerformanceNavigationTiming;

  return {
    dns: timing.domainLookupEnd - timing.domainLookupStart,
    tcp: timing.connectEnd - timing.connectStart,
    ttfb: timing.responseStart - timing.requestStart,
    download: timing.responseEnd - timing.responseStart,
    domParsing: timing.domInteractive - timing.responseEnd,
    domInteractive: timing.domInteractive - timing.fetchStart,
    domComplete: timing.domComplete - timing.fetchStart,
    total: timing.loadEventEnd - timing.fetchStart,
  };
}

/**
 * Performance budget checker hook
 */
export function usePerformanceBudget(budget: number = LOAD_TIME_BUDGET): {
  isWithinBudget: boolean;
  loadTime: number;
  budgetRemaining: number;
} {
  const metrics = usePageLoadTime();

  return {
    isWithinBudget: metrics ? metrics.loadTime <= budget : true,
    loadTime: metrics?.loadTime || 0,
    budgetRemaining: budget - (metrics?.loadTime || 0),
  };
}
