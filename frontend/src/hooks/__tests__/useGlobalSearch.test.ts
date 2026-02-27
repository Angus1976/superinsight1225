import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGlobalSearch } from '../useGlobalSearch';

describe('useGlobalSearch', () => {
  it('initializes with isOpen=false and empty query', () => {
    const { result } = renderHook(() => useGlobalSearch());
    expect(result.current.isOpen).toBe(false);
    expect(result.current.query).toBe('');
  });

  it('open() sets isOpen to true', () => {
    const { result } = renderHook(() => useGlobalSearch());
    act(() => result.current.open());
    expect(result.current.isOpen).toBe(true);
  });

  it('close() resets isOpen to false and query to empty', () => {
    const { result } = renderHook(() => useGlobalSearch());

    act(() => {
      result.current.open();
      result.current.setQuery('test query');
    });
    expect(result.current.isOpen).toBe(true);
    expect(result.current.query).toBe('test query');

    act(() => result.current.close());
    expect(result.current.isOpen).toBe(false);
    expect(result.current.query).toBe('');
  });

  it('setQuery updates the query string', () => {
    const { result } = renderHook(() => useGlobalSearch());
    act(() => result.current.setQuery('hello'));
    expect(result.current.query).toBe('hello');
  });

  it('registers ⌘K / Ctrl+K shortcut on mount', () => {
    const addSpy = vi.spyOn(document, 'addEventListener');
    const { unmount } = renderHook(() => useGlobalSearch());

    const keydownCalls = addSpy.mock.calls.filter(
      ([event]) => event === 'keydown',
    );
    expect(keydownCalls.length).toBeGreaterThanOrEqual(1);

    unmount();
    addSpy.mockRestore();
  });

  it('cleans up keyboard listener on unmount', () => {
    const removeSpy = vi.spyOn(document, 'removeEventListener');
    const { unmount } = renderHook(() => useGlobalSearch());

    unmount();

    const keydownCalls = removeSpy.mock.calls.filter(
      ([event]) => event === 'keydown',
    );
    expect(keydownCalls.length).toBeGreaterThanOrEqual(1);
    removeSpy.mockRestore();
  });

  it('Ctrl+K opens the search modal', () => {
    const { result } = renderHook(() => useGlobalSearch());

    act(() => {
      const event = new KeyboardEvent('keydown', {
        key: 'k',
        ctrlKey: true,
        bubbles: true,
      });
      document.dispatchEvent(event);
    });

    expect(result.current.isOpen).toBe(true);
  });

  it('Meta+K (⌘K) opens the search modal', () => {
    const { result } = renderHook(() => useGlobalSearch());

    act(() => {
      const event = new KeyboardEvent('keydown', {
        key: 'k',
        metaKey: true,
        bubbles: true,
      });
      document.dispatchEvent(event);
    });

    expect(result.current.isOpen).toBe(true);
  });

  it('does not open on plain K press', () => {
    const { result } = renderHook(() => useGlobalSearch());

    act(() => {
      const event = new KeyboardEvent('keydown', {
        key: 'k',
        bubbles: true,
      });
      document.dispatchEvent(event);
    });

    expect(result.current.isOpen).toBe(false);
  });
});
