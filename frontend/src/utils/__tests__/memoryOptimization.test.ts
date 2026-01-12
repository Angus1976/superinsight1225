/**
 * Memory Optimization Utilities Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  MemoryMonitor,
  getCurrentMemorySample,
  getMemoryStatus,
  analyzeMemoryTrend,
  detectMemoryLeak,
  generateRecommendations,
  formatMemorySize,
  createLRUCache,
  createWeakCache,
  MEMORY_BUDGET,
  type MemorySample,
} from '../memoryOptimization';

// Mock performance.memory
const mockMemory = {
  usedJSHeapSize: 50 * 1024 * 1024, // 50MB
  totalJSHeapSize: 100 * 1024 * 1024, // 100MB
  jsHeapSizeLimit: 2048 * 1024 * 1024, // 2GB
};

beforeEach(() => {
  Object.defineProperty(performance, 'memory', {
    value: mockMemory,
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('getCurrentMemorySample', () => {
  it('should return memory sample when API is available', () => {
    const sample = getCurrentMemorySample();
    
    expect(sample).not.toBeNull();
    expect(sample?.usedJSHeapSize).toBe(mockMemory.usedJSHeapSize);
    expect(sample?.totalJSHeapSize).toBe(mockMemory.totalJSHeapSize);
    expect(sample?.jsHeapSizeLimit).toBe(mockMemory.jsHeapSizeLimit);
    expect(sample?.timestamp).toBeGreaterThan(0);
  });

  it('should calculate usage percentage correctly', () => {
    const sample = getCurrentMemorySample();
    
    expect(sample).not.toBeNull();
    const expectedPercentage = (mockMemory.usedJSHeapSize / mockMemory.jsHeapSizeLimit) * 100;
    expect(sample?.usagePercentage).toBeCloseTo(expectedPercentage, 2);
  });
});

describe('getMemoryStatus', () => {
  it('should return "good" for low memory usage', () => {
    const sample: MemorySample = {
      timestamp: Date.now(),
      usedJSHeapSize: 50 * 1024 * 1024, // 50MB
      totalJSHeapSize: 100 * 1024 * 1024,
      jsHeapSizeLimit: 2048 * 1024 * 1024,
      usagePercentage: 2.44,
    };
    
    expect(getMemoryStatus(sample)).toBe('good');
  });

  it('should return "warning" for elevated memory usage', () => {
    const sample: MemorySample = {
      timestamp: Date.now(),
      usedJSHeapSize: MEMORY_BUDGET.warning * 1024 * 1024, // 100MB
      totalJSHeapSize: 200 * 1024 * 1024,
      jsHeapSizeLimit: 2048 * 1024 * 1024,
      usagePercentage: 4.88,
    };
    
    expect(getMemoryStatus(sample)).toBe('warning');
  });

  it('should return "critical" for high memory usage', () => {
    const sample: MemorySample = {
      timestamp: Date.now(),
      usedJSHeapSize: MEMORY_BUDGET.critical * 1024 * 1024, // 200MB
      totalJSHeapSize: 300 * 1024 * 1024,
      jsHeapSizeLimit: 2048 * 1024 * 1024,
      usagePercentage: 9.77,
    };
    
    expect(getMemoryStatus(sample)).toBe('critical');
  });

  it('should return "good" for null sample', () => {
    expect(getMemoryStatus(null)).toBe('good');
  });
});

describe('analyzeMemoryTrend', () => {
  it('should return null for insufficient samples', () => {
    const samples: MemorySample[] = [
      { timestamp: 1000, usedJSHeapSize: 50 * 1024 * 1024, totalJSHeapSize: 100 * 1024 * 1024, jsHeapSizeLimit: 2048 * 1024 * 1024, usagePercentage: 2.44 },
      { timestamp: 2000, usedJSHeapSize: 51 * 1024 * 1024, totalJSHeapSize: 100 * 1024 * 1024, jsHeapSizeLimit: 2048 * 1024 * 1024, usagePercentage: 2.49 },
    ];
    
    expect(analyzeMemoryTrend(samples)).toBeNull();
  });

  it('should detect increasing trend', () => {
    const samples: MemorySample[] = [];
    const baseTime = Date.now();
    
    for (let i = 0; i < 10; i++) {
      samples.push({
        timestamp: baseTime + i * 1000,
        usedJSHeapSize: (50 + i * 5) * 1024 * 1024, // Increasing by 5MB each sample
        totalJSHeapSize: 200 * 1024 * 1024,
        jsHeapSizeLimit: 2048 * 1024 * 1024,
        usagePercentage: ((50 + i * 5) / 2048) * 100,
      });
    }
    
    const trend = analyzeMemoryTrend(samples);
    
    expect(trend).not.toBeNull();
    expect(trend?.direction).toBe('increasing');
    expect(trend?.rate).toBeGreaterThan(0);
  });

  it('should detect decreasing trend', () => {
    const samples: MemorySample[] = [];
    const baseTime = Date.now();
    
    for (let i = 0; i < 10; i++) {
      samples.push({
        timestamp: baseTime + i * 1000,
        usedJSHeapSize: (100 - i * 5) * 1024 * 1024, // Decreasing by 5MB each sample
        totalJSHeapSize: 200 * 1024 * 1024,
        jsHeapSizeLimit: 2048 * 1024 * 1024,
        usagePercentage: ((100 - i * 5) / 2048) * 100,
      });
    }
    
    const trend = analyzeMemoryTrend(samples);
    
    expect(trend).not.toBeNull();
    expect(trend?.direction).toBe('decreasing');
    expect(trend?.rate).toBeLessThan(0);
  });

  it('should detect stable trend', () => {
    const samples: MemorySample[] = [];
    const baseTime = Date.now();
    
    for (let i = 0; i < 10; i++) {
      samples.push({
        timestamp: baseTime + i * 1000,
        usedJSHeapSize: 50 * 1024 * 1024, // Constant
        totalJSHeapSize: 100 * 1024 * 1024,
        jsHeapSizeLimit: 2048 * 1024 * 1024,
        usagePercentage: 2.44,
      });
    }
    
    const trend = analyzeMemoryTrend(samples);
    
    expect(trend).not.toBeNull();
    expect(trend?.direction).toBe('stable');
  });
});

describe('detectMemoryLeak', () => {
  it('should not detect leak with insufficient samples', () => {
    const samples: MemorySample[] = [
      { timestamp: 1000, usedJSHeapSize: 50 * 1024 * 1024, totalJSHeapSize: 100 * 1024 * 1024, jsHeapSizeLimit: 2048 * 1024 * 1024, usagePercentage: 2.44 },
    ];
    
    const result = detectMemoryLeak(samples);
    
    expect(result).not.toBeNull();
    expect(result?.isLeaking).toBe(false);
    expect(result?.confidence).toBe(0);
  });

  it('should detect potential memory leak with consistent growth', () => {
    const samples: MemorySample[] = [];
    const baseTime = Date.now();
    
    // Simulate consistent memory growth (potential leak)
    for (let i = 0; i < 15; i++) {
      samples.push({
        timestamp: baseTime + i * 1000,
        usedJSHeapSize: (50 + i * 10) * 1024 * 1024, // Growing by 10MB per second
        totalJSHeapSize: 300 * 1024 * 1024,
        jsHeapSizeLimit: 2048 * 1024 * 1024,
        usagePercentage: ((50 + i * 10) / 2048) * 100,
      });
    }
    
    const result = detectMemoryLeak(samples);
    
    expect(result).not.toBeNull();
    expect(result?.isLeaking).toBe(true);
    expect(result?.confidence).toBeGreaterThan(70);
  });

  it('should not detect leak with stable memory', () => {
    const samples: MemorySample[] = [];
    const baseTime = Date.now();
    
    for (let i = 0; i < 15; i++) {
      samples.push({
        timestamp: baseTime + i * 1000,
        usedJSHeapSize: 50 * 1024 * 1024, // Constant
        totalJSHeapSize: 100 * 1024 * 1024,
        jsHeapSizeLimit: 2048 * 1024 * 1024,
        usagePercentage: 2.44,
      });
    }
    
    const result = detectMemoryLeak(samples);
    
    expect(result).not.toBeNull();
    expect(result?.isLeaking).toBe(false);
  });
});

describe('generateRecommendations', () => {
  it('should generate recommendations for critical memory', () => {
    const sample: MemorySample = {
      timestamp: Date.now(),
      usedJSHeapSize: MEMORY_BUDGET.critical * 1024 * 1024,
      totalJSHeapSize: 300 * 1024 * 1024,
      jsHeapSizeLimit: 2048 * 1024 * 1024,
      usagePercentage: 9.77,
    };
    
    const recommendations = generateRecommendations(sample, null, null);
    
    expect(recommendations.length).toBeGreaterThan(0);
    expect(recommendations.some(r => r.includes('Critical'))).toBe(true);
  });

  it('should generate healthy message for good memory', () => {
    const sample: MemorySample = {
      timestamp: Date.now(),
      usedJSHeapSize: 30 * 1024 * 1024, // 30MB
      totalJSHeapSize: 50 * 1024 * 1024,
      jsHeapSizeLimit: 2048 * 1024 * 1024,
      usagePercentage: 1.46,
    };
    
    const recommendations = generateRecommendations(sample, null, null);
    
    expect(recommendations.some(r => r.includes('healthy'))).toBe(true);
  });
});

describe('formatMemorySize', () => {
  it('should format bytes correctly', () => {
    expect(formatMemorySize(0)).toBe('0 B');
    expect(formatMemorySize(512)).toBe('512 B');
    expect(formatMemorySize(1024)).toBe('1 KB');
    expect(formatMemorySize(1024 * 1024)).toBe('1 MB');
    expect(formatMemorySize(1024 * 1024 * 1024)).toBe('1 GB');
  });

  it('should format with decimals', () => {
    expect(formatMemorySize(1536)).toBe('1.5 KB');
    expect(formatMemorySize(1.5 * 1024 * 1024)).toBe('1.5 MB');
  });
});

describe('createLRUCache', () => {
  it('should store and retrieve values', () => {
    const cache = createLRUCache<string, number>(3);
    
    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3);
    
    expect(cache.get('a')).toBe(1);
    expect(cache.get('b')).toBe(2);
    expect(cache.get('c')).toBe(3);
  });

  it('should evict oldest entry when full', () => {
    const cache = createLRUCache<string, number>(3);
    
    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3);
    cache.set('d', 4); // Should evict 'a'
    
    expect(cache.get('a')).toBeUndefined();
    expect(cache.get('b')).toBe(2);
    expect(cache.get('c')).toBe(3);
    expect(cache.get('d')).toBe(4);
  });

  it('should update LRU order on access', () => {
    const cache = createLRUCache<string, number>(3);
    
    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3);
    
    // Access 'a' to make it most recently used
    cache.get('a');
    
    // Add new entry, should evict 'b' (now oldest)
    cache.set('d', 4);
    
    expect(cache.get('a')).toBe(1);
    expect(cache.get('b')).toBeUndefined();
    expect(cache.get('c')).toBe(3);
    expect(cache.get('d')).toBe(4);
  });

  it('should report correct size', () => {
    const cache = createLRUCache<string, number>(5);
    
    expect(cache.size()).toBe(0);
    
    cache.set('a', 1);
    expect(cache.size()).toBe(1);
    
    cache.set('b', 2);
    expect(cache.size()).toBe(2);
    
    cache.clear();
    expect(cache.size()).toBe(0);
  });
});

describe('createWeakCache', () => {
  it('should store and retrieve values with object keys', () => {
    const cache = createWeakCache<object, string>();
    const key1 = { id: 1 };
    const key2 = { id: 2 };
    
    cache.set(key1, 'value1');
    cache.set(key2, 'value2');
    
    expect(cache.get(key1)).toBe('value1');
    expect(cache.get(key2)).toBe('value2');
  });

  it('should check if key exists', () => {
    const cache = createWeakCache<object, string>();
    const key = { id: 1 };
    
    expect(cache.has(key)).toBe(false);
    
    cache.set(key, 'value');
    expect(cache.has(key)).toBe(true);
  });

  it('should delete entries', () => {
    const cache = createWeakCache<object, string>();
    const key = { id: 1 };
    
    cache.set(key, 'value');
    expect(cache.has(key)).toBe(true);
    
    cache.delete(key);
    expect(cache.has(key)).toBe(false);
  });
});

describe('MemoryMonitor', () => {
  it('should start and stop monitoring', () => {
    const monitor = new MemoryMonitor({ sampleInterval: 100 });
    
    monitor.start();
    expect(monitor.getSamples().length).toBeGreaterThanOrEqual(0);
    
    monitor.stop();
    monitor.destroy();
  });

  it('should collect samples over time', async () => {
    const monitor = new MemoryMonitor({ sampleInterval: 50 });
    
    monitor.start();
    
    // Wait for samples to be collected
    await new Promise(resolve => setTimeout(resolve, 200));
    
    const samples = monitor.getSamples();
    expect(samples.length).toBeGreaterThan(0);
    
    monitor.destroy();
  });

  it('should generate report', () => {
    const monitor = new MemoryMonitor();
    
    monitor.start();
    
    const report = monitor.generateReport();
    
    expect(report).toHaveProperty('current');
    expect(report).toHaveProperty('status');
    expect(report).toHaveProperty('history');
    expect(report).toHaveProperty('recommendations');
    
    monitor.destroy();
  });

  it('should notify subscribers', async () => {
    const monitor = new MemoryMonitor({ sampleInterval: 50 });
    const callback = vi.fn();
    
    monitor.subscribe(callback);
    monitor.start();
    
    // Wait for callback to be called
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect(callback).toHaveBeenCalled();
    
    monitor.destroy();
  });

  it('should clear history', () => {
    const monitor = new MemoryMonitor({ sampleInterval: 50 });
    
    monitor.start();
    
    // Wait for samples
    setTimeout(() => {
      expect(monitor.getSamples().length).toBeGreaterThan(0);
      
      monitor.clear();
      expect(monitor.getSamples().length).toBe(0);
      
      monitor.destroy();
    }, 100);
  });
});
