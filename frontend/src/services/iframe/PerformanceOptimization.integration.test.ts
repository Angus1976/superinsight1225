/**
 * Performance Optimization Integration Tests
 * Tests the complete performance optimization system
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { IframeManager } from './IframeManager';
import { IframeConfig } from './types';

// Mock IntersectionObserver
const mockIntersectionObserver = vi.fn();
mockIntersectionObserver.mockReturnValue({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
});
window.IntersectionObserver = mockIntersectionObserver;

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
    usedJSHeapSize: 50 * 1024 * 1024,
    totalJSHeapSize: 100 * 1024 * 1024,
    jsHeapSizeLimit: 2 * 1024 * 1024 * 1024,
  },
  configurable: true,
});

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
});

describe('Performance Optimization Integration Tests', () => {
  let iframeManager: IframeManager;
  let container: HTMLElement;
  let mockConfig: IframeConfig;

  beforeEach(() => {
    iframeManager = new IframeManager();
    container = document.createElement('div');
    document.body.appendChild(container);

    mockConfig = {
      url: 'https://example.com/labelstudio',
      projectId: 'test-project',
      taskId: 'test-task',
      userId: 'test-user',
      token: 'test-token',
      permissions: [],
    };

    vi.clearAllMocks();
  });

  afterEach(() => {
    iframeManager.destroy();
    if (container.parentElement) {
      container.parentElement.removeChild(container);
    }
  });

  describe('Complete Performance System', () => {
    it('should initialize all performance features efficiently', () => {
      const startTime = performance.now();
      
      iframeManager.initializePerformanceOptimization(
        {
          threshold: 0.1,
          enablePreload: true,
          maxPreloadCount: 3,
        },
        {
          maxSize: 10 * 1024 * 1024,
          maxEntries: 100,
          enablePersistence: true,
        },
        {
          sampleInterval: 1000,
          enableMemoryMonitoring: true,
          enableCpuMonitoring: true,
          thresholds: {
            maxLoadTime: 5000,
            maxMemoryUsage: 100,
            maxCpuUsage: 80,
          },
        }
      );
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Initialization should be fast
      expect(duration).toBeLessThan(50);
    });

    it('should create iframe with all optimizations enabled', async () => {
      // Initialize performance features
      iframeManager.initializePerformanceOptimization(
        { enablePreload: true },
        { enablePersistence: false },
        { sampleInterval: 100 }
      );
      
      const startTime = performance.now();
      const iframe = await iframeManager.create(mockConfig, container);
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Creation should be efficient
      expect(duration).toBeLessThan(100);
      expect(iframe).toBeTruthy();
      expect(iframe.parentElement).toBe(container);
    });

    it('should provide comprehensive performance statistics', async () => {
      // Initialize all features
      iframeManager.initializePerformanceOptimization(
        { enablePreload: true, maxPreloadCount: 5 },
        { maxSize: 5 * 1024 * 1024, maxEntries: 50 },
        { sampleInterval: 100, enableAlerts: true }
      );
      
      await iframeManager.create(mockConfig, container);
      
      // Wait for some data collection
      await new Promise(resolve => setTimeout(resolve, 300));
      
      const startTime = performance.now();
      const stats = iframeManager.getPerformanceStats();
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Getting stats should be fast
      expect(duration).toBeLessThan(10);
      
      // Should have all performance data
      expect(stats).toHaveProperty('lazyLoading');
      expect(stats).toHaveProperty('caching');
      expect(stats).toHaveProperty('monitoring');
      expect(stats.lazyLoading).toBeTruthy();
      expect(stats.caching).toBeTruthy();
      expect(stats.monitoring).toBeTruthy();
    });

    it('should generate detailed performance report', async () => {
      // Initialize monitoring
      iframeManager.initializePerformanceOptimization(
        undefined,
        undefined,
        { sampleInterval: 50, enableAlerts: true }
      );
      
      await iframeManager.create(mockConfig, container);
      
      // Wait for data collection
      await new Promise(resolve => setTimeout(resolve, 200));
      
      // Record some errors
      iframeManager.recordError(new Error('Test error 1'));
      iframeManager.recordError(new Error('Test error 2'));
      
      const startTime = performance.now();
      const report = iframeManager.getPerformanceReport();
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Report generation should be fast
      expect(duration).toBeLessThan(20);
      expect(report).toBeTruthy();
      expect(report?.metrics.length).toBeGreaterThan(0);
      expect(report?.summary.totalErrors).toBe(2);
    });
  });

  describe('Performance Under Load', () => {
    it('should handle multiple iframes efficiently', async () => {
      // Initialize performance features
      iframeManager.initializePerformanceOptimization(
        { enablePreload: true, maxPreloadCount: 10 },
        { maxSize: 50 * 1024 * 1024, maxEntries: 500 },
        { sampleInterval: 200 }
      );
      
      const startTime = performance.now();
      
      // Create multiple iframe managers (simulating multiple iframes)
      const managers: IframeManager[] = [];
      const containers: HTMLElement[] = [];
      
      for (let i = 0; i < 10; i++) {
        const manager = new IframeManager();
        const cont = document.createElement('div');
        document.body.appendChild(cont);
        
        manager.initializePerformanceOptimization(
          { enablePreload: true },
          { enablePersistence: false },
          { sampleInterval: 500 }
        );
        
        const config = { ...mockConfig, taskId: `task-${i}` };
        await manager.create(config, cont);
        
        managers.push(manager);
        containers.push(cont);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle multiple iframes efficiently
      expect(duration).toBeLessThan(1000);
      
      // Cleanup
      managers.forEach(manager => manager.destroy());
      containers.forEach(cont => {
        if (cont.parentElement) {
          cont.parentElement.removeChild(cont);
        }
      });
    });

    it('should maintain performance during rapid operations', async () => {
      iframeManager.initializePerformanceOptimization(
        { enablePreload: true },
        { maxSize: 10 * 1024 * 1024 },
        { sampleInterval: 100 }
      );
      
      const startTime = performance.now();
      
      // Rapid create/destroy cycles
      for (let i = 0; i < 5; i++) {
        await iframeManager.create(mockConfig, container);
        await new Promise(resolve => setTimeout(resolve, 50));
        await iframeManager.destroy();
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle rapid operations efficiently
      expect(duration).toBeLessThan(2000);
    });
  });

  describe('Resource Management', () => {
    it('should cleanup all resources on destroy', async () => {
      // Initialize all features
      iframeManager.initializePerformanceOptimization(
        { enablePreload: true, maxPreloadCount: 5 },
        { maxSize: 10 * 1024 * 1024, maxEntries: 100 },
        { sampleInterval: 100, enableAlerts: true }
      );
      
      await iframeManager.create(mockConfig, container);
      
      // Wait for some activity
      await new Promise(resolve => setTimeout(resolve, 200));
      
      const startTime = performance.now();
      await iframeManager.destroy();
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Cleanup should be efficient
      expect(duration).toBeLessThan(100);
      
      // Should not be able to get stats after destroy
      const stats = iframeManager.getPerformanceStats();
      expect(Object.keys(stats).length).toBe(0);
    });

    it('should handle resource preloading efficiently', async () => {
      // Mock fetch for preloading
      global.fetch = vi.fn().mockImplementation(() => {
        return Promise.resolve({
          ok: true,
          arrayBuffer: () => Promise.resolve(new ArrayBuffer(1024)),
          headers: {
            get: () => null,
          },
        });
      });

      iframeManager.initializePerformanceOptimization(
        undefined,
        { enablePersistence: false },
        undefined
      );
      
      const urls = [
        'https://example.com/resource1.js',
        'https://example.com/resource2.css',
        'https://example.com/resource3.html',
      ];
      
      const startTime = performance.now();
      await iframeManager.preloadResources(urls);
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Preloading should complete efficiently
      expect(duration).toBeLessThan(1000);
      
      vi.restoreAllMocks();
    });
  });

  describe('Error Handling Performance', () => {
    it('should handle errors efficiently', async () => {
      iframeManager.initializePerformanceOptimization(
        undefined,
        undefined,
        { sampleInterval: 100, enableAlerts: true }
      );
      
      await iframeManager.create(mockConfig, container);
      
      const startTime = performance.now();
      
      // Record many errors rapidly
      for (let i = 0; i < 100; i++) {
        iframeManager.recordError(new Error(`Error ${i}`));
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Error handling should be efficient
      expect(duration).toBeLessThan(100);
      
      const report = iframeManager.getPerformanceReport();
      expect(report?.summary.totalErrors).toBe(100);
    });
  });

  describe('Memory Efficiency', () => {
    it('should not cause memory leaks during normal operation', async () => {
      const initialMemory = (performance as any).memory.usedJSHeapSize;
      
      // Simulate normal usage patterns
      for (let cycle = 0; cycle < 3; cycle++) {
        iframeManager.initializePerformanceOptimization(
          { enablePreload: true },
          { maxSize: 5 * 1024 * 1024 },
          { sampleInterval: 100 }
        );
        
        await iframeManager.create(mockConfig, container);
        await new Promise(resolve => setTimeout(resolve, 200));
        await iframeManager.destroy();
        
        // Force cleanup
        iframeManager.destroyPerformanceOptimization();
      }
      
      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }
      
      const finalMemory = (performance as any).memory.usedJSHeapSize;
      const memoryIncrease = finalMemory - initialMemory;
      
      // Memory increase should be minimal
      expect(memoryIncrease).toBeLessThan(5 * 1024 * 1024); // Less than 5MB
    });
  });
});