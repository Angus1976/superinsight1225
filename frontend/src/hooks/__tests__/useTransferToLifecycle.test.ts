/**
 * Unit Tests for useTransferToLifecycle Hook
 *
 * This hook uses a unified backend endpoint (`transferDataAPI`) to support
 * permission checks and approval workflows. Legacy per-stage create APIs are no
 * longer called by the hook, so tests validate the new contract and mapping.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  useTransferToLifecycle,
  type TransferParams,
  type TransferDataItem,
} from '../useTransferToLifecycle';
import { transferDataAPI } from '@/api/dataLifecycleAPI';

vi.mock('@/api/dataLifecycleAPI', () => ({
  transferDataAPI: vi.fn(),
}));

describe('useTransferToLifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('maps request and returns success counts', async () => {
    vi.mocked(transferDataAPI).mockResolvedValueOnce({
      success: true,
      transferred_count: 2,
      message: 'ok',
    } as any);

    const { result } = renderHook(() => useTransferToLifecycle());

    const data: TransferDataItem[] = [
      { id: '1', name: 'Item 1', content: { text: 'a' } },
      { id: '2', name: 'Item 2', content: { text: 'b' } },
    ];

    const params: TransferParams = {
      sourceType: 'structuring',
      data,
      targetStage: 'temp_data',
      options: { dataType: 'text', tags: ['t1'], remark: 'r1', qualityThreshold: 0.9 },
    };

    const transferResult = await act(async () => {
      return await result.current.transferData(params);
    });

    expect(transferResult).toEqual({
      success: true,
      successCount: 2,
      failedCount: 0,
      failedItems: [],
    });

    expect(vi.mocked(transferDataAPI)).toHaveBeenCalledTimes(1);
    const request = vi.mocked(transferDataAPI).mock.calls[0][0] as any;
    expect(request.source_type).toBe('structuring');
    expect(request.target_state).toBe('temp_stored');
    expect(request.data_attributes).toMatchObject({
      category: 'text',
      tags: ['t1'],
      quality_score: 0.9,
      description: 'r1',
    });
    expect(request.records).toHaveLength(2);
    expect(request.records[0]).toMatchObject({
      id: '1',
      content: { text: 'a' },
      metadata: expect.objectContaining({ name: 'Item 1', sourceType: 'structuring' }),
    });
  });

  it('returns failed items when API throws', async () => {
    vi.mocked(transferDataAPI).mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useTransferToLifecycle());

    const params: TransferParams = {
      sourceType: 'semantic',
      data: [{ id: '1', name: 'Item 1', content: { x: 1 } }],
      targetStage: 'sample_library',
      options: {},
    };

    const transferResult = await act(async () => {
      return await result.current.transferData(params);
    });

    expect(transferResult.success).toBe(false);
    expect(transferResult.successCount).toBe(0);
    expect(transferResult.failedCount).toBe(1);
    expect(transferResult.failedItems[0]).toMatchObject({ id: '1' });
    expect(result.current.error).toBe('Network error');
  });
});

