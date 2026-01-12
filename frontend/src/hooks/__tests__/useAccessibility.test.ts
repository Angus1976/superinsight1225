/**
 * Accessibility Hooks Tests
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  useReducedMotion,
  useHighContrast,
  useFocusVisible,
  useRovingTabIndex,
} from '../useAccessibility';

describe('Accessibility Hooks', () => {
  describe('useReducedMotion', () => {
    let originalMatchMedia: typeof window.matchMedia;

    beforeEach(() => {
      originalMatchMedia = window.matchMedia;
    });

    afterEach(() => {
      window.matchMedia = originalMatchMedia;
    });

    it('should return false when reduced motion is not preferred', () => {
      window.matchMedia = vi.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      const { result } = renderHook(() => useReducedMotion());
      expect(result.current).toBe(false);
    });

    it('should return true when reduced motion is preferred', () => {
      window.matchMedia = vi.fn().mockImplementation((query) => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      const { result } = renderHook(() => useReducedMotion());
      expect(result.current).toBe(true);
    });
  });

  describe('useHighContrast', () => {
    let originalMatchMedia: typeof window.matchMedia;

    beforeEach(() => {
      originalMatchMedia = window.matchMedia;
    });

    afterEach(() => {
      window.matchMedia = originalMatchMedia;
    });

    it('should return false when high contrast is not preferred', () => {
      window.matchMedia = vi.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      const { result } = renderHook(() => useHighContrast());
      expect(result.current).toBe(false);
    });

    it('should return true when high contrast is preferred', () => {
      window.matchMedia = vi.fn().mockImplementation((query) => ({
        matches: query === '(prefers-contrast: more)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      const { result } = renderHook(() => useHighContrast());
      expect(result.current).toBe(true);
    });
  });

  describe('useFocusVisible', () => {
    it('should track focus state', () => {
      const { result } = renderHook(() => useFocusVisible());

      expect(result.current.isFocused).toBe(false);
      expect(result.current.isFocusVisible).toBe(false);
      expect(result.current.focusProps).toBeDefined();
      expect(typeof result.current.focusProps.onFocus).toBe('function');
      expect(typeof result.current.focusProps.onBlur).toBe('function');
    });

    it('should update focus state on focus/blur', () => {
      const { result } = renderHook(() => useFocusVisible());

      act(() => {
        result.current.focusProps.onFocus();
      });

      expect(result.current.isFocused).toBe(true);

      act(() => {
        result.current.focusProps.onBlur();
      });

      expect(result.current.isFocused).toBe(false);
    });
  });

  describe('useRovingTabIndex', () => {
    it('should initialize with correct state', () => {
      const { result } = renderHook(() => useRovingTabIndex(5, 0));

      expect(result.current.focusedIndex).toBe(0);
      expect(typeof result.current.setItemRef).toBe('function');
      expect(typeof result.current.focusItem).toBe('function');
      expect(typeof result.current.focusNext).toBe('function');
      expect(typeof result.current.focusPrevious).toBe('function');
      expect(typeof result.current.focusFirst).toBe('function');
      expect(typeof result.current.focusLast).toBe('function');
      expect(typeof result.current.getTabIndex).toBe('function');
    });

    it('should return correct tabIndex', () => {
      const { result } = renderHook(() => useRovingTabIndex(5, 2));

      expect(result.current.getTabIndex(0)).toBe(-1);
      expect(result.current.getTabIndex(1)).toBe(-1);
      expect(result.current.getTabIndex(2)).toBe(0);
      expect(result.current.getTabIndex(3)).toBe(-1);
      expect(result.current.getTabIndex(4)).toBe(-1);
    });

    it('should handle custom initial index', () => {
      const { result } = renderHook(() => useRovingTabIndex(5, 3));

      expect(result.current.focusedIndex).toBe(3);
      expect(result.current.getTabIndex(3)).toBe(0);
    });
  });
});
