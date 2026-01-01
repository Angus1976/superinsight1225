/**
 * Performance Monitoring Utilities
 *
 * Provides Web Vitals monitoring and performance metrics collection
 * for tracking and optimizing frontend performance.
 */

// Performance metric types
export interface PerformanceMetric {
  name: string
  value: number
  rating: 'good' | 'needs-improvement' | 'poor'
  delta: number
  id: string
  navigationType: string
}

export interface WebVitalsMetrics {
  // Core Web Vitals
  LCP?: PerformanceMetric // Largest Contentful Paint
  FID?: PerformanceMetric // First Input Delay
  CLS?: PerformanceMetric // Cumulative Layout Shift
  // Additional metrics
  FCP?: PerformanceMetric // First Contentful Paint
  TTFB?: PerformanceMetric // Time to First Byte
  INP?: PerformanceMetric // Interaction to Next Paint
}

// Thresholds based on Google's Core Web Vitals
const THRESHOLDS = {
  LCP: { good: 2500, needsImprovement: 4000 },
  FID: { good: 100, needsImprovement: 300 },
  CLS: { good: 0.1, needsImprovement: 0.25 },
  FCP: { good: 1800, needsImprovement: 3000 },
  TTFB: { good: 800, needsImprovement: 1800 },
  INP: { good: 200, needsImprovement: 500 },
}

/**
 * Get rating based on metric value and thresholds
 */
function getRating(
  name: keyof typeof THRESHOLDS,
  value: number
): 'good' | 'needs-improvement' | 'poor' {
  const threshold = THRESHOLDS[name]
  if (value <= threshold.good) return 'good'
  if (value <= threshold.needsImprovement) return 'needs-improvement'
  return 'poor'
}

/**
 * Performance metrics collector
 */
class PerformanceCollector {
  private metrics: WebVitalsMetrics = {}
  private observers: Array<(metrics: WebVitalsMetrics) => void> = []

  /**
   * Add a metric
   */
  addMetric(metric: PerformanceMetric): void {
    const name = metric.name as keyof WebVitalsMetrics
    this.metrics[name] = metric
    this.notifyObservers()
  }

  /**
   * Get all collected metrics
   */
  getMetrics(): WebVitalsMetrics {
    return { ...this.metrics }
  }

  /**
   * Subscribe to metric updates
   */
  subscribe(callback: (metrics: WebVitalsMetrics) => void): () => void {
    this.observers.push(callback)
    return () => {
      this.observers = this.observers.filter((cb) => cb !== callback)
    }
  }

  /**
   * Notify all observers of metric updates
   */
  private notifyObservers(): void {
    const metrics = this.getMetrics()
    this.observers.forEach((cb) => cb(metrics))
  }

  /**
   * Clear all metrics
   */
  clear(): void {
    this.metrics = {}
    this.notifyObservers()
  }
}

// Global performance collector instance
export const performanceCollector = new PerformanceCollector()

/**
 * Report handler for Web Vitals
 */
type ReportHandler = (metric: PerformanceMetric) => void

/**
 * Generate unique ID for metric
 */
function generateId(): string {
  return `v3-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

/**
 * Get navigation type
 */
function getNavigationType(): string {
  if (typeof window === 'undefined') return 'navigate'

  const navigation = performance.getEntriesByType(
    'navigation'
  )[0] as PerformanceNavigationTiming

  return navigation?.type || 'navigate'
}

/**
 * Observe Largest Contentful Paint (LCP)
 */
export function onLCP(onReport: ReportHandler): void {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) return

  try {
    const observer = new PerformanceObserver((entryList) => {
      const entries = entryList.getEntries()
      const lastEntry = entries[entries.length - 1] as PerformanceEntry & {
        startTime: number
      }

      if (lastEntry) {
        const value = lastEntry.startTime
        const metric: PerformanceMetric = {
          name: 'LCP',
          value,
          rating: getRating('LCP', value),
          delta: value,
          id: generateId(),
          navigationType: getNavigationType(),
        }
        performanceCollector.addMetric(metric)
        onReport(metric)
      }
    })

    observer.observe({ type: 'largest-contentful-paint', buffered: true })
  } catch (e) {
    // PerformanceObserver not supported
  }
}

/**
 * Observe First Input Delay (FID)
 */
export function onFID(onReport: ReportHandler): void {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) return

  try {
    const observer = new PerformanceObserver((entryList) => {
      const entries = entryList.getEntries()
      const firstEntry = entries[0] as PerformanceEntry & {
        processingStart: number
        startTime: number
      }

      if (firstEntry) {
        const value = firstEntry.processingStart - firstEntry.startTime
        const metric: PerformanceMetric = {
          name: 'FID',
          value,
          rating: getRating('FID', value),
          delta: value,
          id: generateId(),
          navigationType: getNavigationType(),
        }
        performanceCollector.addMetric(metric)
        onReport(metric)
      }
    })

    observer.observe({ type: 'first-input', buffered: true })
  } catch (e) {
    // PerformanceObserver not supported
  }
}

/**
 * Observe Cumulative Layout Shift (CLS)
 */
export function onCLS(onReport: ReportHandler): void {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) return

  let clsValue = 0
  let sessionValue = 0
  let sessionEntries: PerformanceEntry[] = []

  try {
    const observer = new PerformanceObserver((entryList) => {
      const entries = entryList.getEntries() as Array<
        PerformanceEntry & { hadRecentInput: boolean; value: number }
      >

      for (const entry of entries) {
        if (!entry.hadRecentInput) {
          const firstSessionEntry = sessionEntries[0] as
            | (PerformanceEntry & { startTime: number })
            | undefined
          const lastSessionEntry = sessionEntries[sessionEntries.length - 1] as
            | (PerformanceEntry & { startTime: number })
            | undefined

          if (
            sessionValue &&
            firstSessionEntry &&
            lastSessionEntry &&
            entry.startTime - lastSessionEntry.startTime < 1000 &&
            entry.startTime - firstSessionEntry.startTime < 5000
          ) {
            sessionValue += entry.value
            sessionEntries.push(entry)
          } else {
            sessionValue = entry.value
            sessionEntries = [entry]
          }

          if (sessionValue > clsValue) {
            clsValue = sessionValue
            const metric: PerformanceMetric = {
              name: 'CLS',
              value: clsValue,
              rating: getRating('CLS', clsValue),
              delta: entry.value,
              id: generateId(),
              navigationType: getNavigationType(),
            }
            performanceCollector.addMetric(metric)
            onReport(metric)
          }
        }
      }
    })

    observer.observe({ type: 'layout-shift', buffered: true })
  } catch (e) {
    // PerformanceObserver not supported
  }
}

/**
 * Observe First Contentful Paint (FCP)
 */
export function onFCP(onReport: ReportHandler): void {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) return

  try {
    const observer = new PerformanceObserver((entryList) => {
      const entries = entryList.getEntriesByName('first-contentful-paint')
      const fcpEntry = entries[0] as PerformanceEntry & { startTime: number }

      if (fcpEntry) {
        const value = fcpEntry.startTime
        const metric: PerformanceMetric = {
          name: 'FCP',
          value,
          rating: getRating('FCP', value),
          delta: value,
          id: generateId(),
          navigationType: getNavigationType(),
        }
        performanceCollector.addMetric(metric)
        onReport(metric)
      }
    })

    observer.observe({ type: 'paint', buffered: true })
  } catch (e) {
    // PerformanceObserver not supported
  }
}

/**
 * Observe Time to First Byte (TTFB)
 */
export function onTTFB(onReport: ReportHandler): void {
  if (typeof window === 'undefined') return

  try {
    const navigation = performance.getEntriesByType(
      'navigation'
    )[0] as PerformanceNavigationTiming

    if (navigation) {
      const value = navigation.responseStart - navigation.requestStart
      const metric: PerformanceMetric = {
        name: 'TTFB',
        value,
        rating: getRating('TTFB', value),
        delta: value,
        id: generateId(),
        navigationType: getNavigationType(),
      }
      performanceCollector.addMetric(metric)
      onReport(metric)
    }
  } catch (e) {
    // Navigation timing not supported
  }
}

/**
 * Initialize all Web Vitals observers
 */
export function initWebVitals(
  onReport?: ReportHandler,
  options?: { reportToConsole?: boolean; reportToAnalytics?: boolean }
): void {
  const { reportToConsole = false, reportToAnalytics = false } = options || {}

  const handler: ReportHandler = (metric) => {
    // Console reporting (development only)
    if (reportToConsole) {
      const color =
        metric.rating === 'good'
          ? 'green'
          : metric.rating === 'needs-improvement'
            ? 'orange'
            : 'red'
      console.log(
        `%c[Web Vitals] ${metric.name}: ${metric.value.toFixed(2)} (${metric.rating})`,
        `color: ${color}; font-weight: bold;`
      )
    }

    // Analytics reporting
    if (reportToAnalytics) {
      // Send to analytics service
      sendToAnalytics(metric)
    }

    // Custom report handler
    onReport?.(metric)
  }

  // Initialize all observers
  onLCP(handler)
  onFID(handler)
  onCLS(handler)
  onFCP(handler)
  onTTFB(handler)
}

/**
 * Send metric to analytics service
 */
function sendToAnalytics(metric: PerformanceMetric): void {
  // Implement analytics reporting here
  // Example: Google Analytics, custom backend, etc.

  // Using Beacon API for reliability
  if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
    const data = JSON.stringify({
      type: 'web-vitals',
      metric: metric.name,
      value: metric.value,
      rating: metric.rating,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent,
    })

    // Replace with your analytics endpoint
    // navigator.sendBeacon('/api/analytics/performance', data)
  }
}

/**
 * Get performance summary
 */
export function getPerformanceSummary(): {
  score: number
  metrics: WebVitalsMetrics
  rating: 'good' | 'needs-improvement' | 'poor'
} {
  const metrics = performanceCollector.getMetrics()

  // Calculate weighted score based on Core Web Vitals
  let totalScore = 0
  let metricCount = 0

  const scoreMap = { good: 100, 'needs-improvement': 50, poor: 0 }

  if (metrics.LCP) {
    totalScore += scoreMap[metrics.LCP.rating] * 0.25
    metricCount += 0.25
  }
  if (metrics.FID) {
    totalScore += scoreMap[metrics.FID.rating] * 0.25
    metricCount += 0.25
  }
  if (metrics.CLS) {
    totalScore += scoreMap[metrics.CLS.rating] * 0.25
    metricCount += 0.25
  }
  if (metrics.FCP) {
    totalScore += scoreMap[metrics.FCP.rating] * 0.15
    metricCount += 0.15
  }
  if (metrics.TTFB) {
    totalScore += scoreMap[metrics.TTFB.rating] * 0.1
    metricCount += 0.1
  }

  const score = metricCount > 0 ? totalScore / metricCount : 0

  let rating: 'good' | 'needs-improvement' | 'poor' = 'good'
  if (score < 50) rating = 'poor'
  else if (score < 90) rating = 'needs-improvement'

  return { score, metrics, rating }
}

/**
 * Performance timing utilities
 */
export const performanceTiming = {
  /**
   * Measure execution time of a function
   */
  async measure<T>(name: string, fn: () => Promise<T>): Promise<T> {
    const start = performance.now()
    try {
      return await fn()
    } finally {
      const duration = performance.now() - start
      console.debug(`[Performance] ${name}: ${duration.toFixed(2)}ms`)
    }
  },

  /**
   * Create a performance mark
   */
  mark(name: string): void {
    performance.mark(name)
  },

  /**
   * Measure between two marks
   */
  measureMarks(name: string, startMark: string, endMark: string): number {
    performance.measure(name, startMark, endMark)
    const measures = performance.getEntriesByName(name, 'measure')
    return measures[measures.length - 1]?.duration || 0
  },

  /**
   * Clear all marks and measures
   */
  clear(): void {
    performance.clearMarks()
    performance.clearMeasures()
  },
}
