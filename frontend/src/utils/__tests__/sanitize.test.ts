import { describe, it, expect } from 'vitest';
import { sanitizeSearchQuery } from '../sanitize';

describe('sanitizeSearchQuery', () => {
  it('returns empty string for falsy input', () => {
    expect(sanitizeSearchQuery('')).toBe('');
    expect(sanitizeSearchQuery(null as unknown as string)).toBe('');
    expect(sanitizeSearchQuery(undefined as unknown as string)).toBe('');
  });

  it('trims whitespace', () => {
    expect(sanitizeSearchQuery('  hello  ')).toBe('hello');
  });

  it('collapses multiple spaces', () => {
    expect(sanitizeSearchQuery('hello   world')).toBe('hello world');
  });

  it('strips HTML tags', () => {
    expect(sanitizeSearchQuery('<b>bold</b>')).toBe('bold');
    expect(sanitizeSearchQuery('<script>alert(1)</script>')).toBe('alert(1)');
    expect(sanitizeSearchQuery('a<img src=x>b')).toBe('ab');
  });

  it('removes javascript: patterns', () => {
    expect(sanitizeSearchQuery('javascript:alert(1)')).toBe('alert(1)');
  });

  it('removes onerror= and similar event handlers', () => {
    expect(sanitizeSearchQuery('onerror=alert(1)')).toBe('alert(1)');
    expect(sanitizeSearchQuery('onload=fetch()')).toBe('fetch()');
  });

  it('removes eval() patterns', () => {
    expect(sanitizeSearchQuery('eval("code")')).toBe('"code")');
  });

  it('preserves normal search text', () => {
    expect(sanitizeSearchQuery('data annotation tasks')).toBe('data annotation tasks');
    expect(sanitizeSearchQuery('用户管理')).toBe('用户管理');
  });
});
