/**
 * Property-Based Tests for batchStore and rhythmStore
 *
 * Feature: ai-crowdsource-annotation
 * Tests Property 8: 累计批次进度计算 + rhythmStore rate/priority correctness
 *
 * Uses vitest + fast-check with minimum 100 iterations per property.
 */
import { describe, it, beforeEach } from 'vitest'
import fc from 'fast-check'
import { useBatchStore } from '@/stores/batchStore'
import type { BatchResult } from '@/stores/batchStore'
import { useRhythmStore } from '@/stores/rhythmStore'
import type { PriorityRule } from '@/services/aiAnnotationApi'

// ─── Reset stores between tests ────────────────────────────────────
beforeEach(() => {
  useBatchStore.setState({
    config: {
      batchSize: 100,
      intervalSeconds: 30,
      qualityThreshold: 0.8,
      autoStop: true,
    },
    progress: null,
  })
  useRhythmStore.setState({
    config: { ratePerMinute: 60, concurrency: 4, priorityRules: [] },
    status: { currentRate: 0, queueDepth: 0, resourceUsage: 0 },
  })
})

// ─── Arbitrary generators ──────────────────────────────────────────

const batchResultArb: fc.Arbitrary<BatchResult> = fc.record({
  batchIndex: fc.integer({ min: 0, max: 1000 }),
  accuracy: fc.float({ min: 0, max: 1, noNaN: true }),
  processedCount: fc.integer({ min: 1, max: 10000 }),
  status: fc.constantFrom('completed' as const, 'paused' as const, 'failed' as const),
})

const priorityRuleArb: fc.Arbitrary<PriorityRule> = fc.record({
  field: fc.constantFrom('dataType' as const, 'labelCategory' as const),
  value: fc.string({ minLength: 1, maxLength: 20 }),
  priority: fc.integer({ min: 1, max: 10 }),
})


// ─── Property 8: 累计批次进度计算 ──────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 8: 累计批次进度计算', () => {
  /**
   * **Validates: Requirements 3.3**
   *
   * For any list of BatchResults, after adding all results via addBatchResult:
   * 1. progress.batchResults.length === results.length
   * 2. sum of processedCount across all results is correct
   * 3. currentBatch increments correctly (equals results.length)
   */
  it('batchResults length equals added results count and processedCount sum is correct', () => {
    fc.assert(
      fc.property(
        fc.array(batchResultArb, { minLength: 1, maxLength: 20 }),
        (results) => {
          // Reset store
          useBatchStore.setState({
            config: {
              batchSize: 100,
              intervalSeconds: 30,
              qualityThreshold: 0.8,
              autoStop: false, // Disable auto-stop to avoid status override
            },
            progress: null,
          })

          for (const r of results) {
            useBatchStore.getState().addBatchResult(r)
          }

          const progress = useBatchStore.getState().progress
          if (!progress) return false

          // 1. batchResults.length === results.length
          if (progress.batchResults.length !== results.length) return false

          // 2. sum of processedCount is correct
          const expectedSum = results.reduce((sum, r) => sum + r.processedCount, 0)
          const actualSum = progress.batchResults.reduce((sum, r) => sum + r.processedCount, 0)
          if (actualSum !== expectedSum) return false

          // 3. currentBatch increments correctly
          if (progress.currentBatch !== results.length) return false

          return true
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 3.3**
   *
   * Quality trend data points count equals the number of completed batches.
   */
  it('completed batch count matches batchResults with completed status', () => {
    fc.assert(
      fc.property(
        fc.array(batchResultArb, { minLength: 1, maxLength: 20 }),
        (results) => {
          useBatchStore.setState({
            config: {
              batchSize: 100,
              intervalSeconds: 30,
              qualityThreshold: 0.8,
              autoStop: false,
            },
            progress: null,
          })

          for (const r of results) {
            useBatchStore.getState().addBatchResult(r)
          }

          const progress = useBatchStore.getState().progress
          if (!progress) return false

          const completedCount = progress.batchResults.filter(
            (r) => r.status === 'completed',
          ).length
          const expectedCompleted = results.filter(
            (r) => r.status === 'completed',
          ).length

          return completedCount === expectedCompleted
        },
      ),
      { numRuns: 100 },
    )
  })
})

// ─── RhythmStore: rate update correctness ──────────────────────────
describe('Feature: ai-crowdsource-annotation, RhythmStore rate update correctness', () => {
  /**
   * **Validates: Requirements 5.1**
   *
   * After updateRate(rate), config.ratePerMinute === rate.
   */
  it('updateRate sets config.ratePerMinute to the given value', () => {
    fc.assert(
      fc.property(
        fc.float({ min: Math.fround(0.1), max: 10000, noNaN: true }),
        (rate) => {
          useRhythmStore.setState({
            config: { ratePerMinute: 60, concurrency: 4, priorityRules: [] },
            status: { currentRate: 0, queueDepth: 0, resourceUsage: 0 },
          })

          useRhythmStore.getState().updateRate(rate)
          return useRhythmStore.getState().config.ratePerMinute === rate
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 5.2**
   *
   * After updatePriority(rules), config.priorityRules === rules.
   */
  it('updatePriority sets config.priorityRules to the given rules', () => {
    fc.assert(
      fc.property(
        fc.array(priorityRuleArb, { minLength: 0, maxLength: 10 }),
        (rules) => {
          useRhythmStore.setState({
            config: { ratePerMinute: 60, concurrency: 4, priorityRules: [] },
            status: { currentRate: 0, queueDepth: 0, resourceUsage: 0 },
          })

          useRhythmStore.getState().updatePriority(rules)
          const stored = useRhythmStore.getState().config.priorityRules

          if (stored.length !== rules.length) return false
          return stored.every(
            (r, i) =>
              r.field === rules[i].field &&
              r.value === rules[i].value &&
              r.priority === rules[i].priority,
          )
        },
      ),
      { numRuns: 100 },
    )
  })
})
