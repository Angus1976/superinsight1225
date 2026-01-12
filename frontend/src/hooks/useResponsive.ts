/**
 * useResponsive Hook
 * 
 * Provides responsive design utilities for detecting device types,
 * breakpoints, and orientation changes.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';

// Breakpoint values matching the design system
export const BREAKPOINTS = {
  xs: 480,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
} as const;

export type BreakpointKey = keyof typeof BREAKPOINTS;
export type DeviceType = 'mobile' | 'tablet' | 'desktop' | 'largeDesktop';
export type Orientation = 'portrait' | 'landscape';

export interface ResponsiveState {
  // Current breakpoint
  breakpoint: BreakpointKey;
  
  // Device type
  deviceType: DeviceType;
  
  // Boolean flags for each breakpoint
  isXs: boolean;
  isSm: boolean;
  isMd: boolean;
  isLg: boolean;
  isXl: boolean;
  isXxl: boolean;
  
  // Device type flags
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  isLargeDesktop: boolean;
  
  // Orientation
  orientation: Orientation;
  isPortrait: boolean;
  isLandscape: boolean;
  
  // Screen dimensions
  width: number;
  height: number;
  
  // Touch device detection
  isTouchDevice: boolean;
  
  // Responsive utilities
  isAbove: (breakpoint: BreakpointKey) => boolean;
  isBelow: (breakpoint: BreakpointKey) => boolean;
  isBetween: (min: BreakpointKey, max: BreakpointKey) => boolean;
}

const getBreakpoint = (width: number): BreakpointKey => {
  if (width < BREAKPOINTS.xs) return 'xs';
  if (width < BREAKPOINTS.sm) return 'xs';
  if (width < BREAKPOINTS.md) return 'sm';
  if (width < BREAKPOINTS.lg) return 'md';
  if (width < BREAKPOINTS.xl) return 'lg';
  if (width < BREAKPOINTS.xxl) return 'xl';
  return 'xxl';
};

const getDeviceType = (width: number): DeviceType => {
  if (width < BREAKPOINTS.sm) return 'mobile';
  if (width < BREAKPOINTS.lg) return 'tablet';
  if (width < BREAKPOINTS.xxl) return 'desktop';
  return 'largeDesktop';
};

const getOrientation = (width: number, height: number): Orientation => {
  return width >= height ? 'landscape' : 'portrait';
};

const isTouchDeviceCheck = (): boolean => {
  if (typeof window === 'undefined') return false;
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
};

export const useResponsive = (): ResponsiveState => {
  const [dimensions, setDimensions] = useState(() => ({
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    height: typeof window !== 'undefined' ? window.innerHeight : 800,
  }));

  const [isTouchDevice] = useState(isTouchDeviceCheck);

  // Debounced resize handler
  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;
    
    const handleResize = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        setDimensions({
          width: window.innerWidth,
          height: window.innerHeight,
        });
      }, 100); // Debounce for performance
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleResize);

    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleResize);
    };
  }, []);

  const { width, height } = dimensions;
  const breakpoint = getBreakpoint(width);
  const deviceType = getDeviceType(width);
  const orientation = getOrientation(width, height);

  // Utility functions
  const isAbove = useCallback((bp: BreakpointKey): boolean => {
    return width >= BREAKPOINTS[bp];
  }, [width]);

  const isBelow = useCallback((bp: BreakpointKey): boolean => {
    return width < BREAKPOINTS[bp];
  }, [width]);

  const isBetween = useCallback((min: BreakpointKey, max: BreakpointKey): boolean => {
    return width >= BREAKPOINTS[min] && width < BREAKPOINTS[max];
  }, [width]);

  return useMemo(() => ({
    breakpoint,
    deviceType,
    
    // Breakpoint flags
    isXs: breakpoint === 'xs',
    isSm: breakpoint === 'sm',
    isMd: breakpoint === 'md',
    isLg: breakpoint === 'lg',
    isXl: breakpoint === 'xl',
    isXxl: breakpoint === 'xxl',
    
    // Device type flags
    isMobile: deviceType === 'mobile',
    isTablet: deviceType === 'tablet',
    isDesktop: deviceType === 'desktop' || deviceType === 'largeDesktop',
    isLargeDesktop: deviceType === 'largeDesktop',
    
    // Orientation
    orientation,
    isPortrait: orientation === 'portrait',
    isLandscape: orientation === 'landscape',
    
    // Dimensions
    width,
    height,
    
    // Touch device
    isTouchDevice,
    
    // Utilities
    isAbove,
    isBelow,
    isBetween,
  }), [breakpoint, deviceType, orientation, width, height, isTouchDevice, isAbove, isBelow, isBetween]);
};

/**
 * Hook for responsive values based on breakpoints
 */
export function useResponsiveValue<T>(values: Partial<Record<BreakpointKey, T>> & { default: T }): T {
  const { breakpoint } = useResponsive();
  
  // Find the appropriate value for current breakpoint
  const breakpointOrder: BreakpointKey[] = ['xxl', 'xl', 'lg', 'md', 'sm', 'xs'];
  const currentIndex = breakpointOrder.indexOf(breakpoint);
  
  for (let i = currentIndex; i < breakpointOrder.length; i++) {
    const bp = breakpointOrder[i];
    if (values[bp] !== undefined) {
      return values[bp] as T;
    }
  }
  
  return values.default;
}

/**
 * Hook for responsive column spans
 */
export interface ResponsiveColSpan {
  xs?: number;
  sm?: number;
  md?: number;
  lg?: number;
  xl?: number;
  xxl?: number;
}

export const useResponsiveColSpan = (spans: ResponsiveColSpan): number => {
  const { breakpoint } = useResponsive();
  
  const breakpointOrder: BreakpointKey[] = ['xxl', 'xl', 'lg', 'md', 'sm', 'xs'];
  const currentIndex = breakpointOrder.indexOf(breakpoint);
  
  for (let i = currentIndex; i < breakpointOrder.length; i++) {
    const bp = breakpointOrder[i];
    if (spans[bp] !== undefined) {
      return spans[bp] as number;
    }
  }
  
  return 24; // Default full width
};

export default useResponsive;
