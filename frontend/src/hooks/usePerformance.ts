/**
 * Performance Monitoring Hook
 *
 * React hook for accessing and monitoring Web Vitals performance metrics.
 */

import { useState, useEffect, useCallback } from 'react'
import {
  performanceCollector,
  getPerformanceSummary,
  type WebVitalsMetrics,
  type PerformanceMetric,
} from '@/utils/performance'

interface UsePerformanceResult {
  /** Current performance metrics */
  metrics: WebVitalsMetrics
  /** Overall performance score (0-100) */
  score: number
  /** Overall performance rating */
  rating: 'good' | 'needs-improvement' | 'poor'
  /** Whether metrics are still being collected */
  isCollecting: boolean
  /** Refresh metrics */
  refresh: () => void
}

/**
 * Hook to access Web Vitals performance metrics
 */
export function usePerformance(): UsePerformanceResult {
  const [metrics, setMetrics] = useState<WebVitalsMetrics>({})
  const [isCollecting, setIsCollecting] = useState(true)

  useEffect(() => {
    // Subscribe to metric updates
    const unsubscribe = performanceCollector.subscribe((updatedMetrics) => {
      setMetrics(updatedMetrics)
    })

    // Get initial metrics
    setMetrics(performanceCollector.getMetrics())

    // Stop collecting after 10 seconds (most metrics should be collected by then)
    const timeout = setTimeout(() => {
      setIsCollecting(false)
    }, 10000)

    return () => {
      unsubscribe()
      clearTimeout(timeout)
    }
  }, [])

  const refresh = useCallback(() => {
    setMetrics(performanceCollector.getMetrics())
  }, [])

  const summary = getPerformanceSummary()

  return {
    metrics,
    score: summary.score,
    rating: summary.rating,
    isCollecting,
    refresh,
  }
}

/**
 * Hook to measure component render performance
 */
export function useRenderPerformance(componentName: string): void {
  useEffect(() => {
    const startTime = performance.now()

    return () => {
      const endTime = performance.now()
      const renderTime = endTime - startTime

      if (process.env.NODE_ENV === 'development' && renderTime > 16) {
        // Log slow renders (> 16ms = < 60fps)
        console.warn(
          `[Performance] ${componentName} render took ${renderTime.toFixed(2)}ms`
        )
      }
    }
  })
}

/**
 * Hook to track API call performance
 */
export function useApiPerformance(): {
  trackApiCall: <T>(
    name: string,
    promise: Promise<T>
  ) => Promise<T>
  getApiMetrics: () => ApiMetrics[]
} {
  const [apiMetrics, setApiMetrics] = useState<ApiMetrics[]>([])

  const trackApiCall = useCallback(
    async <T,>(name: string, promise: Promise<T>): Promise<T> => {
      const startTime = performance.now()

      try {
        const result = await promise
        const duration = performance.now() - startTime

        const metric: ApiMetrics = {
          name,
          duration,
          success: true,
          timestamp: Date.now(),
        }

        setApiMetrics((prev) => [...prev.slice(-99), metric])

        if (process.env.NODE_ENV === 'development' && duration > 1000) {
          console.warn(
            `[Performance] API call "${name}" took ${duration.toFixed(2)}ms`
          )
        }

        return result
      } catch (error) {
        const duration = performance.now() - startTime

        const metric: ApiMetrics = {
          name,
          duration,
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
          timestamp: Date.now(),
        }

        setApiMetrics((prev) => [...prev.slice(-99), metric])

        throw error
      }
    },
    []
  )

  const getApiMetrics = useCallback(() => apiMetrics, [apiMetrics])

  return { trackApiCall, getApiMetrics }
}

interface ApiMetrics {
  name: string
  duration: number
  success: boolean
  error?: string
  timestamp: number
}

/**
 * Hook to monitor memory usage
 */
export function useMemoryMonitor(): {
  usedJSHeapSize: number
  totalJSHeapSize: number
  jsHeapSizeLimit: number
  usagePercentage: number
} | null {
  const [memory, setMemory] = useState<{
    usedJSHeapSize: number
    totalJSHeapSize: number
    jsHeapSizeLimit: number
    usagePercentage: number
  } | null>(null)

  useEffect(() => {
    const updateMemory = () => {
      if ('memory' in performance) {
        const memoryInfo = (
          performance as Performance & {
            memory: {
              usedJSHeapSize: number
              totalJSHeapSize: number
              jsHeapSizeLimit: number
            }
          }
        ).memory

        setMemory({
          usedJSHeapSize: memoryInfo.usedJSHeapSize,
          totalJSHeapSize: memoryInfo.totalJSHeapSize,
          jsHeapSizeLimit: memoryInfo.jsHeapSizeLimit,
          usagePercentage:
            (memoryInfo.usedJSHeapSize / memoryInfo.jsHeapSizeLimit) * 100,
        })
      }
    }

    updateMemory()
    const interval = setInterval(updateMemory, 5000)

    return () => clearInterval(interval)
  }, [])

  return memory
}

/**
 * Hook to detect slow network
 */
export function useNetworkInfo(): {
  effectiveType: string
  downlink: number
  rtt: number
  saveData: boolean
  isSlowNetwork: boolean
} | null {
  const [networkInfo, setNetworkInfo] = useState<{
    effectiveType: string
    downlink: number
    rtt: number
    saveData: boolean
    isSlowNetwork: boolean
  } | null>(null)

  useEffect(() => {
    const connection =
      'connection' in navigator
        ? (
            navigator as Navigator & {
              connection: {
                effectiveType: string
                downlink: number
                rtt: number
                saveData: boolean
                addEventListener: (
                  type: string,
                  listener: EventListener
                ) => void
                removeEventListener: (
                  type: string,
                  listener: EventListener
                ) => void
              }
            }
          ).connection
        : null

    if (!connection) return

    const updateNetworkInfo = () => {
      setNetworkInfo({
        effectiveType: connection.effectiveType,
        downlink: connection.downlink,
        rtt: connection.rtt,
        saveData: connection.saveData,
        isSlowNetwork:
          connection.effectiveType === 'slow-2g' ||
          connection.effectiveType === '2g',
      })
    }

    updateNetworkInfo()
    connection.addEventListener('change', updateNetworkInfo)

    return () => {
      connection.removeEventListener('change', updateNetworkInfo)
    }
  }, [])

  return networkInfo
}

/**
 * Format bytes to human readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

/**
 * Format milliseconds to human readable string
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}
