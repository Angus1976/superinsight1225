/**
 * Property 15 — parameterized SQL (no raw concat)
 * **Validates: Requirements 5.4**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { buildParameterizedWhere } from '../../e2e/helpers/security-pure'

describe('sql-injection property', () => {
  it('Property 15: user fragment only appears in params, not spliced into SQL verbatim', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 0, maxLength: 80 }), (user) => {
        const { sql, params } = buildParameterizedWhere('id', user)
        expect(sql).toMatch(/^SELECT \* FROM t WHERE id = \?$/)
        expect(params).toEqual([user])
        return true
      }),
      { numRuns: 120 },
    )
  })
})
