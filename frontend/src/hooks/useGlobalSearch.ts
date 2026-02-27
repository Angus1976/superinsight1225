/**
 * useGlobalSearch Hook
 *
 * Manages global search modal state and registers ⌘K / Ctrl+K keyboard shortcut.
 * - open(): sets isOpen = true
 * - close(): resets isOpen = false AND query = ''
 * - setQuery(q): updates query
 * - Keyboard shortcut auto-registered on mount, cleaned up on unmount
 */

import { useState, useCallback, useEffect } from 'react';

export interface UseGlobalSearchReturn {
  isOpen: boolean;
  query: string;
  open: () => void;
  close: () => void;
  setQuery: (q: string) => void;
}

export function useGlobalSearch(): UseGlobalSearchReturn {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');

  const open = useCallback(() => setIsOpen(true), []);

  const close = useCallback(() => {
    setIsOpen(false);
    setQuery('');
  }, []);

  // Register ⌘K / Ctrl+K keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  return { isOpen, query, open, close, setQuery };
}
