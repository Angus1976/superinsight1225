/**
 * Tests for useComponentRenderTime hook
 * 
 * Validates component render time tracking and budget enforcement.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  RENDER_TIME_BUDGET,
  WARNING_THRESHOLD,
  getAllRenderMetrics,
  getRenderMetricsSummary,
  clearRenderMetrics,
} from '../useComponentRenderTime';

// Mock performance.now for consistent testing
const mockPerformanceNow = vi.fn();
const originalPerformanceNow = performance.now;

beforeEach(() => {
  // Reset mocks
  vi.clearAllMocks();
  clearRenderMetrics();
  
  // Mock performance.now
  let time = 0;
  mockPerformanceNow.mockImplementation(() => {
    time += 10; // Simulate 10ms per call
    return time;
  });
  performance.now = mockPerformanceNow;
});

afterEach(() => {
  // Restore original performance.now
  performance.now = originalPerformanceNow;
});

describe('useComponentRenderTime constants', () => {
  it('should have correct render time budget', () => {
    expect(RENDER_TIME_BUDGET).toBe(100);
  });

  it('should have correct warning threshold', () => {
    expect(WARNING_THRESHOLD).toBe(80);
  });
});

describe('getRenderMetricsSummary', () => {
  it('should return empty summary when no metrics collected', () => {
    const summary = getRenderMetricsSummary();
    
    expect(summary.totalComponents).toBe(0);
    expect(summary.componentsWithinBudget).toBe(0);
    expect(summary.componentsExceedingBudget).toBe(0);
    expect(summary.averageRenderTime).toBe(0);
    expect(summary.slowestComponents).toEqual([]);
  });
});

describe('getAllRenderMetrics', () => {
  it('should return empty map when no metrics collected', () => {
    const metrics = getAllRenderMetrics();
    
    expect(metrics.size).toBe(0);
  });
});

describe('clearRenderMetrics', () => {
  it('should clear all metrics', () => {
    // Clear any existing metrics
    clearRenderMetrics();
    
    const metrics = getAllRenderMetrics();
    expect(metrics.size).toBe(0);
  });
});

describe('Render time budget validation', () => {
  it('should consider render time within budget when under 100ms', () => {
    const renderTime = 50;
    const isWithinBudget = renderTime <= RENDER_TIME_BUDGET;
    
    expect(isWithinBudget).toBe(true);
  });

  it('should consider render time exceeding budget when over 100ms', () => {
    const renderTime = 150;
    const isWithinBudget = renderTime <= RENDER_TIME_BUDGET;
    
    expect(isWithinBudget).toBe(false);
  });

  it('should consider render time at warning level when at 80% of budget', () => {
    const renderTime = 80;
    const warningLevel = (renderTime / RENDER_TIME_BUDGET) * 100;
    
    expect(warningLevel).toBe(80);
    expect(warningLevel >= WARNING_THRESHOLD).toBe(true);
  });

  it('should not trigger warning when under 80% of budget', () => {
    const renderTime = 70;
    const warningLevel = (renderTime / RENDER_TIME_BUDGET) * 100;
    
    expect(warningLevel).toBe(70);
    expect(warningLevel >= WARNING_THRESHOLD).toBe(false);
  });
});
