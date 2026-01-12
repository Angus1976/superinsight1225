/**
 * LazyLoader Performance Tests
 * Tests lazy loading and preloading performance
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { LazyLoader } from './LazyLoader';
import { IframeConfig } from './types';

// Mock IntersectionObserver
const mockObserve = vi.fn();
const mockUnobserve = vi.fn();
const mockDisconnect = vi.fn();

class MockIntersectionObserver {
  constructor(callback: IntersectionObserverCallback) {
    // Store callback for potential use
  }
  observe = mockObserve;
  unobserve = mockUnobserve;
  disconnect = mockDisconnect;
}

// Set up the mock before any tests run
vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

describe('LazyLoader Performance Tests', () => {
  let lazyLoader: LazyLoader;
  let mockElement: HTMLElement;
  let mockConfig: IframeConfig;

  beforeEach(() => {
    lazyLoader = new LazyLoader({
      threshold: 0.1,
      enablePreload: true,
      maxPreloadCount: 3,
      preloadTimeout: 5000,
    });

    mockElement = document.createElement('div');
    mockConfig = {
      url: 'https://example.com/labelstudio',
      projectId: 'test-project',
      taskId: 'test-task',
      userId: 'test-user',
      token: 'test-token',
      permissions: [],
    };

    // Mock document.body.appendChild
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockElement);
    vi.spyOn(document.body, 'removeChild').mockImplementation(() => mockElement);
    
    // Clear mocks
    mockObserve.mockClear();
    mockUnobserve.mockClear();
    mockDisconnect.mockClear();
  });

  afterEach(() => {
    lazyLoader.destroy();
    vi.restoreAllMocks();
  });

  describe('Loading Performance', () => {
    it('should handle multiple iframe observations efficiently', () => {
      const startTime = performance.now();
      
      // Observe multiple iframes
      for (let i = 0; i < 100; i++) {
        const element = document.createElement('div');
        const config = { ...mockConfig, taskId: `task-${i}` };
        lazyLoader.observe(element, `iframe-${i}`, config);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should complete within reasonable time (less than 100ms for 100 iframes)
      expect(duration).toBeLessThan(100);
      
      // Should have called observe for each element
      expect(mockObserve).toHaveBeenCalledTimes(100);
    });

    it('should efficiently manage preload queue', () => {
      const startTime = performance.now();
      
      // Add many items to preload queue
      for (let i = 0; i < 50; i++) {
        const element = document.createElement('div');
        const config = { ...mockConfig, taskId: `task-${i}` };
        lazyLoader.observe(element, `iframe-${i}`, config);
      }
      
      const stats = lazyLoader.getPreloadStats();
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      expect(stats.queueLength).toBeGreaterThanOrEqual(0);
      expect(duration).toBeLessThan(50); // Should be very fast
    });

    it('should limit preloaded iframes to configured maximum', () => {
      const maxPreload = 3;
      lazyLoader = new LazyLoader({
        enablePreload: true,
        maxPreloadCount: maxPreload,
      });

      // Try to preload more than the limit
      for (let i = 0; i < 10; i++) {
        const element = document.createElement('div');
        const config = { ...mockConfig, taskId: `task-${i}` };
        lazyLoader.observe(element, `iframe-${i}`, config);
      }

      const stats = lazyLoader.getPreloadStats();
      expect(stats.preloadedCount).toBeLessThanOrEqual(maxPreload);
    });
  });

  describe('Memory Performance', () => {
    it('should cleanup resources when unobserving', () => {
      const element = document.createElement('div');
      const iframeId = 'test-iframe';
      
      lazyLoader.observe(element, iframeId, mockConfig);
      
      // Check that state exists
      const stateBefore = lazyLoader.getLoadState(iframeId);
      expect(stateBefore).toBeTruthy();
      
      lazyLoader.unobserve(element, iframeId);
      
      // Check that state is cleaned up
      const stateAfter = lazyLoader.getLoadState(iframeId);
      expect(stateAfter).toBeNull();
      
      // Should have called unobserve
      expect(mockUnobserve).toHaveBeenCalledWith(element);
    });

    it('should handle rapid observe/unobserve cycles', () => {
      const startTime = performance.now();
      
      for (let i = 0; i < 100; i++) {
        const element = document.createElement('div');
        const iframeId = `iframe-${i}`;
        
        lazyLoader.observe(element, iframeId, mockConfig);
        lazyLoader.unobserve(element, iframeId);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle rapid cycles efficiently
      expect(duration).toBeLessThan(100);
      
      // Should have no remaining state
      const stats = lazyLoader.getPreloadStats();
      expect(stats.preloadedCount).toBe(0);
      expect(stats.queueLength).toBe(0);
    });
  });

  describe('Performance Metrics', () => {
    it('should provide accurate preload statistics', () => {
      const stats = lazyLoader.getPreloadStats();
      
      expect(stats).toHaveProperty('preloadedCount');
      expect(stats).toHaveProperty('queueLength');
      expect(stats).toHaveProperty('isPreloading');
      expect(stats).toHaveProperty('preloadedIds');
      
      expect(typeof stats.preloadedCount).toBe('number');
      expect(typeof stats.queueLength).toBe('number');
      expect(typeof stats.isPreloading).toBe('boolean');
      expect(Array.isArray(stats.preloadedIds)).toBe(true);
    });

    it('should track load states accurately', () => {
      const element = document.createElement('div');
      const iframeId = 'test-iframe';
      
      // Initially no state
      expect(lazyLoader.getLoadState(iframeId)).toBeNull();
      
      lazyLoader.observe(element, iframeId, mockConfig);
      
      // Should have state after observing
      const state = lazyLoader.getLoadState(iframeId);
      expect(state).toBeTruthy();
      expect(state?.isVisible).toBe(false);
      expect(state?.isLoading).toBe(false);
      expect(state?.isPreloaded).toBe(false);
    });
  });

  describe('Resource Cleanup', () => {
    it('should cleanup all resources on destroy', () => {
      // Create multiple observations
      for (let i = 0; i < 10; i++) {
        const element = document.createElement('div');
        const iframeId = `iframe-${i}`;
        lazyLoader.observe(element, iframeId, mockConfig);
      }
      
      const statsBefore = lazyLoader.getPreloadStats();
      expect(statsBefore.queueLength).toBeGreaterThanOrEqual(0);
      
      const startTime = performance.now();
      lazyLoader.destroy();
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Cleanup should be fast
      expect(duration).toBeLessThan(50);
      
      const statsAfter = lazyLoader.getPreloadStats();
      expect(statsAfter.queueLength).toBe(0);
      expect(statsAfter.preloadedCount).toBe(0);
      
      // Should have called disconnect
      expect(mockDisconnect).toHaveBeenCalled();
    });
  });

  describe('Configuration Performance', () => {
    it('should handle different configurations efficiently', () => {
      const configs = [
        { threshold: 0.1, enablePreload: true, maxPreloadCount: 5 },
        { threshold: 0.5, enablePreload: false, maxPreloadCount: 10 },
        { threshold: 1.0, enablePreload: true, maxPreloadCount: 1 },
      ];

      configs.forEach((config, index) => {
        const startTime = performance.now();
        const loader = new LazyLoader(config);
        
        // Test basic operations
        const element = document.createElement('div');
        loader.observe(element, `test-${index}`, mockConfig);
        const stats = loader.getPreloadStats();
        loader.unobserve(element, `test-${index}`);
        loader.destroy();
        
        const endTime = performance.now();
        const duration = endTime - startTime;
        
        // Should handle different configs efficiently
        expect(duration).toBeLessThan(50);
        expect(stats).toBeTruthy();
      });
    });
  });
});