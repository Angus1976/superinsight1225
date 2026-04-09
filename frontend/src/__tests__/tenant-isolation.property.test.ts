/**
 * Property 16 — tenant data isolation
 * **Validates: Requirements 5.6**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { tenantCanAccessResource } from '../../e2e/helpers/security-pure'

describe('tenant-isolation property', () => {
  it('Property 16: access iff tenant ids match', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 1, maxLength: 24 }), fc.string({ minLength: 1, maxLength: 24 }), (a, b) => {
        expect(tenantCanAccessResource(a, b)).toBe(a === b)
        return true
      }),
      { numRuns: 150 },
    )
  })
})
