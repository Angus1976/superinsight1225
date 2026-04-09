/**
 * Property tests: form interactions (validation, modal, table, dropdown, upload)
 *
 * **Validates: Requirements 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10**
 *
 * Pure logic lives in {@link ../../e2e/helpers/form-interaction-pure.ts}; properties
 * mirror E2E intents from `form-interaction.ts` without Playwright.
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  countRequiredEmptyViolations,
  isWellFormedEmail,
  nextTableSortOrder,
  paginationTotalPages,
  pageSliceLength,
  sortOrderAfterTwoTogglesFromNull,
  dropdownRoundTrip,
  isAllowedUploadExtension,
  modalAfterPrimaryAction,
  deleteConfirmationAfter,
  paginationOffset,
} from '../../e2e/helpers/form-interaction-pure'

describe('form-interactions property', () => {
  it('Property 2: empty required fields → violation count equals number of empty required fields', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            required: fc.boolean(),
            value: fc.string({ maxLength: 20 }),
          }),
          { minLength: 0, maxLength: 30 },
        ),
        (fields) => {
          expect(countRequiredEmptyViolations(fields)).toBe(
            fields.filter((f) => f.required && f.value.trim() === '').length,
          )
          return true
        },
      ),
      { numRuns: 200 },
    )
  })

  it('Property 3: invalid constrained email (when not well-formed) is detectable', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 1, maxLength: 80 }), (raw) => {
        const ok = isWellFormedEmail(raw)
        if (ok) {
          expect(raw).toMatch(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)
        }
        return true
      }),
      { numRuns: 150 },
    )
  })

  it('Property 4: modal open then submit|cancel always closes', () => {
    expect(modalAfterPrimaryAction('closed', 'open')).toBe('open')
    expect(modalAfterPrimaryAction('open', 'submit')).toBe('closed')
    expect(modalAfterPrimaryAction('open', 'cancel')).toBe('closed')
  })

  it('Property 5: delete confirmation — only confirm from confirming reaches done', () => {
    expect(deleteConfirmationAfter('idle', 'requestDelete')).toBe('confirming')
    expect(deleteConfirmationAfter('confirming', 'confirm')).toBe('done')
    expect(deleteConfirmationAfter('confirming', 'cancel')).toBe('idle')
    fc.assert(
      fc.property(fc.constantFrom('requestDelete' as const, 'confirm' as const, 'cancel' as const), (ev) => {
        const afterIdle = deleteConfirmationAfter('idle', ev)
        if (ev === 'requestDelete') expect(afterIdle).toBe('confirming')
        else expect(afterIdle).toBe('idle')
        return true
      }),
      { numRuns: 10 },
    )
  })

  it('Property 6: pagination — page slice length ≤ pageSize and sums cover total', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 5000 }),
        fc.integer({ min: 1, max: 200 }),
        (total, pageSize) => {
          const pages = paginationTotalPages(total, pageSize)
          let sum = 0
          for (let p = 0; p < pages; p++) {
            const len = pageSliceLength(total, p, pageSize)
            expect(len).toBeLessThanOrEqual(pageSize)
            sum += len
          }
          expect(sum).toBe(total)
          return true
        },
      ),
      { numRuns: 150 },
    )
  })

  it('Property 6: offset is non-decreasing with page index', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 100 }),
        fc.integer({ min: 1, max: 50 }),
        fc.integer({ min: 0, max: 20 }),
        fc.integer({ min: 0, max: 20 }),
        (total, pageSize, p1, p2) => {
          const pages = paginationTotalPages(total, pageSize)
          const a = Math.min(p1, Math.max(0, pages - 1))
          const b = Math.min(p2, Math.max(0, pages - 1))
          const o1 = paginationOffset(a, pageSize)
          const o2 = paginationOffset(b, pageSize)
          if (a <= b) expect(o1).toBeLessThanOrEqual(o2)
          return true
        },
      ),
      { numRuns: 100 },
    )
  })

  it('Property 7: table sort toggles cycle ascend/descend from null', () => {
    expect(sortOrderAfterTwoTogglesFromNull()).toBe('descend')
    fc.assert(
      fc.property(fc.constantFrom(null, 'ascend' as const, 'descend' as const), (order) => {
        const n = nextTableSortOrder(order)
        return n === 'ascend' || n === 'descend'
      }),
      { numRuns: 30 },
    )
  })

  it('Property 8: dropdown round-trip preserves selected label', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 0, maxLength: 100 }), (label) => {
        expect(dropdownRoundTrip(label)).toBe(label)
        return true
      }),
      { numRuns: 100 },
    )
  })

  it('Property 9: file upload — only allowed extensions pass', () => {
    const allowed = ['.csv', '.json', '.txt'] as const
    fc.assert(
      fc.property(fc.string({ minLength: 1, maxLength: 80 }), (name) => {
        const ok = isAllowedUploadExtension(name, allowed)
        const lower = name.toLowerCase()
        const dot = lower.lastIndexOf('.')
        if (dot === -1) {
          expect(ok).toBe(false)
        } else {
          const ext = lower.slice(dot)
          expect(ok).toBe(allowed.includes(ext as (typeof allowed)[number]))
        }
        return true
      }),
      { numRuns: 200 },
    )
  })
})
