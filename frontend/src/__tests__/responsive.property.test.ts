/**
 * Properties 32–33 — responsive layout
 * **Validates: Requirements 11.1, 11.4, 11.5**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  hasNoHorizontalOverflow,
  meetsTouchTarget,
  MIN_TOUCH_TARGET_PX,
} from '../../e2e/helpers/responsive-pure'

describe('responsive property', () => {
  it('Property 32: content ≤ viewport width', () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 2000 }), fc.integer({ min: 320, max: 2000 }), (cw, vw) => {
        expect(hasNoHorizontalOverflow(Math.min(cw, vw), vw)).toBe(true)
        return true
      }),
      { numRuns: 120 },
    )
  })

  it('Property 33: touch targets ≥ 44px', () => {
    fc.assert(
      fc.property(fc.integer({ min: MIN_TOUCH_TARGET_PX, max: 120 }), (s) => {
        expect(meetsTouchTarget(s)).toBe(true)
        return true
      }),
      { numRuns: 40 },
    )
  })

  it('Property 33: undersized targets fail', () => {
    expect(meetsTouchTarget(MIN_TOUCH_TARGET_PX - 1)).toBe(false)
  })
})
