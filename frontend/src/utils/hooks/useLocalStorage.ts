/**
 * useLocalStorage Hook
 * 
 * A hook for persisting state to localStorage with
 * automatic serialization and synchronization.
 * 
 * @module hooks/useLocalStorage
 * @version 1.0.0
 */

import { useState, useCallback, useEffect, useMemo } from 'react';

/**
 * Options for useLocalStorage
 */
export interface UseLocalStorageOptions<T> {
  /** Custom serializer */
  serializer?: (value: T) => string;
  /** Custom deserializer */
  deserializer?: (value: string) => T;
  /** Sync across tabs */
  syncTabs?: boolean;
  /** Error handler */
  onError?: (error: Error) => void;
}

/**
 * Hook for persisting state to localStorage
 * 
 * @param key - Storage key
 * @param initialValue - Initial value if not in storage
 * @param options - Configuration options
 * @returns [value, setValue, removeValue]
 * 
 * @example
 * ```typescript
 * const [theme, setTheme, removeTheme] = useLocalStorage('theme', 'light');
 * 
 * return (
 *   <select value={theme} onChange={e => setTheme(e.target.value)}>
 *     <option value="light">Light</option>
 *     <option value="dark">Dark</option>
 *   </select>
 * );
 * ```
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
  options: UseLocalStorageOptions<T> = {}
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
  const {
    serializer = JSON.stringify,
    deserializer = JSON.parse,
    syncTabs = true,
    onError,
  } = options;

  // Get initial value from storage or use default
  const getStoredValue = useCallback((): T => {
    try {
      const item = localStorage.getItem(key);
      if (item !== null) {
        return deserializer(item);
      }
    } catch (error) {
      onError?.(error instanceof Error ? error : new Error(String(error)));
    }
    return initialValue;
  }, [key, initialValue, deserializer, onError]);

  const [storedValue, setStoredValue] = useState<T>(getStoredValue);

  // Update localStorage when value changes
  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      try {
        const valueToStore = value instanceof Function ? value(storedValue) : value;
        setStoredValue(valueToStore);
        localStorage.setItem(key, serializer(valueToStore));
      } catch (error) {
        onError?.(error instanceof Error ? error : new Error(String(error)));
      }
    },
    [key, storedValue, serializer, onError]
  );

  // Remove from localStorage
  const removeValue = useCallback(() => {
    try {
      localStorage.removeItem(key);
      setStoredValue(initialValue);
    } catch (error) {
      onError?.(error instanceof Error ? error : new Error(String(error)));
    }
  }, [key, initialValue, onError]);

  // Sync across tabs
  useEffect(() => {
    if (!syncTabs) return;

    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === key && event.newValue !== null) {
        try {
          setStoredValue(deserializer(event.newValue));
        } catch (error) {
          onError?.(error instanceof Error ? error : new Error(String(error)));
        }
      } else if (event.key === key && event.newValue === null) {
        setStoredValue(initialValue);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [key, initialValue, deserializer, syncTabs, onError]);

  return [storedValue, setValue, removeValue];
}

/**
 * Hook for persisting state to sessionStorage
 */
export function useSessionStorage<T>(
  key: string,
  initialValue: T,
  options: Omit<UseLocalStorageOptions<T>, 'syncTabs'> = {}
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
  const {
    serializer = JSON.stringify,
    deserializer = JSON.parse,
    onError,
  } = options;

  const getStoredValue = useCallback((): T => {
    try {
      const item = sessionStorage.getItem(key);
      if (item !== null) {
        return deserializer(item);
      }
    } catch (error) {
      onError?.(error instanceof Error ? error : new Error(String(error)));
    }
    return initialValue;
  }, [key, initialValue, deserializer, onError]);

  const [storedValue, setStoredValue] = useState<T>(getStoredValue);

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      try {
        const valueToStore = value instanceof Function ? value(storedValue) : value;
        setStoredValue(valueToStore);
        sessionStorage.setItem(key, serializer(valueToStore));
      } catch (error) {
        onError?.(error instanceof Error ? error : new Error(String(error)));
      }
    },
    [key, storedValue, serializer, onError]
  );

  const removeValue = useCallback(() => {
    try {
      sessionStorage.removeItem(key);
      setStoredValue(initialValue);
    } catch (error) {
      onError?.(error instanceof Error ? error : new Error(String(error)));
    }
  }, [key, initialValue, onError]);

  return [storedValue, setValue, removeValue];
}

export default useLocalStorage;
