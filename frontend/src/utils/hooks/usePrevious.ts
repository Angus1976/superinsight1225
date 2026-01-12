/**
 * usePrevious Hook
 * 
 * A hook that returns the previous value of a variable.
 * Useful for comparing current and previous values in effects.
 * 
 * @module hooks/usePrevious
 * @version 1.0.0
 */

import { useRef, useEffect } from 'react';

/**
 * Returns the previous value of a variable.
 * 
 * @param value - The current value
 * @returns The previous value (undefined on first render)
 * 
 * @example
 * ```typescript
 * const MyComponent = ({ count }) => {
 *   const prevCount = usePrevious(count);
 *   
 *   useEffect(() => {
 *     if (prevCount !== undefined && count > prevCount) {
 *       console.log('Count increased!');
 *     }
 *   }, [count, prevCount]);
 *   
 *   return <div>Count: {count}, Previous: {prevCount}</div>;
 * };
 * ```
 */
export function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined);

  useEffect(() => {
    ref.current = value;
  }, [value]);

  return ref.current;
}

/**
 * Returns the previous value with an initial value.
 * 
 * @param value - The current value
 * @param initialValue - The initial previous value
 * @returns The previous value
 */
export function usePreviousWithInitial<T>(value: T, initialValue: T): T {
  const ref = useRef<T>(initialValue);

  useEffect(() => {
    ref.current = value;
  }, [value]);

  return ref.current;
}

/**
 * Returns whether the value has changed from the previous render.
 * 
 * @param value - The current value
 * @param compareFn - Optional comparison function
 * @returns True if the value has changed
 */
export function useHasChanged<T>(
  value: T,
  compareFn: (prev: T | undefined, curr: T) => boolean = (prev, curr) => prev !== curr
): boolean {
  const prevValue = usePrevious(value);
  return compareFn(prevValue, value);
}

export default usePrevious;
