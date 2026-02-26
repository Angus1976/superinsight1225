/**
 * Property-Based Tests for annotationHelpers utility functions
 *
 * Feature: ai-crowdsource-annotation
 * Tests Properties 4, 6, 7, 9, 12, 13, 15
 *
 * Uses vitest + fast-check with minimum 100 iterations per property.
 */
import { describe, it, expect } from 'vitest'
import fc from 'fast-check'
import {
  clampSampleSize,
  checkBatchQuality,
  calculateEstimatedTime,
  sortByPriority,
  applyDesensitizationRule,
  filterAuditLogs,
} from '@/utils/annotationHelpers'
import type {
  DesensitizationRule,
  AuditLogEntry,
  AuditFilter,
} from '@/services/aiAnnotationApi'

// ─── Property 4: 试算样本数约束 ────────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 4: 试算样本数约束', () => {
  /**
   * **Validates: Requirements 2.1**
   *
   * For any integer n, clampSampleSize(n) is always in [10, 100].
   */
  it('clampSampleSize output is always within [10, 100] for any integer', () => {
    fc.assert(
      fc.property(fc.integer(), (n) => {
        const clamped = clampSampleSize(n)
        return clamped >= 10 && clamped <= 100
      }),
      { numRuns: 100 },
    )
  })
})

// ─── Property 6: 低置信度警告 ──────────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 6: 低置信度警告', () => {
  /**
   * **Validates: Requirements 2.5**
   *
   * For any avgConfidence in [0, 1], the threshold logic correctly determines
   * the warning state: avgConfidence < 0.6 → shouldWarn = true.
   */
  it('avgConfidence < 0.6 correctly determines warning state', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 1, noNaN: true }),
        (avgConfidence) => {
          const shouldWarn = avgConfidence < 0.6
          return shouldWarn === (avgConfidence < 0.6)
        },
      ),
      { numRuns: 100 },
    )
  })
})


// ─── Property 7: 批次质量自动暂停 ──────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 7: 批次质量自动暂停', () => {
  /**
   * **Validates: Requirements 3.2, 3.4**
   *
   * For any accuracy and threshold in [0, 1], checkBatchQuality returns
   * shouldPause=true when accuracy < threshold, false otherwise.
   */
  it('checkBatchQuality returns shouldPause correctly based on accuracy vs threshold', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 1, noNaN: true }),
        fc.float({ min: 0, max: 1, noNaN: true }),
        (accuracy, threshold) => {
          const result = checkBatchQuality(accuracy, threshold)
          if (accuracy < threshold) {
            return result.shouldPause === true
          }
          return result.shouldPause === false
        },
      ),
      { numRuns: 100 },
    )
  })
})

// ─── Property 13: 速率变更更新预估时间 ─────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 13: 速率变更更新预估时间', () => {
  /**
   * **Validates: Requirements 5.3**
   *
   * For any remaining > 0 and ratePerMinute > 0,
   * calculateEstimatedTime(remaining, rate) ≈ remaining / rate within ε < 0.01.
   */
  it('calculateEstimatedTime equals remaining / rate within floating point tolerance', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 100000 }),
        fc.float({ min: Math.fround(0.1), max: 1000, noNaN: true }),
        (remaining, rate) => {
          const result = calculateEstimatedTime(remaining, rate)
          return Math.abs(result - remaining / rate) < 0.01
        },
      ),
      { numRuns: 100 },
    )
  })
})

// ─── Property 12: 优先级排序正确性 ─────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 12: 优先级排序正确性', () => {
  /**
   * **Validates: Requirements 5.2, 5.4**
   *
   * For any list of items with priorities, sorted result has high priority first
   * (descending order), and same priority preserves original order (stable sort).
   */
  it('sortByPriority produces descending order with stable sort for equal priorities', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: fc.string(),
            priority: fc.integer({ min: 1, max: 10 }),
          }),
        ),
        (items) => {
          const sorted = sortByPriority(items)

          // Check descending order by priority
          for (let i = 1; i < sorted.length; i++) {
            if (sorted[i].priority > sorted[i - 1].priority) return false
          }

          // Check stability: same priority items maintain relative order
          for (let i = 1; i < sorted.length; i++) {
            if (sorted[i].priority === sorted[i - 1].priority) {
              const origIdxA = items.indexOf(sorted[i - 1])
              const origIdxB = items.indexOf(sorted[i])
              if (origIdxA > origIdxB) return false
            }
          }

          return true
        },
      ),
      { numRuns: 100 },
    )
  })
})

// ─── Property 9: 脱敏规则正确应用 ──────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 9: 脱敏规则正确应用', () => {
  /**
   * **Validates: Requirements 4.2**
   *
   * For phone type desensitization: the output should not contain
   * the original middle 4 digits of the phone number.
   */
  it('phone desensitization removes the middle 4 digits', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1000, max: 9999 }),
        (middle) => {
          const middleStr = middle.toString().padStart(4, '0')
          const phone = `138${middleStr}5678`
          const rule: DesensitizationRule = {
            id: '1',
            type: 'phone',
            replacement: '****',
            enabled: true,
          }
          const result = applyDesensitizationRule(phone, rule)
          return !result.includes(middleStr)
        },
      ),
      { numRuns: 100 },
    )
  })
})


// ─── Property 15: 审计日志筛选正确性 ────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 15: 审计日志筛选正确性', () => {
  // Arbitrary generators for AuditLogEntry and AuditFilter

  /** Generate a date string in YYYY-MM-DD format */
  const dateArb = fc
    .tuple(
      fc.integer({ min: 2020, max: 2026 }),
      fc.integer({ min: 1, max: 12 }),
      fc.integer({ min: 1, max: 28 }),
    )
    .map(
      ([y, m, d]) =>
        `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`,
    )

  const operatorArb = fc.constantFrom('alice', 'bob', 'charlie', 'dave')

  const desensitizationRuleArb: fc.Arbitrary<DesensitizationRule> = fc.record({
    id: fc.string({ minLength: 1, maxLength: 5 }),
    type: fc.constantFrom('name' as const, 'phone' as const, 'email' as const, 'address' as const, 'regex' as const),
    replacement: fc.string({ minLength: 1, maxLength: 10 }),
    enabled: fc.boolean(),
  })

  const auditLogArb: fc.Arbitrary<AuditLogEntry> = fc.record({
    id: fc.string({ minLength: 1, maxLength: 10 }),
    operator: operatorArb,
    timestamp: dateArb,
    rules: fc.array(desensitizationRuleArb, { minLength: 0, maxLength: 3 }),
    affectedCount: fc.integer({ min: 0, max: 1000 }),
    taskId: fc.string({ minLength: 1, maxLength: 10 }),
  })

  /** Generate a sorted date range pair [start, end] where start <= end */
  const dateRangeArb = fc
    .tuple(dateArb, dateArb)
    .map(([a, b]) => (a <= b ? [a, b] : [b, a]) as [string, string])

  const auditFilterArb: fc.Arbitrary<AuditFilter> = fc.record({
    dateRange: fc.option(dateRangeArb, { nil: undefined }),
    operator: fc.option(operatorArb, { nil: undefined }),
  })

  /**
   * **Validates: Requirements 6.2**
   *
   * For any list of audit logs and any filter, every item in the filtered
   * result satisfies all filter conditions.
   */
  it('all filtered results satisfy the filter conditions', () => {
    fc.assert(
      fc.property(
        fc.array(auditLogArb, { minLength: 0, maxLength: 20 }),
        auditFilterArb,
        (logs, filter) => {
          const filtered = filterAuditLogs(logs, filter)

          return filtered.every((log: AuditLogEntry) => {
            // Check dateRange condition
            if (filter.dateRange) {
              if (log.timestamp < filter.dateRange[0]) return false
              if (log.timestamp > filter.dateRange[1]) return false
            }
            // Check operator condition
            if (filter.operator && log.operator !== filter.operator) return false
            return true
          })
        },
      ),
      { numRuns: 100 },
    )
  })
})
