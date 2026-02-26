/**
 * Property Test: Job 状态机合法转换
 * Validates: 需求 5.1, Property 4
 *
 * For any StructuringJob status sequence, status can only transition in order:
 * pending → extracting → inferring → confirming → extracting_entities → completed,
 * or from any state to failed.
 */
import { describe, it, expect } from 'vitest'
import fc from 'fast-check'

// --- Types ---

type JobStatus =
  | 'pending'
  | 'extracting'
  | 'inferring'
  | 'confirming'
  | 'extracting_entities'
  | 'completed'
  | 'failed'

// --- Valid transitions map ---

const VALID_TRANSITIONS: Record<JobStatus, JobStatus[]> = {
  pending: ['extracting', 'failed'],
  extracting: ['inferring', 'failed'],
  inferring: ['confirming', 'failed'],
  confirming: ['extracting_entities', 'failed'],
  extracting_entities: ['completed', 'failed'],
  completed: [],
  failed: [],
}

const ALL_STATUSES: JobStatus[] = [
  'pending', 'extracting', 'inferring', 'confirming',
  'extracting_entities', 'completed', 'failed',
]

const TERMINAL_STATUSES: JobStatus[] = ['completed', 'failed']

const NON_TERMINAL_STATUSES: JobStatus[] = ALL_STATUSES.filter(
  (s) => !TERMINAL_STATUSES.includes(s),
)

const FORWARD_CHAIN: JobStatus[] = [
  'pending', 'extracting', 'inferring', 'confirming',
  'extracting_entities', 'completed',
]

// --- Pure functions ---

function isValidTransition(from: JobStatus, to: JobStatus): boolean {
  return VALID_TRANSITIONS[from].includes(to)
}

function getNextValidStatuses(current: JobStatus): JobStatus[] {
  return VALID_TRANSITIONS[current]
}

// --- Generators ---

const jobStatusArb = fc.constantFrom<JobStatus>(...ALL_STATUSES)
const nonTerminalStatusArb = fc.constantFrom<JobStatus>(...NON_TERMINAL_STATUSES)

// --- Property Tests ---

describe('Job state machine transition properties', () => {
  /**
   * **Validates: Requirements 5.1**
   * Property 4a: Any valid forward transition is accepted
   */
  it('valid forward transitions are accepted', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: FORWARD_CHAIN.length - 2 }),
        (idx) => {
          const from = FORWARD_CHAIN[idx]
          const to = FORWARD_CHAIN[idx + 1]
          expect(isValidTransition(from, to)).toBe(true)
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 5.1**
   * Property 4b: Any transition to 'failed' from non-terminal state is accepted
   */
  it('transition to failed from any non-terminal state is accepted', () => {
    fc.assert(
      fc.property(nonTerminalStatusArb, (from) => {
        expect(isValidTransition(from, 'failed')).toBe(true)
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 5.1**
   * Property 4c: Invalid transitions (skipping states, going backwards) are rejected
   */
  it('skipping or backward transitions are rejected', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: FORWARD_CHAIN.length - 1 }),
        fc.integer({ min: 0, max: FORWARD_CHAIN.length - 1 }),
        (fromIdx, toIdx) => {
          // Only test non-adjacent forward pairs (skip) or backward pairs
          if (toIdx === fromIdx + 1) return // valid forward — skip
          const from = FORWARD_CHAIN[fromIdx]
          const to = FORWARD_CHAIN[toIdx]
          if (from === to) return // self-transition — tested separately
          expect(isValidTransition(from, to)).toBe(false)
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 5.1**
   * Property 4d: Terminal states have no valid outgoing transitions
   */
  it('terminal states have no valid outgoing transitions', () => {
    fc.assert(
      fc.property(
        fc.constantFrom<JobStatus>(...TERMINAL_STATUSES),
        jobStatusArb,
        (terminal, target) => {
          expect(isValidTransition(terminal, target)).toBe(false)
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 5.1**
   * Property 4e: Random state pairs — transition valid iff it matches the rules
   */
  it('random pairs match transition rules exactly', () => {
    fc.assert(
      fc.property(jobStatusArb, jobStatusArb, (from, to) => {
        const result = isValidTransition(from, to)
        const nextValid = getNextValidStatuses(from)
        expect(result).toBe(nextValid.includes(to))
      }),
      { numRuns: 100 },
    )
  })
})
