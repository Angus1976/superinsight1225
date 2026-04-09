/**
 * Property 35 — mock API JSON shapes from mock-api-factory generators
 * **Validates: Requirements 16.2**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  buildTaskRecord,
  generateTasks,
  generateBillingRecords,
} from '../../e2e/helpers/mock-api-factory'

function assertTaskShape(t: ReturnType<typeof buildTaskRecord>) {
  expect(typeof t.id).toBe('string')
  expect(typeof t.tenant_id).toBe('string')
  expect(['pending', 'in_progress', 'completed']).toContain(t.status)
  expect(typeof t.progress).toBe('number')
}

describe('mock-schema property', () => {
  it('Property 35: buildTaskRecord always yields consistent task shape', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 24 }),
        fc.string({ minLength: 1, maxLength: 16 }),
        fc.integer({ min: 0, max: 50 }),
        (id, tenantId, index) => {
          const t = buildTaskRecord(id, tenantId, index)
          assertTaskShape(t)
          expect(t.tenant_id).toBe(tenantId)
          return true
        },
      ),
      { numRuns: 100 },
    )
  })

  it('Property 35: generateTasks list matches TaskListResponse counts', () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 20 }), fc.string({ minLength: 1, maxLength: 12 }), (count, tid) => {
        const items = generateTasks(count, tid)
        expect(items.length).toBe(count)
        items.forEach(assertTaskShape)
        return true
      }),
      { numRuns: 40 },
    )
  })

  it('Property 35: billing records have id, amount, tenant_id', () => {
    const rows = generateBillingRecords(3, 'tenant-x')
    expect(rows.length).toBe(3)
    rows.forEach((r) => {
      expect(typeof r.id).toBe('string')
      expect(typeof r.amount).toBe('number')
      expect(r.tenant_id).toBe('tenant-x')
    })
  })
})
