/**
 * PerformanceMonitor - Monitors iframe performance metrics
 * Tracks loading time, memory usage, CPU usage, and other performance indicators
 */

export interface PerformanceMetrics {
  loadTime: number;
  memoryUsage: number;
  cpuUsage: number;
  networkRequests: number;
  errorCount: number;
  timestamp: number;
}

export interface PerformanceThresholds {
  maxLoadTime?: number; // milliseconds
  maxMemoryUsage?: number; // MB
  maxCpuUsage?: number; // percentage
  maxErrorRate?: number; // percentage
}

export interface PerformanceAlert {
  type: 'load_time' | 'memory' | 'cpu' | 'error_rate' | 'network';
  severity: 'warning' | 'critical';
  message: string;
  value: number;
  threshold: number;
  timestamp: number;
  iframeId: string;
}

export interface PerformanceReport {
  iframeId: string;
  startTime: number;
  endTime: number;
  metrics: PerformanceMetrics[];
  alerts: PerformanceAlert[];
  summary: {
    avgLoadTime: number;
    avgMemoryUsage: number;
    avgCpuUsage: number;
    totalErrors: number;
    uptime: number;
  };
}

export interface MonitorConfig {
  sampleInterval?: number; // milliseconds
  enableMemoryMonitoring?: boolean;
  enableCpuMonitoring?: boolean;
  enableNetworkMonitoring?: boolean;
  thresholds?: PerformanceThresholds;
  maxHistorySize?: number;
  enableAlerts?: boolean;
  alertCallback?: (alert: PerformanceAlert) => void;
}

export class PerformanceMonitor {
  private config: Required<MonitorConfig>;
  private metrics: Map<string, PerformanceMetrics[]> = new Map();
  private alerts: Map<string, PerformanceAlert[]> = new Map();
  private observers: Map<string, PerformanceObserver> = new Map();
  private intervals: Map<string, NodeJS.Timeout> = new Map();
  private startTimes: Map<string, number> = new Map();
  private networkRequests: Map<string, number> = new Map();
  private errorCounts: Map<string, number> = new Map();

  constructor(config: MonitorConfig = {}) {
    this.config = {
      sampleInterval: 1000, // 1 second
      enableMemoryMonitoring: true,
      enableCpuMonitoring: true,
      enableNetworkMonitoring: true,
      thresholds: {
        maxLoadTime: 5000, // 5 seconds
        maxMemoryUsage: 100, // 100MB
        maxCpuUsage: 80, // 80%
        maxErrorRate: 5, // 5%
      },
      maxHistorySize: 1000,
      enableAlerts: true,
      alertCallback: undefined,
      ...config,
    };
  }

  /**
   * Start monitoring iframe performance
   */
  startMonitoring(iframeId: string, iframe: HTMLIFrameElement): void {
    if (this.intervals.has(iframeId)) {
      this.stopMonitoring(iframeId);
    }

    this.startTimes.set(iframeId, Date.now());
    this.metrics.set(iframeId, []);
    this.alerts.set(iframeId, []);
    this.networkRequests.set(iframeId, 0);
    this.errorCounts.set(iframeId, 0);

    // Setup performance observer for navigation timing
    this.setupPerformanceObserver(iframeId);

    // Setup periodic monitoring
    const interval = setInterval(() => {
      this.collectMetrics(iframeId, iframe);
    }, this.config.sampleInterval);

    this.intervals.set(iframeId, interval);

    // Monitor iframe load event
    this.monitorLoadTime(iframeId, iframe);

    // Monitor network requests
    if (this.config.enableNetworkMonitoring) {
      this.monitorNetworkRequests(iframeId);
    }
  }

  /**
   * Stop monitoring iframe performance
   */
  stopMonitoring(iframeId: string): void {
    const interval = this.intervals.get(iframeId);
    if (interval) {
      clearInterval(interval);
      this.intervals.delete(iframeId);
    }

    const observer = this.observers.get(iframeId);
    if (observer) {
      observer.disconnect();
      this.observers.delete(iframeId);
    }

    this.startTimes.delete(iframeId);
    this.networkRequests.delete(iframeId);
    this.errorCounts.delete(iframeId);
  }

  /**
   * Get current metrics for iframe
   */
  getCurrentMetrics(iframeId: string): PerformanceMetrics | null {
    const metrics = this.metrics.get(iframeId);
    return metrics && metrics.length > 0 ? metrics[metrics.length - 1] : null;
  }

  /**
   * Get all metrics for iframe
   */
  getAllMetrics(iframeId: string): PerformanceMetrics[] {
    return this.metrics.get(iframeId) || [];
  }

  /**
   * Get alerts for iframe
   */
  getAlerts(iframeId: string): PerformanceAlert[] {
    return this.alerts.get(iframeId) || [];
  }

  /**
   * Generate performance report
   */
  generateReport(iframeId: string): PerformanceReport | null {
    const metrics = this.metrics.get(iframeId);
    const alerts = this.alerts.get(iframeId);
    const startTime = this.startTimes.get(iframeId);

    if (!metrics || !alerts || !startTime) {
      return null;
    }

    const loadTimes = metrics.map(m => m.loadTime).filter(t => t > 0);
    const memoryUsages = metrics.map(m => m.memoryUsage).filter(m => m > 0);
    const cpuUsages = metrics.map(m => m.cpuUsage).filter(c => c > 0);

    return {
      iframeId,
      startTime,
      endTime: Date.now(),
      metrics,
      alerts,
      summary: {
        avgLoadTime: loadTimes.length > 0 ? loadTimes.reduce((a, b) => a + b, 0) / loadTimes.length : 0,
        avgMemoryUsage: memoryUsages.length > 0 ? memoryUsages.reduce((a, b) => a + b, 0) / memoryUsages.length : 0,
        avgCpuUsage: cpuUsages.length > 0 ? cpuUsages.reduce((a, b) => a + b, 0) / cpuUsages.length : 0,
        totalErrors: this.errorCounts.get(iframeId) || 0,
        uptime: Date.now() - startTime,
      },
    };
  }

  /**
   * Record error for iframe
   */
  recordError(iframeId: string, error: Error): void {
    const currentCount = this.errorCounts.get(iframeId) || 0;
    this.errorCounts.set(iframeId, currentCount + 1);

    // Check error rate threshold
    const metrics = this.metrics.get(iframeId);
    if (metrics && metrics.length > 0) {
      const errorRate = (currentCount / metrics.length) * 100;
      if (errorRate > (this.config.thresholds.maxErrorRate || 5)) {
        this.createAlert(iframeId, {
          type: 'error_rate',
          severity: 'critical',
          message: `Error rate exceeded threshold: ${errorRate.toFixed(1)}%`,
          value: errorRate,
          threshold: this.config.thresholds.maxErrorRate || 5,
          timestamp: Date.now(),
          iframeId,
        });
      }
    }
  }

  /**
   * Setup performance observer
   */
  private setupPerformanceObserver(iframeId: string): void {
    if (!('PerformanceObserver' in window)) {
      console.warn('PerformanceObserver not supported');
      return;
    }

    try {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry) => {
          if (entry.entryType === 'navigation') {
            this.processNavigationEntry(iframeId, entry as PerformanceNavigationTiming);
          } else if (entry.entryType === 'resource') {
            this.processResourceEntry(iframeId, entry as PerformanceResourceTiming);
          }
        });
      });

      observer.observe({ entryTypes: ['navigation', 'resource'] });
      this.observers.set(iframeId, observer);
    } catch (error) {
      console.warn('Failed to setup PerformanceObserver:', error);
    }
  }

  /**
   * Process navigation timing entry
   */
  private processNavigationEntry(iframeId: string, entry: PerformanceNavigationTiming): void {
    const loadTime = entry.loadEventEnd - entry.loadEventStart;
    
    if (loadTime > (this.config.thresholds.maxLoadTime || 5000)) {
      this.createAlert(iframeId, {
        type: 'load_time',
        severity: loadTime > 10000 ? 'critical' : 'warning',
        message: `Load time exceeded threshold: ${loadTime}ms`,
        value: loadTime,
        threshold: this.config.thresholds.maxLoadTime || 5000,
        timestamp: Date.now(),
        iframeId,
      });
    }
  }

  /**
   * Process resource timing entry
   */
  private processResourceEntry(iframeId: string, entry: PerformanceResourceTiming): void {
    const currentCount = this.networkRequests.get(iframeId) || 0;
    this.networkRequests.set(iframeId, currentCount + 1);
  }

  /**
   * Monitor iframe load time
   */
  private monitorLoadTime(iframeId: string, iframe: HTMLIFrameElement): void {
    const startTime = Date.now();

    const onLoad = () => {
      const loadTime = Date.now() - startTime;
      
      if (loadTime > (this.config.thresholds.maxLoadTime || 5000)) {
        this.createAlert(iframeId, {
          type: 'load_time',
          severity: loadTime > 10000 ? 'critical' : 'warning',
          message: `Iframe load time exceeded threshold: ${loadTime}ms`,
          value: loadTime,
          threshold: this.config.thresholds.maxLoadTime || 5000,
          timestamp: Date.now(),
          iframeId,
        });
      }

      iframe.removeEventListener('load', onLoad);
    };

    iframe.addEventListener('load', onLoad);
  }

  /**
   * Monitor network requests
   */
  private monitorNetworkRequests(iframeId: string): void {
    // This is a simplified implementation
    // In a real scenario, you might need to intercept fetch/XMLHttpRequest
    // or use other methods to monitor network activity
  }

  /**
   * Collect performance metrics
   */
  private collectMetrics(iframeId: string, iframe: HTMLIFrameElement): void {
    const metrics: PerformanceMetrics = {
      loadTime: 0,
      memoryUsage: this.getMemoryUsage(),
      cpuUsage: this.getCpuUsage(),
      networkRequests: this.networkRequests.get(iframeId) || 0,
      errorCount: this.errorCounts.get(iframeId) || 0,
      timestamp: Date.now(),
    };

    // Add to metrics history
    const metricsArray = this.metrics.get(iframeId) || [];
    metricsArray.push(metrics);

    // Limit history size
    if (metricsArray.length > this.config.maxHistorySize) {
      metricsArray.shift();
    }

    this.metrics.set(iframeId, metricsArray);

    // Check thresholds
    this.checkThresholds(iframeId, metrics);
  }

  /**
   * Get memory usage (approximation)
   */
  private getMemoryUsage(): number {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      return memory.usedJSHeapSize / (1024 * 1024); // Convert to MB
    }
    return 0;
  }

  /**
   * Get CPU usage (approximation)
   */
  private getCpuUsage(): number {
    // This is a simplified implementation
    // Real CPU monitoring would require more sophisticated techniques
    if ('timing' in performance) {
      const timing = performance.timing;
      const total = timing.loadEventEnd - timing.navigationStart;
      const processing = timing.domComplete - timing.domLoading;
      return total > 0 ? (processing / total) * 100 : 0;
    }
    return 0;
  }

  /**
   * Check performance thresholds
   */
  private checkThresholds(iframeId: string, metrics: PerformanceMetrics): void {
    if (!this.config.enableAlerts) return;

    const thresholds = this.config.thresholds;

    // Check memory usage
    if (thresholds.maxMemoryUsage && metrics.memoryUsage > thresholds.maxMemoryUsage) {
      this.createAlert(iframeId, {
        type: 'memory',
        severity: metrics.memoryUsage > thresholds.maxMemoryUsage * 1.5 ? 'critical' : 'warning',
        message: `Memory usage exceeded threshold: ${metrics.memoryUsage.toFixed(1)}MB`,
        value: metrics.memoryUsage,
        threshold: thresholds.maxMemoryUsage,
        timestamp: Date.now(),
        iframeId,
      });
    }

    // Check CPU usage
    if (thresholds.maxCpuUsage && metrics.cpuUsage > thresholds.maxCpuUsage) {
      this.createAlert(iframeId, {
        type: 'cpu',
        severity: metrics.cpuUsage > thresholds.maxCpuUsage * 1.2 ? 'critical' : 'warning',
        message: `CPU usage exceeded threshold: ${metrics.cpuUsage.toFixed(1)}%`,
        value: metrics.cpuUsage,
        threshold: thresholds.maxCpuUsage,
        timestamp: Date.now(),
        iframeId,
      });
    }
  }

  /**
   * Create performance alert
   */
  private createAlert(iframeId: string, alert: PerformanceAlert): void {
    const alerts = this.alerts.get(iframeId) || [];
    alerts.push(alert);

    // Limit alerts history
    if (alerts.length > this.config.maxHistorySize) {
      alerts.shift();
    }

    this.alerts.set(iframeId, alerts);

    // Call alert callback if provided
    if (this.config.alertCallback) {
      try {
        this.config.alertCallback(alert);
      } catch (error) {
        console.error('Error in alert callback:', error);
      }
    }
  }

  /**
   * Clear metrics and alerts for iframe
   */
  clearHistory(iframeId: string): void {
    this.metrics.set(iframeId, []);
    this.alerts.set(iframeId, []);
    this.errorCounts.set(iframeId, 0);
    this.networkRequests.set(iframeId, 0);
  }

  /**
   * Get performance summary for all monitored iframes
   */
  getOverallSummary(): {
    totalIframes: number;
    totalAlerts: number;
    avgMemoryUsage: number;
    avgCpuUsage: number;
    totalErrors: number;
  } {
    const allMetrics: PerformanceMetrics[] = [];
    let totalAlerts = 0;
    let totalErrors = 0;

    for (const [iframeId, metrics] of this.metrics) {
      allMetrics.push(...metrics);
      totalAlerts += (this.alerts.get(iframeId) || []).length;
      totalErrors += this.errorCounts.get(iframeId) || 0;
    }

    const memoryUsages = allMetrics.map(m => m.memoryUsage).filter(m => m > 0);
    const cpuUsages = allMetrics.map(m => m.cpuUsage).filter(c => c > 0);

    return {
      totalIframes: this.metrics.size,
      totalAlerts,
      avgMemoryUsage: memoryUsages.length > 0 ? memoryUsages.reduce((a, b) => a + b, 0) / memoryUsages.length : 0,
      avgCpuUsage: cpuUsages.length > 0 ? cpuUsages.reduce((a, b) => a + b, 0) / cpuUsages.length : 0,
      totalErrors,
    };
  }

  /**
   * Destroy monitor and cleanup resources
   */
  destroy(): void {
    // Stop all monitoring
    for (const iframeId of this.intervals.keys()) {
      this.stopMonitoring(iframeId);
    }

    // Clear all data
    this.metrics.clear();
    this.alerts.clear();
    this.startTimes.clear();
    this.networkRequests.clear();
    this.errorCounts.clear();
  }
}