/**
 * Interaction Hooks
 * 
 * Custom hooks for managing smooth interactions, animations,
 * and user feedback throughout the application.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { message, notification } from 'antd';

// ============================================
// Types
// ============================================

export interface InteractionFeedback {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  description?: string;
  duration?: number;
}

export interface AnimationState {
  isAnimating: boolean;
  animationClass: string;
}

export interface GestureState {
  isDragging: boolean;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  deltaX: number;
  deltaY: number;
}

// ============================================
// useInteractionFeedback Hook
// ============================================

/**
 * Hook for providing consistent user feedback
 */
export function useInteractionFeedback() {
  const showFeedback = useCallback((feedback: InteractionFeedback) => {
    const { type, message: msg, description, duration = 3 } = feedback;
    
    if (description) {
      notification[type]({
        message: msg,
        description,
        duration,
        placement: 'topRight',
      });
    } else {
      message[type](msg, duration);
    }
  }, []);

  const showSuccess = useCallback((msg: string, description?: string) => {
    showFeedback({ type: 'success', message: msg, description });
  }, [showFeedback]);

  const showError = useCallback((msg: string, description?: string) => {
    showFeedback({ type: 'error', message: msg, description });
  }, [showFeedback]);

  const showWarning = useCallback((msg: string, description?: string) => {
    showFeedback({ type: 'warning', message: msg, description });
  }, [showFeedback]);

  const showInfo = useCallback((msg: string, description?: string) => {
    showFeedback({ type: 'info', message: msg, description });
  }, [showFeedback]);

  return {
    showFeedback,
    showSuccess,
    showError,
    showWarning,
    showInfo,
  };
}

// ============================================
// useAnimatedState Hook
// ============================================

/**
 * Hook for managing animated state transitions
 */
export function useAnimatedState<T>(
  initialValue: T,
  animationDuration: number = 250
): [T, (newValue: T) => void, boolean] {
  const [value, setValue] = useState<T>(initialValue);
  const [isAnimating, setIsAnimating] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const setAnimatedValue = useCallback((newValue: T) => {
    setIsAnimating(true);
    
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      setValue(newValue);
      setIsAnimating(false);
    }, animationDuration);
  }, [animationDuration]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return [value, setAnimatedValue, isAnimating];
}

// ============================================
// useHoverState Hook
// ============================================

/**
 * Hook for managing hover state with smooth transitions
 */
export function useHoverState(delay: number = 0) {
  const [isHovered, setIsHovered] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    if (delay > 0) {
      timeoutRef.current = setTimeout(() => {
        setIsHovered(true);
      }, delay);
    } else {
      setIsHovered(true);
    }
  }, [delay]);

  const handleMouseLeave = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsHovered(false);
  }, []);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    isHovered,
    hoverProps: {
      onMouseEnter: handleMouseEnter,
      onMouseLeave: handleMouseLeave,
    },
  };
}

// ============================================
// usePressState Hook
// ============================================

/**
 * Hook for managing press/active state
 */
export function usePressState() {
  const [isPressed, setIsPressed] = useState(false);

  const pressProps = {
    onMouseDown: () => setIsPressed(true),
    onMouseUp: () => setIsPressed(false),
    onMouseLeave: () => setIsPressed(false),
    onTouchStart: () => setIsPressed(true),
    onTouchEnd: () => setIsPressed(false),
  };

  return { isPressed, pressProps };
}

// ============================================
// useFocusState Hook
// ============================================

/**
 * Hook for managing focus state with keyboard navigation
 */
export function useFocusState() {
  const [isFocused, setIsFocused] = useState(false);
  const [isFocusVisible, setIsFocusVisible] = useState(false);

  const handleFocus = useCallback((e: React.FocusEvent) => {
    setIsFocused(true);
    // Check if focus was triggered by keyboard
    if (e.target.matches(':focus-visible')) {
      setIsFocusVisible(true);
    }
  }, []);

  const handleBlur = useCallback(() => {
    setIsFocused(false);
    setIsFocusVisible(false);
  }, []);

  return {
    isFocused,
    isFocusVisible,
    focusProps: {
      onFocus: handleFocus,
      onBlur: handleBlur,
    },
  };
}

// ============================================
// useGesture Hook
// ============================================

/**
 * Hook for handling touch/mouse gestures
 */
export function useGesture(options?: {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  threshold?: number;
}) {
  const { 
    onSwipeLeft, 
    onSwipeRight, 
    onSwipeUp, 
    onSwipeDown,
    threshold = 50 
  } = options || {};

  const [gesture, setGesture] = useState<GestureState>({
    isDragging: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    deltaX: 0,
    deltaY: 0,
  });

  const handleStart = useCallback((clientX: number, clientY: number) => {
    setGesture({
      isDragging: true,
      startX: clientX,
      startY: clientY,
      currentX: clientX,
      currentY: clientY,
      deltaX: 0,
      deltaY: 0,
    });
  }, []);

  const handleMove = useCallback((clientX: number, clientY: number) => {
    setGesture(prev => {
      if (!prev.isDragging) return prev;
      return {
        ...prev,
        currentX: clientX,
        currentY: clientY,
        deltaX: clientX - prev.startX,
        deltaY: clientY - prev.startY,
      };
    });
  }, []);

  const handleEnd = useCallback(() => {
    setGesture(prev => {
      if (!prev.isDragging) return prev;

      const { deltaX, deltaY } = prev;
      const absX = Math.abs(deltaX);
      const absY = Math.abs(deltaY);

      // Determine swipe direction
      if (absX > threshold || absY > threshold) {
        if (absX > absY) {
          // Horizontal swipe
          if (deltaX > 0) {
            onSwipeRight?.();
          } else {
            onSwipeLeft?.();
          }
        } else {
          // Vertical swipe
          if (deltaY > 0) {
            onSwipeDown?.();
          } else {
            onSwipeUp?.();
          }
        }
      }

      return {
        isDragging: false,
        startX: 0,
        startY: 0,
        currentX: 0,
        currentY: 0,
        deltaX: 0,
        deltaY: 0,
      };
    });
  }, [onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown, threshold]);

  const gestureProps = {
    onMouseDown: (e: React.MouseEvent) => handleStart(e.clientX, e.clientY),
    onMouseMove: (e: React.MouseEvent) => handleMove(e.clientX, e.clientY),
    onMouseUp: handleEnd,
    onMouseLeave: handleEnd,
    onTouchStart: (e: React.TouchEvent) => {
      const touch = e.touches[0];
      handleStart(touch.clientX, touch.clientY);
    },
    onTouchMove: (e: React.TouchEvent) => {
      const touch = e.touches[0];
      handleMove(touch.clientX, touch.clientY);
    },
    onTouchEnd: handleEnd,
  };

  return { gesture, gestureProps };
}

// ============================================
// useScrollReveal Hook
// ============================================

/**
 * Hook for scroll-triggered reveal animations
 */
export function useScrollReveal(options?: {
  threshold?: number;
  rootMargin?: string;
}) {
  const { threshold = 0.1, rootMargin = '0px' } = options || {};
  const [isVisible, setIsVisible] = useState(false);
  const elementRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(element);
        }
      },
      { threshold, rootMargin }
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [threshold, rootMargin]);

  return { isVisible, elementRef };
}

// ============================================
// useDebounce Hook
// ============================================

/**
 * Hook for debouncing values
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

// ============================================
// useThrottle Hook
// ============================================

/**
 * Hook for throttling function calls
 */
export function useThrottle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): T {
  const lastCall = useRef<number>(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const throttledFn = useCallback((...args: Parameters<T>) => {
    const now = Date.now();
    const timeSinceLastCall = now - lastCall.current;

    if (timeSinceLastCall >= delay) {
      lastCall.current = now;
      fn(...args);
    } else {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        lastCall.current = Date.now();
        fn(...args);
      }, delay - timeSinceLastCall);
    }
  }, [fn, delay]) as T;

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return throttledFn;
}

// ============================================
// useKeyboardNavigation Hook
// ============================================

/**
 * Hook for keyboard navigation support
 */
export function useKeyboardNavigation(options?: {
  onEnter?: () => void;
  onEscape?: () => void;
  onArrowUp?: () => void;
  onArrowDown?: () => void;
  onArrowLeft?: () => void;
  onArrowRight?: () => void;
  onTab?: (shiftKey: boolean) => void;
}) {
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'Enter':
        options?.onEnter?.();
        break;
      case 'Escape':
        options?.onEscape?.();
        break;
      case 'ArrowUp':
        e.preventDefault();
        options?.onArrowUp?.();
        break;
      case 'ArrowDown':
        e.preventDefault();
        options?.onArrowDown?.();
        break;
      case 'ArrowLeft':
        options?.onArrowLeft?.();
        break;
      case 'ArrowRight':
        options?.onArrowRight?.();
        break;
      case 'Tab':
        options?.onTab?.(e.shiftKey);
        break;
    }
  }, [options]);

  return { onKeyDown: handleKeyDown };
}

// ============================================
// useReducedMotion Hook
// ============================================

/**
 * Hook for detecting reduced motion preference
 */
export function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return prefersReducedMotion;
}

// ============================================
// useClickOutside Hook
// ============================================

/**
 * Hook for detecting clicks outside an element
 */
export function useClickOutside<T extends HTMLElement>(
  callback: () => void
): React.RefObject<T | null> {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        callback();
      }
    };

    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [callback]);

  return ref;
}

// ============================================
// useLongPress Hook
// ============================================

/**
 * Hook for detecting long press gestures
 */
export function useLongPress(
  callback: () => void,
  options?: { delay?: number; onStart?: () => void; onCancel?: () => void }
) {
  const { delay = 500, onStart, onCancel } = options || {};
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [isLongPressing, setIsLongPressing] = useState(false);

  const start = useCallback(() => {
    onStart?.();
    timeoutRef.current = setTimeout(() => {
      setIsLongPressing(true);
      callback();
    }, delay);
  }, [callback, delay, onStart]);

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsLongPressing(false);
    onCancel?.();
  }, [onCancel]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    isLongPressing,
    longPressProps: {
      onMouseDown: start,
      onMouseUp: cancel,
      onMouseLeave: cancel,
      onTouchStart: start,
      onTouchEnd: cancel,
    },
  };
}
