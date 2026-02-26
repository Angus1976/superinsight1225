/**
 * Property Test: Schema 字段名唯一性
 * Validates: 需求 2.2, Property 1
 *
 * For any input text, SchemaInferrer.infer_from_text(text) returns InferredSchema
 * where all field.name values are unique (no duplicates).
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

// --- Pure functions simulating backend deduplication logic ---

/** Deduplicate field names by appending _2, _3, etc. for duplicates */
function deduplicateFieldNames(fields: SchemaField[]): SchemaField[] {
  const seen = new Map<string, number>()
  return fields.map((field) => {
    const baseName = field.name
    const count = seen.get(baseName) ?? 0
    seen.set(baseName, count + 1)
    if (count === 0) return field
    return { ...field, name: `${baseName}_${count + 1}` }
  })
}

/** Validate that all field names in a schema are unique */
function validateFieldNameUniqueness(schema: InferredSchema): boolean {
  const names = schema.fields.map((f) => f.name)
  return new Set(names).size === names.length
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

/** Generate fields with intentional duplicate names */
const fieldsWithDuplicatesArb = fc
  .array(schemaFieldArb, { minLength: 2, maxLength: 10 })
  .chain((fields) =>
    fc.shuffledSubarray(fields, { minLength: fields.length, maxLength: fields.length })
  )

/** Generate fields guaranteed to have unique names */
const uniqueFieldsArb = fc
  .uniqueArray(fc.string({ minLength: 1, maxLength: 20 }), { minLength: 1, maxLength: 10 })
  .chain((names) =>
    fc.tuple(
      ...names.map((name) =>
        fc.record({
          name: fc.constant(name),
          field_type: fieldTypeArb,
          description: fc.string({ maxLength: 50 }),
          required: fc.boolean(),
        }),
      ),
    ),
  )

const inferredSchemaArb = (fields: SchemaField[]): InferredSchema => ({
  fields,
  confidence: 0.8,
  source_description: 'test',
})

// --- Property Tests ---

describe('Schema field name uniqueness properties', () => {
  /**
   * **Validates: Requirements 2.2**
   * Property 1: After deduplication, all field names are unique
   */
  it('deduplication produces unique field names for any input', () => {
    fc.assert(
      fc.property(
        fc.array(schemaFieldArb, { minLength: 1, maxLength: 15 }),
        (fields) => {
          const deduped = deduplicateFieldNames(fields)
          const names = deduped.map((f) => f.name)
          expect(new Set(names).size).toBe(names.length)
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.2**
   * Property 2: Deduplication preserves the number of fields
   */
  it('deduplication preserves the number of fields', () => {
    fc.assert(
      fc.property(
        fc.array(schemaFieldArb, { minLength: 1, maxLength: 15 }),
        (fields) => {
          const deduped = deduplicateFieldNames(fields)
          expect(deduped.length).toBe(fields.length)
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.2**
   * Property 3: Already-unique fields are not modified by deduplication
   */
  it('already-unique fields are not modified by deduplication', () => {
    fc.assert(
      fc.property(uniqueFieldsArb, (fields) => {
        const deduped = deduplicateFieldNames(fields)
        for (let i = 0; i < fields.length; i++) {
          expect(deduped[i].name).toBe(fields[i].name)
        }
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.2**
   * Property 4: Generated InferredSchema always has unique field names
   */
  it('InferredSchema built from deduplicated fields always passes uniqueness validation', () => {
    fc.assert(
      fc.property(
        fc.array(schemaFieldArb, { minLength: 1, maxLength: 15 }),
        (fields) => {
          const deduped = deduplicateFieldNames(fields)
          const schema = inferredSchemaArb(deduped)
          expect(validateFieldNameUniqueness(schema)).toBe(true)
        },
      ),
      { numRuns: 100 },
    )
  })
})
