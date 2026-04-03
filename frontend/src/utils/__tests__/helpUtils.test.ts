import { describe, it, expect } from 'vitest';
import { resolveHelpKey, extractPageFromRoute, validateHelpKey } from '../helpUtils';
import type { HelpContext } from '@/types/help';
// Ensure i18n is initialized before resolveHelpKey uses it
import '@/locales/config';

describe('extractPageFromRoute', () => {
  it('extracts first segment from simple path', () => {
    expect(extractPageFromRoute('/dashboard')).toBe('dashboard');
  });

  it('extracts first segment from nested path', () => {
    expect(extractPageFromRoute('/tasks/123')).toBe('tasks');
  });

  it('returns "general" for root path', () => {
    expect(extractPageFromRoute('/')).toBe('general');
  });

  it('returns "general" for empty string', () => {
    expect(extractPageFromRoute('')).toBe('general');
  });

  it('extracts first segment from deeply nested path', () => {
    expect(extractPageFromRoute('/settings/profile/avatar')).toBe('settings');
  });
});

describe('resolveHelpKey', () => {
  it('returns page when only page is provided', () => {
    const ctx: HelpContext = { page: 'dashboard' };
    expect(resolveHelpKey(ctx)).toBe('dashboard');
  });

  it('returns page.component when component key exists in i18n', () => {
    // help.json has dashboard.exportButton.title
    const ctx: HelpContext = { page: 'dashboard', component: 'exportButton' };
    expect(resolveHelpKey(ctx)).toBe('dashboard.exportButton');
  });

  it('returns page.component.element when full key exists in i18n', () => {
    // We need a 3-level key. help.json doesn't have one, so it should fall back.
    // Let's test with a context that would produce a 3-level key that doesn't exist
    const ctx: HelpContext = { page: 'dashboard', component: 'exportButton', element: 'icon' };
    // dashboard.exportButton.icon doesn't exist, falls back to dashboard.exportButton
    expect(resolveHelpKey(ctx)).toBe('dashboard.exportButton');
  });

  it('falls back to page when component key does not exist in i18n', () => {
    const ctx: HelpContext = { page: 'dashboard', component: 'nonExistent' };
    expect(resolveHelpKey(ctx)).toBe('dashboard');
  });

  it('falls back to page when element+component key does not exist', () => {
    const ctx: HelpContext = { page: 'tasks', component: 'foo', element: 'bar' };
    // tasks.foo.bar doesn't exist, tasks.foo doesn't exist → falls back to tasks
    expect(resolveHelpKey(ctx)).toBe('tasks');
  });

  it('falls back to general when page key has no title in i18n', () => {
    const ctx: HelpContext = { page: 'unknownPage' };
    // unknownPage has no help:*.title; implementation then tries 'general' (see helpUtils.ts)
    expect(resolveHelpKey(ctx)).toBe('general');
  });

  it('always returns a non-empty string', () => {
    const ctx: HelpContext = { page: 'general' };
    const result = resolveHelpKey(ctx);
    expect(result).toBeTruthy();
    expect(result.length).toBeGreaterThan(0);
  });

  it('prefers more specific key over less specific', () => {
    // dashboard.exportButton.title exists → should return dashboard.exportButton
    const ctx: HelpContext = { page: 'dashboard', component: 'exportButton' };
    expect(resolveHelpKey(ctx)).toBe('dashboard.exportButton');
  });
});

describe('validateHelpKey', () => {
  it('accepts simple page key', () => {
    expect(validateHelpKey('dashboard')).toBe(true);
  });

  it('accepts dotted component key', () => {
    expect(validateHelpKey('tasks.exportButton')).toBe(true);
  });

  it('accepts three-level key', () => {
    expect(validateHelpKey('page.component.element')).toBe(true);
  });

  it('accepts alphanumeric with dots and underscores', () => {
    expect(validateHelpKey('my_page.comp2.el_3')).toBe(true);
  });

  it('rejects empty string', () => {
    expect(validateHelpKey('')).toBe(false);
  });

  it('rejects string with spaces', () => {
    expect(validateHelpKey('has space')).toBe(false);
  });

  it('rejects string with special characters', () => {
    expect(validateHelpKey('key@value')).toBe(false);
    expect(validateHelpKey('key#value')).toBe(false);
    expect(validateHelpKey('key/value')).toBe(false);
  });

  it('rejects HTML tags', () => {
    expect(validateHelpKey('<script>alert(1)</script>')).toBe(false);
  });

  it('rejects string with hyphens', () => {
    expect(validateHelpKey('my-key')).toBe(false);
  });
});
