/**
 * Tests for useResponsive hook
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useResponsive, useResponsiveValue, BREAKPOINTS } from '../useResponsive';

// Mock window dimensions
const mockWindowDimensions = (width: number, height: number) => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  });
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: height,
  });
};

describe('useResponsive', () => {
  const originalInnerWidth = window.innerWidth;
  const originalInnerHeight = window.innerHeight;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    mockWindowDimensions(originalInnerWidth, originalInnerHeight);
  });

  describe('breakpoint detection', () => {
    it('should detect xs breakpoint for small screens', () => {
      mockWindowDimensions(400, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.breakpoint).toBe('xs');
      expect(result.current.isXs).toBe(true);
      expect(result.current.isMobile).toBe(true);
    });

    it('should detect sm breakpoint', () => {
      mockWindowDimensions(500, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.breakpoint).toBe('xs');
      expect(result.current.isMobile).toBe(true);
    });

    it('should detect md breakpoint', () => {
      mockWindowDimensions(700, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.breakpoint).toBe('sm');
      expect(result.current.isTablet).toBe(true);
    });

    it('should detect lg breakpoint', () => {
      mockWindowDimensions(1000, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.breakpoint).toBe('lg');
      expect(result.current.isDesktop).toBe(true);
    });

    it('should detect xl breakpoint', () => {
      mockWindowDimensions(1400, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.breakpoint).toBe('xl');
      expect(result.current.isDesktop).toBe(true);
    });

    it('should detect xxl breakpoint', () => {
      mockWindowDimensions(1800, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.breakpoint).toBe('xxl');
      expect(result.current.isLargeDesktop).toBe(true);
    });
  });

  describe('device type detection', () => {
    it('should detect mobile device', () => {
      mockWindowDimensions(400, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.deviceType).toBe('mobile');
      expect(result.current.isMobile).toBe(true);
      expect(result.current.isTablet).toBe(false);
      expect(result.current.isDesktop).toBe(false);
    });

    it('should detect tablet device', () => {
      mockWindowDimensions(800, 1024);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.deviceType).toBe('tablet');
      expect(result.current.isMobile).toBe(false);
      expect(result.current.isTablet).toBe(true);
      expect(result.current.isDesktop).toBe(false);
    });

    it('should detect desktop device', () => {
      mockWindowDimensions(1200, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.deviceType).toBe('desktop');
      expect(result.current.isMobile).toBe(false);
      expect(result.current.isTablet).toBe(false);
      expect(result.current.isDesktop).toBe(true);
    });
  });

  describe('orientation detection', () => {
    it('should detect portrait orientation', () => {
      mockWindowDimensions(400, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.orientation).toBe('portrait');
      expect(result.current.isPortrait).toBe(true);
      expect(result.current.isLandscape).toBe(false);
    });

    it('should detect landscape orientation', () => {
      mockWindowDimensions(800, 400);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.orientation).toBe('landscape');
      expect(result.current.isPortrait).toBe(false);
      expect(result.current.isLandscape).toBe(true);
    });
  });

  describe('utility functions', () => {
    it('should correctly check isAbove', () => {
      mockWindowDimensions(1000, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.isAbove('xs')).toBe(true);
      expect(result.current.isAbove('sm')).toBe(true);
      expect(result.current.isAbove('md')).toBe(true);
      expect(result.current.isAbove('lg')).toBe(true);
      expect(result.current.isAbove('xl')).toBe(false);
    });

    it('should correctly check isBelow', () => {
      mockWindowDimensions(700, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.isBelow('xs')).toBe(false);
      expect(result.current.isBelow('sm')).toBe(false);
      expect(result.current.isBelow('md')).toBe(true);
      expect(result.current.isBelow('lg')).toBe(true);
    });

    it('should correctly check isBetween', () => {
      mockWindowDimensions(800, 600);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.isBetween('sm', 'lg')).toBe(true);
      expect(result.current.isBetween('lg', 'xl')).toBe(false);
    });
  });

  describe('resize handling', () => {
    it('should update on window resize', async () => {
      mockWindowDimensions(1200, 800);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.isDesktop).toBe(true);
      
      // Simulate resize to mobile
      act(() => {
        mockWindowDimensions(400, 800);
        window.dispatchEvent(new Event('resize'));
      });
      
      // Wait for debounce
      await act(async () => {
        vi.advanceTimersByTime(150);
      });
      
      expect(result.current.isMobile).toBe(true);
    });
  });

  describe('dimensions', () => {
    it('should provide current dimensions', () => {
      mockWindowDimensions(1024, 768);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.width).toBe(1024);
      expect(result.current.height).toBe(768);
    });
  });
});

describe('useResponsiveValue', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should return value for current breakpoint', () => {
    mockWindowDimensions(400, 800);
    
    const { result } = renderHook(() => 
      useResponsiveValue({
        default: 'default',
        xs: 'extra-small',
        md: 'medium',
        lg: 'large',
      })
    );
    
    expect(result.current).toBe('extra-small');
  });

  it('should fall back to smaller breakpoint value', () => {
    mockWindowDimensions(700, 800);
    
    const { result } = renderHook(() => 
      useResponsiveValue({
        default: 'default',
        xs: 'extra-small',
        lg: 'large',
      })
    );
    
    // sm breakpoint should fall back to xs value
    expect(result.current).toBe('extra-small');
  });

  it('should return default when no matching breakpoint', () => {
    mockWindowDimensions(1800, 800);
    
    const { result } = renderHook(() => 
      useResponsiveValue({
        default: 'default-value',
      })
    );
    
    expect(result.current).toBe('default-value');
  });
});

describe('BREAKPOINTS', () => {
  it('should have correct breakpoint values', () => {
    expect(BREAKPOINTS.xs).toBe(480);
    expect(BREAKPOINTS.sm).toBe(576);
    expect(BREAKPOINTS.md).toBe(768);
    expect(BREAKPOINTS.lg).toBe(992);
    expect(BREAKPOINTS.xl).toBe(1200);
    expect(BREAKPOINTS.xxl).toBe(1600);
  });
});
