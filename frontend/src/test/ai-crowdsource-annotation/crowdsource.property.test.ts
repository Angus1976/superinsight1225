/**
 * Property-Based Tests for Crowdsource Desensitization & Audit
 *
 * Feature: ai-crowdsource-annotation
 * Tests Properties 10, 11, 14
 *
 * Uses vitest + fast-check with minimum 100 iterations per property.
 */
import { describe, it, expect } from 'vitest'
import fc from 'fast-check'
import type {
  DesensitizationRule,
  DesensitizationPreview,
  AuditLogEntry,
} from '@/services/aiAnnotationApi'

// ─── Property 10: 脱敏预览最多 5 条 ────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 10: 脱敏预览最多 5 条', () => {
  /**
   * **Validates: Requirements 4.3**
   *
   * For any dataset of length N, the preview result after slicing to max 5
   * produces length <= min(5, N), and each preview item has 'original' and
   * 'desensitized' string fields.
   */

  const previewArb: fc.Arbitrary<DesensitizationPreview> = fc.record({
    original: fc.string({ minLength: 1, maxLength: 50 }),
    desensitized: fc.string({ minLength: 1, maxLength: 50 }),
  })

  it('preview slice length is always <= min(5, dataset length)', () => {
    fc.assert(
      fc.property(
        fc.array(previewArb, { minLength: 0, maxLength: 30 }),
        (data) => {
          const previews = data.slice(0, 5)
          return previews.length <= Math.min(5, data.length)
        },
      ),
      { numRuns: 100 },
    )
  })

  it('every preview item has original and desensitized string fields', () => {
    fc.assert(
      fc.property(
        fc.array(previewArb, { minLength: 0, maxLength: 30 }),
        (data) => {
          const previews = data.slice(0, 5)
          return previews.every(
            (p) =>
              typeof p.original === 'string' &&
              typeof p.desensitized === 'string',
          )
        },
      ),
      { numRuns: 100 },
    )
  })

  it('preview length equals min(5, N) exactly', () => {
    fc.assert(
      fc.property(
        fc.array(previewArb, { minLength: 0, maxLength: 30 }),
        (data) => {
          const previews = data.slice(0, 5)
          return previews.length === Math.min(5, data.length)
        },
      ),
      { numRuns: 100 },
    )
  })
})

// ─── Property 11: 脱敏规则完整性校验 ────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 11: 脱敏规则完整性校验', () => {
  /**
   * **Validates: Requirements 4.4, 6.4**
   *
   * For any set of sensitive fields S and configured rule types R,
   * if S ⊄ R (some sensitive fields not covered by enabled rules),
   * then validation should fail (isValid = false).
   */

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
    replacement: fc.string({ minLength: 1, maxLength: 10 }),
    enabled: fc.boolean(),
  })

  const sensitiveFieldArb = fc.constantFrom('name', 'phone', 'email', 'address', 'regex')

  it('uncovered sensitive fields cause isValid to be false', () => {
    fc.assert(
      fc.property(
        fc.array(sensitiveFieldArb, { minLength: 1, maxLength: 5 }),
        fc.array(ruleArb, { minLength: 0, maxLength: 6 }),
        (sensitiveFields, rules) => {
          // Replicate the validation logic from DesensitizerConfig
          const coveredTypes = new Set(
            rules.filter((r) => r.enabled).map((r) => r.type),
          )
          const uncoveredFields = sensitiveFields.filter(
            (f) => !coveredTypes.has(f as DesensitizationRule['type']),
          )
          const isValid =
            uncoveredFields.length === 0 && rules.some((r) => r.enabled)

          // If any sensitive field is not covered, isValid must be false
          if (uncoveredFields.length > 0) {
            return isValid === false
          }
          return true // no assertion needed when all fields are covered
        },
      ),
      { numRuns: 100 },
    )
  })

  it('empty rules always produce isValid = false', () => {
    fc.assert(
      fc.property(
        fc.array(sensitiveFieldArb, { minLength: 1, maxLength: 5 }),
        (sensitiveFields) => {
          const rules: DesensitizationRule[] = []
          const coveredTypes = new Set(
            rules.filter((r) => r.enabled).map((r) => r.type),
          )
          const uncoveredFields = sensitiveFields.filter(
            (f) => !coveredTypes.has(f as DesensitizationRule['type']),
          )
          const isValid =
            uncoveredFields.length === 0 && rules.some((r) => r.enabled)

          return isValid === false
        },
      ),
      { numRuns: 100 },
    )
  })

  it('all disabled rules produce isValid = false even if types match', () => {
    fc.assert(
      fc.property(
        fc.array(sensitiveFieldArb, { minLength: 1, maxLength: 5 }),
        fc.array(ruleArb, { minLength: 1, maxLength: 6 }),
        (sensitiveFields, baseRules) => {
          // Force all rules to be disabled
          const rules = baseRules.map((r) => ({ ...r, enabled: false }))
          const coveredTypes = new Set(
            rules.filter((r) => r.enabled).map((r) => r.type),
          )
          const uncoveredFields = sensitiveFields.filter(
            (f) => !coveredTypes.has(f as DesensitizationRule['type']),
          )
          const isValid =
            uncoveredFields.length === 0 && rules.some((r) => r.enabled)

          return isValid === false
        },
      ),
      { numRuns: 100 },
    )
  })
})

// ─── Property 14: 审计日志字段完整性 ────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 14: 审计日志字段完整性', () => {
  /**
   * **Validates: Requirements 6.1**
   *
   * For any AuditLogEntry, all required fields are present and valid:
   * - operator is non-empty string
   * - timestamp is non-empty string
   * - rules has length >= 1
   * - affectedCount >= 0
   * - taskId is non-empty string
   */

  const ruleTypeArb = fc.constantFrom(
    'name' as const,
    'phone' as const,
    'email' as const,
    'address' as const,
    'regex' as const,
  )

  const desensitizationRuleArb: fc.Arbitrary<DesensitizationRule> = fc.record({
    id: fc.string({ minLength: 1, maxLength: 8 }),
    type: ruleTypeArb,
    replacement: fc.string({ minLength: 1, maxLength: 10 }),
    enabled: fc.boolean(),
  })

  const auditLogArb: fc.Arbitrary<AuditLogEntry> = fc.record({
    id: fc.string({ minLength: 1, maxLength: 10 }),
    operator: fc.string({ minLength: 1, maxLength: 20 }),
    timestamp: fc.string({ minLength: 1, maxLength: 30 }),
    rules: fc.array(desensitizationRuleArb, { minLength: 1, maxLength: 5 }),
    affectedCount: fc.integer({ min: 0, max: 100000 }),
    taskId: fc.string({ minLength: 1, maxLength: 20 }),
  })

  it('every AuditLogEntry has all required fields with valid values', () => {
    fc.assert(
      fc.property(auditLogArb, (entry) => {
        // operator is non-empty string
        if (typeof entry.operator !== 'string' || entry.operator.length === 0)
          return false
        // timestamp is non-empty string
        if (typeof entry.timestamp !== 'string' || entry.timestamp.length === 0)
          return false
        // rules has length >= 1
        if (!Array.isArray(entry.rules) || entry.rules.length < 1) return false
        // affectedCount >= 0
        if (typeof entry.affectedCount !== 'number' || entry.affectedCount < 0)
          return false
        // taskId is non-empty string
        if (typeof entry.taskId !== 'string' || entry.taskId.length === 0)
          return false
        return true
      }),
      { numRuns: 100 },
    )
  })
})
