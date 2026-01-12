/**
 * Tests for useInteraction hooks
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  useAnimatedState,
  useHoverState,
  usePressState,
  useFocusState,
  useDebounce,
  useReducedMotion,
  useKeyboardNavigation,
} from '../useInteraction';

describe('useInteraction hooks', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('useAnimatedState', () => {
    it('should return initial value', () => {
      const { result } = renderHook(() => useAnimatedState('initial'));
      expect(result.current[0]).toBe('initial');
    });

    it('should update value after animation duration', () => {
      const { result } = renderHook(() => useAnimatedState('initial', 250));
      
      act(() => {
        result.current[1]('updated');
      });

      // Value should not change immediately
      expect(result.current[0]).toBe('initial');
      expect(result.current[2]).toBe(true); // isAnimating

      // Fast forward past animation duration
      act(() => {
        vi.advanceTimersByTime(300);
      });

      expect(result.current[0]).toBe('updated');
      expect(result.current[2]).toBe(false); // isAnimating
    });
  });

  describe('useHoverState', () => {
    it('should start with isHovered as false', () => {
      const { result } = renderHook(() => useHoverState());
      expect(result.current.isHovered).toBe(false);
    });

    it('should set isHovered to true on mouse enter', () => {
      const { result } = renderHook(() => useHoverState());
      
      act(() => {
        result.current.hoverProps.onMouseEnter();
      });

      expect(result.current.isHovered).toBe(true);
    });

    it('should set isHovered to false on mouse leave', () => {
      const { result } = renderHook(() => useHoverState());
      
      act(() => {
        result.current.hoverProps.onMouseEnter();
      });
      
      act(() => {
        result.current.hoverProps.onMouseLeave();
      });

      expect(result.current.isHovered).toBe(false);
    });

    it('should respect delay parameter', () => {
      const { result } = renderHook(() => useHoverState(100));
      
      act(() => {
        result.current.hoverProps.onMouseEnter();
      });

      // Should not be hovered immediately
      expect(result.current.isHovered).toBe(false);

      act(() => {
        vi.advanceTimersByTime(150);
      });

      expect(result.current.isHovered).toBe(true);
    });
  });

  describe('usePressState', () => {
    it('should start with isPressed as false', () => {
      const { result } = renderHook(() => usePressState());
      expect(result.current.isPressed).toBe(false);
    });

    it('should set isPressed to true on mouse down', () => {
      const { result } = renderHook(() => usePressState());
      
      act(() => {
        result.current.pressProps.onMouseDown();
      });

      expect(result.current.isPressed).toBe(true);
    });

    it('should set isPressed to false on mouse up', () => {
      const { result } = renderHook(() => usePressState());
      
      act(() => {
        result.current.pressProps.onMouseDown();
      });
      
      act(() => {
        result.current.pressProps.onMouseUp();
      });

      expect(result.current.isPressed).toBe(false);
    });
  });

  describe('useFocusState', () => {
    it('should start with isFocused as false', () => {
      const { result } = renderHook(() => useFocusState());
      expect(result.current.isFocused).toBe(false);
    });

    it('should set isFocused to true on focus', () => {
      const { result } = renderHook(() => useFocusState());
      
      const mockEvent = {
        target: {
          matches: () => false,
        },
      } as unknown as React.FocusEvent;

      act(() => {
        result.current.focusProps.onFocus(mockEvent);
      });

      expect(result.current.isFocused).toBe(true);
    });

    it('should set isFocused to false on blur', () => {
      const { result } = renderHook(() => useFocusState());
      
      const mockEvent = {
        target: {
          matches: () => false,
        },
      } as unknown as React.FocusEvent;

      act(() => {
        result.current.focusProps.onFocus(mockEvent);
      });
      
      act(() => {
        result.current.focusProps.onBlur();
      });

      expect(result.current.isFocused).toBe(false);
    });
  });

  describe('useDebounce', () => {
    it('should return initial value immediately', () => {
      const { result } = renderHook(() => useDebounce('initial', 300));
      expect(result.current).toBe('initial');
    });

    it('should debounce value changes', () => {
      const { result, rerender } = renderHook(
        ({ value }) => useDebounce(value, 300),
        { initialProps: { value: 'initial' } }
      );

      rerender({ value: 'updated' });

      // Value should not change immediately
      expect(result.current).toBe('initial');

      act(() => {
        vi.advanceTimersByTime(350);
      });

      expect(result.current).toBe('updated');
    });
  });

  describe('useReducedMotion', () => {
    it('should return false by default', () => {
      // Mock matchMedia
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });

      const { result } = renderHook(() => useReducedMotion());
      expect(result.current).toBe(false);
    });
  });

  describe('useKeyboardNavigation', () => {
    it('should call onEnter when Enter key is pressed', () => {
      const onEnter = vi.fn();
      const { result } = renderHook(() => useKeyboardNavigation({ onEnter }));
      
      const mockEvent = {
        key: 'Enter',
        preventDefault: vi.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        result.current.onKeyDown(mockEvent);
      });

      expect(onEnter).toHaveBeenCalled();
    });

    it('should call onEscape when Escape key is pressed', () => {
      const onEscape = vi.fn();
      const { result } = renderHook(() => useKeyboardNavigation({ onEscape }));
      
      const mockEvent = {
        key: 'Escape',
        preventDefault: vi.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        result.current.onKeyDown(mockEvent);
      });

      expect(onEscape).toHaveBeenCalled();
    });

    it('should call onArrowUp when ArrowUp key is pressed', () => {
      const onArrowUp = vi.fn();
      const { result } = renderHook(() => useKeyboardNavigation({ onArrowUp }));
      
      const mockEvent = {
        key: 'ArrowUp',
        preventDefault: vi.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        result.current.onKeyDown(mockEvent);
      });

      expect(onArrowUp).toHaveBeenCalled();
      expect(mockEvent.preventDefault).toHaveBeenCalled();
    });

    it('should call onArrowDown when ArrowDown key is pressed', () => {
      const onArrowDown = vi.fn();
      const { result } = renderHook(() => useKeyboardNavigation({ onArrowDown }));
      
      const mockEvent = {
        key: 'ArrowDown',
        preventDefault: vi.fn(),
      } as unknown as React.KeyboardEvent;

      act(() => {
        result.current.onKeyDown(mockEvent);
      });

      expect(onArrowDown).toHaveBeenCalled();
      expect(mockEvent.preventDefault).toHaveBeenCalled();
    });
  });
});
