/**
 * Property 19 — page load time threshold (model)
 * **Validates: Requirements 6.3**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { isWithinLoadBudget } from '../../e2e/helpers/performance-pure'

describe('performance property', () => {
  it('Property 19: measured ms within budget iff both non-negative and ≤ budget', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 30_000 }),
        fc.integer({ min: 0, max: 30_000 }),
        (ms, budget) => {
          const ok = isWithinLoadBudget(ms, budget)
          expect(ok).toBe(ms <= budget)
          return true
        },
      ),
      { numRuns: 150 },
    )
  })
})
