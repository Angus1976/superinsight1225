/**
 * Property 36 — console noise filter (E2E fixtures)
 * **Validates: Requirements 16.4**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  shouldIgnoreConsoleNoise,
  filterConsoleErrorLines,
  E2E_KNOWN_CONSOLE_IGNORE_SUBSTRINGS,
} from '../../e2e/helpers/console-filter'

describe('console-filter property', () => {
  it('Property 36: known substrings always ignored', () => {
    for (const frag of E2E_KNOWN_CONSOLE_IGNORE_SUBSTRINGS) {
      expect(shouldIgnoreConsoleNoise(`prefix ${frag} suffix`)).toBe(true)
    }
  })

  it('Property 36: filter removes only matching lines', () => {
    const lines = ['ok', 'Failed to fetch', 'still ok']
    expect(filterConsoleErrorLines(lines)).toEqual(['ok', 'still ok'])
  })

  it('Property 36: random suffix append preserves ignore for known issues', () => {
    fc.assert(
      fc.property(fc.string({ maxLength: 40 }), (suffix) => {
        const msg = `Failed to fetch ${suffix}`
        expect(shouldIgnoreConsoleNoise(msg)).toBe(true)
        return true
      }),
      { numRuns: 80 },
    )
  })
})
