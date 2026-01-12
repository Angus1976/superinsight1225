/**
 * useStableCallback Hook
 * 
 * A hook that returns a stable callback reference that always calls
 * the latest version of the provided callback. This is useful for
 * avoiding stale closures in event handlers and effects.
 * 
 * @module hooks/useStableCallback
 * @version 1.0.0
 */

import { useCallback, useRef, useEffect } from 'react';

/**
 * Returns a stable callback that always calls the latest version of the provided function.
 * 
 * This hook is useful when you need to pass a callback to a child component or
 * use it in a useEffect dependency array, but you don't want the callback
 * reference to change on every render.
 * 
 * @param callback - The callback function to stabilize
 * @returns A stable callback reference
 * 
 * @example
 * ```typescript
 * const MyComponent = ({ onSave }) => {
 *   const [value, setValue] = useState('');
 *   
 *   // This callback reference never changes, but always calls the latest onSave
 *   const handleSave = useStableCallback(() => {
 *     onSave(value);
 *   });
 *   
 *   return (
 *     <ChildComponent onSave={handleSave} />
 *   );
 * };
 * ```
 */
export function useStableCallback<T extends (...args: Parameters<T>) => ReturnType<T>>(
  callback: T
): T {
  const callbackRef = useRef<T>(callback);

  // Update the ref on every render
  useEffect(() => {
    callbackRef.current = callback;
  });

  // Return a stable callback that calls the latest version
  return useCallback(
    ((...args: Parameters<T>) => {
      return callbackRef.current(...args);
    }) as T,
    []
  );
}

/**
 * Returns a stable callback that is only created once and never changes.
 * The callback will always have access to the latest values through refs.
 * 
 * @param callback - The callback function
 * @returns A stable callback reference
 * 
 * @example
 * ```typescript
 * const MyComponent = () => {
 *   const [count, setCount] = useState(0);
 *   
 *   // This callback is created once and never changes
 *   const handleClick = useEventCallback(() => {
 *     console.log('Current count:', count);
 *   });
 *   
 *   return <button onClick={handleClick}>Log Count</button>;
 * };
 * ```
 */
export function useEventCallback<T extends (...args: Parameters<T>) => ReturnType<T>>(
  callback: T
): T {
  const callbackRef = useRef<T>(callback);

  // Update the ref synchronously
  callbackRef.current = callback;

  // Return a stable callback
  return useCallback(
    ((...args: Parameters<T>) => {
      return callbackRef.current(...args);
    }) as T,
    []
  );
}

export default useStableCallback;
