import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { createElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useHelpContext, extractPageFromRoute } from '../useHelpContext';

// Router wrapper factory
function createWrapper(initialEntries: string[] = ['/dashboard']) {
  return ({ children }: { children: ReactNode }) =>
    createElement(MemoryRouter, { initialEntries }, children);
}

describe('extractPageFromRoute', () => {
  it('extracts first path segment', () => {
    expect(extractPageFromRoute('/dashboard')).toBe('dashboard');
  });

  it('extracts first segment from nested route', () => {
    expect(extractPageFromRoute('/tasks/123/edit')).toBe('tasks');
  });

  it('returns "general" for root path', () => {
    expect(extractPageFromRoute('/')).toBe('general');
  });

  it('returns "general" for empty string', () => {
    expect(extractPageFromRoute('')).toBe('general');
  });
});

describe('useHelpContext', () => {
  let helpKeyEl: HTMLDivElement | null = null;

  afterEach(() => {
    if (helpKeyEl) {
      document.body.removeChild(helpKeyEl);
      helpKeyEl = null;
    }
  });

  it('returns page from current route', () => {
    const { result } = renderHook(() => useHelpContext(), {
      wrapper: createWrapper(['/dashboard']),
    });

    expect(result.current.page).toBe('dashboard');
    expect(result.current.component).toBeUndefined();
    expect(result.current.element).toBeUndefined();
  });

  it('returns "general" for root route', () => {
    const { result } = renderHook(() => useHelpContext(), {
      wrapper: createWrapper(['/']),
    });

    expect(result.current.page).toBe('general');
  });

  it('extracts page from nested route', () => {
    const { result } = renderHook(() => useHelpContext(), {
      wrapper: createWrapper(['/tasks/42']),
    });

    expect(result.current.page).toBe('tasks');
  });

  it('parses data-help-key with component.element format', () => {
    helpKeyEl = document.createElement('div');
    helpKeyEl.setAttribute('data-help-key', 'taskTable.exportButton');
    document.body.appendChild(helpKeyEl);
    helpKeyEl.focus();
    // Make it focusable
    helpKeyEl.tabIndex = 0;
    helpKeyEl.focus();

    const { result } = renderHook(() => useHelpContext(), {
      wrapper: createWrapper(['/tasks']),
    });

    expect(result.current.page).toBe('tasks');
    expect(result.current.component).toBe('taskTable');
    expect(result.current.element).toBe('exportButton');
  });

  it('parses data-help-key with single element format', () => {
    helpKeyEl = document.createElement('div');
    helpKeyEl.setAttribute('data-help-key', 'searchBar');
    helpKeyEl.tabIndex = 0;
    document.body.appendChild(helpKeyEl);
    helpKeyEl.focus();

    const { result } = renderHook(() => useHelpContext(), {
      wrapper: createWrapper(['/dashboard']),
    });

    expect(result.current.page).toBe('dashboard');
    expect(result.current.component).toBeUndefined();
    expect(result.current.element).toBe('searchBar');
  });

  it('falls back to page-only context when no data-help-key', () => {
    // No focused element with data-help-key
    const { result } = renderHook(() => useHelpContext(), {
      wrapper: createWrapper(['/settings']),
    });

    expect(result.current.page).toBe('settings');
    expect(result.current.component).toBeUndefined();
    expect(result.current.element).toBeUndefined();
  });

  it('walks up DOM via closest() to find data-help-key', () => {
    helpKeyEl = document.createElement('div');
    helpKeyEl.setAttribute('data-help-key', 'form.nameInput');
    const child = document.createElement('input');
    child.type = 'text';
    helpKeyEl.appendChild(child);
    document.body.appendChild(helpKeyEl);
    child.focus();

    const { result } = renderHook(() => useHelpContext(), {
      wrapper: createWrapper(['/tasks']),
    });

    expect(result.current.component).toBe('form');
    expect(result.current.element).toBe('nameInput');
  });
});
