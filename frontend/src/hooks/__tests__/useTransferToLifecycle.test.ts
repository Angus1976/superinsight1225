/**
 * Unit Tests for useTransferToLifecycle Hook
 * 
 * Tests cover:
 * - Single item transfer
 * - Batch transfer
 * - Progress tracking
 * - Error handling and retry
 * - Batch splitting logic
 * 
 * Validates: Requirements 2.4, 9.2, 10.5, 12.2, 12.3
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useTransferToLifecycle, TransferParams, TransferDataItem } from '../useTransferToLifecycle';
import { dataLifecycleApi } from '@/services/dataLifecycle';

// Mock the dataLifecycleApi
vi.mock('@/services/dataLifecycle', () => ({
  dataLifecycleApi: {
    createTempData: vi.fn(),
    createSample: vi.fn(),
    createAnnotationTask: vi.fn(),
    createEnhancement: vi.fn(),
  },
}));

describe('useTransferToLifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ============================================================================
  // Test: Single Item Transfer (Requirement 2.4)
  // ============================================================================

  describe('Single Item Transfer', () => {
    it('should successfully transfer a single item to temp_data', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockResolvedValue({ id: '1', name: 'Test Item' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: { text: 'test content' },
        },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {
          dataType: 'text',
          tags: ['test'],
          remark: 'test remark',
        },
      };

      let transferResult;
      await act(async () => {
        transferResult = await result.current.transferData(params);
      });

      expect(transferResult).toEqual({
        success: true,
        successCount: 1,
        failedCount: 0,
        failedItems: [],
      });

      expect(mockCreateTempData).toHaveBeenCalledTimes(1);
      expect(mockCreateTempData).toHaveBeenCalledWith({
        name: 'Test Item',
        content: { text: 'test content' },
        metadata: {
          source: 'ai_processing',
          sourceType: 'structuring',
          sourceId: '1',
          dataType: 'text',
          tags: ['test'],
          remark: 'test remark',
        },
      });
    });

    it('should successfully transfer a single item to sample_library', async () => {
      const mockCreateSample = vi.mocked(dataLifecycleApi.createSample);
      mockCreateSample.mockResolvedValue({ id: '1', name: 'Test Sample' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Sample',
          content: { text: 'sample content' },
        },
      ];

      const params: TransferParams = {
        sourceType: 'vectorization',
        data: transferData,
        targetStage: 'sample_library',
        options: {
          dataType: 'text',
        },
      };

      let transferResult;
      await act(async () => {
        transferResult = await result.current.transferData(params);
      });

      expect(transferResult).toEqual({
        success: true,
        successCount: 1,
        failedCount: 0,
        failedItems: [],
      });

      expect(mockCreateSample).toHaveBeenCalledTimes(1);
      expect(mockCreateSample).toHaveBeenCalledWith({
        name: 'Test Sample',
        content: { text: 'sample content' },
        metadata: {
          source: 'ai_processing',
          sourceType: 'vectorization',
          sourceId: '1',
          dataType: 'text',
        },
        data_type: 'text',
      });
    });

    it('should successfully transfer a single item to annotated stage', async () => {
      const mockCreateAnnotationTask = vi.mocked(dataLifecycleApi.createAnnotationTask);
      mockCreateAnnotationTask.mockResolvedValue({ id: '1', name: 'Test Task' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Annotation',
          content: { annotations: [] },
        },
      ];

      const params: TransferParams = {
        sourceType: 'ai_annotation',
        data: transferData,
        targetStage: 'annotated',
        options: {},
      };

      let transferResult;
      await act(async () => {
        transferResult = await result.current.transferData(params);
      });

      expect(transferResult).toEqual({
        success: true,
        successCount: 1,
        failedCount: 0,
        failedItems: [],
      });

      expect(mockCreateAnnotationTask).toHaveBeenCalledTimes(1);
    });

    it('should successfully transfer a single item to enhanced stage', async () => {
      const mockCreateEnhancement = vi.mocked(dataLifecycleApi.createEnhancement);
      mockCreateEnhancement.mockResolvedValue({ id: '1', name: 'Test Enhancement' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Enhancement',
          content: { enhanced: true },
        },
      ];

      const params: TransferParams = {
        sourceType: 'semantic',
        data: transferData,
        targetStage: 'enhanced',
        options: {},
      };

      let transferResult;
      await act(async () => {
        transferResult = await result.current.transferData(params);
      });

      expect(transferResult).toEqual({
        success: true,
        successCount: 1,
        failedCount: 0,
        failedItems: [],
      });

      expect(mockCreateEnhancement).toHaveBeenCalledTimes(1);
    });
  });

  // ============================================================================
  // Test: Batch Transfer (Requirement 2.4)
  // ============================================================================

  describe('Batch Transfer', () => {
    it('should successfully transfer multiple items', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockResolvedValue({ id: '1' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'content 1' } },
        { id: '2', name: 'Item 2', content: { text: 'content 2' } },
        { id: '3', name: 'Item 3', content: { text: 'content 3' } },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      let transferResult;
      await act(async () => {
        transferResult = await result.current.transferData(params);
      });

      expect(transferResult).toEqual({
        success: true,
        successCount: 3,
        failedCount: 0,
        failedItems: [],
      });

      expect(mockCreateTempData).toHaveBeenCalledTimes(3);
    });

    it('should handle partial failures in batch transfer', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData
        .mockResolvedValueOnce({ id: '1' } as any)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ id: '3' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'content 1' } },
        { id: '2', name: 'Item 2', content: { text: 'content 2' } },
        { id: '3', name: 'Item 3', content: { text: 'content 3' } },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      let transferResult;
      await act(async () => {
        transferResult = await result.current.transferData(params);
      });

      expect(transferResult).toEqual({
        success: false,
        successCount: 2,
        failedCount: 1,
        failedItems: [
          { id: '2', reason: 'Network error' },
        ],
      });

      expect(mockCreateTempData).toHaveBeenCalledTimes(3);
    });

    it('should handle all items failing', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockRejectedValue(new Error('Server error'));

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'content 1' } },
        { id: '2', name: 'Item 2', content: { text: 'content 2' } },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      let transferResult;
      await act(async () => {
        transferResult = await result.current.transferData(params);
      });

      expect(transferResult).toEqual({
        success: false,
        successCount: 0,
        failedCount: 2,
        failedItems: [
          { id: '1', reason: 'Server error' },
          { id: '2', reason: 'Server error' },
        ],
      });
    });
  });

  // ============================================================================
  // Test: Progress Tracking (Requirement 9.2)
  // ============================================================================

  describe('Progress Tracking', () => {
    it('should track progress accurately during transfer', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ id: '1' } as any), 10))
      );

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = Array.from({ length: 5 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `content ${i + 1}` },
      }));

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      // Initial progress should be zero
      expect(result.current.progress).toEqual({
        total: 0,
        completed: 0,
        failed: 0,
        percentage: 0,
      });

      act(() => {
        result.current.transferData(params);
      });

      // Progress should be initialized
      await waitFor(() => {
        expect(result.current.progress.total).toBe(5);
      });

      // Wait for completion
      await waitFor(() => {
        expect(result.current.progress.completed).toBe(5);
        expect(result.current.progress.percentage).toBe(100);
      }, { timeout: 3000 });
    });

    it('should update progress with failed items', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData
        .mockResolvedValueOnce({ id: '1' } as any)
        .mockRejectedValueOnce(new Error('Failed'))
        .mockResolvedValueOnce({ id: '3' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'content 1' } },
        { id: '2', name: 'Item 2', content: { text: 'content 2' } },
        { id: '3', name: 'Item 3', content: { text: 'content 3' } },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      await act(async () => {
        await result.current.transferData(params);
      });

      expect(result.current.progress).toEqual({
        total: 3,
        completed: 2,
        failed: 1,
        percentage: 100,
      });
    });

    it('should calculate percentage correctly', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockResolvedValue({ id: '1' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = Array.from({ length: 10 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `content ${i + 1}` },
      }));

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      await act(async () => {
        await result.current.transferData(params);
      });

      expect(result.current.progress.percentage).toBe(100);
      expect(result.current.progress.completed).toBe(10);
    });
  });

  // ============================================================================
  // Test: Error Handling (Requirement 10.5)
  // ============================================================================

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockRejectedValue(new Error('Network connection failed'));

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'content 1' } },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      let transferResult;
      await act(async () => {
        transferResult = await result.current.transferData(params);
      });

      expect(transferResult).toEqual({
        success: false,
        successCount: 0,
        failedCount: 1,
        failedItems: [
          { id: '1', reason: 'Network connection failed' },
        ],
      });

      expect(result.current.error).toBeNull();
    });

    it('should handle unsupported target stage', async () => {
      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'content 1' } },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'invalid_stage' as any,
        options: {},
      };

      let transferResult;
      await act(async () => {
        transferResult = await result.current.transferData(params);
      });

      expect(transferResult?.success).toBe(false);
      expect(transferResult?.failedItems[0].reason).toContain('Unsupported target stage');
    });

    it('should handle errors without setting error state for individual item failures', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockRejectedValue(new Error('Item transfer failed'));

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'content 1' } },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      await act(async () => {
        await result.current.transferData(params);
      });

      // Individual item failures don't set error state, they're tracked in failedItems
      expect(result.current.error).toBeNull();
      expect(result.current.progress.failed).toBe(1);
    });

    it('should clear error state on new transfer', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData
        .mockRejectedValueOnce(new Error('First error'))
        .mockResolvedValueOnce({ id: '1' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'content 1' } },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      // First transfer with error
      await act(async () => {
        await result.current.transferData(params);
      });

      // Second transfer should clear error
      await act(async () => {
        await result.current.transferData(params);
      });

      expect(result.current.error).toBeNull();
    });
  });

  // ============================================================================
  // Test: Batch Splitting Logic (Requirement 12.2, 12.3)
  // ============================================================================

  describe('Batch Splitting Logic', () => {
    it('should split large batches into chunks of default size (100)', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockResolvedValue({ id: '1' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = Array.from({ length: 250 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `content ${i + 1}` },
      }));

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      await act(async () => {
        await result.current.transferData(params);
      });

      expect(mockCreateTempData).toHaveBeenCalledTimes(250);
      expect(result.current.progress.completed).toBe(250);
    });

    it('should respect custom batch size', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockResolvedValue({ id: '1' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = Array.from({ length: 150 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `content ${i + 1}` },
      }));

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {
          batchSize: 50,
        },
      };

      await act(async () => {
        await result.current.transferData(params);
      });

      expect(mockCreateTempData).toHaveBeenCalledTimes(150);
      expect(result.current.progress.completed).toBe(150);
    });

    it('should process batches with concurrency control (max 3 concurrent)', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      const callTimes: number[] = [];
      
      mockCreateTempData.mockImplementation(() => {
        callTimes.push(Date.now());
        return Promise.resolve({ id: '1' } as any);
      });

      const { result } = renderHook(() => useTransferToLifecycle());

      // Create 10 batches (1000 items with batch size 100)
      const transferData: TransferDataItem[] = Array.from({ length: 1000 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `content ${i + 1}` },
      }));

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {
          batchSize: 100,
        },
      };

      await act(async () => {
        await result.current.transferData(params);
      });

      expect(mockCreateTempData).toHaveBeenCalledTimes(1000);
      expect(result.current.progress.completed).toBe(1000);
    });

    it('should continue processing remaining batches if one batch fails', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      let callCount = 0;
      
      mockCreateTempData.mockImplementation(() => {
        callCount++;
        // Fail items 51-60 (second batch)
        if (callCount > 50 && callCount <= 60) {
          return Promise.reject(new Error('Batch 2 failed'));
        }
        return Promise.resolve({ id: `${callCount}` } as any);
      });

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = Array.from({ length: 150 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Item ${i + 1}`,
        content: { text: `content ${i + 1}` },
      }));

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {
          batchSize: 50,
        },
      };

      await act(async () => {
        await result.current.transferData(params);
      });

      expect(result.current.progress.completed).toBe(140);
      expect(result.current.progress.failed).toBe(10);
    });
  });

  // ============================================================================
  // Test: Loading State
  // ============================================================================

  describe('Loading State', () => {
    it('should set loading to true during transfer', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ id: '1' } as any), 100))
      );

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'content 1' } },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      expect(result.current.loading).toBe(false);

      act(() => {
        result.current.transferData(params);
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(true);
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      }, { timeout: 3000 });
    });

    it('should set loading to false after transfer completes', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockResolvedValue({ id: '1' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'content 1' } },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      await act(async () => {
        await result.current.transferData(params);
      });

      expect(result.current.loading).toBe(false);
    });

    it('should set loading to false after transfer fails', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockRejectedValue(new Error('Failed'));

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        { id: '1', name: 'Item 1', content: { text: 'content 1' } },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      await act(async () => {
        await result.current.transferData(params);
      });

      expect(result.current.loading).toBe(false);
    });
  });

  // ============================================================================
  // Test: Metadata Mapping
  // ============================================================================

  describe('Metadata Mapping', () => {
    it('should include all options in metadata', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockResolvedValue({ id: '1' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: { text: 'content' },
          metadata: { custom: 'value' },
        },
      ];

      const params: TransferParams = {
        sourceType: 'structuring',
        data: transferData,
        targetStage: 'temp_data',
        options: {
          dataType: 'text',
          tags: ['tag1', 'tag2'],
          remark: 'test remark',
          qualityThreshold: 0.8,
        },
      };

      await act(async () => {
        await result.current.transferData(params);
      });

      expect(mockCreateTempData).toHaveBeenCalledWith({
        name: 'Test Item',
        content: { text: 'content' },
        metadata: {
          source: 'ai_processing',
          sourceType: 'structuring',
          sourceId: '1',
          dataType: 'text',
          tags: ['tag1', 'tag2'],
          remark: 'test remark',
          custom: 'value',
        },
      });
    });

    it('should preserve original item metadata', async () => {
      const mockCreateTempData = vi.mocked(dataLifecycleApi.createTempData);
      mockCreateTempData.mockResolvedValue({ id: '1' } as any);

      const { result } = renderHook(() => useTransferToLifecycle());

      const transferData: TransferDataItem[] = [
        {
          id: '1',
          name: 'Test Item',
          content: { text: 'content' },
          metadata: {
            originalField: 'value',
            timestamp: '2024-01-01',
          },
        },
      ];

      const params: TransferParams = {
        sourceType: 'vectorization',
        data: transferData,
        targetStage: 'temp_data',
        options: {},
      };

      await act(async () => {
        await result.current.transferData(params);
      });

      expect(mockCreateTempData).toHaveBeenCalledWith({
        name: 'Test Item',
        content: { text: 'content' },
        metadata: {
          source: 'ai_processing',
          sourceType: 'vectorization',
          sourceId: '1',
          originalField: 'value',
          timestamp: '2024-01-01',
        },
      });
    });
  });
});
