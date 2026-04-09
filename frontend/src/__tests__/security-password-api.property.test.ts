/**
 * Properties 17, 18 — password field contract; safe client error messages
 * **Validates: Requirements 5.8, 5.10**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  passwordFieldAttributes,
  isSafeClientErrorMessage,
} from '../../e2e/helpers/security-pure'

describe('security-password-api property', () => {
  it('Property 17: password field uses password type and disables autocomplete', () => {
    const a = passwordFieldAttributes()
    expect(a.type).toBe('password')
    expect(a.autoComplete).toBe('off')
  })

  it('Property 18: benign user-facing messages are safe', () => {
    const safe = ['Something went wrong', 'Please try again', 'Not found']
    for (const m of safe) expect(isSafeClientErrorMessage(m)).toBe(true)
  })

  it('Property 18: stack-like / SQL-like strings flagged unsafe', () => {
    expect(isSafeClientErrorMessage('at Object.foo (/app/src/x.ts:1:1)')).toBe(false)
    expect(isSafeClientErrorMessage('SELECT * FROM users')).toBe(false)
  })

  it('Property 18: random strings never throw', () => {
    fc.assert(
      fc.property(fc.string({ maxLength: 300 }), (s) => {
        const v = isSafeClientErrorMessage(s)
        expect(typeof v).toBe('boolean')
        return true
      }),
      { numRuns: 200 },
    )
  })
})
