/**
 * Properties 27–31 — accessibility models
 * **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  isStrictlyIncreasingOrder,
  hasVisibleFocusIndicator,
  focusInModalTrap,
  allControlsHaveAccessibleName,
  afterEscape,
} from '../../e2e/helpers/a11y-pure'

describe('accessibility property', () => {
  it('Property 27: strictly increasing positions are valid tab order', () => {
    fc.assert(
      fc.property(fc.array(fc.integer({ min: 0, max: 500 }), { minLength: 2, maxLength: 20 }), (arr) => {
        const sorted = [...arr].sort((a, b) => a - b)
        const unique = sorted.filter((v, i) => i === 0 || v !== sorted[i - 1])
        expect(isStrictlyIncreasingOrder(unique)).toBe(true)
        return true
      }),
      { numRuns: 80 },
    )
  })

  it('Property 28: positive outline width implies visible focus', () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 20 }), (w) => {
        expect(hasVisibleFocusIndicator(w)).toBe(true)
        return true
      }),
      { numRuns: 20 },
    )
  })

  it('Property 29: focus within modal bounds', () => {
    expect(focusInModalTrap(5, 2, 8)).toBe(true)
    expect(focusInModalTrap(1, 2, 8)).toBe(false)
  })

  it('Property 30: all true flags = all names present', () => {
    expect(allControlsHaveAccessibleName([true, true])).toBe(true)
    expect(allControlsHaveAccessibleName([true, false])).toBe(false)
  })

  it('Property 31: escape closes overlay', () => {
    expect(afterEscape('modal')).toBe('none')
    expect(afterEscape('none')).toBe('none')
  })
})
