/**
 * Custom Hooks Index
 * 
 * This module exports all custom hooks for easy importing.
 * 
 * @module utils/hooks
 * @version 1.0.0
 */

// Callback and memoization hooks
export { useStableCallback, useEventCallback } from './useStableCallback';

// State tracking hooks
export { usePrevious, usePreviousWithInitial, useHasChanged } from './usePrevious';

// Debounce hooks
export { useDebounce, useDebouncedCallback, useDebouncedCallbackWithControl } from './useDebounce';

// Toggle hooks
export { useToggle, useToggles, type UseToggleReturn } from './useToggle';

// Storage hooks
export { useLocalStorage, useSessionStorage, type UseLocalStorageOptions } from './useLocalStorage';

// Event hooks
export { useClickOutside, useClickOutsideMultiple, type UseClickOutsideOptions } from './useClickOutside';

// Responsive hooks
export { 
  useMediaQuery, 
  useBreakpoint, 
  useResponsiveValue, 
  usePreferences,
  breakpoints,
  type Breakpoint 
} from './useMediaQuery';
