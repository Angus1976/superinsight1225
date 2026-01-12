/**
 * useToggle Hook
 * 
 * A hook for managing boolean toggle state with
 * convenient toggle, set, and reset functions.
 * 
 * @module hooks/useToggle
 * @version 1.0.0
 */

import { useState, useCallback, useMemo } from 'react';

/**
 * Toggle state and actions
 */
export interface UseToggleReturn {
  /** Current value */
  value: boolean;
  /** Toggle the value */
  toggle: () => void;
  /** Set to true */
  setTrue: () => void;
  /** Set to false */
  setFalse: () => void;
  /** Set to specific value */
  setValue: (value: boolean) => void;
}

/**
 * Hook for managing boolean toggle state
 * 
 * @param initialValue - Initial boolean value
 * @returns Toggle state and actions
 * 
 * @example
 * ```typescript
 * const { value: isOpen, toggle, setTrue: open, setFalse: close } = useToggle(false);
 * 
 * return (
 *   <div>
 *     <button onClick={toggle}>Toggle</button>
 *     <button onClick={open}>Open</button>
 *     <button onClick={close}>Close</button>
 *     {isOpen && <Modal />}
 *   </div>
 * );
 * ```
 */
export function useToggle(initialValue = false): UseToggleReturn {
  const [value, setValue] = useState(initialValue);

  const toggle = useCallback(() => {
    setValue(prev => !prev);
  }, []);

  const setTrue = useCallback(() => {
    setValue(true);
  }, []);

  const setFalse = useCallback(() => {
    setValue(false);
  }, []);

  return useMemo(
    () => ({
      value,
      toggle,
      setTrue,
      setFalse,
      setValue,
    }),
    [value, toggle, setTrue, setFalse]
  );
}

/**
 * Hook for managing multiple toggle states
 * 
 * @param keys - Array of toggle keys
 * @param initialValues - Initial values for each key
 * @returns Object with toggle states and actions
 */
export function useToggles<K extends string>(
  keys: K[],
  initialValues?: Partial<Record<K, boolean>>
): {
  values: Record<K, boolean>;
  toggle: (key: K) => void;
  setTrue: (key: K) => void;
  setFalse: (key: K) => void;
  setValue: (key: K, value: boolean) => void;
  setAll: (value: boolean) => void;
  reset: () => void;
} {
  const getInitialState = useCallback(() => {
    const state: Record<string, boolean> = {};
    keys.forEach(key => {
      state[key] = initialValues?.[key] ?? false;
    });
    return state as Record<K, boolean>;
  }, [keys, initialValues]);

  const [values, setValues] = useState<Record<K, boolean>>(getInitialState);

  const toggle = useCallback((key: K) => {
    setValues(prev => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const setTrue = useCallback((key: K) => {
    setValues(prev => ({ ...prev, [key]: true }));
  }, []);

  const setFalse = useCallback((key: K) => {
    setValues(prev => ({ ...prev, [key]: false }));
  }, []);

  const setValue = useCallback((key: K, value: boolean) => {
    setValues(prev => ({ ...prev, [key]: value }));
  }, []);

  const setAll = useCallback((value: boolean) => {
    setValues(prev => {
      const newState = { ...prev };
      keys.forEach(key => {
        newState[key] = value;
      });
      return newState;
    });
  }, [keys]);

  const reset = useCallback(() => {
    setValues(getInitialState());
  }, [getInitialState]);

  return useMemo(
    () => ({
      values,
      toggle,
      setTrue,
      setFalse,
      setValue,
      setAll,
      reset,
    }),
    [values, toggle, setTrue, setFalse, setValue, setAll, reset]
  );
}

export default useToggle;
