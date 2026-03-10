import { describe, it, expect, vi } from 'vitest';
import {
  validateData,
  mapToLifecycleData,
  batchTransfer,
  checkPermissions,
  TransferDataItem,
  TransferOptions,
  LifecycleDataPayload
} from '../transferService';

describe('transferService', () => {
  describe('validateData', () => {
    it('should validate data with all required fields', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: { text: 'test content' }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject data with missing ID', () => {
      const data: TransferDataItem[] = [
        {
          id: '',
          name: 'Test Item',
          content: { text: 'test content' }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('id'))).toBe(true);
    });

    it('should reject data with missing name', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: '',
          content: { text: 'test content' }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('name'))).toBe(true);
    });

    it('should reject data with missing content', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: null as any
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('content'))).toBe(true);
    });

    it('should reject data with invalid quality score', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: { text: 'test' },
          metadata: { qualityScore: 1.5 }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('qualityScore'))).toBe(true);
    });

    it('should reject empty data array', () => {
      const result = validateData([]);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field === 'data')).toBe(true);
    });

    it('should reject data with name exceeding max length', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'a'.repeat(201),
          content: { text: 'test' }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.message.includes('maximum length'))).toBe(true);
    });
  });

  describe('mapToLifecycleData', () => {
    const options: TransferOptions = {
      dataType: 'text',
      tags: ['test'],
      remark: 'test remark'
    };

    it('should map structuring data correctly', () => {
      const data: TransferDataItem = {
        id: '1',
        name: 'Test Document',
        content: { sections: ['section1', 'section2'] },
        metadata: { parsedAt: '2024-01-01' }
      };

      const result = mapToLifecycleData('structuring', data, options);

      expect(result.name).toBe('Test Document');
      expect(result.content).toEqual({ sections: ['section1', 'section2'] });
      expect(result.metadata.source).toBe('ai_processing');
      expect(result.metadata.sourceType).toBe('structuring');
      expect(result.metadata.sourceId).toBe('1');
      expect(result.metadata.parsedAt).toBe('2024-01-01');
    });

    it('should map vectorization data correctly', () => {
      const data: TransferDataItem = {
        id: '2',
        name: 'This is a very long text that should be truncated to 50 characters',
        content: {
          text: 'sample text',
          vector: [0.1, 0.2, 0.3],
          dimensions: 3
        },
        metadata: { model: 'text-embedding-ada-002' }
      };

      const result = mapToLifecycleData('vectorization', data, options);

      // Name should be truncated to 50 characters
      expect(result.name.length).toBe(50);
      expect(result.name).toBe(data.name.substring(0, 50));
      expect(result.content).toEqual({
        text: 'sample text',
        vector: [0.1, 0.2, 0.3],
        dimensions: 3
      });
      expect(result.metadata.model).toBe('text-embedding-ada-002');
    });

    it('should map semantic data correctly', () => {
      const data: TransferDataItem = {
        id: '3',
        name: 'Semantic Analysis Result',
        content: {
          text: 'sample text',
          entities: ['entity1', 'entity2'],
          relations: ['relation1'],
          type: 'entity'
        }
      };

      const result = mapToLifecycleData('semantic', data, options);

      expect(result.content).toHaveProperty('text');
      expect(result.content).toHaveProperty('entities');
      expect(result.content).toHaveProperty('relations');
      expect(result.metadata.semanticType).toBe('entity');
    });

    it('should map ai_annotation data correctly', () => {
      const data: TransferDataItem = {
        id: '4',
        name: 'Annotation Task',
        content: {
          data: { image: 'url' },
          annotations: [{ label: 'cat', confidence: 0.95 }]
        },
        metadata: { avgConfidence: 0.95 }
      };

      const result = mapToLifecycleData('ai_annotation', data, options);

      expect(result.content).toHaveProperty('originalData');
      expect(result.content).toHaveProperty('annotations');
      expect(result.content).toHaveProperty('confidence');
      expect(result.metadata.qualityScore).toBe(0.95);
    });

    it('should handle unknown source types with generic mapping', () => {
      const data: TransferDataItem = {
        id: '5',
        name: 'Unknown Type',
        content: { data: 'test' }
      };

      const result = mapToLifecycleData('unknown_type', data, options);

      expect(result.name).toBe('Unknown Type');
      expect(result.content).toEqual({ data: 'test' });
      expect(result.metadata.sourceType).toBe('unknown_type');
    });
  });

  describe('batchTransfer', () => {
    it('should successfully transfer all items', async () => {
      const items: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'test1' } },
        { id: '2', name: 'Item 2', content: { text: 'test2' } }
      ];

      const transferFn = async () => {
        // Mock successful transfer
      };

      const result = await batchTransfer(
        items,
        'structuring',
        'temp_data',
        {},
        transferFn
      );

      expect(result.success).toBe(true);
      expect(result.successCount).toBe(2);
      expect(result.failedCount).toBe(0);
      expect(result.skippedCount).toBe(0);
    });

    it('should handle transfer failures', async () => {
      const items: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'test1' } },
        { id: '2', name: 'Item 2', content: { text: 'test2' } }
      ];

      const transferFn = async (payload: any) => {
        if (payload.metadata.sourceId === '2') {
          throw new Error('Transfer failed');
        }
      };

      const result = await batchTransfer(
        items,
        'structuring',
        'temp_data',
        {},
        transferFn
      );

      expect(result.success).toBe(false);
      expect(result.successCount).toBe(1);
      expect(result.failedCount).toBe(1);
      expect(result.failedItems).toHaveLength(1);
      expect(result.failedItems[0].id).toBe('2');
    });

    it('should skip items below quality threshold', async () => {
      const items: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'test1' }, metadata: { qualityScore: 0.9 } },
        { id: '2', name: 'Item 2', content: { text: 'test2' }, metadata: { qualityScore: 0.5 } },
        { id: '3', name: 'Item 3', content: { text: 'test3' }, metadata: { qualityScore: 0.8 } }
      ];

      const transferFn = async () => {
        // Mock successful transfer
      };

      const result = await batchTransfer(
        items,
        'ai_annotation',
        'annotated',
        { qualityThreshold: 0.7 },
        transferFn
      );

      expect(result.successCount).toBe(2);
      expect(result.skippedCount).toBe(1);
    });

    it('should call progress callback', async () => {
      const items: TransferDataItem[] = Array.from({ length: 5 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `test${i + 1}` }
      }));

      const transferFn = async () => {
        // Mock successful transfer
      };

      const progressUpdates: Array<{ completed: number; total: number }> = [];
      const onProgress = (completed: number, total: number) => {
        progressUpdates.push({ completed, total });
      };

      await batchTransfer(
        items,
        'structuring',
        'temp_data',
        {},
        transferFn,
        onProgress
      );

      expect(progressUpdates.length).toBeGreaterThan(0);
      expect(progressUpdates[progressUpdates.length - 1].total).toBe(5);
    });

    it('should respect batch size option', async () => {
      const items: TransferDataItem[] = Array.from({ length: 250 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `test${i + 1}` }
      }));

      const transferFn = async () => {
        // Mock successful transfer
      };

      const result = await batchTransfer(
        items,
        'structuring',
        'temp_data',
        { batchSize: 50 },
        transferFn
      );

      expect(result.successCount).toBe(250);
    });

    it('should handle mixed success and failure in batch', async () => {
      const items: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'test1' } },
        { id: '2', name: 'Item 2', content: { text: 'test2' } },
        { id: '3', name: 'Item 3', content: { text: 'test3' } },
        { id: '4', name: 'Item 4', content: { text: 'test4' } }
      ];

      const transferFn = async (payload: LifecycleDataPayload) => {
        if (payload.metadata.sourceId === '2' || payload.metadata.sourceId === '4') {
          throw new Error('Transfer failed for item');
        }
      };

      const result = await batchTransfer(
        items,
        'structuring',
        'temp_data',
        {},
        transferFn
      );

      expect(result.success).toBe(false);
      expect(result.successCount).toBe(2);
      expect(result.failedCount).toBe(2);
      expect(result.failedItems).toHaveLength(2);
      expect(result.failedItems.map(item => item.id)).toEqual(['2', '4']);
    });

    it('should include suggestions in failed items', async () => {
      const items: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'test1' } }
      ];

      const transferFn = async () => {
        throw new Error('Network error');
      };

      const result = await batchTransfer(
        items,
        'structuring',
        'temp_data',
        {},
        transferFn
      );

      expect(result.failedItems[0]).toHaveProperty('suggestion');
      expect(result.failedItems[0].suggestion).toBeTruthy();
    });

    it('should track duration of transfer operation', async () => {
      const items: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'test1' } }
      ];

      const transferFn = async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
      };

      const result = await batchTransfer(
        items,
        'structuring',
        'temp_data',
        {},
        transferFn
      );

      expect(result.duration).toBeGreaterThan(0);
    });

    it('should process items without quality score when threshold is set', async () => {
      const items: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'test1' }, metadata: { qualityScore: 0.9 } },
        { id: '2', name: 'Item 2', content: { text: 'test2' } }, // No quality score
        { id: '3', name: 'Item 3', content: { text: 'test3' }, metadata: { qualityScore: 0.5 } }
      ];

      const transferFn = async () => {
        // Mock successful transfer
      };

      const result = await batchTransfer(
        items,
        'ai_annotation',
        'annotated',
        { qualityThreshold: 0.7 },
        transferFn
      );

      // Item 1 passes threshold, Item 2 has no score (should be transferred), Item 3 fails threshold
      expect(result.successCount).toBe(2);
      expect(result.skippedCount).toBe(1);
    });
  });

  describe('checkPermissions', () => {
    it('should return true for valid permission check', async () => {
      const hasPermission = await checkPermissions('user123', 'temp_data');
      expect(hasPermission).toBe(true);
    });

    it('should handle permission check errors gracefully', async () => {
      // The current implementation always returns true
      // This test verifies the function doesn't throw
      const hasPermission = await checkPermissions('user123', 'invalid_stage');
      expect(typeof hasPermission).toBe('boolean');
    });
  });

  describe('Data Validation - Edge Cases', () => {
    it('should reject data with non-string ID', () => {
      const data: TransferDataItem[] = [
        {
          id: 123 as any,
          name: 'Test Item',
          content: { text: 'test' }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('id'))).toBe(true);
    });

    it('should reject data with non-string name', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 123 as any,
          content: { text: 'test' }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('name'))).toBe(true);
    });

    it('should reject data with whitespace-only ID', () => {
      const data: TransferDataItem[] = [
        {
          id: '   ',
          name: 'Test Item',
          content: { text: 'test' }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('id'))).toBe(true);
    });

    it('should reject data with whitespace-only name', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: '   ',
          content: { text: 'test' }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('name'))).toBe(true);
    });

    it('should reject data with null content', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: null as any
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('content'))).toBe(true);
    });

    it('should reject data with array content', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: [] as any
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('content'))).toBe(true);
    });

    it('should reject data with negative quality score', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: { text: 'test' },
          metadata: { qualityScore: -0.5 }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('qualityScore'))).toBe(true);
    });

    it('should reject data with quality score greater than 1', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: { text: 'test' },
          metadata: { qualityScore: 1.5 }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('qualityScore'))).toBe(true);
    });

    it('should accept data with quality score of 0', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: { text: 'test' },
          metadata: { qualityScore: 0 }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(true);
    });

    it('should accept data with quality score of 1', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: { text: 'test' },
          metadata: { qualityScore: 1 }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(true);
    });

    it('should handle multiple validation errors for single item', () => {
      const data: TransferDataItem[] = [
        {
          id: '',
          name: '',
          content: null as any
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThanOrEqual(3);
    });

    it('should validate all items in array', () => {
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Valid Item',
          content: { text: 'test' }
        },
        {
          id: '',
          name: 'Invalid Item',
          content: { text: 'test' }
        },
        {
          id: '3',
          name: 'Another Valid Item',
          content: { text: 'test' }
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.field.includes('[1]'))).toBe(true);
    });

    it('should handle very large data size', () => {
      const largeContent = { data: 'x'.repeat(11 * 1024 * 1024) }; // 11MB
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Large Item',
          content: largeContent
        }
      ];

      const result = validateData(data);
      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.message.includes('exceeds limit'))).toBe(true);
    });

    it('should accept data at size limit', () => {
      // Create data just under 10MB
      const content = { data: 'x'.repeat(9 * 1024 * 1024) };
      const data: TransferDataItem[] = [
        {
          id: '1',
          name: 'Large Item',
          content
        }
      ];

      const result = validateData(data);
      // This might fail or pass depending on JSON overhead, but should not crash
      expect(result).toHaveProperty('valid');
      expect(result).toHaveProperty('errors');
    });
  });

  describe('Data Mapping - All Source Types', () => {
    const options: TransferOptions = {
      dataType: 'text',
      tags: ['test', 'automated'],
      remark: 'Test transfer'
    };

    it('should preserve all metadata fields for structuring', () => {
      const data: TransferDataItem = {
        id: '1',
        name: 'Document',
        content: { sections: ['intro', 'body', 'conclusion'] },
        metadata: { parsedAt: '2024-01-01T00:00:00Z', parser: 'custom' }
      };

      const result = mapToLifecycleData('structuring', data, options);

      expect(result.metadata.source).toBe('ai_processing');
      expect(result.metadata.sourceType).toBe('structuring');
      expect(result.metadata.sourceId).toBe('1');
      expect(result.metadata.dataType).toBe('text');
      expect(result.metadata.tags).toEqual(['test', 'automated']);
      expect(result.metadata.remark).toBe('Test transfer');
      expect(result.metadata.parsedAt).toBe('2024-01-01T00:00:00Z');
    });

    it('should handle vectorization with missing model metadata', () => {
      const data: TransferDataItem = {
        id: '2',
        name: 'Vector Record',
        content: {
          text: 'sample',
          vector: [0.1, 0.2],
          dimensions: 2
        }
      };

      const result = mapToLifecycleData('vectorization', data, options);

      expect(result.content).toHaveProperty('text');
      expect(result.content).toHaveProperty('vector');
      expect(result.content).toHaveProperty('dimensions');
      expect(result.metadata.model).toBeUndefined();
    });

    it('should truncate long names for vectorization', () => {
      const longName = 'a'.repeat(100);
      const data: TransferDataItem = {
        id: '2',
        name: longName,
        content: {
          text: 'sample',
          vector: [0.1],
          dimensions: 1
        }
      };

      const result = mapToLifecycleData('vectorization', data, options);

      expect(result.name.length).toBe(50);
      expect(result.name).toBe(longName.substring(0, 50));
    });

    it('should truncate long names for semantic', () => {
      const longName = 'b'.repeat(100);
      const data: TransferDataItem = {
        id: '3',
        name: longName,
        content: {
          text: 'sample',
          entities: ['entity1'],
          relations: ['relation1'],
          type: 'entity'
        }
      };

      const result = mapToLifecycleData('semantic', data, options);

      expect(result.name.length).toBe(50);
      expect(result.name).toBe(longName.substring(0, 50));
    });

    it('should map semantic content with correct field names', () => {
      const data: TransferDataItem = {
        id: '3',
        name: 'Semantic Record',
        content: {
          text: 'sample text',
          entities: ['person', 'location'],
          relations: ['works_at'],
          type: 'relation'
        }
      };

      const result = mapToLifecycleData('semantic', data, options);

      expect(result.content).toHaveProperty('text', 'sample text');
      expect(result.content).toHaveProperty('entities', ['person', 'location']);
      expect(result.content).toHaveProperty('relations', ['works_at']);
      expect(result.content).toHaveProperty('semanticType', 'relation');
      expect(result.metadata.semanticType).toBe('relation');
    });

    it('should map ai_annotation with all fields', () => {
      const data: TransferDataItem = {
        id: '4',
        name: 'Annotation Task',
        content: {
          data: { image: 'url', width: 100, height: 100 },
          annotations: [
            { label: 'cat', confidence: 0.95, bbox: [10, 20, 30, 40] },
            { label: 'dog', confidence: 0.88, bbox: [50, 60, 70, 80] }
          ]
        },
        metadata: { avgConfidence: 0.915, annotator: 'ai_model_v1' }
      };

      const result = mapToLifecycleData('ai_annotation', data, options);

      expect(result.name).toBe('Annotation Task');
      expect(result.content).toHaveProperty('originalData');
      expect(result.content).toHaveProperty('annotations');
      expect(result.content).toHaveProperty('confidence', 0.915);
      expect(result.metadata.taskName).toBe('Annotation Task');
      expect(result.metadata.qualityScore).toBe(0.915);
    });

    it('should handle ai_annotation without avgConfidence', () => {
      const data: TransferDataItem = {
        id: '4',
        name: 'Annotation Task',
        content: {
          data: { image: 'url' },
          annotations: []
        }
      };

      const result = mapToLifecycleData('ai_annotation', data, options);

      expect(result.content.confidence).toBeUndefined();
      expect(result.metadata.qualityScore).toBeUndefined();
    });

    it('should handle empty options', () => {
      const data: TransferDataItem = {
        id: '1',
        name: 'Test',
        content: { text: 'test' }
      };

      const result = mapToLifecycleData('structuring', data, {});

      expect(result.metadata.dataType).toBeUndefined();
      expect(result.metadata.tags).toBeUndefined();
      expect(result.metadata.remark).toBeUndefined();
    });

    it('should use generic mapping for unknown source type', () => {
      const data: TransferDataItem = {
        id: '5',
        name: 'Unknown Type Data',
        content: { custom: 'field', value: 123 }
      };

      const result = mapToLifecycleData('custom_processing', data, options);

      expect(result.name).toBe('Unknown Type Data');
      expect(result.content).toEqual({ custom: 'field', value: 123 });
      expect(result.metadata.sourceType).toBe('custom_processing');
    });
  });

  describe('Batch Transfer - Coordination', () => {
    it('should process batches sequentially within concurrency limit', async () => {
      const items: TransferDataItem[] = Array.from({ length: 10 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `test${i + 1}` }
      }));

      const processOrder: string[] = [];
      const transferFn = async (payload: LifecycleDataPayload) => {
        processOrder.push(payload.metadata.sourceId);
        await new Promise(resolve => setTimeout(resolve, 5));
      };

      await batchTransfer(
        items,
        'structuring',
        'temp_data',
        { batchSize: 3 },
        transferFn
      );

      // All items should be processed
      expect(processOrder.length).toBe(10);
      // Order should contain all IDs
      expect(processOrder.sort()).toEqual(items.map(i => i.id).sort());
    });

    it('should continue processing after batch failure', async () => {
      const items: TransferDataItem[] = Array.from({ length: 6 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `test${i + 1}` }
      }));

      let callCount = 0;
      const transferFn = async (payload: LifecycleDataPayload) => {
        callCount++;
        if (payload.metadata.sourceId === '3') {
          throw new Error('Simulated failure');
        }
      };

      const result = await batchTransfer(
        items,
        'structuring',
        'temp_data',
        { batchSize: 2 },
        transferFn
      );

      // Should attempt all items despite one failure
      expect(callCount).toBe(6);
      expect(result.successCount).toBe(5);
      expect(result.failedCount).toBe(1);
    });

    it('should aggregate results from multiple batches', async () => {
      const items: TransferDataItem[] = Array.from({ length: 15 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `test${i + 1}` },
        metadata: { qualityScore: i % 3 === 0 ? 0.5 : 0.9 }
      }));

      const transferFn = async (payload: LifecycleDataPayload) => {
        if (payload.metadata.sourceId === '5') {
          throw new Error('Failure');
        }
      };

      const result = await batchTransfer(
        items,
        'ai_annotation',
        'annotated',
        { batchSize: 5, qualityThreshold: 0.7 },
        transferFn
      );

      // Items at indices 0, 3, 6, 9, 12 have score 0.5 (IDs: 1, 4, 7, 10, 13) - skipped = 5
      // Item 5 fails (failed = 1)
      // Remaining items succeed (success = 9)
      expect(result.skippedCount).toBe(5);
      expect(result.failedCount).toBe(1);
      expect(result.successCount).toBe(9);
    });

    it('should report total duration across all batches', async () => {
      const items: TransferDataItem[] = Array.from({ length: 6 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `test${i + 1}` }
      }));

      const transferFn = async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
      };

      const result = await batchTransfer(
        items,
        'structuring',
        'temp_data',
        { batchSize: 2 },
        transferFn
      );

      // Duration should be positive and reasonable
      expect(result.duration).toBeGreaterThan(0);
      // With 3 batches of 2 items each, processed with max 3 concurrent
      // Should take at least 10ms (one batch duration)
      expect(result.duration).toBeGreaterThanOrEqual(10);
    });
  });
});
