/**
 * Core auth + formatting helpers used across the app (high value / low flake).
 * Note: `src/test/setup.ts` replaces localStorage/sessionStorage with noop mocks;
 * we install in-memory stores so storage/token behave realistically.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { storage, sessionStorage as sess } from '../storage';
import {
  getToken,
  setToken,
  removeToken,
  getRefreshToken,
  setRefreshToken,
  removeRefreshToken,
  decodeToken,
  isTokenExpired,
  clearAuthTokens,
} from '../token';
import {
  formatDate,
  formatDateTime,
  formatRelativeTime,
  formatNumber,
  formatCurrency,
  formatPercent,
  formatDuration,
  formatFileSize,
} from '../format';
import { STORAGE_KEYS } from '@/constants';

function installMemoryLocalStorage() {
  const data: Record<string, string> = {};
  const mock = {
    getItem: vi.fn((k: string) => (Object.prototype.hasOwnProperty.call(data, k) ? data[k] : null)),
    setItem: vi.fn((k: string, v: string) => {
      data[k] = v;
    }),
    removeItem: vi.fn((k: string) => {
      delete data[k];
    }),
    clear: vi.fn(() => {
      Object.keys(data).forEach((k) => delete data[k]);
    }),
    length: 0,
    key: vi.fn(),
  };
  Object.defineProperty(window, 'localStorage', { value: mock, configurable: true });
  return mock;
}

function installMemorySessionStorage() {
  const data: Record<string, string> = {};
  const mock = {
    getItem: vi.fn((k: string) => (Object.prototype.hasOwnProperty.call(data, k) ? data[k] : null)),
    setItem: vi.fn((k: string, v: string) => {
      data[k] = v;
    }),
    removeItem: vi.fn((k: string) => {
      delete data[k];
    }),
    clear: vi.fn(() => {
      Object.keys(data).forEach((k) => delete data[k]);
    }),
    length: 0,
    key: vi.fn(),
  };
  Object.defineProperty(window, 'sessionStorage', { value: mock, configurable: true });
  return mock;
}

describe('storage', () => {
  beforeEach(() => {
    installMemoryLocalStorage();
    installMemorySessionStorage();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('get/set/remove/clear localStorage', () => {
    expect(storage.get('k')).toBeNull();
    storage.set('k', { a: 1 });
    expect(storage.get<{ a: number }>('k')).toEqual({ a: 1 });
    storage.remove('k');
    expect(storage.get('k')).toBeNull();
    storage.set('x', 1);
    storage.clear();
    expect(storage.get('x')).toBeNull();
  });

  it('returns null on invalid JSON', () => {
    localStorage.setItem('bad', 'not-json');
    expect(storage.get('bad')).toBeNull();
  });

  it('sessionStorage get/set/remove/clear', () => {
    expect(sess.get('s')).toBeNull();
    sess.set('s', [1, 2]);
    expect(sess.get<number[]>('s')).toEqual([1, 2]);
    sess.remove('s');
    sess.set('t', 1);
    sess.clear();
    expect(sess.get('t')).toBeNull();
  });
});

describe('token', () => {
  beforeEach(() => {
    installMemoryLocalStorage();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('get/set/remove token and refresh', () => {
    expect(getToken()).toBeNull();
    setToken('abc');
    expect(getToken()).toBe('abc');
    removeToken();
    expect(getToken()).toBeNull();

    setRefreshToken('r');
    expect(getRefreshToken()).toBe('r');
    removeRefreshToken();
    expect(getRefreshToken()).toBeNull();
  });

  it('decodeToken parses valid JWT payload', () => {
    const payload = { sub: 'u1', exp: 2_000_000_000, tenant_id: 't1' };
    const b64 = btoa(JSON.stringify(payload)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    const token = `h.${b64}.s`;
    expect(decodeToken(token)).toMatchObject({ sub: 'u1', tenant_id: 't1' });
  });

  it('decodeToken returns null on garbage', () => {
    expect(decodeToken('not-a-jwt')).toBeNull();
  });

  it('isTokenExpired respects exp and buffer', () => {
    const past = Math.floor(Date.now() / 1000) - 3600;
    const b64 = btoa(JSON.stringify({ sub: 'u', exp: past, tenant_id: 't' }))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');
    expect(isTokenExpired(`h.${b64}.s`)).toBe(true);
    expect(isTokenExpired('bad')).toBe(true);
  });

  it('clearAuthTokens clears user/tenant keys', () => {
    setToken('t');
    localStorage.setItem(STORAGE_KEYS.USER, '"x"');
    localStorage.setItem(STORAGE_KEYS.TENANT, '"y"');
    clearAuthTokens();
    expect(getToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(storage.get(STORAGE_KEYS.USER)).toBeNull();
    expect(storage.get(STORAGE_KEYS.TENANT)).toBeNull();
  });
});

describe('format', () => {
  it('formatDate / formatDateTime', () => {
    const d = new Date('2024-06-01T12:34:56Z');
    expect(formatDate(d)).toMatch(/2024-06-01/);
    expect(formatDateTime(d)).toMatch(/2024-06-01/);
  });

  it('formatRelativeTime', () => {
    expect(formatRelativeTime(new Date())).toBeTruthy();
  });

  it('formatNumber and formatCurrency', () => {
    expect(formatNumber(1234.5, 1)).toContain('1');
    expect(formatCurrency(99)).toContain('99');
  });

  it('formatPercent', () => {
    expect(formatPercent(0.125, 2)).toBe('12.50%');
  });

  it('formatDuration branches', () => {
    expect(formatDuration(30)).toContain('s');
    expect(formatDuration(90)).toContain('m');
    expect(formatDuration(4000)).toMatch(/h|m/);
  });

  it('formatFileSize', () => {
    expect(formatFileSize(0)).toBe('0 B');
    expect(formatFileSize(1536)).toMatch(/KB/);
  });
});
