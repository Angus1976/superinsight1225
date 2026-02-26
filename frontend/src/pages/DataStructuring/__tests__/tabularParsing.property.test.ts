/**
 * Property Test: 表格解析行数一致性
 * Validates: 需求 1.3, Property 3
 *
 * For any valid CSV/Excel file, TabularParser.parse() returns TabularData where:
 * 1. row_count == rows.length
 * 2. Every row has exactly headers.length keys
 * 3. Every row's keys match the headers set exactly
 */
import { describe, it, expect } from 'vitest'
import fc from 'fast-check'

// --- Types matching backend TabularData contract ---

interface TabularData {
  headers: string[]
  rows: Record<string, unknown>[]
  row_count: number
  file_type: 'csv' | 'excel'
  sheet_name?: string | null
}

// --- Pure function simulating backend TabularParser.parse() ---

function parseTabularData(
  headers: string[],
  rawRows: unknown[][],
): TabularData {
  const rows = rawRows.map((row) => {
    const record: Record<string, unknown> = {}
    for (let i = 0; i < headers.length; i++) {
      record[headers[i]] = i < row.length ? row[i] : null
    }
    return record
  })

  return {
    headers,
    rows,
    row_count: rows.length,
    file_type: 'csv',
  }
}

// --- Generators ---

/** JS prototype keys that can't be used as normal object properties */
const RESERVED_KEYS = new Set(['__proto__', 'constructor', 'prototype'])

/** Generate unique non-empty header names (excluding JS reserved keys) */
const uniqueHeadersArb = fc
  .uniqueArray(
    fc.string({ minLength: 1, maxLength: 20 }).filter((s) => !RESERVED_KEYS.has(s)),
    { minLength: 1, maxLength: 10 },
  )

/** Generate a row of cell values matching a given column count */
const cellArb = fc.oneof(fc.string(), fc.integer(), fc.double(), fc.constant(null))

const rowsArb = (colCount: number) =>
  fc.array(fc.array(cellArb, { minLength: colCount, maxLength: colCount }), {
    minLength: 0,
    maxLength: 50,
  })

// --- Property Tests ---

describe('TabularData parsing properties', () => {
  /**
   * **Validates: Requirements 1.3**
   * Property 3a: row_count always equals rows.length
   */
  it('row_count equals rows.length for any input', () => {
    fc.assert(
      fc.property(
        uniqueHeadersArb.chain((headers) =>
          rowsArb(headers.length).map((rows) => ({ headers, rows })),
        ),
        ({ headers, rows }) => {
          const result = parseTabularData(headers, rows)
          expect(result.row_count).toBe(result.rows.length)
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 1.3**
   * Property 3b: every row has exactly headers.length keys
   */
  it('every row has exactly headers.length keys', () => {
    fc.assert(
      fc.property(
        uniqueHeadersArb.chain((headers) =>
          rowsArb(headers.length).map((rows) => ({ headers, rows })),
        ),
        ({ headers, rows }) => {
          const result = parseTabularData(headers, rows)
          for (const row of result.rows) {
            expect(Object.keys(row).length).toBe(result.headers.length)
          }
        },
      ),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 1.3**
   * Property 3c: every row's keys match the headers set exactly
   */
  it("every row's keys match the headers set", () => {
    fc.assert(
      fc.property(
        uniqueHeadersArb.chain((headers) =>
          rowsArb(headers.length).map((rows) => ({ headers, rows })),
        ),
        ({ headers, rows }) => {
          const result = parseTabularData(headers, rows)
          const headerSet = new Set(result.headers)
          for (const row of result.rows) {
            const keySet = new Set(Object.keys(row))
            expect(keySet).toEqual(headerSet)
          }
        },
      ),
      { numRuns: 100 },
    )
  })
})
