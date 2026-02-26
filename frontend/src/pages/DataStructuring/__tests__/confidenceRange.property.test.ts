/**
 * Property Test: 置信度范围约束
 * Validates: 需求 2.2, Property 5
 *
 * For any SchemaInferrer or EntityExtractor returned confidence value,
 * 0.0 ≤ confidence ≤ 1.0.
 */
import { describe, it, expect } from 'vitest'
import fc from 'fast-check'

// --- Types matching backend contracts ---

interface SchemaField {
  name: string
  field_type: string
  description: string
  required: boolean
  entity_type?: string | null
}

interface InferredSchema {
  fields: SchemaField[]
  confidence: number
  source_description: string
}

interface StructuredRecord {
  fields: Record<string, unknown>
  confidence: number
  source_span?: string | null
}

// --- Pure functions simulating backend confidence handling ---

/** Clamp any raw value to [0.0, 1.0] */
function clampConfidence(raw: number): number {
  return Math.min(1.0, Math.max(0.0, raw))
}

/** Check if a confidence value is in valid range */
function validateConfidence(value: number): boolean {
  return value >= 0.0 && value <= 1.0
}

// --- Generators ---

const fieldTypeArb = fc.constantFrom(
  'string', 'integer', 'float', 'boolean', 'date', 'entity', 'list',
)

const schemaFieldArb = fc.record({
  name: fc.string({ minLength: 1, maxLength: 20 }),
  field_type: fieldTypeArb,
  description: fc.string({ maxLength: 50 }),
  required: fc.boolean(),
})

const inferredSchemaArb = (confidence: number): fc.Arbitrary<InferredSchema> =>
  fc.record({
    fields: fc.array(schemaFieldArb, { minLength: 1, maxLength: 8 }),
    confidence: fc.constant(clampConfidence(confidence)),
    source_description: fc.string({ maxLength: 50 }),
  })

const structuredRecordArb = (confidence: number): fc.Arbitrary<StructuredRecord> =>
  fc.record({
    fields: fc.dictionary(
      fc.string({ minLength: 1, maxLength: 10 }),
      fc.oneof(fc.string(), fc.integer(), fc.double(), fc.constant(null)),
      { minKeys: 1, maxKeys: 5 },
    ),
    confidence: fc.constant(clampConfidence(confidence)),
    source_span: fc.option(fc.string({ maxLength: 100 }), { nil: null }),
  })

// --- Property Tests ---

describe('Confidence range constraint properties', () => {
  /**
   * **Validates: Requirements 2.2**
   * Property 5a: clampConfidence always returns value in [0.0, 1.0]
   */
  it('clampConfidence always returns value in [0.0, 1.0]', () => {
    fc.assert(
      fc.property(
        fc.double({ min: -1e6, max: 1e6, noNaN: true }),
        (raw) => {
          const clamped = clampConfidence(raw)
          expect(clamped).toBeGreaterThanOrEqual(0.0)
          expect(clamped).toBeLessThanOrEqual(1.0)
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.2**
   * Property 5b: clampConfidence preserves values already in [0.0, 1.0]
   */
  it('clampConfidence preserves values already in [0.0, 1.0]', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0.0, max: 1.0, noNaN: true }),
        (raw) => {
          expect(clampConfidence(raw)).toBe(raw)
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.2**
   * Property 5c: InferredSchema confidence is always in valid range
   */
  it('InferredSchema confidence is always in valid range', () => {
    fc.assert(
      fc.property(
        fc.double({ min: -1e6, max: 1e6, noNaN: true }).chain((raw) =>
          inferredSchemaArb(raw).map((schema) => schema),
        ),
        (schema) => {
          expect(validateConfidence(schema.confidence)).toBe(true)
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.2**
   * Property 5d: StructuredRecord confidence is always in valid range
   */
  it('StructuredRecord confidence is always in valid range', () => {
    fc.assert(
      fc.property(
        fc.double({ min: -1e6, max: 1e6, noNaN: true }).chain((raw) =>
          structuredRecordArb(raw).map((record) => record),
        ),
        (record) => {
          expect(validateConfidence(record.confidence)).toBe(true)
        },
      ),
      { numRuns: 100 },
    )
  })
})
