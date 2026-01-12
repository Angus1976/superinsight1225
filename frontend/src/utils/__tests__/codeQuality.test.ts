/**
 * Code Quality Utilities Tests
 * 
 * Tests for type guards, assertions, and utility functions.
 */

import { describe, it, expect, vi } from 'vitest';
import {
  isDefined,
  isNonEmptyString,
  isValidNumber,
  isNonEmptyArray,
  isPlainObject,
  isFunction,
  isValidDate,
  assert,
  assertDefined,
  assertNever,
  validationSuccess,
  validationFailure,
  isValidEmail,
  isValidUrl,
  hasMinLength,
  hasMaxLength,
  isInRange,
  safeJsonParse,
  safeJsonStringify,
  safeGet,
  debounce,
  throttle,
  omit,
  pick,
  deepMerge,
  deepEqual,
} from '../codeQuality';

describe('Type Guards', () => {
  describe('isDefined', () => {
    it('returns true for defined values', () => {
      expect(isDefined('hello')).toBe(true);
      expect(isDefined(0)).toBe(true);
      expect(isDefined(false)).toBe(true);
      expect(isDefined({})).toBe(true);
      expect(isDefined([])).toBe(true);
    });

    it('returns false for null and undefined', () => {
      expect(isDefined(null)).toBe(false);
      expect(isDefined(undefined)).toBe(false);
    });
  });

  describe('isNonEmptyString', () => {
    it('returns true for non-empty strings', () => {
      expect(isNonEmptyString('hello')).toBe(true);
      expect(isNonEmptyString('  hello  ')).toBe(true);
    });

    it('returns false for empty or whitespace strings', () => {
      expect(isNonEmptyString('')).toBe(false);
      expect(isNonEmptyString('   ')).toBe(false);
    });

    it('returns false for non-strings', () => {
      expect(isNonEmptyString(123)).toBe(false);
      expect(isNonEmptyString(null)).toBe(false);
      expect(isNonEmptyString(undefined)).toBe(false);
    });
  });

  describe('isValidNumber', () => {
    it('returns true for valid numbers', () => {
      expect(isValidNumber(0)).toBe(true);
      expect(isValidNumber(42)).toBe(true);
      expect(isValidNumber(-3.14)).toBe(true);
    });

    it('returns false for NaN and Infinity', () => {
      expect(isValidNumber(NaN)).toBe(false);
      expect(isValidNumber(Infinity)).toBe(false);
      expect(isValidNumber(-Infinity)).toBe(false);
    });

    it('returns false for non-numbers', () => {
      expect(isValidNumber('42')).toBe(false);
      expect(isValidNumber(null)).toBe(false);
    });
  });

  describe('isNonEmptyArray', () => {
    it('returns true for non-empty arrays', () => {
      expect(isNonEmptyArray([1, 2, 3])).toBe(true);
      expect(isNonEmptyArray(['a'])).toBe(true);
    });

    it('returns false for empty arrays', () => {
      expect(isNonEmptyArray([])).toBe(false);
    });

    it('returns false for non-arrays', () => {
      expect(isNonEmptyArray('array')).toBe(false);
      expect(isNonEmptyArray({ length: 1 })).toBe(false);
    });
  });

  describe('isPlainObject', () => {
    it('returns true for plain objects', () => {
      expect(isPlainObject({})).toBe(true);
      expect(isPlainObject({ a: 1 })).toBe(true);
    });

    it('returns false for arrays and null', () => {
      expect(isPlainObject([])).toBe(false);
      expect(isPlainObject(null)).toBe(false);
    });
  });

  describe('isFunction', () => {
    it('returns true for functions', () => {
      expect(isFunction(() => {})).toBe(true);
      expect(isFunction(function() {})).toBe(true);
    });

    it('returns false for non-functions', () => {
      expect(isFunction('function')).toBe(false);
      expect(isFunction({})).toBe(false);
    });
  });

  describe('isValidDate', () => {
    it('returns true for valid dates', () => {
      expect(isValidDate(new Date())).toBe(true);
      expect(isValidDate(new Date('2024-01-01'))).toBe(true);
    });

    it('returns false for invalid dates', () => {
      expect(isValidDate(new Date('invalid'))).toBe(false);
    });

    it('returns false for non-dates', () => {
      expect(isValidDate('2024-01-01')).toBe(false);
      expect(isValidDate(Date.now())).toBe(false);
    });
  });
});

describe('Assertions', () => {
  describe('assert', () => {
    it('does not throw for true conditions', () => {
      expect(() => assert(true, 'Should not throw')).not.toThrow();
    });

    it('throws for false conditions', () => {
      expect(() => assert(false, 'Test error')).toThrow('Assertion failed: Test error');
    });
  });

  describe('assertDefined', () => {
    it('does not throw for defined values', () => {
      expect(() => assertDefined('value')).not.toThrow();
      expect(() => assertDefined(0)).not.toThrow();
    });

    it('throws for null and undefined', () => {
      expect(() => assertDefined(null, 'Value is null')).toThrow('Assertion failed: Value is null');
      expect(() => assertDefined(undefined)).toThrow();
    });
  });

  describe('assertNever', () => {
    it('always throws', () => {
      expect(() => assertNever('value' as never)).toThrow();
    });
  });
});

describe('Validation Helpers', () => {
  describe('validationSuccess', () => {
    it('creates a success result', () => {
      const result = validationSuccess({ name: 'test' });
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual({ name: 'test' });
      }
    });
  });

  describe('validationFailure', () => {
    it('creates a failure result', () => {
      const result = validationFailure(['Error 1', 'Error 2']);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors).toEqual(['Error 1', 'Error 2']);
      }
    });
  });

  describe('isValidEmail', () => {
    it('validates correct email formats', () => {
      expect(isValidEmail('test@example.com')).toBe(true);
      expect(isValidEmail('user.name@domain.co.uk')).toBe(true);
    });

    it('rejects invalid email formats', () => {
      expect(isValidEmail('invalid')).toBe(false);
      expect(isValidEmail('test@')).toBe(false);
      expect(isValidEmail('@example.com')).toBe(false);
    });
  });

  describe('isValidUrl', () => {
    it('validates correct URLs', () => {
      expect(isValidUrl('https://example.com')).toBe(true);
      expect(isValidUrl('http://localhost:3000')).toBe(true);
    });

    it('rejects invalid URLs', () => {
      expect(isValidUrl('not-a-url')).toBe(false);
      expect(isValidUrl('')).toBe(false);
    });
  });

  describe('hasMinLength', () => {
    it('checks minimum length', () => {
      expect(hasMinLength('hello', 3)).toBe(true);
      expect(hasMinLength('hi', 3)).toBe(false);
    });
  });

  describe('hasMaxLength', () => {
    it('checks maximum length', () => {
      expect(hasMaxLength('hi', 5)).toBe(true);
      expect(hasMaxLength('hello world', 5)).toBe(false);
    });
  });

  describe('isInRange', () => {
    it('checks if number is in range', () => {
      expect(isInRange(5, 1, 10)).toBe(true);
      expect(isInRange(1, 1, 10)).toBe(true);
      expect(isInRange(10, 1, 10)).toBe(true);
      expect(isInRange(0, 1, 10)).toBe(false);
      expect(isInRange(11, 1, 10)).toBe(false);
    });
  });
});

describe('Safe Operations', () => {
  describe('safeJsonParse', () => {
    it('parses valid JSON', () => {
      expect(safeJsonParse('{"a":1}')).toEqual({ a: 1 });
      expect(safeJsonParse('[1,2,3]')).toEqual([1, 2, 3]);
    });

    it('returns null for invalid JSON', () => {
      expect(safeJsonParse('invalid')).toBeNull();
      expect(safeJsonParse('')).toBeNull();
    });
  });

  describe('safeJsonStringify', () => {
    it('stringifies objects', () => {
      expect(safeJsonStringify({ a: 1 })).toBe('{"a":1}');
    });

    it('handles circular references', () => {
      const obj: Record<string, unknown> = { a: 1 };
      obj.self = obj;
      expect(safeJsonStringify(obj)).toBeNull();
    });
  });

  describe('safeGet', () => {
    it('gets nested properties', () => {
      const obj = { user: { profile: { name: 'John' } } };
      expect(safeGet(obj, 'user.profile.name')).toBe('John');
    });

    it('returns undefined for missing paths', () => {
      const obj = { user: { profile: {} } };
      expect(safeGet(obj, 'user.profile.name')).toBeUndefined();
      expect(safeGet(obj, 'user.settings.theme')).toBeUndefined();
    });
  });
});

describe('Debounce and Throttle', () => {
  describe('debounce', () => {
    it('debounces function calls', async () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn();
      debouncedFn();
      debouncedFn();

      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(100);

      expect(fn).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });
  });

  describe('throttle', () => {
    it('throttles function calls', () => {
      vi.useFakeTimers();
      const fn = vi.fn();
      const throttledFn = throttle(fn, 100);

      throttledFn();
      throttledFn();
      throttledFn();

      expect(fn).toHaveBeenCalledTimes(1);

      vi.advanceTimersByTime(100);
      throttledFn();

      expect(fn).toHaveBeenCalledTimes(2);
      vi.useRealTimers();
    });
  });
});

describe('Object Utilities', () => {
  describe('omit', () => {
    it('omits specified keys', () => {
      const obj = { a: 1, b: 2, c: 3 };
      expect(omit(obj, ['b'])).toEqual({ a: 1, c: 3 });
    });
  });

  describe('pick', () => {
    it('picks specified keys', () => {
      const obj = { a: 1, b: 2, c: 3 };
      expect(pick(obj, ['a', 'c'])).toEqual({ a: 1, c: 3 });
    });
  });

  describe('deepMerge', () => {
    it('deeply merges objects', () => {
      const target = { a: 1, b: { c: 2 } };
      const source = { b: { d: 3 }, e: 4 };
      expect(deepMerge(target, source)).toEqual({
        a: 1,
        b: { c: 2, d: 3 },
        e: 4,
      });
    });
  });

  describe('deepEqual', () => {
    it('compares primitive values', () => {
      expect(deepEqual(1, 1)).toBe(true);
      expect(deepEqual('a', 'a')).toBe(true);
      expect(deepEqual(1, 2)).toBe(false);
    });

    it('compares arrays', () => {
      expect(deepEqual([1, 2], [1, 2])).toBe(true);
      expect(deepEqual([1, 2], [1, 3])).toBe(false);
    });

    it('compares objects', () => {
      expect(deepEqual({ a: 1 }, { a: 1 })).toBe(true);
      expect(deepEqual({ a: 1 }, { a: 2 })).toBe(false);
    });

    it('compares nested structures', () => {
      expect(deepEqual(
        { a: { b: [1, 2] } },
        { a: { b: [1, 2] } }
      )).toBe(true);
    });
  });
});
