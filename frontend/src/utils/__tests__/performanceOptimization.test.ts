/**
 * Tests for Performance Optimization Utilities
 * 
 * Validates component render time optimization utilities.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  COMPONENT_RENDER_BUDGET,
  checkComponentRenderBudget,
  throttle,
  debounce,
  memoize,
  calculateVisibleRange,
  measureRenderTime,
} from '../performanceOptimization';

describe('COMPONENT_RENDER_BUDGET', () => {
  it('should be 100ms', () => {
    expect(COMPONENT_RENDER_BUDGET).toBe(100);
  });
});

describe('checkComponentRenderBudget', () => {
  it('should pass when render time is under budget', () => {
    const result = checkComponentRenderBudget(50);
    
    expect(result.passed).toBe(true);
    expect(result.isWarning).toBe(false);
    expect(result.renderTime).toBe(50);
    expect(result.budget).toBe(100);
    expect(result.usagePercent).toBe(50);
  });

  it('should fail when render time exceeds budget', () => {
    const result = checkComponentRenderBudget(150);
    
    expect(result.passed).toBe(false);
    expect(result.renderTime).toBe(150);
    expect(result.usagePercent).toBe(150);
  });

  it('should show warning when at 80% of budget', () => {
    const result = checkComponentRenderBudget(80);
    
    expect(result.passed).toBe(true);
    expect(result.isWarning).toBe(true);
    expect(result.usagePercent).toBe(80);
  });

  it('should not show warning when under 80% of budget', () => {
    const result = checkComponentRenderBudget(70);
    
    expect(result.passed).toBe(true);
    expect(result.isWarning).toBe(false);
  });

  it('should use custom budget when provided', () => {
    const result = checkComponentRenderBudget(60, { maxRenderTime: 50 });
    
    expect(result.passed).toBe(false);
    expect(result.budget).toBe(50);
    expect(result.usagePercent).toBe(120);
  });

  it('should round render time to 2 decimal places', () => {
    const result = checkComponentRenderBudget(50.12345);
    
    expect(result.renderTime).toBe(50.12);
  });
});

describe('throttle', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should call function immediately on first call', () => {
    const fn = vi.fn();
    const throttled = throttle(fn, 100);
    
    throttled();
    
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('should not call function again within throttle period', () => {
    const fn = vi.fn();
    const throttled = throttle(fn, 100);
    
    throttled();
    throttled();
    throttled();
    
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('should call function again after throttle period', () => {
    const fn = vi.fn();
    const throttled = throttle(fn, 100);
    
    throttled();
    vi.advanceTimersByTime(100);
    throttled();
    
    expect(fn).toHaveBeenCalledTimes(2);
  });
});

describe('debounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should not call function immediately', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);
    
    debounced();
    
    expect(fn).not.toHaveBeenCalled();
  });

  it('should call function after wait period', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);
    
    debounced();
    vi.advanceTimersByTime(100);
    
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('should reset timer on subsequent calls', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);
    
    debounced();
    vi.advanceTimersByTime(50);
    debounced();
    vi.advanceTimersByTime(50);
    
    expect(fn).not.toHaveBeenCalled();
    
    vi.advanceTimersByTime(50);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('should call immediately when immediate is true', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100, true);
    
    debounced();
    
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe('memoize', () => {
  it('should cache function results', () => {
    const fn = vi.fn((x: number) => x * 2);
    const memoized = memoize(fn);
    
    expect(memoized(5)).toBe(10);
    expect(memoized(5)).toBe(10);
    
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('should call function for different arguments', () => {
    const fn = vi.fn((x: number) => x * 2);
    const memoized = memoize(fn);
    
    expect(memoized(5)).toBe(10);
    expect(memoized(10)).toBe(20);
    
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it('should use custom resolver when provided', () => {
    const fn = vi.fn((obj: { id: number }) => obj.id * 2);
    const memoized = memoize(fn, (obj) => String(obj.id));
    
    expect(memoized({ id: 5 })).toBe(10);
    expect(memoized({ id: 5 })).toBe(10);
    
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe('calculateVisibleRange', () => {
  it('should calculate correct visible range', () => {
    const result = calculateVisibleRange(
      0,      // scrollTop
      500,    // containerHeight
      50,     // itemHeight
      100,    // totalItems
      3       // overscan
    );
    
    expect(result.start).toBe(0);
    expect(result.end).toBe(16); // 10 visible + 6 overscan
    expect(result.offsetY).toBe(0);
  });

  it('should handle scrolled position', () => {
    const result = calculateVisibleRange(
      500,    // scrollTop (scrolled down 10 items)
      500,    // containerHeight
      50,     // itemHeight
      100,    // totalItems
      3       // overscan
    );
    
    expect(result.start).toBe(7); // 10 - 3 overscan
    expect(result.end).toBe(23); // 10 + 10 visible + 3 overscan
    expect(result.offsetY).toBe(350); // 7 * 50
  });

  it('should not exceed total items', () => {
    const result = calculateVisibleRange(
      4500,   // scrollTop (near end)
      500,    // containerHeight
      50,     // itemHeight
      100,    // totalItems
      3       // overscan
    );
    
    expect(result.end).toBeLessThanOrEqual(100);
  });

  it('should not go below 0', () => {
    const result = calculateVisibleRange(
      0,      // scrollTop
      500,    // containerHeight
      50,     // itemHeight
      100,    // totalItems
      10      // large overscan
    );
    
    expect(result.start).toBeGreaterThanOrEqual(0);
  });
});

describe('measureRenderTime', () => {
  it('should return start and end functions', () => {
    const measure = measureRenderTime('TestComponent');
    
    expect(typeof measure.start).toBe('function');
    expect(typeof measure.end).toBe('function');
  });

  it('should measure render time', () => {
    const measure = measureRenderTime('TestComponent');
    
    measure.start();
    // Simulate some work
    const renderTime = measure.end();
    
    expect(typeof renderTime).toBe('number');
    expect(renderTime).toBeGreaterThanOrEqual(0);
  });
});
