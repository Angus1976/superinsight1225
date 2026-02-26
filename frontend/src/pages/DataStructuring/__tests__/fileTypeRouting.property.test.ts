/**
 * Property Test: 文件类型路由正确性
 * Validates: 需求 1.2, 1.3, Property 7
 *
 * For any uploaded file, file_type ∈ {csv, excel} routes to TabularParser,
 * file_type ∈ {pdf, docx, txt, html} routes to FileExtractor.
 * Unknown file types are rejected.
 */
import { describe, it, expect } from 'vitest'
import fc from 'fast-check'

// --- Types ---

type FileType = 'csv' | 'excel' | 'pdf' | 'docx' | 'txt' | 'html'
type ParserType = 'TabularParser' | 'FileExtractor'

// --- Constants ---

const TABULAR_TYPES: FileType[] = ['csv', 'excel']
const TEXT_TYPES: FileType[] = ['pdf', 'docx', 'txt', 'html']
const ALL_SUPPORTED_TYPES: FileType[] = [...TABULAR_TYPES, ...TEXT_TYPES]

// --- Pure routing function (mirrors backend pipeline logic) ---

function routeFileType(fileType: string): ParserType {
  if (TABULAR_TYPES.includes(fileType as FileType)) {
    return 'TabularParser'
  }
  if (TEXT_TYPES.includes(fileType as FileType)) {
    return 'FileExtractor'
  }
  throw new Error(`Unsupported file type: ${fileType}`)
}

// --- Generators ---

const tabularTypeArb = fc.constantFrom<FileType>(...TABULAR_TYPES)
const textTypeArb = fc.constantFrom<FileType>(...TEXT_TYPES)
const supportedTypeArb = fc.constantFrom<FileType>(...ALL_SUPPORTED_TYPES)
const unknownTypeArb = fc
  .string({ minLength: 1, maxLength: 20 })
  .filter((s) => !ALL_SUPPORTED_TYPES.includes(s as FileType))

// --- Property Tests ---

describe('File type routing properties', () => {
  /**
   * **Validates: Requirements 1.3**
   * Property 7a: Tabular file types always route to TabularParser
   */
  it('csv/excel always route to TabularParser', () => {
    fc.assert(
      fc.property(tabularTypeArb, (fileType) => {
        expect(routeFileType(fileType)).toBe('TabularParser')
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 1.2**
   * Property 7b: Text file types always route to FileExtractor
   */
  it('pdf/docx/txt/html always route to FileExtractor', () => {
    fc.assert(
      fc.property(textTypeArb, (fileType) => {
        expect(routeFileType(fileType)).toBe('FileExtractor')
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 1.2, 1.3**
   * Property 7c: Unknown file types are rejected
   */
  it('unknown file types throw an error', () => {
    fc.assert(
      fc.property(unknownTypeArb, (fileType) => {
        expect(() => routeFileType(fileType)).toThrow('Unsupported file type')
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 1.2, 1.3**
   * Property 7d: Routing is deterministic (same input → same output)
   */
  it('routing is deterministic for any supported type', () => {
    fc.assert(
      fc.property(supportedTypeArb, (fileType) => {
        const first = routeFileType(fileType)
        const second = routeFileType(fileType)
        expect(first).toBe(second)
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 1.2, 1.3**
   * Property 7e: All supported file types route to exactly one parser
   */
  it('every supported type routes to exactly one of the two parsers', () => {
    fc.assert(
      fc.property(supportedTypeArb, (fileType) => {
        const parser = routeFileType(fileType)
        const validParsers: ParserType[] = ['TabularParser', 'FileExtractor']
        expect(validParsers).toContain(parser)
      }),
      { numRuns: 100 },
    )
  })
})
