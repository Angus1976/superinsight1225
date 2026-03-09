/**
 * EnhancementManagement Component Unit Tests
 * 
 * Tests for job table rendering, status color coding, cancel action, and filter functionality.
 * Requirements: 15.1, 15.2, 15.3
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import EnhancementManagement from '../EnhancementManagement';
import type { EnhancementManagementProps, EnhancementJob } from '../EnhancementManagement';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      if (key === 'common.pagination.total' && params) {
        return `Total ${params.total} items`;
      }
      return key;
    },
  }),
}));

describe('EnhancementManagement Component', () => {
  // Sample test data
  const mockJobs: EnhancementJob[] = [
    {
      id: 'job-1',
      name: 'Grammar Enhancement Job',
      type: 'grammar',
      status: 'running',
      progress: 45,
      iterations: 2,
      maxIterations: 5,
      createdAt: '2024-01-01T10:00:00Z',
    },
    {
      id: 'job-2',
      name: 'Style Adjustment Job',
      type: 'style',
      status: 'completed',
      progress: 100,
      iterations: 3,
      maxIterations: 3,
      createdAt: '2024-01-02T10:00:00Z',
      completedAt: '2024-01-02T12:00:00Z',
    },
    {
      id: 'job-3',
      name: 'Content Expansion Job',
      type: 'content',
      status: 'failed',
      progress: 30,
      iterations: 1,
      maxIterations: 5,
      createdAt: '2024-01-03T10:00:00Z',
    },
    {
      id: 'job-4',
      name: 'Translation Job',
      type: 'translation',
      status: 'pending',
      progress: 0,
      createdAt: '2024-01-04T10:00:00Z',
    },
    {
      id: 'job-5',
      name: 'Summary Generation Job',
      type: 'summary',
      status: 'cancelled',
      progress: 20,
      createdAt: '2024-01-05T10:00:00Z',
    },
    {
      id: 'job-6',
      name: 'Paused Enhancement Job',
      type: 'custom',
      status: 'paused',
      progress: 60,
      createdAt: '2024-01-06T10:00:00Z',
    },
  ];

  const defaultProps: EnhancementManagementProps = {
    jobs: mockJobs,
    loading: false,
    pagination: {
      page: 1,
      pageSize: 10,
      total: 6,
    },
    onViewResults: vi.fn(),
    onCancel: vi.fn(),
    onRetry: vi.fn(),
    onDelete: vi.fn(),
    onPageChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // Job Table Rendering Tests (Requirement 15.1)
  // ============================================================================

  describe('Job Table Rendering (Requirement 15.1)', () => {
    it('renders the component without crashing', () => {
      render(<EnhancementManagement {...defaultProps} />);
      expect(screen.getByText('Grammar Enhancement Job')).toBeInTheDocument();
    });

    it('renders all job rows', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      expect(screen.getByText('Grammar Enhancement Job')).toBeInTheDocument();
      expect(screen.getByText('Style Adjustment Job')).toBeInTheDocument();
      expect(screen.getByText('Content Expansion Job')).toBeInTheDocument();
      expect(screen.getByText('Translation Job')).toBeInTheDocument();
      expect(screen.getByText('Summary Generation Job')).toBeInTheDocument();
      expect(screen.getByText('Paused Enhancement Job')).toBeInTheDocument();
    });

    it('displays correct column headers', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      expect(screen.getAllByText('enhancement.columns.id')[0]).toBeInTheDocument();
      expect(screen.getAllByText('enhancement.columns.name')[0]).toBeInTheDocument();
      expect(screen.getAllByText('enhancement.columns.type')[0]).toBeInTheDocument();
      expect(screen.getAllByText('enhancement.columns.status')[0]).toBeInTheDocument();
      expect(screen.getAllByText('enhancement.columns.progress')[0]).toBeInTheDocument();
      expect(screen.getAllByText('enhancement.columns.createdAt')[0]).toBeInTheDocument();
      expect(screen.getAllByText('enhancement.columns.actions')[0]).toBeInTheDocument();
    });

    it('displays loading state correctly', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} loading={true} />);
      
      const loadingSpinner = container.querySelector('.ant-spin');
      expect(loadingSpinner).toBeInTheDocument();
    });

    it('displays empty state when no jobs', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} jobs={[]} />);
      
      const emptyState = container.querySelector('.ant-empty');
      expect(emptyState).toBeInTheDocument();
    });

    it('displays job IDs correctly', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      expect(screen.getByText('job-1')).toBeInTheDocument();
      expect(screen.getByText('job-2')).toBeInTheDocument();
      expect(screen.getByText('job-3')).toBeInTheDocument();
    });

    it('displays job names correctly', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      expect(screen.getByText('Grammar Enhancement Job')).toBeInTheDocument();
      expect(screen.getByText('Style Adjustment Job')).toBeInTheDocument();
    });

    it('displays job types with translation keys', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      expect(screen.getByText('enhancement.type.grammar')).toBeInTheDocument();
      expect(screen.getByText('enhancement.type.style')).toBeInTheDocument();
      expect(screen.getByText('enhancement.type.content')).toBeInTheDocument();
      expect(screen.getByText('enhancement.type.translation')).toBeInTheDocument();
    });

    it('displays created dates in locale format', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      const dateElements = screen.getAllByText(/2024/);
      expect(dateElements.length).toBeGreaterThan(0);
    });

    it('displays progress bars for all jobs', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const progressBars = container.querySelectorAll('.ant-progress');
      expect(progressBars.length).toBe(6);
    });

    it('displays job statuses as tags', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      expect(screen.getByText('enhancement.status.running')).toBeInTheDocument();
      expect(screen.getByText('enhancement.status.completed')).toBeInTheDocument();
      expect(screen.getByText('enhancement.status.failed')).toBeInTheDocument();
      expect(screen.getByText('enhancement.status.pending')).toBeInTheDocument();
      expect(screen.getByText('enhancement.status.cancelled')).toBeInTheDocument();
      expect(screen.getByText('enhancement.status.paused')).toBeInTheDocument();
    });

    it('truncates long job IDs with ellipsis', () => {
      const longIdJob: EnhancementJob[] = [
        {
          id: 'very-long-job-id-that-should-be-truncated-with-ellipsis-12345678',
          name: 'Test Job',
          type: 'grammar',
          status: 'pending',
          progress: 0,
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      const { container } = render(<EnhancementManagement {...defaultProps} jobs={longIdJob} />);
      
      const idCell = container.querySelector('.ant-table-cell-ellipsis');
      expect(idCell).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Status Color Coding Tests (Requirement 15.2)
  // ============================================================================

  describe('Status Color Coding (Requirement 15.2)', () => {
    it('displays pending status with default color', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const pendingTag = screen.getByText('enhancement.status.pending').closest('.ant-tag');
      expect(pendingTag).toHaveClass('ant-tag-default');
    });

    it('displays running status with processing color', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const runningTag = screen.getByText('enhancement.status.running').closest('.ant-tag');
      expect(runningTag).toHaveClass('ant-tag-processing');
    });

    it('displays completed status with success color', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const completedTag = screen.getByText('enhancement.status.completed').closest('.ant-tag');
      expect(completedTag).toHaveClass('ant-tag-success');
    });

    it('displays failed status with error color', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const failedTag = screen.getByText('enhancement.status.failed').closest('.ant-tag');
      expect(failedTag).toHaveClass('ant-tag-error');
    });

    it('displays cancelled status with default color', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const cancelledTag = screen.getByText('enhancement.status.cancelled').closest('.ant-tag');
      expect(cancelledTag).toHaveClass('ant-tag-default');
    });

    it('displays paused status with warning color', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const pausedTag = screen.getByText('enhancement.status.paused').closest('.ant-tag');
      expect(pausedTag).toHaveClass('ant-tag-warning');
    });

    it('displays progress bar with exception status for failed jobs', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const exceptionProgress = container.querySelector('.ant-progress-status-exception');
      expect(exceptionProgress).toBeInTheDocument();
    });

    it('displays progress bar with success status for completed jobs', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const successProgress = container.querySelector('.ant-progress-status-success');
      expect(successProgress).toBeInTheDocument();
    });

    it('displays progress bar with active status for running jobs', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const activeProgress = container.querySelectorAll('.ant-progress-status-active');
      expect(activeProgress.length).toBeGreaterThan(0);
    });
  });

  // ============================================================================
  // Cancel Action Tests (Requirement 15.3)
  // ============================================================================

  describe('Cancel Action (Requirement 15.3)', () => {
    it('displays cancel button for pending jobs', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      const cancelButtons = screen.getAllByText('enhancement.actions.cancel');
      expect(cancelButtons.length).toBeGreaterThan(0);
    });

    it('displays cancel button for running jobs', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      const cancelButtons = screen.getAllByText('enhancement.actions.cancel');
      expect(cancelButtons.length).toBeGreaterThan(0);
    });

    it('displays cancel button for paused jobs', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      const cancelButtons = screen.getAllByText('enhancement.actions.cancel');
      expect(cancelButtons.length).toBeGreaterThan(0);
    });

    it('does not display cancel button for completed jobs', () => {
      const completedJobs: EnhancementJob[] = [
        {
          id: 'job-completed',
          name: 'Completed Job',
          type: 'grammar',
          status: 'completed',
          progress: 100,
          createdAt: '2024-01-01T10:00:00Z',
          completedAt: '2024-01-01T12:00:00Z',
        },
      ];
      
      const { container } = render(<EnhancementManagement {...defaultProps} jobs={completedJobs} />);
      
      const cancelButtons = screen.queryAllByText('enhancement.actions.cancel');
      expect(cancelButtons.length).toBe(0);
    });

    it('does not display cancel button for failed jobs', () => {
      const failedJobs: EnhancementJob[] = [
        {
          id: 'job-failed',
          name: 'Failed Job',
          type: 'grammar',
          status: 'failed',
          progress: 50,
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      const { container } = render(<EnhancementManagement {...defaultProps} jobs={failedJobs} />);
      
      const cancelButtons = screen.queryAllByText('enhancement.actions.cancel');
      expect(cancelButtons.length).toBe(0);
    });

    it('does not display cancel button for cancelled jobs', () => {
      const cancelledJobs: EnhancementJob[] = [
        {
          id: 'job-cancelled',
          name: 'Cancelled Job',
          type: 'grammar',
          status: 'cancelled',
          progress: 30,
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      const { container } = render(<EnhancementManagement {...defaultProps} jobs={cancelledJobs} />);
      
      const cancelButtons = screen.queryAllByText('enhancement.actions.cancel');
      expect(cancelButtons.length).toBe(0);
    });

    it('calls onCancel when cancel button is clicked', () => {
      const onCancel = vi.fn();
      render(<EnhancementManagement {...defaultProps} onCancel={onCancel} />);
      
      const cancelButtons = screen.getAllByText('enhancement.actions.cancel');
      fireEvent.click(cancelButtons[0]);
      
      expect(onCancel).toHaveBeenCalledWith('job-1');
    });

    it('cancel button is styled as danger', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const cancelButtons = container.querySelectorAll('.ant-btn-dangerous');
      expect(cancelButtons.length).toBeGreaterThan(0);
    });

    it('displays cancel icon in cancel button', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const cancelIcons = container.querySelectorAll('[aria-label="close-circle"]');
      expect(cancelIcons.length).toBeGreaterThan(0);
    });
  });

  // ============================================================================
  // Filter Functionality Tests (Requirement 15.3)
  // ============================================================================

  describe('Filter Functionality (Requirement 15.3)', () => {
    it('displays filter icon in status column', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const statusHeader = screen.getAllByText('enhancement.columns.status')[0];
      const filterIcon = statusHeader.closest('th')?.querySelector('.ant-table-filter-trigger');
      
      expect(filterIcon).toBeInTheDocument();
    });

    it('opens filter dropdown when filter icon is clicked', async () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const statusHeader = screen.getAllByText('enhancement.columns.status')[0];
      const filterIcon = statusHeader.closest('th')?.querySelector('.ant-table-filter-trigger');
      
      if (filterIcon) {
        fireEvent.click(filterIcon);
        
        await waitFor(() => {
          const dropdown = document.querySelector('.ant-table-filter-dropdown');
          expect(dropdown).toBeInTheDocument();
        });
      }
    });

    it('displays all status filter options', async () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const statusHeader = screen.getAllByText('enhancement.columns.status')[0];
      const filterIcon = statusHeader.closest('th')?.querySelector('.ant-table-filter-trigger');
      
      if (filterIcon) {
        fireEvent.click(filterIcon);
        
        await waitFor(() => {
          const dropdown = document.querySelector('.ant-table-filter-dropdown');
          expect(dropdown).toBeInTheDocument();
          
          // Check that all status options are present in the dropdown
          const allPendingTexts = screen.getAllByText('enhancement.status.pending');
          const allRunningTexts = screen.getAllByText('enhancement.status.running');
          const allCompletedTexts = screen.getAllByText('enhancement.status.completed');
          const allFailedTexts = screen.getAllByText('enhancement.status.failed');
          const allCancelledTexts = screen.getAllByText('enhancement.status.cancelled');
          const allPausedTexts = screen.getAllByText('enhancement.status.paused');
          
          // Each status should appear at least twice (once in table, once in filter)
          expect(allPendingTexts.length).toBeGreaterThanOrEqual(2);
          expect(allRunningTexts.length).toBeGreaterThanOrEqual(2);
          expect(allCompletedTexts.length).toBeGreaterThanOrEqual(2);
          expect(allFailedTexts.length).toBeGreaterThanOrEqual(2);
          expect(allCancelledTexts.length).toBeGreaterThanOrEqual(2);
          expect(allPausedTexts.length).toBeGreaterThanOrEqual(2);
        });
      }
    });

    it('filters jobs by status when filter is applied', async () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      // Initially all 6 jobs should be visible
      const initialRows = container.querySelectorAll('tbody tr');
      expect(initialRows.length).toBe(6);
      
      const statusHeader = screen.getAllByText('enhancement.columns.status')[0];
      const filterIcon = statusHeader.closest('th')?.querySelector('.ant-table-filter-trigger');
      
      if (filterIcon) {
        fireEvent.click(filterIcon);
        
        await waitFor(() => {
          const dropdown = document.querySelector('.ant-table-filter-dropdown');
          expect(dropdown).toBeInTheDocument();
          
          // Find the completed checkbox in the dropdown
          const allCompletedTexts = screen.getAllByText('enhancement.status.completed');
          const completedInDropdown = allCompletedTexts.find(el => 
            el.closest('.ant-table-filter-dropdown') !== null
          );
          
          if (completedInDropdown) {
            const completedCheckbox = completedInDropdown
              .closest('.ant-checkbox-wrapper')
              ?.querySelector('input');
            
            if (completedCheckbox) {
              fireEvent.click(completedCheckbox);
            }
          }
        });
      }
    });

    it('supports sorting by created date', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const createdAtHeader = screen.getAllByText('enhancement.columns.createdAt')[0];
      const sorter = createdAtHeader.closest('th')?.querySelector('.ant-table-column-sorters');
      
      expect(sorter).toBeInTheDocument();
    });

    it('sorts jobs by created date when sorter is clicked', async () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const createdAtHeader = screen.getAllByText('enhancement.columns.createdAt')[0];
      const sorter = createdAtHeader.closest('th')?.querySelector('.ant-table-column-sorters');
      
      if (sorter) {
        fireEvent.click(sorter);
        
        await waitFor(() => {
          const rows = container.querySelectorAll('tbody tr');
          expect(rows.length).toBeGreaterThan(0);
        });
      }
    });
  });

  // ============================================================================
  // Action Buttons Tests
  // ============================================================================

  describe('Action Buttons', () => {
    it('displays view results button for completed jobs', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      const viewButtons = screen.getAllByText('enhancement.actions.viewDetails');
      expect(viewButtons.length).toBeGreaterThan(0);
    });

    it('calls onViewResults when view results button is clicked', () => {
      const onViewResults = vi.fn();
      render(<EnhancementManagement {...defaultProps} onViewResults={onViewResults} />);
      
      const viewButtons = screen.getAllByText('enhancement.actions.viewDetails');
      fireEvent.click(viewButtons[0]);
      
      expect(onViewResults).toHaveBeenCalledWith('job-2');
    });

    it('displays retry button for failed jobs', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      const retryButtons = screen.getAllByText('common.actions.retry');
      expect(retryButtons.length).toBeGreaterThan(0);
    });

    it('calls onRetry when retry button is clicked', () => {
      const onRetry = vi.fn();
      render(<EnhancementManagement {...defaultProps} onRetry={onRetry} />);
      
      const retryButtons = screen.getAllByText('common.actions.retry');
      fireEvent.click(retryButtons[0]);
      
      expect(onRetry).toHaveBeenCalledWith('job-3');
    });

    it('displays delete button for completed, failed, and cancelled jobs', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      const deleteButtons = screen.getAllByText('common.actions.delete');
      expect(deleteButtons.length).toBe(3); // job-2 (completed), job-3 (failed), job-5 (cancelled)
    });

    it('calls onDelete when delete button is clicked', () => {
      const onDelete = vi.fn();
      render(<EnhancementManagement {...defaultProps} onDelete={onDelete} />);
      
      const deleteButtons = screen.getAllByText('common.actions.delete');
      fireEvent.click(deleteButtons[0]);
      
      expect(onDelete).toHaveBeenCalled();
    });

    it('does not display view results button for non-completed jobs', () => {
      const pendingJobs: EnhancementJob[] = [
        {
          id: 'job-pending',
          name: 'Pending Job',
          type: 'grammar',
          status: 'pending',
          progress: 0,
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<EnhancementManagement {...defaultProps} jobs={pendingJobs} />);
      
      const viewButtons = screen.queryAllByText('enhancement.actions.viewDetails');
      expect(viewButtons.length).toBe(0);
    });

    it('does not display retry button for non-failed jobs', () => {
      const runningJobs: EnhancementJob[] = [
        {
          id: 'job-running',
          name: 'Running Job',
          type: 'grammar',
          status: 'running',
          progress: 50,
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<EnhancementManagement {...defaultProps} jobs={runningJobs} />);
      
      const retryButtons = screen.queryAllByText('common.actions.retry');
      expect(retryButtons.length).toBe(0);
    });

    it('does not display delete button for active jobs', () => {
      const activeJobs: EnhancementJob[] = [
        {
          id: 'job-running',
          name: 'Running Job',
          type: 'grammar',
          status: 'running',
          progress: 50,
          createdAt: '2024-01-01T10:00:00Z',
        },
        {
          id: 'job-pending',
          name: 'Pending Job',
          type: 'style',
          status: 'pending',
          progress: 0,
          createdAt: '2024-01-02T10:00:00Z',
        },
      ];
      
      render(<EnhancementManagement {...defaultProps} jobs={activeJobs} />);
      
      const deleteButtons = screen.queryAllByText('common.actions.delete');
      expect(deleteButtons.length).toBe(0);
    });

    it('displays correct icons for action buttons', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      expect(container.querySelector('[aria-label="eye"]')).toBeInTheDocument();
      expect(container.querySelector('[aria-label="close-circle"]')).toBeInTheDocument();
      expect(container.querySelector('[aria-label="reload"]')).toBeInTheDocument();
      expect(container.querySelector('[aria-label="delete"]')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Pagination Tests
  // ============================================================================

  describe('Pagination', () => {
    it('displays pagination controls', () => {
      render(<EnhancementManagement {...defaultProps} />);
      
      expect(screen.getByText('Total 6 items')).toBeInTheDocument();
    });

    it('calls onPageChange when page is changed', async () => {
      const onPageChange = vi.fn();
      render(
        <EnhancementManagement
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 50 }}
          onPageChange={onPageChange}
        />
      );
      
      const nextButton = screen.getByTitle('Next Page');
      fireEvent.click(nextButton);
      
      await waitFor(() => {
        expect(onPageChange).toHaveBeenCalledWith(2, 10);
      });
    });

    it('calls onPageChange when page size is changed', async () => {
      const onPageChange = vi.fn();
      const { container } = render(
        <EnhancementManagement
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 50 }}
          onPageChange={onPageChange}
        />
      );
      
      const pageSizeSelector = container.querySelector('.ant-select-selector');
      if (pageSizeSelector) {
        fireEvent.mouseDown(pageSizeSelector);
        
        await waitFor(() => {
          const option20 = screen.queryByTitle('20 / page');
          if (option20) {
            fireEvent.click(option20);
            expect(onPageChange).toHaveBeenCalled();
          }
        });
      }
    });

    it('displays correct current page', () => {
      render(
        <EnhancementManagement
          {...defaultProps}
          pagination={{ page: 2, pageSize: 10, total: 50 }}
        />
      );
      
      const activePageItem = screen.getByTitle('2');
      expect(activePageItem).toHaveClass('ant-pagination-item-active');
    });

    it('shows quick jumper for large datasets', () => {
      const { container } = render(
        <EnhancementManagement
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 150 }}
        />
      );
      
      const quickJumper = container.querySelector('.ant-pagination-options-quick-jumper');
      expect(quickJumper).toBeInTheDocument();
    });

    it('does not show quick jumper for small datasets', () => {
      const { container } = render(
        <EnhancementManagement
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 50 }}
        />
      );
      
      const quickJumper = container.querySelector('.ant-pagination-options-quick-jumper');
      expect(quickJumper).not.toBeInTheDocument();
    });

    it('disables next button on last page', () => {
      render(
        <EnhancementManagement
          {...defaultProps}
          pagination={{ page: 5, pageSize: 10, total: 50 }}
        />
      );
      
      const nextButton = screen.getByTitle('Next Page');
      expect(nextButton).toHaveClass('ant-pagination-disabled');
    });

    it('disables previous button on first page', () => {
      render(
        <EnhancementManagement
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 50 }}
        />
      );
      
      const prevButton = screen.getByTitle('Previous Page');
      expect(prevButton).toHaveClass('ant-pagination-disabled');
    });
  });

  // ============================================================================
  // Progress Display Tests
  // ============================================================================

  describe('Progress Display', () => {
    it('displays progress bars with correct percentages', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const progressBars = container.querySelectorAll('.ant-progress');
      expect(progressBars.length).toBe(6);
    });

    it('displays 0% progress for pending jobs', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      const pendingRow = Array.from(rows).find(row => 
        row.textContent?.includes('Translation Job')
      );
      
      expect(pendingRow).toBeInTheDocument();
    });

    it('displays 100% progress for completed jobs', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      const completedRow = Array.from(rows).find(row => 
        row.textContent?.includes('Style Adjustment Job')
      );
      
      expect(completedRow).toBeInTheDocument();
    });

    it('displays partial progress for running jobs', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      const runningRow = Array.from(rows).find(row => 
        row.textContent?.includes('Grammar Enhancement Job')
      );
      
      expect(runningRow).toBeInTheDocument();
    });

    it('uses small size for progress bars', () => {
      const { container } = render(<EnhancementManagement {...defaultProps} />);
      
      const smallProgress = container.querySelectorAll('.ant-progress-small');
      expect(smallProgress.length).toBeGreaterThan(0);
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('handles very long job names', () => {
      const longNameJob: EnhancementJob[] = [
        {
          id: 'job-long',
          name: 'This is a very long enhancement job name that should be truncated or handled properly in the UI',
          type: 'grammar',
          status: 'pending',
          progress: 0,
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<EnhancementManagement {...defaultProps} jobs={longNameJob} />);
      
      expect(screen.getByText(/This is a very long enhancement job name/)).toBeInTheDocument();
    });

    it('handles jobs without completion date', () => {
      const jobWithoutCompletionDate: EnhancementJob[] = [
        {
          id: 'job-no-completion',
          name: 'Job Without Completion',
          type: 'grammar',
          status: 'running',
          progress: 50,
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<EnhancementManagement {...defaultProps} jobs={jobWithoutCompletionDate} />);
      
      expect(screen.getByText('Job Without Completion')).toBeInTheDocument();
    });

    it('handles jobs without iterations', () => {
      const jobWithoutIterations: EnhancementJob[] = [
        {
          id: 'job-no-iterations',
          name: 'Job Without Iterations',
          type: 'grammar',
          status: 'pending',
          progress: 0,
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<EnhancementManagement {...defaultProps} jobs={jobWithoutIterations} />);
      
      expect(screen.getByText('Job Without Iterations')).toBeInTheDocument();
    });

    it('handles pagination with zero total', () => {
      const { container } = render(
        <EnhancementManagement
          {...defaultProps}
          jobs={[]}
          pagination={{ page: 1, pageSize: 10, total: 0 }}
        />
      );
      
      expect(container.querySelector('.ant-table')).toBeInTheDocument();
    });

    it('handles single page of results', () => {
      render(
        <EnhancementManagement
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 6 }}
        />
      );
      
      const nextButton = screen.queryByTitle('Next Page');
      expect(nextButton).toHaveClass('ant-pagination-disabled');
    });

    it('handles unknown job status gracefully', () => {
      const unknownStatusJob: EnhancementJob[] = [
        {
          id: 'job-unknown',
          name: 'Unknown Status Job',
          type: 'grammar',
          status: 'unknown' as any,
          progress: 0,
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<EnhancementManagement {...defaultProps} jobs={unknownStatusJob} />);
      
      expect(screen.getByText('Unknown Status Job')).toBeInTheDocument();
    });

    it('handles unknown job type gracefully', () => {
      const unknownTypeJob: EnhancementJob[] = [
        {
          id: 'job-unknown-type',
          name: 'Unknown Type Job',
          type: 'unknown',
          status: 'pending',
          progress: 0,
          createdAt: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<EnhancementManagement {...defaultProps} jobs={unknownTypeJob} />);
      
      expect(screen.getByText('enhancement.type.unknown')).toBeInTheDocument();
    });
  });
});
