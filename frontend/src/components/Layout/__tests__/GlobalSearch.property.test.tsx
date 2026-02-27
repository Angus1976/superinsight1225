/**
 * Property Tests for GlobalSearch
 *
 * **Validates: Requirements 4.2, 7.3**
 *
 * Property 6: GlobalSearch close resets query state
 * Property 9: Global search query sanitization
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { renderHook, act } from '@testing-library/react';
import { useGlobalSearch } from '@/hooks/useGlobalSearch';
import { sanitizeSearchQuery } from '@/utils/sanitize';

// ---------------------------------------------------------------------------
// Property 6: GlobalSearch close resets query state
// ---------------------------------------------------------------------------

describe('Property 6: GlobalSearch close resets query state', () => {
  /**
   * **Validates: Requirement 4.2**
   *
   * For any non-empty query string, calling close() SHALL result in
   * isOpen=false and query=''.
   */
  it('close() resets isOpen to false and query to empty for any query', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 100 }),
        (queryStr) => {
          const { result, unmount } = renderHook(() => useGlobalSearch());

          // Open and set a query
          act(() => {
            result.current.open();
          });
          act(() => {
            result.current.setQuery(queryStr);
          });

          // Verify state is set
          expect(result.current.isOpen).toBe(true);
          expect(result.current.query).toBe(queryStr);

          // Close
          act(() => {
            result.current.close();
          });

          // Verify reset
          expect(result.current.isOpen).toBe(false);
          expect(result.current.query).toBe('');

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirement 4.2**
   *
   * Closing from an already-closed state still maintains isOpen=false and query=''.
   */
  it('close() is idempotent — calling close on already-closed state keeps reset', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        (queryStr) => {
          const { result, unmount } = renderHook(() => useGlobalSearch());

          // Open, set query, close, then close again
          act(() => { result.current.open(); });
          act(() => { result.current.setQuery(queryStr); });
          act(() => { result.current.close(); });
          act(() => { result.current.close(); });

          expect(result.current.isOpen).toBe(false);
          expect(result.current.query).toBe('');

          unmount();
        },
      ),
      { numRuns: 50 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 9: Global search query sanitization
// ---------------------------------------------------------------------------

describe('Property 9: Global search query sanitization', () => {
  /**
   * **Validates: Requirement 7.3**
   *
   * For any input string containing HTML tags, the sanitizer SHALL produce
   * an output with no HTML tags remaining.
   */
  it('strips all HTML tags from any input', () => {
    const htmlTagArb = fc
      .record({
        tag: fc.constantFrom('script', 'div', 'img', 'iframe', 'a', 'style', 'object', 'embed'),
        content: fc.string({ minLength: 0, maxLength: 20 }),
      })
      .map(({ tag, content }) => `<${tag}>${content}</${tag}>`);

    const inputWithHtmlArb = fc
      .tuple(
        fc.string({ minLength: 0, maxLength: 20 }),
        htmlTagArb,
        fc.string({ minLength: 0, maxLength: 20 }),
      )
      .map(([before, html, after]) => `${before}${html}${after}`);

    fc.assert(
      fc.property(inputWithHtmlArb, (input) => {
        const result = sanitizeSearchQuery(input);
        expect(result).not.toMatch(/<[^>]*>/);
      }),
      { numRuns: 200 },
    );
  });

  /**
   * **Validates: Requirement 7.3**
   *
   * For any input containing script injection patterns (javascript:, on*=,
   * eval(), etc.), the sanitizer SHALL remove those patterns.
   */
  it('removes script injection patterns', () => {
    const injectionPatternArb = fc.constantFrom(
      'javascript:alert(1)',
      'javascript: void(0)',
      'onerror=alert(1)',
      'onclick=steal()',
      'onload=hack()',
      'onmouseover=xss()',
      'expression(evil)',
      'url(evil)',
      'import(evil)',
      'eval(document.cookie)',
    );

    const inputWithInjectionArb = fc
      .tuple(
        fc.string({ minLength: 0, maxLength: 15 }),
        injectionPatternArb,
        fc.string({ minLength: 0, maxLength: 15 }),
      )
      .map(([before, pattern, after]) => `${before} ${pattern} ${after}`);

    fc.assert(
      fc.property(inputWithInjectionArb, (input) => {
        const result = sanitizeSearchQuery(input);
        // None of the dangerous patterns should survive
        expect(result).not.toMatch(/javascript\s*:/i);
        expect(result).not.toMatch(/on\w+\s*=/i);
        expect(result).not.toMatch(/expression\s*\(/i);
        expect(result).not.toMatch(/url\s*\(/i);
        expect(result).not.toMatch(/import\s*\(/i);
        expect(result).not.toMatch(/eval\s*\(/i);
      }),
      { numRuns: 200 },
    );
  });

  /**
   * **Validates: Requirement 7.3**
   *
   * The sanitizer output never has leading/trailing whitespace and never
   * contains consecutive spaces.
   */
  it('output is trimmed with no consecutive spaces', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 0, maxLength: 100 }), (input) => {
        const result = sanitizeSearchQuery(input);
        // No leading/trailing whitespace
        expect(result).toBe(result.trim());
        // No consecutive spaces
        expect(result).not.toMatch(/  /);
      }),
      { numRuns: 200 },
    );
  });

  /**
   * **Validates: Requirement 7.3**
   *
   * Plain text without HTML or injection patterns passes through unchanged
   * (modulo whitespace normalization).
   */
  it('preserves plain text content (only normalizes whitespace)', () => {
    const plainTextArb = fc
      .stringMatching(/^[a-zA-Z0-9 ]{1,50}$/)
      .filter((s) => s.trim().length > 0 && !s.match(/\s{2,}/));

    fc.assert(
      fc.property(plainTextArb, (input) => {
        const result = sanitizeSearchQuery(input);
        expect(result).toBe(input.trim());
      }),
      { numRuns: 200 },
    );
  });
});
