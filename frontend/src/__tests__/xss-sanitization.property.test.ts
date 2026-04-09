/**
 * Property 13, 14 — XSS / API text escaping
 * **Validates: Requirements 5.1, 5.2**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  escapeHtmlText,
  escapedHasNoRawTags,
  safeApiTextForDisplay,
} from '../../e2e/helpers/security-pure'

describe('xss-sanitization property', () => {
  it('Property 13: escaped user strings do not retain raw tag openers', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 0, maxLength: 200 }), (s) => {
        const e = escapeHtmlText(s)
        if (s.includes('<')) {
          expect(e).toContain('&lt;')
        }
        expect(escapedHasNoRawTags(s)).toBe(true)
        return true
      }),
      { numRuns: 150 },
    )
  })

  it('Property 14: API text for display matches escapeHtmlText', () => {
    fc.assert(
      fc.property(fc.string({ maxLength: 120 }), (s) => {
        expect(safeApiTextForDisplay(s)).toBe(escapeHtmlText(s))
        return true
      }),
      { numRuns: 80 },
    )
  })
})
