/**
 * useDebounce Hook
 * 
 * Hooks for debouncing values and callbacks.
 * Useful for search inputs, form validation, and API calls.
 * 
 * @module hooks/useDebounce
 * @version 1.0.0
 */

import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Returns a debounced version of a value.
 * 
 * @param value - The value to debounce
 * @param delay - The debounce delay in milliseconds
 * @returns The debounced value
 * 
 * @example
 * ```typescript
 * const MyComponent = () => {
 *   const [searchTerm, setSearchTerm] = useState('');
 *   const debouncedSearchTerm = useDebounce(searchTerm, 300);
 *   
 *   useEffect(() => {
 *     if (debouncedSearchTerm) {
 *       // Perform search
 *       searchApi(debouncedSearchTerm);
 *     }
 *   }, [debouncedSearchTerm]);
 *   
 *   return <input value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />;
 * };
 * ```
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

/**
 * Returns a debounced callback function.
 * 
 * @param callback - The callback to debounce
 * @param delay - The debounce delay in milliseconds
 * @param deps - Dependencies for the callback
 * @returns The debounced callback
 * 
 * @example
 * ```typescript
 * const MyComponent = () => {
 *   const handleSearch = useDebouncedCallback(
 *     (term: string) => {
 *       searchApi(term);
 *     },
 *     300,
 *     []
 *   );
 *   
 *   return <input onChange={e => handleSearch(e.target.value)} />;
 * };
 * ```
 */
export function useDebouncedCallback<T extends (...args: Parameters<T>) => void>(
  callback: T,
  delay: number,
  deps: React.DependencyList = []
): T {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(callback);

  // Update callback ref when callback changes
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return useCallback(
    ((...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        callbackRef.current(...args);
      }, delay);
    }) as T,
    [delay, ...deps]
  );
}

/**
 * Returns a debounced callback with cancel and flush capabilities.
 * 
 * @param callback - The callback to debounce
 * @param delay - The debounce delay in milliseconds
 * @returns Object with debounced callback, cancel, and flush functions
 */
export function useDebouncedCallbackWithControl<T extends (...args: unknown[]) => void>(
  callback: T,
  delay: number
): {
  debouncedCallback: (...args: Parameters<T>) => void;
  cancel: () => void;
  flush: () => void;
  isPending: () => boolean;
} {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(callback);
  const argsRef = useRef<unknown[] | null>(null);

  // Update callback ref when callback changes
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
      argsRef.current = null;
    }
  }, []);

  const flush = useCallback(() => {
    if (timeoutRef.current && argsRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
      const args = argsRef.current;
      argsRef.current = null;
      (callbackRef.current as (...args: unknown[]) => void)(...args);
    }
  }, []);

  const isPending = useCallback(() => {
    return timeoutRef.current !== null;
  }, []);

  const debouncedCallback = useCallback(
    (...args: Parameters<T>) => {
      argsRef.current = args;

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        timeoutRef.current = null;
        (callbackRef.current as (...args: unknown[]) => void)(...args);
        argsRef.current = null;
      }, delay);
    },
    [delay]
  );

  return {
    debouncedCallback,
    cancel,
    flush,
    isPending,
  };
}

export default useDebounce;
