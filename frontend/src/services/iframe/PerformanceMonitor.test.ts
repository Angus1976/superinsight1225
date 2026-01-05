/**
 * PerformanceMonitor Performance Tests
 * Tests performance monitoring capabilities and overhead
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { PerformanceMonitor } from './PerformanceMonitor';

// Mock PerformanceObserver
const mockPerformanceObserver = vi.fn();
mockPerformanceObserver.mockImplementation((callback) => ({
  observe: vi.fn(),
  disconnect: vi.fn(),
}));
window.PerformanceObserver = mockPerformanceObserver;

// Mock performance.memory
Object.defineProperty(performance, 'memory', {
  value: {
    usedJSHeapSize: 50 * 1024 * 1024, // 50MB
    totalJSHeapSize: 100 * 1024 * 1024, // 100MB
    jsHeapSizeLimit: 2 * 1024 * 1024 * 1024, // 2GB
  },
  configurable: true,
});

describe('PerformanceMonitor Performance Tests', () => {
  let monitor: PerformanceMonitor;
  let mockIframe: HTMLIFrameElement;

  beforeEach(() => {
    monitor = new PerformanceMonitor({
      sampleInterval: 100, // Fast sampling for tests
      enableMemoryMonitoring: true,
      enableCpuMonitoring: true,
      enableNetworkMonitoring: true,
      thresholds: {
        maxLoadTime: 2000,
        maxMemoryUsage: 100,
        maxCpuUsage: 80,
        maxErrorRate: 5,
      },
      maxHistorySize: 100,
      enableAlerts: true,
    });

    mockIframe = document.createElement('iframe');
    mockIframe.src = 'https://example.com/test';
  });

  afterEach(() => {
    monitor.destroy();
    vi.clearAllMocks();
  });

  describe('Monitoring Overhead', () => {
    it('should have minimal overhead when starting monitoring', () => {
      const startTime = performance.now();
      
      // Start monitoring multiple iframes
      for (let i = 0; i < 10; i++) {
        const iframe = document.createElement('iframe');
        monitor.startMonitoring(`iframe-${i}`, iframe);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Starting monitoring should be fast
      expect(duration).toBeLessThan(50);
    });

    it('should efficiently collect metrics', async () => {
      const iframeId = 'test-iframe';
      monitor.startMonitoring(iframeId, mockIframe);
      
      // Wait for a few sampling intervals
      await new Promise(resolve => setTimeout(resolve, 300));
      
      const startTime = performance.now();
      const metrics = monitor.getCurrentMetrics(iframeId);
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Getting metrics should be very fast
      expect(duration).toBeLessThan(5);
      expect(metrics).toBeTruthy();
      expect(metrics?.timestamp).toBeGreaterThan(0);
    });

    it('should handle multiple concurrent monitoring sessions', () => {
      const startTime = performance.now();
      
      // Start monitoring many iframes
      const iframeCount = 50;
      for (let i = 0; i < iframeCount; i++) {
        const iframe = document.createElement('iframe');
        monitor.startMonitoring(`iframe-${i}`, iframe);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle many concurrent sessions efficiently
      expect(duration).toBeLessThan(100);
      
      // Check that all sessions are active
      const summary = monitor.getOverallSummary();
      expect(summary.totalIframes).toBe(iframeCount);
    });
  });

  describe('Metrics Collection Performance', () => {
    it('should collect metrics efficiently over time', async () => {
      const iframeId = 'test-iframe';
      monitor.startMonitoring(iframeId, mockIframe);
      
      // Let it collect metrics for a while
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const startTime = performance.now();
      const allMetrics = monitor.getAllMetrics(iframeId);
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Getting all metrics should be fast even with history
      expect(duration).toBeLessThan(10);
      expect(allMetrics.length).toBeGreaterThan(0);
      
      // Metrics should be properly timestamped
      allMetrics.forEach((metric, index) => {
        expect(metric.timestamp).toBeGreaterThan(0);
        if (index > 0) {
          expect(metric.timestamp).toBeGreaterThanOrEqual(allMetrics[index - 1].timestamp);
        }
      });
    });

    it('should limit history size efficiently', async () => {
      const maxHistorySize = 10;
      monitor = new PerformanceMonitor({
        sampleInterval: 10, // Very fast sampling
        maxHistorySize,
      });

      const iframeId = 'test-iframe';
      monitor.startMonitoring(iframeId, mockIframe);
      
      // Wait for more samples than the limit
      await new Promise(resolve => setTimeout(resolve, 200));
      
      const metrics = monitor.getAllMetrics(iframeId);
      
      // Should respect history size limit
      expect(metrics.length).toBeLessThanOrEqual(maxHistorySize);
    });

    it('should handle memory usage calculation efficiently', () => {
      const iframeId = 'test-iframe';
      monitor.startMonitoring(iframeId, mockIframe);
      
      const startTime = performance.now();
      
      // Trigger multiple memory calculations
      for (let i = 0; i < 100; i++) {
        monitor.getCurrentMetrics(iframeId);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Memory calculations should be efficient
      expect(duration).toBeLessThan(50);
    });
  });

  describe('Alert System Performance', () => {
    it('should generate alerts efficiently', async () => {
      const alertCallback = vi.fn();
      monitor = new PerformanceMonitor({
        sampleInterval: 50,
        thresholds: {
          maxMemoryUsage: 1, // Very low threshold to trigger alerts
          maxCpuUsage: 1,
        },
        enableAlerts: true,
        alertCallback,
      });

      const iframeId = 'test-iframe';
      monitor.startMonitoring(iframeId, mockIframe);
      
      // Wait for alerts to be generated
      await new Promise(resolve => setTimeout(resolve, 200));
      
      const startTime = performance.now();
      const alerts = monitor.getAlerts(iframeId);
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Getting alerts should be fast
      expect(duration).toBeLessThan(5);
      expect(alerts.length).toBeGreaterThan(0);
      expect(alertCallback).toHaveBeenCalled();
    });

    it('should handle error recording efficiently', () => {
      const iframeId = 'test-iframe';
      monitor.startMonitoring(iframeId, mockIframe);
      
      const startTime = performance.now();
      
      // Record many errors
      for (let i = 0; i < 100; i++) {
        monitor.recordError(iframeId, new Error(`Test error ${i}`));
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Error recording should be efficient
      expect(duration).toBeLessThan(50);
    });
  });

  describe('Report Generation Performance', () => {
    it('should generate reports efficiently', async () => {
      const iframeId = 'test-iframe';
      monitor.startMonitoring(iframeId, mockIframe);
      
      // Let it collect some data
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // Record some errors
      for (let i = 0; i < 10; i++) {
        monitor.recordError(iframeId, new Error(`Test error ${i}`));
      }
      
      const startTime = performance.now();
      const report = monitor.generateReport(iframeId);
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Report generation should be fast
      expect(duration).toBeLessThan(20);
      expect(report).toBeTruthy();
      expect(report?.iframeId).toBe(iframeId);
      expect(report?.metrics.length).toBeGreaterThan(0);
      expect(report?.summary.totalErrors).toBe(10);
    });

    it('should calculate summary statistics efficiently', async () => {
      // Start monitoring multiple iframes
      for (let i = 0; i < 10; i++) {
        const iframe = document.createElement('iframe');
        monitor.startMonitoring(`iframe-${i}`, iframe);
      }
      
      // Let them collect data
      await new Promise(resolve => setTimeout(resolve, 200));
      
      const startTime = performance.now();
      const summary = monitor.getOverallSummary();
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Summary calculation should be efficient
      expect(duration).toBeLessThan(20);
      expect(summary.totalIframes).toBe(10);
      expect(summary.avgMemoryUsage).toBeGreaterThanOrEqual(0);
      expect(summary.avgCpuUsage).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Resource Cleanup Performance', () => {
    it('should stop monitoring efficiently', () => {
      const iframeId = 'test-iframe';
      monitor.startMonitoring(iframeId, mockIframe);
      
      const startTime = performance.now();
      monitor.stopMonitoring(iframeId);
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Stopping should be fast
      expect(duration).toBeLessThan(10);
      
      // Should clean up resources
      const metrics = monitor.getCurrentMetrics(iframeId);
      expect(metrics).toBeNull();
    });

    it('should destroy all resources efficiently', async () => {
      // Start monitoring many iframes
      for (let i = 0; i < 20; i++) {
        const iframe = document.createElement('iframe');
        monitor.startMonitoring(`iframe-${i}`, iframe);
      }
      
      // Let them collect some data
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const startTime = performance.now();
      monitor.destroy();
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Destruction should be efficient
      expect(duration).toBeLessThan(50);
      
      // Should clean up all resources
      const summary = monitor.getOverallSummary();
      expect(summary.totalIframes).toBe(0);
    });

    it('should clear history efficiently', async () => {
      const iframeId = 'test-iframe';
      monitor.startMonitoring(iframeId, mockIframe);
      
      // Let it collect data
      await new Promise(resolve => setTimeout(resolve, 200));
      
      // Verify data exists
      const metricsBefore = monitor.getAllMetrics(iframeId);
      expect(metricsBefore.length).toBeGreaterThan(0);
      
      const startTime = performance.now();
      monitor.clearHistory(iframeId);
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Clearing should be fast
      expect(duration).toBeLessThan(5);
      
      // Should clear all history
      const metricsAfter = monitor.getAllMetrics(iframeId);
      const alertsAfter = monitor.getAlerts(iframeId);
      expect(metricsAfter.length).toBe(0);
      expect(alertsAfter.length).toBe(0);
    });
  });

  describe('Memory Usage', () => {
    it('should not leak memory during normal operation', async () => {
      const initialMemory = (performance as any).memory.usedJSHeapSize;
      
      // Simulate normal operation
      for (let cycle = 0; cycle < 5; cycle++) {
        // Start monitoring
        for (let i = 0; i < 10; i++) {
          const iframe = document.createElement('iframe');
          monitor.startMonitoring(`iframe-${cycle}-${i}`, iframe);
        }
        
        // Let it run
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Stop monitoring
        for (let i = 0; i < 10; i++) {
          monitor.stopMonitoring(`iframe-${cycle}-${i}`);
        }
      }
      
      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }
      
      const finalMemory = (performance as any).memory.usedJSHeapSize;
      const memoryIncrease = finalMemory - initialMemory;
      
      // Memory increase should be reasonable (less than 10MB)
      expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024);
    });
  });
});