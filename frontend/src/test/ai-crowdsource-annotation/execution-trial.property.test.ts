/**
 * Property-Based Tests for ExecutionPanel and TrialRunner stores
 *
 * Feature: ai-crowdsource-annotation
 * Tests Properties 1, 2, 3, 5
 *
 * Uses vitest + fast-check with minimum 100 iterations per property.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import fc from 'fast-check'
import { useExecutionStore } from '@/stores/executionStore'
import { useTrialStore } from '@/stores/trialStore'
import type { TrialResult, TrialConfig } from '@/stores/trialStore'

// ─── Reset stores between tests ────────────────────────────────────
beforeEach(() => {
  useExecutionStore.setState({ executions: {} })
  useTrialStore.setState({ trials: [] })
})

// ─── Arbitrary generators ──────────────────────────────────────────

const distributionEntryArb = fc.record({
  range: fc.string({ minLength: 1, maxLength: 10 }),
  count: fc.integer({ min: 0, max: 10000 }),
})

const labelEntryArb = fc.record({
  label: fc.string({ minLength: 1, maxLength: 20 }),
  count: fc.integer({ min: 0, max: 10000 }),
})

const executionErrorArb = fc.record({
  code: fc.string({ minLength: 1, maxLength: 10 }),
  message: fc.string({ minLength: 1, maxLength: 50 }),
})

const executionUpdateArb = fc.record({
  progress: fc.float({ min: 0, max: 100, noNaN: true }),
  processed: fc.integer({ min: 0, max: 100000 }),
  remaining: fc.integer({ min: 0, max: 100000 }),
  estimatedTime: fc.float({ min: 0, max: 100000, noNaN: true }),
  confidenceDistribution: fc.array(distributionEntryArb, { minLength: 0, maxLength: 5 }),
  labelDistribution: fc.array(labelEntryArb, { minLength: 0, maxLength: 5 }),
  errors: fc.array(executionErrorArb, { minLength: 0, maxLength: 3 }),
})

const trialConfigArb: fc.Arbitrary<TrialConfig> = fc.record({
  sampleSize: fc.integer({ min: 10, max: 100 }),
  annotationType: fc.string({ minLength: 1, maxLength: 20 }),
  confidenceThreshold: fc.float({ min: 0, max: 1, noNaN: true }),
})

const trialResultArb: fc.Arbitrary<TrialResult> = fc.record({
  trialId: fc.uuid(),
  config: trialConfigArb,
  accuracy: fc.float({ min: 0, max: 1, noNaN: true }),
  avgConfidence: fc.float({ min: 0, max: 1, noNaN: true }),
  confidenceDistribution: fc.array(distributionEntryArb, { minLength: 0, maxLength: 5 }),
  labelDistribution: fc.array(labelEntryArb, { minLength: 0, maxLength: 5 }),
  duration: fc.integer({ min: 0, max: 600000 }),
  timestamp: fc.date().map((d) => d.toISOString()),
})

// ─── Property 1: 执行状态渲染完整性 ────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 1: 执行状态渲染完整性', () => {
  /**
   * **Validates: Requirements 1.1, 1.3**
   *
   * For any random ExecutionState update, after startExecution + updateProgress,
   * the stored state contains all required fields: progress, processed, remaining,
   * estimatedTime, labelDistribution, confidenceDistribution, errors, status.
   */
  it('stored state contains all required fields after startExecution + updateProgress', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 20 }),
        executionUpdateArb,
        (taskId, update) => {
          useExecutionStore.setState({ executions: {} })
          const store = useExecutionStore.getState()

          store.startExecution(taskId)
          useExecutionStore.getState().updateProgress(taskId, update)

          const state = useExecutionStore.getState().executions[taskId]
          if (!state) return false

          // All required fields must exist
          return (
            typeof state.progress === 'number' &&
            typeof state.processed === 'number' &&
            typeof state.remaining === 'number' &&
            typeof state.estimatedTime === 'number' &&
            Array.isArray(state.labelDistribution) &&
            Array.isArray(state.confidenceDistribution) &&
            Array.isArray(state.errors) &&
            typeof state.status === 'string' &&
            ['running', 'paused', 'completed', 'error'].includes(state.status)
          )
        },
      ),
      { numRuns: 100 },
    )
  })
})

// ─── Property 2: WebSocket 消息正确更新状态 ─────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 2: WebSocket 消息正确更新状态', () => {
  /**
   * **Validates: Requirements 1.2**
   *
   * For any sequence of progress values, after applying them via updateProgress,
   * the stored progress should be >= the maximum of all previously applied values
   * (monotonically increasing enforcement).
   */
  it('progress is monotonically increasing after a sequence of updateProgress calls', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 20 }),
        fc.array(fc.float({ min: 0, max: 100, noNaN: true }), { minLength: 1, maxLength: 20 }),
        (taskId, progressValues) => {
          useExecutionStore.setState({ executions: {} })
          const store = useExecutionStore.getState()
          store.startExecution(taskId)

          let maxSoFar = 0
          for (const p of progressValues) {
            useExecutionStore.getState().updateProgress(taskId, { progress: p })
            const current = useExecutionStore.getState().executions[taskId].progress
            // Progress must never decrease below the running maximum
            if (current < maxSoFar) return false
            maxSoFar = Math.max(maxSoFar, p)
          }

          // Final progress should equal the max of all applied values
          const finalProgress = useExecutionStore.getState().executions[taskId].progress
          return finalProgress >= maxSoFar
        },
      ),
      { numRuns: 100 },
    )
  })
})

// ─── Property 3: 暂停保留已完成结果 ────────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 3: 暂停保留已完成结果', () => {
  /**
   * **Validates: Requirements 1.5**
   *
   * For any ExecutionState with status='running', after pauseExecution:
   * - status becomes 'paused'
   * - processed remains the same
   * - labelDistribution remains the same
   */
  it('pauseExecution preserves processed and labelDistribution, sets status to paused', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 20 }),
        executionUpdateArb,
        (taskId, update) => {
          useExecutionStore.setState({ executions: {} })
          const store = useExecutionStore.getState()

          store.startExecution(taskId)
          useExecutionStore.getState().updateProgress(taskId, update)

          // Capture state before pause
          const beforePause = useExecutionStore.getState().executions[taskId]
          const processedBefore = beforePause.processed
          const labelDistBefore = JSON.stringify(beforePause.labelDistribution)

          // Pause
          useExecutionStore.getState().pauseExecution(taskId)

          const afterPause = useExecutionStore.getState().executions[taskId]

          return (
            afterPause.status === 'paused' &&
            afterPause.processed === processedBefore &&
            JSON.stringify(afterPause.labelDistribution) === labelDistBefore
          )
        },
      ),
      { numRuns: 100 },
    )
  })
})

// ─── Property 5: 多次试算对比表完整性 ──────────────────────────────
describe('Feature: ai-crowdsource-annotation, Property 5: 多次试算对比表完整性', () => {
  /**
   * **Validates: Requirements 2.2, 2.4**
   *
   * For any list of TrialResults (length >= 1), after adding them all via addTrial,
   * trials.length equals the number of added results, and each result contains
   * config, accuracy, avgConfidence, duration fields.
   */
  it('trialStore correctly maintains trial results with all required fields', () => {
    fc.assert(
      fc.property(
        fc.array(trialResultArb, { minLength: 1, maxLength: 10 }),
        (results) => {
          useTrialStore.setState({ trials: [] })

          for (const r of results) {
            useTrialStore.getState().addTrial(r)
          }

          const trials = useTrialStore.getState().trials

          // Length must match
          if (trials.length !== results.length) return false

          // Each trial must have required fields
          return trials.every(
            (t) =>
              t.config !== undefined &&
              typeof t.accuracy === 'number' &&
              typeof t.avgConfidence === 'number' &&
              typeof t.duration === 'number',
          )
        },
      ),
      { numRuns: 100 },
    )
  })
})
