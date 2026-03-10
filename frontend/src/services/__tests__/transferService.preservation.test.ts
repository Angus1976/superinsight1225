/**
 * Property-Based Tests for Transfer Service - Source Metadata Preservation
 * 
 * Property 10: Source Metadata Preservation
 * Validates: Requirements 6.2, 6.3
 * 
 * Verifies that all transferred data preserves source metadata (source, sourceType, sourceId)
 * regardless of the input data or source type.
 * 
 * **Feature: ai-processing-transfer-to-lifecycle**
 * **Testing Framework: fast-check**
 * **Minimum Iterations: 100 per property**
 */

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { mapToLifecycleData, TransferDataItem, TransferOptions } from '../transferService';

// ============================================================================
// Property-Based Test Generators
// ============================================================================

/**
 * Generator for valid source types
 */
const arbitrarySourceType = (): fc.Arbitrary<string> =>
  fc.constantFrom('structuring', 'vectorization', 'semantic', 'ai_annotation');

/**
 * Generator for valid transfer data items
 * Ensures all required fields are present
 */
const arbitraryTransferDataItem = (): fc.Arbitrary<TransferDataItem> =>
  fc.record({
    id: fc.string({ minLength: 1, maxLength: 100 }),
    name: fc.string({ minLength: 1, maxLength: 200 }),
    content: fc.dictionary(fc.string(), fc.anything(), { minKeys: 1 }),
    metadata: fc.option(
      fc.dictionary(fc.string(), fc.anything())
    ),
  });

/**
 * Generator for transfer options
 */
const arbitraryTransferOptions = (): fc.Arbitrary<TransferOptions> =>
  fc.record({
    dataType: fc.option(fc.constantFrom('text', 'image', 'audio', 'video')),
    tags: fc.option(fc.array(fc.string({ minLength: 1, maxLength: 50 }), { maxLength: 10 })),
    remark: fc.option(fc.string({ maxLength: 500 })),
    qualityThreshold: fc.option(fc.float({ min: 0, max: 1 })),
    batchSize: fc.option(fc.integer({ min: 1, max: 100 })),
  });

// ============================================================================
// Property 10: Source Metadata Preservation
// ============================================================================

describe('Property 10: Source Metadata Preservation', () => {
  /**
   * **Validates: Requirements 6.2, 6.3**
   * 
   * For all transferred data, the metadata should contain source information
   * including source type (structuring/vectorization/semantic/ai_annotation)
   * and source ID.
   * 
   * This property verifies that:
   * 1. metadata.source is always 'ai_processing'
   * 2. metadata.sourceType matches the input sourceType
   * 3. metadata.sourceId matches the input data.id
   * 4. These fields are present regardless of other metadata or options
   */
  it('should preserve source metadata for all source types and data combinations', () => {
    fc.assert(
      fc.property(
        arbitrarySourceType(),
        arbitraryTransferDataItem(),
        arbitraryTransferOptions(),
        (sourceType, dataItem, options) => {
          // Execute the mapping
          const result = mapToLifecycleData(sourceType, dataItem, options);

          // Verify source metadata is preserved
          expect(result.metadata).toBeDefined();
          expect(result.metadata.source).toBe('ai_processing');
          expect(result.metadata.sourceType).toBe(sourceType);
          expect(result.metadata.sourceId).toBe(dataItem.id);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Verify source metadata is preserved even with empty options
   */
  it('should preserve source metadata even with empty options', () => {
    fc.assert(
      fc.property(
        arbitrarySourceType(),
        arbitraryTransferDataItem(),
        (sourceType, dataItem) => {
          const result = mapToLifecycleData(sourceType, dataItem, {});

          expect(result.metadata.source).toBe('ai_processing');
          expect(result.metadata.sourceType).toBe(sourceType);
          expect(result.metadata.sourceId).toBe(dataItem.id);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Verify source metadata is always present regardless of original metadata
   */
  it('should preserve source metadata regardless of original item metadata', () => {
    fc.assert(
      fc.property(
        arbitrarySourceType(),
        arbitraryTransferDataItem(),
        arbitraryTransferOptions(),
        (sourceType, dataItem, options) => {
          const result = mapToLifecycleData(sourceType, dataItem, options);

          // Source metadata should always be present
          expect(result.metadata.source).toBe('ai_processing');
          expect(result.metadata.sourceType).toBe(sourceType);
          expect(result.metadata.sourceId).toBe(dataItem.id);

          // These fields should exist regardless of what's in original metadata
          expect('source' in result.metadata).toBe(true);
          expect('sourceType' in result.metadata).toBe(true);
          expect('sourceId' in result.metadata).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Verify source metadata is preserved for structuring source type
   */
  it('should preserve source metadata for structuring data', () => {
    fc.assert(
      fc.property(
        arbitraryTransferDataItem(),
        arbitraryTransferOptions(),
        (dataItem, options) => {
          const result = mapToLifecycleData('structuring', dataItem, options);

          expect(result.metadata.source).toBe('ai_processing');
          expect(result.metadata.sourceType).toBe('structuring');
          expect(result.metadata.sourceId).toBe(dataItem.id);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Verify source metadata is preserved for vectorization source type
   */
  it('should preserve source metadata for vectorization data', () => {
    fc.assert(
      fc.property(
        arbitraryTransferDataItem(),
        arbitraryTransferOptions(),
        (dataItem, options) => {
          const result = mapToLifecycleData('vectorization', dataItem, options);

          expect(result.metadata.source).toBe('ai_processing');
          expect(result.metadata.sourceType).toBe('vectorization');
          expect(result.metadata.sourceId).toBe(dataItem.id);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Verify source metadata is preserved for semantic source type
   */
  it('should preserve source metadata for semantic data', () => {
    fc.assert(
      fc.property(
        arbitraryTransferDataItem(),
        arbitraryTransferOptions(),
        (dataItem, options) => {
          const result = mapToLifecycleData('semantic', dataItem, options);

          expect(result.metadata.source).toBe('ai_processing');
          expect(result.metadata.sourceType).toBe('semantic');
          expect(result.metadata.sourceId).toBe(dataItem.id);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Verify source metadata is preserved for ai_annotation source type
   */
  it('should preserve source metadata for ai_annotation data', () => {
    fc.assert(
      fc.property(
        arbitraryTransferDataItem(),
        arbitraryTransferOptions(),
        (dataItem, options) => {
          const result = mapToLifecycleData('ai_annotation', dataItem, options);

          expect(result.metadata.source).toBe('ai_processing');
          expect(result.metadata.sourceType).toBe('ai_annotation');
          expect(result.metadata.sourceId).toBe(dataItem.id);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Verify source metadata is preserved even for unknown source types
   */
  it('should preserve source metadata for unknown source types', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }),
        arbitraryTransferDataItem(),
        arbitraryTransferOptions(),
        (unknownSourceType, dataItem, options) => {
          const result = mapToLifecycleData(unknownSourceType, dataItem, options);

          expect(result.metadata.source).toBe('ai_processing');
          expect(result.metadata.sourceType).toBe(unknownSourceType);
          expect(result.metadata.sourceId).toBe(dataItem.id);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Verify source metadata fields are non-empty strings
   */
  it('should ensure source metadata fields are non-empty strings', () => {
    fc.assert(
      fc.property(
        arbitrarySourceType(),
        arbitraryTransferDataItem(),
        arbitraryTransferOptions(),
        (sourceType, dataItem, options) => {
          const result = mapToLifecycleData(sourceType, dataItem, options);

          // All source metadata fields should be non-empty strings
          expect(typeof result.metadata.source).toBe('string');
          expect(result.metadata.source.length).toBeGreaterThan(0);
          
          expect(typeof result.metadata.sourceType).toBe('string');
          expect(result.metadata.sourceType.length).toBeGreaterThan(0);
          
          expect(typeof result.metadata.sourceId).toBe('string');
          expect(result.metadata.sourceId.length).toBeGreaterThan(0);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Verify source metadata is preserved with various option combinations
   */
  it('should preserve source metadata with all option combinations', () => {
    fc.assert(
      fc.property(
        arbitrarySourceType(),
        arbitraryTransferDataItem(),
        fc.boolean(), // dataType present
        fc.boolean(), // tags present
        fc.boolean(), // remark present
        fc.boolean(), // qualityThreshold present
        (sourceType, dataItem, hasDataType, hasTags, hasRemark, hasQualityThreshold) => {
          const options: TransferOptions = {};
          if (hasDataType) options.dataType = 'text';
          if (hasTags) options.tags = ['tag1', 'tag2'];
          if (hasRemark) options.remark = 'test remark';
          if (hasQualityThreshold) options.qualityThreshold = 0.8;

          const result = mapToLifecycleData(sourceType, dataItem, options);

          // Source metadata should always be present regardless of options
          expect(result.metadata.source).toBe('ai_processing');
          expect(result.metadata.sourceType).toBe(sourceType);
          expect(result.metadata.sourceId).toBe(dataItem.id);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Verify source metadata is immutable (not affected by input mutations)
   */
  it('should preserve source metadata immutably', () => {
    fc.assert(
      fc.property(
        arbitrarySourceType(),
        arbitraryTransferDataItem(),
        arbitraryTransferOptions(),
        (sourceType, dataItem, options) => {
          // Store original values
          const originalId = dataItem.id;
          const originalSourceType = sourceType;

          // Map the data
          const result = mapToLifecycleData(sourceType, dataItem, options);

          // Verify metadata matches original values
          expect(result.metadata.sourceId).toBe(originalId);
          expect(result.metadata.sourceType).toBe(originalSourceType);

          // Mutate the input (simulating external changes)
          dataItem.id = 'mutated-id';

          // Result metadata should still have original values
          expect(result.metadata.sourceId).toBe(originalId);
          expect(result.metadata.sourceType).toBe(originalSourceType);
        }
      ),
      { numRuns: 100 }
    );
  });
});
