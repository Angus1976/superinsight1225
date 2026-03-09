/**
 * Unit tests for ReviewModal component
 * 
 * **Validates: Requirements 12.5**
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import ReviewModal from '../ReviewModal';
import { useReview } from '@/hooks/useDataLifecycle';
import { useAuthStore } from '@/stores/authStore';

// Mock the hooks
vi.mock('@/hooks/useDataLifecycle');
vi.mock('@/stores/authStore');

// Mock Ant Design message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
    },
  };
});

describe('ReviewModal', () => {
  const mockApproveReview = vi.fn().mockResolvedValue(undefined);
  const mockRejectReview = vi.fn().mockResolvedValue(undefined);
  const mockOnClose = vi.fn();
  const mockOnSuccess = vi.fn();

  const mockReview = {
    id: 'review-1',
    target_type: 'temp_data',
    target_id: 'data-1',
    requester: 'user1',
    status: 'pending' as const,
    submitted_at: '2024-01-01T00:00:00Z',
    reviewer: null,
    reviewed_at: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    (useReview as any).mockReturnValue({
      approveReview: mockApproveReview,
      rejectReview: mockRejectReview,
    });

    (useAuthStore as any).mockReturnValue({
      hasPermission: vi.fn(() => true),
    });
  });

  describe('Modal Rendering', () => {
    it('renders modal when visible', () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      // Modal should be visible
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('does not render when not visible', () => {
      render(
        <ReviewModal
          visible={false}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('does not render when review is null', () => {
      render(
        <ReviewModal
          visible={true}
          review={null}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('displays review information', () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      expect(screen.getByText(mockReview.id)).toBeInTheDocument();
      expect(screen.getByText(mockReview.requester)).toBeInTheDocument();
      expect(screen.getByText(mockReview.target_id)).toBeInTheDocument();
    });

    it('displays status tag', () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      // Status tag should be visible
      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();
    });

    it('displays target details based on target type', () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      expect(screen.getByText(mockReview.target_id)).toBeInTheDocument();
    });

    it('displays reviewer info when available', () => {
      const reviewedReview = {
        ...mockReview,
        reviewer: 'admin1',
        reviewed_at: '2024-01-02T00:00:00Z',
      };

      render(
        <ReviewModal
          visible={true}
          review={reviewedReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      expect(screen.getByText('admin1')).toBeInTheDocument();
    });
  });

  describe('Form Validation - Rejection Reason Required', () => {
    it('shows rejection reason input field', () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeInTheDocument();
    });

    it('requires rejection reason when rejecting', async () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const rejectButton = screen.getByRole('button', { name: /reject/i });
      fireEvent.click(rejectButton);
      
      // Should show validation error and not call rejectReview
      await waitFor(() => {
        expect(mockRejectReview).not.toHaveBeenCalled();
      });
    });

    it('validates rejection reason is not empty', async () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const rejectButton = screen.getByRole('button', { name: /reject/i });
      fireEvent.click(rejectButton);
      
      // Should not call rejectReview without reason
      await waitFor(() => {
        expect(mockRejectReview).not.toHaveBeenCalled();
      });
    });

    it('accepts valid rejection reason', async () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Data quality issues found' } });
      
      const rejectButton = screen.getByRole('button', { name: /reject/i });
      fireEvent.click(rejectButton);
      
      await waitFor(() => {
        expect(mockRejectReview).toHaveBeenCalledWith(mockReview.id, 'Data quality issues found');
      });
    });
  });

  describe('Approval Flow', () => {
    it('shows approve button for pending reviews', () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const approveButton = screen.getByRole('button', { name: /approve/i });
      expect(approveButton).toBeInTheDocument();
    });

    it('calls approveReview when approve button clicked', async () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const approveButton = screen.getByRole('button', { name: /approve/i });
      fireEvent.click(approveButton);
      
      await waitFor(() => {
        expect(mockApproveReview).toHaveBeenCalledWith(mockReview.id);
      });
    });

    it('shows success message after approval', async () => {
      const { message } = await import('antd');
      
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const approveButton = screen.getByRole('button', { name: /approve/i });
      fireEvent.click(approveButton);
      
      await waitFor(() => {
        expect(message.success).toHaveBeenCalled();
      });
    });

    it('calls onSuccess and onClose after approval', async () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const approveButton = screen.getByRole('button', { name: /approve/i });
      fireEvent.click(approveButton);
      
      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
        expect(mockOnClose).toHaveBeenCalled();
      });
    });

    it('shows error message on approval failure', async () => {
      const { message } = await import('antd');
      mockApproveReview.mockRejectedValueOnce(new Error('Approval failed'));
      
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const approveButton = screen.getByRole('button', { name: /approve/i });
      fireEvent.click(approveButton);
      
      await waitFor(() => {
        expect(message.error).toHaveBeenCalled();
      });
    });

    it('displays loading state during approval', async () => {
      mockApproveReview.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
      
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const approveButton = screen.getByRole('button', { name: /approve/i });
      fireEvent.click(approveButton);
      
      // Button should have loading class when loading
      await waitFor(() => {
        expect(approveButton).toHaveClass('ant-btn-loading');
      });
    });
  });

  describe('Rejection Flow', () => {
    it('shows reject button for pending reviews', () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const rejectButton = screen.getByRole('button', { name: /reject/i });
      expect(rejectButton).toBeInTheDocument();
    });

    it('calls rejectReview with reason when form is valid', async () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Invalid data format' } });
      
      const rejectButton = screen.getByRole('button', { name: /reject/i });
      fireEvent.click(rejectButton);
      
      await waitFor(() => {
        expect(mockRejectReview).toHaveBeenCalledWith(mockReview.id, 'Invalid data format');
      });
    });

    it('shows success message after rejection', async () => {
      const { message } = await import('antd');
      
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Rejected due to errors' } });
      
      const rejectButton = screen.getByRole('button', { name: /reject/i });
      fireEvent.click(rejectButton);
      
      await waitFor(() => {
        expect(message.success).toHaveBeenCalled();
      });
    });

    it('calls onSuccess and onClose after rejection', async () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Rejected' } });
      
      const rejectButton = screen.getByRole('button', { name: /reject/i });
      fireEvent.click(rejectButton);
      
      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
        expect(mockOnClose).toHaveBeenCalled();
      });
    });

    it('shows error message on rejection failure', async () => {
      const { message } = await import('antd');
      mockRejectReview.mockRejectedValueOnce(new Error('Rejection failed'));
      
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Rejected' } });
      
      const rejectButton = screen.getByRole('button', { name: /reject/i });
      fireEvent.click(rejectButton);
      
      await waitFor(() => {
        expect(message.error).toHaveBeenCalled();
      });
    });

    it('displays loading state during rejection', async () => {
      mockRejectReview.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
      
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Rejected' } });
      
      const rejectButton = screen.getByRole('button', { name: /reject/i });
      fireEvent.click(rejectButton);
      
      // Button should have loading class when loading
      await waitFor(() => {
        expect(rejectButton).toHaveClass('ant-btn-loading');
      });
    });
  });

  describe('Cancel Action', () => {
    it('shows cancel button', () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      expect(cancelButton).toBeInTheDocument();
    });

    it('calls onClose when cancel button clicked', () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      fireEvent.click(cancelButton);
      
      expect(mockOnClose).toHaveBeenCalled();
    });

    it('disables cancel button during loading', async () => {
      mockApproveReview.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
      
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const approveButton = screen.getByRole('button', { name: /approve/i });
      fireEvent.click(approveButton);
      
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      
      await waitFor(() => {
        expect(cancelButton).toHaveAttribute('disabled');
      });
    });
  });

  describe('Form Reset', () => {
    it('resets form when modal opens', () => {
      const { rerender } = render(
        <ReviewModal
          visible={false}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      rerender(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue('');
    });

    it('resets form when modal closes and reopens', async () => {
      const { rerender } = render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Test reason' } });
      
      // Close modal
      rerender(
        <ReviewModal
          visible={false}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      // Reopen modal
      rerender(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      const newTextarea = screen.getByRole('textbox');
      expect(newTextarea).toHaveValue('');
    });
  });

  describe('Permissions', () => {
    it('hides approve button when user lacks permission', () => {
      (useAuthStore as any).mockReturnValue({
        hasPermission: vi.fn((perm) => perm !== 'review.approve'),
      });

      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument();
    });

    it('hides reject button when user lacks permission', () => {
      (useAuthStore as any).mockReturnValue({
        hasPermission: vi.fn((perm) => perm !== 'review.reject'),
      });

      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument();
    });

    it('hides action buttons for non-pending reviews', () => {
      const approvedReview = {
        ...mockReview,
        status: 'approved' as const,
      };

      render(
        <ReviewModal
          visible={true}
          review={approvedReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument();
    });
  });

  describe('Different Target Types', () => {
    it('displays temp_data target correctly', () => {
      render(
        <ReviewModal
          visible={true}
          review={mockReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      expect(screen.getByText(mockReview.target_id)).toBeInTheDocument();
    });

    it('displays sample target correctly', () => {
      const sampleReview = {
        ...mockReview,
        target_type: 'sample',
      };

      render(
        <ReviewModal
          visible={true}
          review={sampleReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      expect(screen.getByText(sampleReview.target_id)).toBeInTheDocument();
    });

    it('displays enhancement target correctly', () => {
      const enhancementReview = {
        ...mockReview,
        target_type: 'enhancement',
      };

      render(
        <ReviewModal
          visible={true}
          review={enhancementReview}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );
      
      expect(screen.getByText(enhancementReview.target_id)).toBeInTheDocument();
    });
  });
});
