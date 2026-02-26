/**
 * Property-Based Test for 脱敏标注映射往返 (Desensitization Round-Trip)
 *
 * Feature: ai-crowdsource-annotation
 * Property 16: mapBack(desensitize(data)).id === data.id
 *
 * **Validates: Requirements 6.3**
 *
 * Uses vitest + fast-check with minimum 100 iterations.
 */
import { describe, it, expect } from 'vitest'
import fc from 'fast-check'
import {
  desensitizeRecords,
  mapBackToOriginalIds,
} from '@/utils/annotationHelpers'
import type {
  DataRecord,
  DesensitizedRecord,
} from '@/utils/annotationHelpers'
import type { DesensitizationRule } from '@/services/aiAnnotationApi'

// ─── Arbitrary generators ──────────────────────────────────────────

const ruleTypeArb = fc.constantFrom(
  'name' as const,
  'phone' as const,
  'email' as const,
  'address' as const,
  'regex' as const,
)

const ruleArb: fc.Arbitrary<DesensitizationRule> = fc.record({
  id: fc.string({ minLength: 1, maxLength: 8 }),
  type: ruleTypeArb,
  replacement: fc.constant('***'),
  enabled: fc.boolean(),
})

/** Generate a DataRecord with a unique id and 1-3 arbitrary string fields */
const dataRecordArb: fc.Arbitrary<DataRecord> = fc
  .record({
    id: fc.uuid(),
    field1: fc.string({ minLength: 0, maxLength: 30 }),
    field2: fc.string({ minLength: 0, maxLength: 30 }),
  })

const sensitiveFieldsArb = fc.constantFrom(
  ['field1'],
  ['field2'],
  ['field1', 'field2'],
)

// ─── Property 16: 脱敏标注映射往返 ─────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 16: 脱敏标注映射往返', () => {
  /**
   * **Validates: Requirements 6.3**
   *
   * For any original data that goes through desensitization and then
   * mapBack, the resulting record's id must equal the original data's id.
   * mapBack(desensitize(data)).id === data.id
   */
  it('mapBack after desensitize preserves all original ids', () => {
    fc.assert(
      fc.property(
        fc.array(dataRecordArb, { minLength: 1, maxLength: 20 }),
        fc.array(ruleArb, { minLength: 0, maxLength: 4 }),
        sensitiveFieldsArb,
        (records, rules, sensitiveFields) => {
          const desensitized = desensitizeRecords(records, sensitiveFields, rules)
          const mappedBack = mapBackToOriginalIds(desensitized)

          // Core invariant: every mapped-back id matches the original
          if (mappedBack.length !== records.length) return false

          for (let i = 0; i < records.length; i++) {
            if (mappedBack[i].id !== records[i].id) return false
          }

          return true
        },
      ),
      { numRuns: 100 },
    )
  })

  it('desensitize-mapBack round trip preserves record count', () => {
    fc.assert(
      fc.property(
        fc.array(dataRecordArb, { minLength: 0, maxLength: 20 }),
        fc.array(ruleArb, { minLength: 0, maxLength: 4 }),
        sensitiveFieldsArb,
        (records, rules, sensitiveFields) => {
          const desensitized = desensitizeRecords(records, sensitiveFields, rules)
          const mappedBack = mapBackToOriginalIds(desensitized)
          return mappedBack.length === records.length
        },
      ),
      { numRuns: 100 },
    )
  })

  it('desensitized records do not expose original ids', () => {
    fc.assert(
      fc.property(
        fc.array(dataRecordArb, { minLength: 1, maxLength: 20 }),
        fc.array(ruleArb, { minLength: 0, maxLength: 4 }),
        sensitiveFieldsArb,
        (records, rules, sensitiveFields) => {
          const desensitized = desensitizeRecords(records, sensitiveFields, rules)

          // maskedId should not equal originalId (they use different formats)
          for (const d of desensitized) {
            if (d.maskedId === d.originalId) return false
          }

          return true
        },
      ),
      { numRuns: 100 },
    )
  })
})
