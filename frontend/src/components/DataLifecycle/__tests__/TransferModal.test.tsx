/**
 * TransferModal Component Tests
 * 
 * Tests for the TransferModal component including:
 * - Rendering and form fields
 * - Permission checking
 * - Form validation
 * - Submit success/approval/error scenarios
 * - i18n integration
 * - Modal open/close behavior
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { message } from 'antd';
import { TransferModal } from '../TransferModal';
import * as dataLifecycleAPI from '@/api/dataLifecycleAPI';

// Mock the API
vi.mock('@/api/dataLifecycleAPI');

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      const translations: Record<string, string> = {
        'transfer.modal.title': 'Data Transfer Configuration',
        'transfer.actions.confirm': 'Confirm Transfer',
        'transfer.actions.cancel': 'Cancel',
        'transfer.summary.title': 'Data Summary',
        'transfer.summary.source': 'Source',
        'transfer.summary.recordCount': 'Record Count',
        'transfer.sourceTypes.structuring': 'Data Structuring',
        'transfer.fields.targetState': 'Target State',
        'transfer.fields.targetStateRequired': 'Please select target state',
        'transfer.fields.category': 'Data Category',
        'transfer.fields.categoryPlaceholder': 'e.g., Product Information',
        'transfer.fields.tags': 'Tags',
        'transfer.fields.tagsPlaceholder': 'Add tag',
        'transfer.fields.qualityScore': 'Quality Score',
        'transfer.fields.description': 'Description',
        'transfer.fields.descriptionPlaceholder': 'Enter data description (optional)',
        'transfer.targetStates.temp_stored': 'Temporary Storage',
        'transfer.targetStates.in_sample_library': 'Sample Library',
        'transfer.targetStates.annotation_pending': 'Pending Annotation',
        'transfer.permissions.requiresApproval': '(Requires Approval)',
        'transfer.permissions.noPermission': '(No Permission)',
        'transfer.validation.targetStateRequired': 'Please select target state',
        'transfer.validation.categoryRequired': 'Please enter category',
        'transfer.validation.invalidQualityScore': 'Quality score must be between 0 and 1',
        'transfer.messages.success': `Successfully transferred ${params?.count} records to ${params?.state}`,
        'transfer.messages.approvalRequired': 'Transfer request submitted for approval',
        'transfer.messages.error': `Transfer failed: ${params?.error}`,
        'transfer.messages.internalError': 'Internal server error',
        'common.status.loading': 'Loading...',
        'common.messages.networkError': 'Network error, please try again later',
      };
      return translations[key] || key;
    },
  }),
}));

// Mock message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
    },
  };
});

describe('TransferModal', () => {
  const mockOnClose = vi.fn();
  const mockOnSuccess = vi.fn();
  
  const defaultProps = {
    visible: true,
    onClose: mockOnClose,
    sourceType: 'structuring' as const,
    sourceId: 'test-source-123',
    records: [
      {
        id: 'record-1',
        content: { name: 'Test Record 1' },
        metadata: {},
      },
      {
        id: 'record-2',
        content: { name: 'Test Record 2' },
        metadata: {},
      },
    ],
    onSuccess: mockOnSuccess,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default permission check response
    vi.mocked(dataLifecycleAPI.checkPermissionAPI).mockResolvedValue({
      allowed: true,
      requires_approval: false,
      user_role: 'data_manager',
    });
  });

  // ============================================================================
  // Rendering Tests
  // ============================================================================

  it('should render modal with title', async () => {
    render(<TransferModal {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Data Transfer Configuration')).toBeInTheDocument();
    });
  });

  it('should render all form fields', async () => {
    render(<TransferModal {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByLabelText('Target State')).toBeInTheDocument();
      expect(screen.getByLabelText('Data Category')).toBeInTheDocument();
      expect(screen.getByLabelText('Tags')).toBeInTheDocument();
      expect(screen.getByLabelText('Quality Score')).toBeInTheDocument();
      expect(screen.getByLabelText('Description')).toBeInTheDocument();
    });
  });

  it('should display data summary', async () => {
    render(<TransferModal {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Data Summary')).toBeInTheDocument();
      expect(screen.getByText(/Data Structuring/)).toBeInTheDocument();
      expect(screen.getByText(/2/)).toBeInTheDocument(); // Record count
    });
  });

  // ============================================================================
  // Permission Checking Tests
  // ============================================================================

  it('should check permissions for all target states on mount', async () => {
    render(<TransferModal {...defaultProps} />);
    
    await waitFor(() => {
      expect(dataLifecycleAPI.checkPermissionAPI).toHaveBeenCalledTimes(3);
      expect(dataLifecycleAPI.checkPermissionAPI).toHaveBeenCalledWith({
        source_type: 'structuring',
        target_state: 'temp_stored',
      });
      expect(dataLifecycleAPI.checkPermissionAPI).toHaveBeenCalledWith({
        source_type: 'structuring',
        target_state: 'in_sample_library',
      });
      expect(dataLifecycleAPI.checkPermissionAPI).toHaveBeenCalledWith({
        source_type: 'structuring',
        target_state: 'annotation_pending',
      });
    });
  });

  it('should disable options without permission', async () => {
    vi.mocked(dataLifecycleAPI.checkPermissionAPI)
      .mockResolvedValueOnce({ allowed: true, requires_approval: false })
      .mockResolvedValueOnce({ allowed: false, requires_approval: false })
      .mockResolvedValueOnce({ allowed: true, requires_approval: true });
    
    render(<TransferModal {...defaultProps} />);
    
    await waitFor(() => {
      const select = screen.getByLabelText('Target State');
      fireEvent.mouseDown(select);
    });
    
    await waitFor(() => {
      expect(screen.getByText(/Temporary Storage/)).toBeInTheDocument();
      expect(screen.getByText(/Sample Library.*No Permission/)).toBeInTheDocument();
      expect(screen.getByText(/Pending Annotation.*Requires Approval/)).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Form Validation Tests
  // ============================================================================

  it('should validate required target state', async () => {
    render(<TransferModal {...defaultProps} />);
    
    await waitFor(() => {
      const confirmButton = screen.getByText('Confirm Transfer');
      fireEvent.click(confirmButton);
    });
    
    await waitFor(() => {
      expect(screen.getByText('Please select target state')).toBeInTheDocument();
    });
  });

  it('should validate required category', async () => {
    render(<TransferModal {...defaultProps} />);
    
    await waitFor(() => {
      const targetStateSelect = screen.getByLabelText('Target State');
      fireEvent.mouseDown(targetStateSelect);
    });
    
    await waitFor(() => {
      const option = screen.getByText('Temporary Storage');
      fireEvent.click(option);
    });
    
    const confirmButton = screen.getByText('Confirm Transfer');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(screen.getByText('Please enter category')).toBeInTheDocument();
    });
  });

  it('should validate quality score range', async () => {
    render(<TransferModal {...defaultProps} />);
    
    await waitFor(() => {
      const qualityScoreInput = screen.getByLabelText('Quality Score');
      fireEvent.change(qualityScoreInput, { target: { value: '1.5' } });
    });
    
    const confirmButton = screen.getByText('Confirm Transfer');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(screen.getByText('Quality score must be between 0 and 1')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Submit Tests
  // ============================================================================

  it('should submit successfully', async () => {
    const mockResponse = {
      success: true,
      transferred_count: 2,
      lifecycle_ids: ['id-1', 'id-2'],
      target_state: 'temp_stored',
      message: 'Success',
    };
    
    vi.mocked(dataLifecycleAPI.transferDataAPI).mockResolvedValue(mockResponse);
    
    render(<TransferModal {...defaultProps} />);
    
    // Fill form
    await waitFor(() => {
      const targetStateSelect = screen.getByLabelText('Target State');
      fireEvent.mouseDown(targetStateSelect);
    });
    
    await waitFor(() => {
      const option = screen.getByText('Temporary Storage');
      fireEvent.click(option);
    });
    
    const categoryInput = screen.getByLabelText('Data Category');
    fireEvent.change(categoryInput, { target: { value: 'Test Category' } });
    
    // Submit
    const confirmButton = screen.getByText('Confirm Transfer');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(dataLifecycleAPI.transferDataAPI).toHaveBeenCalledWith({
        source_type: 'structuring',
        source_id: 'test-source-123',
        target_state: 'temp_stored',
        data_attributes: {
          category: 'Test Category',
          tags: [],
          quality_score: 0.8,
          description: undefined,
        },
        records: defaultProps.records,
      });
      
      expect(message.success).toHaveBeenCalled();
      expect(mockOnSuccess).toHaveBeenCalledWith(mockResponse);
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('should handle approval required', async () => {
    const mockResponse = {
      success: true,
      approval_required: true,
      approval_id: 'approval-123',
      message: 'Approval required',
      estimated_approval_time: '2-3 business days',
    };
    
    vi.mocked(dataLifecycleAPI.transferDataAPI).mockResolvedValue(mockResponse);
    
    render(<TransferModal {...defaultProps} />);
    
    // Fill and submit form
    await waitFor(() => {
      const targetStateSelect = screen.getByLabelText('Target State');
      fireEvent.mouseDown(targetStateSelect);
    });
    
    await waitFor(() => {
      const option = screen.getByText('Temporary Storage');
      fireEvent.click(option);
    });
    
    const categoryInput = screen.getByLabelText('Data Category');
    fireEvent.change(categoryInput, { target: { value: 'Test Category' } });
    
    const confirmButton = screen.getByText('Confirm Transfer');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(message.info).toHaveBeenCalled();
      expect(mockOnSuccess).toHaveBeenCalledWith(mockResponse);
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('should handle transfer error', async () => {
    const mockError = new dataLifecycleAPI.DataTransferError(
      'Permission denied',
      'PERMISSION_DENIED',
      403
    );
    
    vi.mocked(dataLifecycleAPI.transferDataAPI).mockRejectedValue(mockError);
    
    render(<TransferModal {...defaultProps} />);
    
    // Fill and submit form
    await waitFor(() => {
      const targetStateSelect = screen.getByLabelText('Target State');
      fireEvent.mouseDown(targetStateSelect);
    });
    
    await waitFor(() => {
      const option = screen.getByText('Temporary Storage');
      fireEvent.click(option);
    });
    
    const categoryInput = screen.getByLabelText('Data Category');
    fireEvent.change(categoryInput, { target: { value: 'Test Category' } });
    
    const confirmButton = screen.getByText('Confirm Transfer');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(message.error).toHaveBeenCalled();
      expect(mockOnSuccess).not.toHaveBeenCalled();
      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  // ============================================================================
  // Modal Behavior Tests
  // ============================================================================

  it('should reset form when modal closes', async () => {
    const { rerender } = render(<TransferModal {...defaultProps} />);
    
    // Fill form
    await waitFor(() => {
      const categoryInput = screen.getByLabelText('Data Category');
      fireEvent.change(categoryInput, { target: { value: 'Test Category' } });
    });
    
    // Close modal
    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);
    
    expect(mockOnClose).toHaveBeenCalled();
    
    // Reopen modal
    rerender(<TransferModal {...defaultProps} visible={false} />);
    rerender(<TransferModal {...defaultProps} visible={true} />);
    
    await waitFor(() => {
      const categoryInput = screen.getByLabelText('Data Category') as HTMLInputElement;
      expect(categoryInput.value).toBe('');
    });
  });

  it('should not render when visible is false', () => {
    const { container } = render(<TransferModal {...defaultProps} visible={false} />);
    expect(container.querySelector('.ant-modal')).not.toBeInTheDocument();
  });
});
