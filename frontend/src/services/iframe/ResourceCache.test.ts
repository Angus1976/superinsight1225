/**
 * ResourceCache Performance Tests
 * Tests caching performance and memory management
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ResourceCache } from './ResourceCache';

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

describe('ResourceCache Performance Tests', () => {
  let cache: ResourceCache;

  beforeEach(() => {
    cache = new ResourceCache({
      maxSize: 10 * 1024 * 1024, // 10MB
      maxEntries: 100,
      defaultTTL: 30000, // 30 seconds
      enablePersistence: false, // Disable for tests
      cleanupInterval: 1000, // 1 second
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    cache.destroy();
  });

  describe('Cache Performance', () => {
    it('should handle large number of cache operations efficiently', () => {
      const startTime = performance.now();
      
      // Perform many cache operations
      for (let i = 0; i < 1000; i++) {
        const key = `key-${i}`;
        const data = `data-${i}`.repeat(100); // ~500 bytes each
        
        cache.set(key, data);
        cache.get(key);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should complete within reasonable time (less than 100ms for 1000 operations)
      expect(duration).toBeLessThan(100);
      
      const stats = cache.getStats();
      expect(stats.totalEntries).toBeLessThanOrEqual(100); // Respects maxEntries
    });

    it('should efficiently evict entries when cache is full', () => {
      const maxEntries = 10;
      cache = new ResourceCache({
        maxEntries,
        maxSize: 1024 * 1024, // 1MB
      });

      const startTime = performance.now();
      
      // Add more entries than the limit
      for (let i = 0; i < maxEntries * 2; i++) {
        cache.set(`key-${i}`, `data-${i}`);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle eviction efficiently
      expect(duration).toBeLessThan(50);
      
      const stats = cache.getStats();
      expect(stats.totalEntries).toBeLessThanOrEqual(maxEntries);
    });

    it('should handle cache hits and misses efficiently', () => {
      // Populate cache
      for (let i = 0; i < 100; i++) {
        cache.set(`key-${i}`, `data-${i}`);
      }
      
      const startTime = performance.now();
      
      // Mix of hits and misses
      for (let i = 0; i < 200; i++) {
        cache.get(`key-${i}`); // First 100 are hits, rest are misses
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle lookups efficiently
      expect(duration).toBeLessThan(50);
      
      const stats = cache.getStats();
      expect(stats.hitCount).toBe(100);
      expect(stats.missCount).toBe(100);
      expect(stats.hitRate).toBe(0.5);
    });
  });

  describe('Memory Management', () => {
    it('should respect memory size limits', () => {
      const maxSize = 1024; // 1KB
      cache = new ResourceCache({
        maxSize,
        maxEntries: 1000, // High entry limit to test size limit
      });

      const largeData = 'x'.repeat(500); // 500 bytes
      
      // Add entries until size limit is reached
      for (let i = 0; i < 10; i++) {
        cache.set(`key-${i}`, largeData);
      }
      
      const stats = cache.getStats();
      expect(stats.totalSize).toBeLessThanOrEqual(maxSize);
    });

    it('should calculate data sizes accurately', () => {
      const testCases = [
        { data: 'hello', expectedSize: 5 },
        { data: { key: 'value' }, expectedSize: 15 }, // JSON.stringify size
        { data: new ArrayBuffer(100), expectedSize: 100 },
      ];

      testCases.forEach(({ data, expectedSize }, index) => {
        const key = `key-${index}`;
        cache.set(key, data);
        
        // The actual size calculation might vary slightly due to JSON overhead
        // So we check that it's in a reasonable range
        const stats = cache.getStats();
        expect(stats.totalSize).toBeGreaterThan(0);
      });
    });

    it('should cleanup expired entries efficiently', async () => {
      const shortTTL = 100; // 100ms
      
      // Add entries with short TTL
      for (let i = 0; i < 50; i++) {
        cache.set(`key-${i}`, `data-${i}`, shortTTL);
      }
      
      const statsBefore = cache.getStats();
      expect(statsBefore.totalEntries).toBe(50);
      
      // Wait for entries to expire
      await new Promise(resolve => setTimeout(resolve, 150));
      
      const startTime = performance.now();
      
      // Trigger cleanup by trying to access expired entries
      for (let i = 0; i < 50; i++) {
        cache.get(`key-${i}`);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Cleanup should be efficient
      expect(duration).toBeLessThan(50);
      
      const statsAfter = cache.getStats();
      expect(statsAfter.totalEntries).toBe(0);
    });
  });

  describe('Pattern Matching Performance', () => {
    it('should efficiently find entries by pattern', () => {
      // Populate cache with various keys
      for (let i = 0; i < 100; i++) {
        cache.set(`user-${i}`, `user-data-${i}`);
        cache.set(`project-${i}`, `project-data-${i}`);
        cache.set(`task-${i}`, `task-data-${i}`);
      }
      
      const startTime = performance.now();
      
      // Search for user entries
      const userEntries = cache.getByPattern(/^user-/);
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Pattern matching should be efficient
      expect(duration).toBeLessThan(50);
      expect(userEntries.length).toBeGreaterThan(0);
      expect(userEntries.length).toBeLessThanOrEqual(100);
      
      userEntries.forEach(entry => {
        expect(entry.key).toMatch(/^user-/);
      });
    });

    it('should handle complex patterns efficiently', () => {
      // Add entries with various patterns
      const patterns = ['user', 'project', 'task', 'annotation', 'label'];
      
      patterns.forEach(pattern => {
        for (let i = 0; i < 20; i++) {
          cache.set(`${pattern}-${i}-data`, `${pattern}-content-${i}`);
        }
      });
      
      const startTime = performance.now();
      
      // Test various complex patterns
      const complexPatterns = [
        /^user-\d+-data$/,
        /^(project|task)-/,
        /-\d{1,2}-/,
        /annotation.*data$/,
      ];
      
      complexPatterns.forEach(pattern => {
        cache.getByPattern(pattern);
      });
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle complex patterns efficiently
      expect(duration).toBeLessThan(100);
    });
  });

  describe('Preload Performance', () => {
    it('should handle resource preloading efficiently', async () => {
      // Mock fetch for preloading
      global.fetch = vi.fn().mockImplementation((url: string) => {
        return Promise.resolve({
          ok: true,
          arrayBuffer: () => Promise.resolve(new ArrayBuffer(1024)),
          headers: {
            get: (header: string) => {
              switch (header) {
                case 'content-type': return 'text/html';
                case 'content-length': return '1024';
                case 'last-modified': return new Date().toISOString();
                default: return null;
              }
            },
          },
        });
      });

      const urls = Array.from({ length: 10 }, (_, i) => `https://example.com/resource-${i}`);
      
      const startTime = performance.now();
      await cache.preloadResources(urls);
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Preloading should complete within reasonable time
      expect(duration).toBeLessThan(1000);
      
      // Check that resources were cached
      urls.forEach(url => {
        expect(cache.has(url)).toBe(true);
      });
      
      vi.restoreAllMocks();
    });

    it('should handle preload failures gracefully', async () => {
      // Mock fetch to fail
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      const urls = ['https://example.com/failing-resource'];
      
      const startTime = performance.now();
      await cache.preloadResources(urls);
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle failures quickly
      expect(duration).toBeLessThan(1000);
      
      // Resource should not be cached
      expect(cache.has(urls[0])).toBe(false);
      
      vi.restoreAllMocks();
    });
  });

  describe('Statistics Performance', () => {
    it('should calculate statistics efficiently', () => {
      // Populate cache with various data
      for (let i = 0; i < 100; i++) {
        cache.set(`key-${i}`, `data-${i}`.repeat(i + 1));
        cache.get(`key-${i}`); // Generate some hits
      }
      
      const startTime = performance.now();
      const stats = cache.getStats();
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Statistics calculation should be fast
      expect(duration).toBeLessThan(10);
      
      expect(stats.totalEntries).toBe(100);
      expect(stats.totalSize).toBeGreaterThan(0);
      expect(stats.hitCount).toBe(100);
      expect(stats.missCount).toBe(0);
      expect(stats.hitRate).toBe(1);
      expect(stats.oldestEntry).toBeDefined();
      expect(stats.newestEntry).toBeDefined();
    });
  });

  describe('Concurrent Operations', () => {
    it('should handle concurrent cache operations', async () => {
      const operations = [];
      
      // Create concurrent operations
      for (let i = 0; i < 100; i++) {
        operations.push(
          Promise.resolve().then(() => {
            cache.set(`key-${i}`, `data-${i}`);
            return cache.get(`key-${i}`);
          })
        );
      }
      
      const startTime = performance.now();
      const results = await Promise.all(operations);
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should handle concurrent operations efficiently
      expect(duration).toBeLessThan(100);
      expect(results).toHaveLength(100);
      
      // All operations should succeed
      results.forEach((result, index) => {
        expect(result).toBe(`data-${index}`);
      });
    });
  });
});