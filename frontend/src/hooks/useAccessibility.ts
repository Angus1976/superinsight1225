/**
 * useAccessibility Hook
 * 
 * Comprehensive accessibility hook for WCAG 2.1 compliance.
 * Provides focus management, keyboard navigation, and screen reader support.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  announce,
  announceError,
  announceSuccess,
  trapFocus,
  restoreFocus,
  getFocusableElements,
  focusFirstElement,
  prefersReducedMotion,
  prefersHighContrast,
  createKeyboardNavigation,
  initLiveRegion,
} from '@/utils/accessibility';

// ============================================
// useFocusTrap Hook
// ============================================

interface UseFocusTrapOptions {
  enabled?: boolean;
  restoreFocusOnUnmount?: boolean;
}

/**
 * Hook to trap focus within a container (for modals, dialogs)
 */
export const useFocusTrap = <T extends HTMLElement>(
  options: UseFocusTrapOptions = {}
) => {
  const { enabled = true, restoreFocusOnUnmount = true } = options;
  const containerRef = useRef<T>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!enabled || !containerRef.current) return;

    // Store the previously focused element
    previousFocusRef.current = document.activeElement as HTMLElement;

    // Set up focus trap
    const cleanup = trapFocus(containerRef.current);

    return () => {
      cleanup();
      if (restoreFocusOnUnmount && previousFocusRef.current) {
        restoreFocus(previousFocusRef.current);
      }
    };
  }, [enabled, restoreFocusOnUnmount]);

  return containerRef;
};

// ============================================
// useAnnounce Hook
// ============================================

/**
 * Hook for screen reader announcements
 */
export const useAnnounce = () => {
  useEffect(() => {
    initLiveRegion();
  }, []);

  return {
    announce,
    announceError,
    announceSuccess,
  };
};

// ============================================
// useKeyboardNavigation Hook
// ============================================

interface UseKeyboardNavigationOptions {
  orientation?: 'horizontal' | 'vertical';
  loop?: boolean;
  onSelect?: (index: number) => void;
  onEscape?: () => void;
}

/**
 * Hook for keyboard navigation in lists/menus
 */
export const useKeyboardNavigation = <T extends HTMLElement>(
  itemCount: number,
  options: UseKeyboardNavigationOptions = {}
) => {
  const { orientation = 'vertical', loop = true, onSelect, onEscape } = options;
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<T>(null);
  const itemRefs = useRef<(HTMLElement | null)[]>([]);

  const setItemRef = useCallback((index: number) => (el: HTMLElement | null) => {
    itemRefs.current[index] = el;
  }, []);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      const prevKey = orientation === 'vertical' ? 'ArrowUp' : 'ArrowLeft';
      const nextKey = orientation === 'vertical' ? 'ArrowDown' : 'ArrowRight';

      switch (event.key) {
        case prevKey:
          event.preventDefault();
          setActiveIndex(prev => {
            const newIndex = prev > 0 ? prev - 1 : loop ? itemCount - 1 : prev;
            itemRefs.current[newIndex]?.focus();
            return newIndex;
          });
          break;

        case nextKey:
          event.preventDefault();
          setActiveIndex(prev => {
            const newIndex = prev < itemCount - 1 ? prev + 1 : loop ? 0 : prev;
            itemRefs.current[newIndex]?.focus();
            return newIndex;
          });
          break;

        case 'Home':
          event.preventDefault();
          setActiveIndex(0);
          itemRefs.current[0]?.focus();
          break;

        case 'End':
          event.preventDefault();
          setActiveIndex(itemCount - 1);
          itemRefs.current[itemCount - 1]?.focus();
          break;

        case 'Enter':
        case ' ':
          event.preventDefault();
          onSelect?.(activeIndex);
          break;

        case 'Escape':
          event.preventDefault();
          onEscape?.();
          break;
      }
    },
    [orientation, loop, itemCount, activeIndex, onSelect, onEscape]
  );

  const getItemProps = useCallback(
    (index: number) => ({
      ref: setItemRef(index),
      tabIndex: index === activeIndex ? 0 : -1,
      'aria-selected': index === activeIndex,
      onFocus: () => setActiveIndex(index),
    }),
    [activeIndex, setItemRef]
  );

  return {
    containerRef,
    activeIndex,
    setActiveIndex,
    handleKeyDown,
    getItemProps,
  };
};

// ============================================
// useReducedMotion Hook
// ============================================

/**
 * Hook to detect user's reduced motion preference
 */
export const useReducedMotion = (): boolean => {
  const [reducedMotion, setReducedMotion] = useState(prefersReducedMotion);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    
    const handleChange = (e: MediaQueryListEvent) => {
      setReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return reducedMotion;
};

// ============================================
// useHighContrast Hook
// ============================================

/**
 * Hook to detect user's high contrast preference
 */
export const useHighContrast = (): boolean => {
  const [highContrast, setHighContrast] = useState(prefersHighContrast);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-contrast: more)');
    
    const handleChange = (e: MediaQueryListEvent) => {
      setHighContrast(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return highContrast;
};

// ============================================
// useFocusVisible Hook
// ============================================

/**
 * Hook to track focus-visible state
 */
export const useFocusVisible = () => {
  const [isFocusVisible, setIsFocusVisible] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const hadKeyboardEventRef = useRef(false);

  useEffect(() => {
    const handleKeyDown = () => {
      hadKeyboardEventRef.current = true;
    };

    const handlePointerDown = () => {
      hadKeyboardEventRef.current = false;
    };

    document.addEventListener('keydown', handleKeyDown, true);
    document.addEventListener('mousedown', handlePointerDown, true);
    document.addEventListener('pointerdown', handlePointerDown, true);

    return () => {
      document.removeEventListener('keydown', handleKeyDown, true);
      document.removeEventListener('mousedown', handlePointerDown, true);
      document.removeEventListener('pointerdown', handlePointerDown, true);
    };
  }, []);

  const handleFocus = useCallback(() => {
    setIsFocused(true);
    setIsFocusVisible(hadKeyboardEventRef.current);
  }, []);

  const handleBlur = useCallback(() => {
    setIsFocused(false);
    setIsFocusVisible(false);
  }, []);

  return {
    isFocusVisible,
    isFocused,
    focusProps: {
      onFocus: handleFocus,
      onBlur: handleBlur,
    },
  };
};

// ============================================
// useAriaLive Hook
// ============================================

interface UseAriaLiveOptions {
  politeness?: 'polite' | 'assertive' | 'off';
  atomic?: boolean;
  relevant?: 'additions' | 'removals' | 'text' | 'all';
}

/**
 * Hook for managing ARIA live regions
 */
export const useAriaLive = (options: UseAriaLiveOptions = {}) => {
  const { politeness = 'polite', atomic = true, relevant = 'additions text' } = options;
  const [message, setMessage] = useState('');

  const liveRegionProps = {
    role: 'status',
    'aria-live': politeness,
    'aria-atomic': atomic,
    'aria-relevant': relevant,
  };

  const announceMessage = useCallback((newMessage: string) => {
    // Clear and set to trigger announcement
    setMessage('');
    requestAnimationFrame(() => {
      setMessage(newMessage);
    });
  }, []);

  return {
    message,
    liveRegionProps,
    announce: announceMessage,
  };
};

// ============================================
// useRovingTabIndex Hook
// ============================================

/**
 * Hook for roving tabindex pattern
 */
export const useRovingTabIndex = <T extends HTMLElement>(
  itemCount: number,
  initialIndex: number = 0
) => {
  const [focusedIndex, setFocusedIndex] = useState(initialIndex);
  const itemRefs = useRef<(T | null)[]>([]);

  const setItemRef = useCallback((index: number) => (el: T | null) => {
    itemRefs.current[index] = el;
  }, []);

  const focusItem = useCallback((index: number) => {
    if (index >= 0 && index < itemCount) {
      setFocusedIndex(index);
      itemRefs.current[index]?.focus();
    }
  }, [itemCount]);

  const focusNext = useCallback(() => {
    focusItem((focusedIndex + 1) % itemCount);
  }, [focusedIndex, itemCount, focusItem]);

  const focusPrevious = useCallback(() => {
    focusItem((focusedIndex - 1 + itemCount) % itemCount);
  }, [focusedIndex, itemCount, focusItem]);

  const focusFirst = useCallback(() => {
    focusItem(0);
  }, [focusItem]);

  const focusLast = useCallback(() => {
    focusItem(itemCount - 1);
  }, [itemCount, focusItem]);

  const getTabIndex = useCallback(
    (index: number) => (index === focusedIndex ? 0 : -1),
    [focusedIndex]
  );

  return {
    focusedIndex,
    setItemRef,
    focusItem,
    focusNext,
    focusPrevious,
    focusFirst,
    focusLast,
    getTabIndex,
  };
};

// ============================================
// useSkipLink Hook
// ============================================

/**
 * Hook for skip link functionality
 */
export const useSkipLink = (targetId: string) => {
  const skipToContent = useCallback(() => {
    const target = document.getElementById(targetId);
    if (target) {
      target.setAttribute('tabindex', '-1');
      target.focus();
      // Remove tabindex after focus to maintain natural tab order
      target.addEventListener('blur', () => {
        target.removeAttribute('tabindex');
      }, { once: true });
    }
  }, [targetId]);

  return {
    skipToContent,
    skipLinkProps: {
      href: `#${targetId}`,
      onClick: (e: React.MouseEvent) => {
        e.preventDefault();
        skipToContent();
      },
    },
  };
};

// ============================================
// useAccessibilityPreferences Hook
// ============================================

interface AccessibilityPreferences {
  reducedMotion: boolean;
  highContrast: boolean;
  fontSize: 'normal' | 'large' | 'larger';
}

/**
 * Hook to manage all accessibility preferences
 */
export const useAccessibilityPreferences = () => {
  const reducedMotion = useReducedMotion();
  const highContrast = useHighContrast();
  const [fontSize, setFontSize] = useState<'normal' | 'large' | 'larger'>('normal');

  // Load saved preferences
  useEffect(() => {
    const savedFontSize = localStorage.getItem('a11y-font-size');
    if (savedFontSize && ['normal', 'large', 'larger'].includes(savedFontSize)) {
      setFontSize(savedFontSize as 'normal' | 'large' | 'larger');
    }
  }, []);

  // Apply font size to document
  useEffect(() => {
    const fontSizeMap = {
      normal: '100%',
      large: '125%',
      larger: '150%',
    };
    document.documentElement.style.fontSize = fontSizeMap[fontSize];
    localStorage.setItem('a11y-font-size', fontSize);
  }, [fontSize]);

  const preferences: AccessibilityPreferences = {
    reducedMotion,
    highContrast,
    fontSize,
  };

  return {
    preferences,
    setFontSize,
  };
};

export default {
  useFocusTrap,
  useAnnounce,
  useKeyboardNavigation,
  useReducedMotion,
  useHighContrast,
  useFocusVisible,
  useAriaLive,
  useRovingTabIndex,
  useSkipLink,
  useAccessibilityPreferences,
};
