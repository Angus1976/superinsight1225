/**
 * useMediaQuery Hook
 * 
 * A hook for responsive design that tracks media query matches.
 * Provides breakpoint detection and responsive utilities.
 * 
 * @module hooks/useMediaQuery
 * @version 1.0.0
 */

import { useState, useEffect, useMemo } from 'react';

/**
 * Standard breakpoints (matching Ant Design)
 */
export const breakpoints = {
  xs: 480,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
} as const;

export type Breakpoint = keyof typeof breakpoints;

/**
 * Hook for tracking a media query match
 * 
 * @param query - Media query string
 * @returns Whether the media query matches
 * 
 * @example
 * ```typescript
 * const isMobile = useMediaQuery('(max-width: 768px)');
 * const prefersDark = useMediaQuery('(prefers-color-scheme: dark)');
 * ```
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia(query);
    setMatches(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handler);
      return () => mediaQuery.removeEventListener('change', handler);
    }
    // Legacy browsers
    mediaQuery.addListener(handler);
    return () => mediaQuery.removeListener(handler);
  }, [query]);

  return matches;
}

/**
 * Hook for tracking current breakpoint
 * 
 * @returns Current breakpoint and utility functions
 * 
 * @example
 * ```typescript
 * const { breakpoint, isMobile, isTablet, isDesktop, isAbove, isBelow } = useBreakpoint();
 * 
 * if (isMobile) {
 *   return <MobileLayout />;
 * }
 * ```
 */
export function useBreakpoint(): {
  breakpoint: Breakpoint;
  width: number;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  isAbove: (bp: Breakpoint) => boolean;
  isBelow: (bp: Breakpoint) => boolean;
  isBetween: (min: Breakpoint, max: Breakpoint) => boolean;
} {
  const [width, setWidth] = useState(() => {
    if (typeof window === 'undefined') return 1200;
    return window.innerWidth;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleResize = () => {
      setWidth(window.innerWidth);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const breakpoint = useMemo<Breakpoint>(() => {
    if (width < breakpoints.xs) return 'xs';
    if (width < breakpoints.sm) return 'xs';
    if (width < breakpoints.md) return 'sm';
    if (width < breakpoints.lg) return 'md';
    if (width < breakpoints.xl) return 'lg';
    if (width < breakpoints.xxl) return 'xl';
    return 'xxl';
  }, [width]);

  const isMobile = width < breakpoints.md;
  const isTablet = width >= breakpoints.md && width < breakpoints.lg;
  const isDesktop = width >= breakpoints.lg;

  const isAbove = (bp: Breakpoint) => width >= breakpoints[bp];
  const isBelow = (bp: Breakpoint) => width < breakpoints[bp];
  const isBetween = (min: Breakpoint, max: Breakpoint) => 
    width >= breakpoints[min] && width < breakpoints[max];

  return {
    breakpoint,
    width,
    isMobile,
    isTablet,
    isDesktop,
    isAbove,
    isBelow,
    isBetween,
  };
}

/**
 * Hook for responsive values based on breakpoint
 * 
 * @param values - Object mapping breakpoints to values
 * @param defaultValue - Default value if no breakpoint matches
 * @returns Current value based on breakpoint
 * 
 * @example
 * ```typescript
 * const columns = useResponsiveValue({ xs: 1, sm: 2, md: 3, lg: 4 }, 4);
 * const fontSize = useResponsiveValue({ xs: 14, md: 16, lg: 18 }, 16);
 * ```
 */
export function useResponsiveValue<T>(
  values: Partial<Record<Breakpoint, T>>,
  defaultValue: T
): T {
  const { breakpoint } = useBreakpoint();

  return useMemo(() => {
    // Check breakpoints from largest to smallest
    const orderedBreakpoints: Breakpoint[] = ['xxl', 'xl', 'lg', 'md', 'sm', 'xs'];
    const currentIndex = orderedBreakpoints.indexOf(breakpoint);

    // Find the first defined value at or below current breakpoint
    for (let i = currentIndex; i < orderedBreakpoints.length; i++) {
      const bp = orderedBreakpoints[i];
      if (values[bp] !== undefined) {
        return values[bp] as T;
      }
    }

    return defaultValue;
  }, [values, breakpoint, defaultValue]);
}

/**
 * Hook for detecting user preferences
 */
export function usePreferences(): {
  prefersReducedMotion: boolean;
  prefersDarkMode: boolean;
  prefersHighContrast: boolean;
} {
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
  const prefersHighContrast = useMediaQuery('(prefers-contrast: high)');

  return {
    prefersReducedMotion,
    prefersDarkMode,
    prefersHighContrast,
  };
}

export default useMediaQuery;
