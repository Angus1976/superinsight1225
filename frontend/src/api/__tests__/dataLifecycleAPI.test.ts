/**
 * Data Lifecycle API Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  transferDataAPI,
  batchTransferDataAPI,
  checkPermissionAPI,
  listApprovalsAPI,
  approveTransferAPI,
  DataTransferError,
  type DataTransferRequest,
  type TransferResponse,
} from '../dataLifecycleAPI';

// Mock the API client
vi.mock('@/services/api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

// Import after mocking
const apiClient = await import('@/services/api/client').then(m => m.default);

describe('Data Lifecycle API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('transferDataAPI', () => {
    it('should successfully transfer data', async () => {
      const mockRequest: DataTransferRequest = {
        source_type: 'structuring',
        source_id: 'test-123',
        target_state: 'temp_stored',
        data_attributes: {
          category: 'test',
          tags: ['tag1'],
          quality_score: 0.9,
        },
        records: [
          {
            id: 'record-1',
            content: { field: 'value' },
          },
        ],
      };

      const mockResponse: TransferResponse = {
        success: true,
        transferred_count: 1,
        lifecycle_ids: ['lifecycle-1'],
        target_state: 'temp_stored',
        message: 'Transfer successful',
        navigation_url: '/data-lifecycle/temp-data',
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const result = await transferDataAPI(mockRequest);

      expect(result).toEqual(mockResponse);
      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/data-lifecycle/transfer',
        mockRequest,
        expect.objectContaining({
          headers: expect.objectContaining({
            'Accept-Language': expect.any(String),
          }),
          timeout: 30000,
        })
      );
    });

    it('should handle approval required response', async () => {
      const mockRequest: DataTransferRequest = {
        source_type: 'augmentation',
        source_id: 'test-456',
        target_state: 'in_sample_library',
        data_attributes: {
          category: 'test',
          tags: [],
        },
        records: [],
      };

      const mockResponse: TransferResponse = {
        success: true,
        approval_required: true,
        approval_id: 'approval-123',
        message: 'Transfer request submitted for approval',
        estimated_approval_time: '2-3 business days',
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const result = await transferDataAPI(mockRequest);

      expect(result.approval_required).toBe(true);
      expect(result.approval_id).toBe('approval-123');
    });

    it('should throw DataTransferError on API error', async () => {
      const mockRequest: DataTransferRequest = {
        source_type: 'structuring',
        source_id: 'test-789',
        target_state: 'temp_stored',
        data_attributes: {
          category: 'test',
          tags: [],
        },
        records: [],
      };

      vi.mocked(apiClient.post).mockRejectedValue({
        response: {
          status: 403,
          data: {
            error_code: 'PERMISSION_DENIED',
            message: 'You do not have permission',
          },
        },
      });

      await expect(transferDataAPI(mockRequest)).rejects.toThrow(DataTransferError);
    });
  });

  describe('checkPermissionAPI', () => {
    it('should check permissions successfully', async () => {
      const mockResponse = {
        allowed: true,
        requires_approval: false,
        user_role: 'data_manager',
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await checkPermissionAPI({
        source_type: 'structuring',
        target_state: 'temp_stored',
      });

      expect(result).toEqual(mockResponse);
      expect(apiClient.get).toHaveBeenCalledWith(
        '/api/data-lifecycle/permissions/check',
        expect.objectContaining({
          params: {
            source_type: 'structuring',
            target_state: 'temp_stored',
          },
        })
      );
    });
  });

  describe('listApprovalsAPI', () => {
    it('should list approvals successfully', async () => {
      const mockResponse = {
        success: true,
        approvals: [],
        total: 0,
        limit: 20,
        offset: 0,
        has_more: false,
      };

      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await listApprovalsAPI({ status: 'pending' });

      expect(result).toEqual(mockResponse);
      expect(apiClient.get).toHaveBeenCalledWith(
        '/api/data-lifecycle/approvals',
        expect.objectContaining({
          params: { status: 'pending' },
        })
      );
    });
  });

  describe('approveTransferAPI', () => {
    it('should approve transfer successfully', async () => {
      const mockApproval = {
        id: 'approval-123',
        status: 'approved',
        approver_id: 'user-456',
        approved_at: '2026-03-10T10:00:00Z',
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockApproval });

      const result = await approveTransferAPI('approval-123', true, 'Looks good');

      expect(result).toEqual(mockApproval);
      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/data-lifecycle/approvals/approval-123/approve',
        {
          approved: true,
          comment: 'Looks good',
        },
        expect.any(Object)
      );
    });
  });

  describe('batchTransferDataAPI', () => {
    it('should batch transfer successfully', async () => {
      const mockRequests: DataTransferRequest[] = [
        {
          source_type: 'structuring',
          source_id: 'test-1',
          target_state: 'temp_stored',
          data_attributes: { category: 'test', tags: [] },
          records: [],
        },
      ];

      const mockResponse = {
        success: true,
        total_transfers: 1,
        successful_transfers: 1,
        failed_transfers: 0,
        results: [{ success: true }],
      };

      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const result = await batchTransferDataAPI(mockRequests);

      expect(result).toEqual(mockResponse);
      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/data-lifecycle/batch-transfer',
        { transfers: mockRequests },
        expect.objectContaining({
          timeout: 60000,
        })
      );
    });
  });
});
