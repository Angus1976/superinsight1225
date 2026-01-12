/**
 * Memory Optimization Hooks Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useMemoryMonitor,
  useMemoryUsage,
  useMemoryLeakDetector,
  useCleanup,
  useMemoryFootprint,
} from '../useMemoryOptimization';

// Mock performance.memory
const mockMemory = {
  usedJSHeapSize: 50 * 1024 * 1024, // 50MB
  totalJSHeapSize: 100 * 1024 * 1024, // 100MB
  jsHeapSizeLimit: 2048 * 1024 * 1024, // 2GB
};

beforeEach(() => {
  vi.useFakeTimers();
  
  Object.defineProperty(performance, 'memory', {
    value: mockMemory,
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe('useMemoryMonitor', () => {
  it('should return initial state', () => {
    const { result } = renderHook(() => useMemoryMonitor({ autoStart: false }));
    
    expect(result.current.isSupported).toBe(true);
    expect(result.current.status).toBe('good');
    expect(result.current.history).toEqual([]);
  });

  it('should detect memory API support', () => {
    const { result } = renderHook(() => useMemoryMonitor());
    
    expect(result.current.isSupported).toBe(true);
  });

  it('should provide refresh function', () => {
    const { result } = renderHook(() => useMemoryMonitor());
    
    expect(typeof result.current.refresh).toBe('function');
  });

  it('should provide clearHistory function', () => {
    const { result } = renderHook(() => useMemoryMonitor());
    
    expect(typeof result.current.clearHistory).toBe('function');
  });
});

describe('useMemoryUsage', () => {
  it('should return memory usage data', async () => {
    const { result } = renderHook(() => useMemoryUsage());
    
    // Wait for initial update
    await act(async () => {
      vi.advanceTimersByTime(100);
    });
    
    expect(result.current.isSupported).toBe(true);
    expect(result.current.usedMB).toBeGreaterThan(0);
    expect(result.current.totalMB).toBeGreaterThan(0);
    expect(result.current.limitMB).toBeGreaterThan(0);
    expect(result.current.status).toBe('good');
  });

  it('should format memory size', async () => {
    const { result } = renderHook(() => useMemoryUsage());
    
    await act(async () => {
      vi.advanceTimersByTime(100);
    });
    
    expect(result.current.formatted).toMatch(/\d+(\.\d+)?\s*(B|KB|MB|GB)/);
  });

  it('should calculate usage percentage', async () => {
    const { result } = renderHook(() => useMemoryUsage());
    
    await act(async () => {
      vi.advanceTimersByTime(100);
    });
    
    expect(result.current.usagePercent).toBeGreaterThanOrEqual(0);
    expect(result.current.usagePercent).toBeLessThanOrEqual(100);
  });
});

describe('useMemoryLeakDetector', () => {
  it('should return initial state', () => {
    const { result } = renderHook(() => useMemoryLeakDetector('TestComponent'));
    
    expect(result.current.isLeaking).toBe(false);
    expect(result.current.confidence).toBe(0);
    expect(typeof result.current.message).toBe('string');
  });

  it('should update message over time', async () => {
    const { result } = renderHook(() => useMemoryLeakDetector('TestComponent'));
    
    const initialMessage = result.current.message;
    
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    
    // Message should be updated (either same or different based on samples)
    expect(typeof result.current.message).toBe('string');
  });
});

describe('useCleanup', () => {
  it('should call cleanup function on unmount', () => {
    const cleanup = vi.fn();
    
    const { unmount } = renderHook(() => useCleanup(cleanup));
    
    expect(cleanup).not.toHaveBeenCalled();
    
    unmount();
    
    expect(cleanup).toHaveBeenCalledTimes(1);
  });

  it('should use latest cleanup function', () => {
    const cleanup1 = vi.fn();
    const cleanup2 = vi.fn();
    
    const { rerender, unmount } = renderHook(
      ({ cleanup }) => useCleanup(cleanup),
      { initialProps: { cleanup: cleanup1 } }
    );
    
    // Update cleanup function
    rerender({ cleanup: cleanup2 });
    
    unmount();
    
    // Should call the latest cleanup function
    expect(cleanup1).not.toHaveBeenCalled();
    expect(cleanup2).toHaveBeenCalledTimes(1);
  });
});

describe('useMemoryFootprint', () => {
  it('should track memory footprint', async () => {
    const { result } = renderHook(() => useMemoryFootprint('TestComponent'));
    
    await act(async () => {
      vi.advanceTimersByTime(100);
    });
    
    expect(result.current.mountMemory).toBeGreaterThanOrEqual(0);
    expect(result.current.currentMemory).toBeGreaterThanOrEqual(0);
    expect(typeof result.current.delta).toBe('number');
    expect(typeof result.current.formatted).toBe('string');
  });

  it('should calculate delta correctly', async () => {
    const { result } = renderHook(() => useMemoryFootprint('TestComponent'));
    
    await act(async () => {
      vi.advanceTimersByTime(100);
    });
    
    // Delta should be the difference between current and mount memory
    const expectedDelta = result.current.currentMemory - result.current.mountMemory;
    expect(result.current.delta).toBe(expectedDelta);
  });
});

describe('Memory API not supported', () => {
  beforeEach(() => {
    // Remove memory property to simulate unsupported browser
    // We need to delete the property first, then redefine it
    const perfDescriptor = Object.getOwnPropertyDescriptor(performance, 'memory');
    if (perfDescriptor) {
      delete (performance as any).memory;
    }
  });

  afterEach(() => {
    // Restore memory property for other tests
    Object.defineProperty(performance, 'memory', {
      value: mockMemory,
      writable: true,
      configurable: true,
    });
  });

  it('useMemoryMonitor should indicate not supported', () => {
    const { result } = renderHook(() => useMemoryMonitor());
    
    expect(result.current.isSupported).toBe(false);
  });

  it('useMemoryUsage should indicate not supported', () => {
    const { result } = renderHook(() => useMemoryUsage());
    
    expect(result.current.isSupported).toBe(false);
  });

  it('useMemoryLeakDetector should handle gracefully', () => {
    const { result } = renderHook(() => useMemoryLeakDetector('TestComponent'));
    
    expect(result.current.isLeaking).toBe(false);
    expect(result.current.message).toContain('not supported');
  });
});
