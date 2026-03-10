/**
 * Data Lifecycle Transfer API
 * Frontend API integration for data lifecycle transfer operations
 */

import apiClient from '@/services/api/client';
import type { AxiosError } from 'axios';

// ============================================================================
// Types
// ============================================================================

export interface DataAttributes {
  category: string;
  tags: string[];
  quality_score?: number;
  description?: string;
}

export interface TransferRecord {
  id: string;
  content: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface DataTransferRequest {
  source_type: 'structuring' | 'augmentation' | 'sync' | 'annotation' | 'ai_assistant' | 'manual';
  source_id: string;
  target_state: 'temp_stored' | 'in_sample_library' | 'annotation_pending';
  data_attributes: DataAttributes;
  records: TransferRecord[];
  request_approval?: boolean;
}

export interface TransferResponse {
  success: boolean;
  transferred_count?: number;
  lifecycle_ids?: string[];
  target_state?: string;
  message: string;
  navigation_url?: string;
  approval_required?: boolean;
  approval_id?: string;
  estimated_approval_time?: string;
}

export interface BatchTransferRequest {
  transfers: DataTransferRequest[];
}

export interface BatchTransferResponse {
  success: boolean;
  total_transfers: number;
  successful_transfers: number;
  failed_transfers: number;
  results: Array<{
    success: boolean;
    error?: string;
    [key: string]: any;
  }>;
}

export interface PermissionCheckParams {
  source_type?: string;
  target_state?: string;
  operation?: string;
}

export interface PermissionCheckResponse {
  allowed: boolean;
  requires_approval: boolean;
  user_role: string;
  reason?: string;
}

export interface Approval {
  id: string;
  transfer_request: DataTransferRequest;
  requester_id: string;
  requester_role: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  created_at: string;
  expires_at: string;
  approver_id?: string;
  approved_at?: string;
  comment?: string;
}

export interface ApprovalListParams {
  status?: 'pending' | 'approved' | 'rejected' | 'expired';
  user_id?: string;
  limit?: number;
  offset?: number;
}

export interface ApprovalListResponse {
  success: boolean;
  approvals: Approval[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface ApprovalActionRequest {
  approved: boolean;
  comment?: string;
}

// ============================================================================
// Error Types
// ============================================================================

export class DataTransferError extends Error {
  constructor(
    message: string,
    public code: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'DataTransferError';
  }
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get Accept-Language header based on current locale
 */
const getLanguageHeader = (): string => {
  const locale = localStorage.getItem('locale') || 'zh-CN';
  return locale.startsWith('zh') ? 'zh-CN' : 'en-US';
};

/**
 * Retry logic with exponential backoff
 */
async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 100
): Promise<T> {
  let lastError: Error;
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      const axiosError = error as AxiosError;
      
      // Don't retry on client errors (4xx) except 408 (timeout)
      if (axiosError.response?.status) {
        const status = axiosError.response.status;
        if (status >= 400 && status < 500 && status !== 408) {
          throw error;
        }
      }
      
      // Don't retry on last attempt
      if (attempt === maxRetries - 1) {
        throw error;
      }
      
      // Exponential backoff: 100ms, 200ms, 400ms
      const delay = baseDelay * Math.pow(2, attempt);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError!;
}

/**
 * Handle API errors and convert to DataTransferError
 */
function handleApiError(error: any): never {
  const axiosError = error as AxiosError<any>;
  
  if (axiosError.response) {
    const { status, data } = axiosError.response;
    const message = data?.message || data?.detail || 'Unknown error';
    const code = data?.error_code || 'UNKNOWN_ERROR';
    
    throw new DataTransferError(message, code, status, data);
  } else if (axiosError.request) {
    throw new DataTransferError(
      'Network error: No response from server',
      'NETWORK_ERROR'
    );
  } else {
    throw new DataTransferError(
      axiosError.message || 'Unknown error',
      'UNKNOWN_ERROR'
    );
  }
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Transfer data to data lifecycle system
 */
export async function transferDataAPI(
  request: DataTransferRequest
): Promise<TransferResponse> {
  try {
    const response = await retryWithBackoff(
      () => apiClient.post<TransferResponse>(
        '/api/data-lifecycle/transfer',
        request,
        {
          headers: {
            'Accept-Language': getLanguageHeader(),
          },
          timeout: 30000, // 30 seconds
        }
      )
    );
    
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
}

/**
 * Batch transfer multiple data sources
 */
export async function batchTransferDataAPI(
  requests: DataTransferRequest[]
): Promise<BatchTransferResponse> {
  try {
    const response = await retryWithBackoff(
      () => apiClient.post<BatchTransferResponse>(
        '/api/data-lifecycle/batch-transfer',
        { transfers: requests },
        {
          headers: {
            'Accept-Language': getLanguageHeader(),
          },
          timeout: 60000, // 60 seconds for batch operations
        }
      ),
      1 // Only retry once for batch operations
    );
    
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
}

/**
 * Check user permissions for data transfer operations
 */
export async function checkPermissionAPI(
  params: PermissionCheckParams
): Promise<PermissionCheckResponse> {
  try {
    const response = await apiClient.get<PermissionCheckResponse>(
      '/api/data-lifecycle/permissions/check',
      {
        params,
        headers: {
          'Accept-Language': getLanguageHeader(),
        },
      }
    );
    
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
}

/**
 * List approval requests
 */
export async function listApprovalsAPI(
  params?: ApprovalListParams
): Promise<ApprovalListResponse> {
  try {
    const response = await apiClient.get<ApprovalListResponse>(
      '/api/data-lifecycle/approvals',
      {
        params,
        headers: {
          'Accept-Language': getLanguageHeader(),
        },
      }
    );
    
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
}

/**
 * Approve or reject a transfer request
 */
export async function approveTransferAPI(
  approvalId: string,
  approved: boolean,
  comment?: string
): Promise<Approval> {
  try {
    const response = await apiClient.post<Approval>(
      `/api/data-lifecycle/approvals/${approvalId}/approve`,
      {
        approved,
        comment,
      },
      {
        headers: {
          'Accept-Language': getLanguageHeader(),
        },
      }
    );
    
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
}

// ============================================================================
// Export all functions
// ============================================================================

export default {
  transferDataAPI,
  batchTransferDataAPI,
  checkPermissionAPI,
  listApprovalsAPI,
  approveTransferAPI,
};
