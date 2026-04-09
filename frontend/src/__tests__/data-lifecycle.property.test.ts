/**
 * Property 10: Data lifecycle count invariant
 * **Validates: Requirements 3.6**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  assertLifecycleCountInvariant,
  pipelineTotalMatchesExport,
} from '../../e2e/helpers/data-lifecycle-pure'

describe('data-lifecycle property', () => {
  it('Property 10: aligned pipeline counts satisfy invariant', () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 100_000 }), (n) => {
        expect(
          assertLifecycleCountInvariant({
            acquisition: n,
            annotationTask: n,
            exportRecord: n,
          }),
        ).toBe(true)
        return true
      }),
      { numRuns: 100 },
    )
  })

  it('Property 10: mismatched counts break invariant', () => {
    expect(
      assertLifecycleCountInvariant({
        acquisition: 1,
        annotationTask: 2,
        exportRecord: 1,
      }),
    ).toBe(false)
  })

  it('pipeline totals match export when all equal', () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 50_000 }), (n) => {
        expect(pipelineTotalMatchesExport(n, n, n)).toBe(true)
        return true
      }),
      { numRuns: 80 },
    )
  })
})
