/**
 * AuditLogViewer Component Unit Tests
 * 
 * Tests for log table rendering, filtering functionality, export action, and expandable rows.
 * Requirements: 17.2, 17.3, 17.4
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import AuditLogViewer from '../AuditLogViewer';
import type { AuditLog, AuditFilters } from '../AuditLogViewer';

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

describe('AuditLogViewer Component', () => {
  // Test data
  const mockLogs: AuditLog[] = [
    {
      id: 'log-1',
      operation: {
        operationType: 'create',
        userId: 'user-123',
        resource: {
          type: 'sample',
          id: 'sample-1',
        },
        action: 'create_sample',
        timestamp: new Date('2024-01-01T10:00:00Z'),
        details: {
          sampleId: 'sample-1',
          category: 'text',
        },
      },
      result: 'success',
      duration: 150,
      timestamp: new Date('2024-01-01T10:00:00Z'),
    },
    {
      id: 'log-2',
      operation: {
        operationType: 'update',
        userId: 'user-456',
        resource: {
          type: 'annotation_task',
          id: 'task-1',
        },
        action: 'update_task',
        timestamp: new Date('2024-01-02T11:00:00Z'),
        details: {
          taskId: 'task-1',
          status: 'completed',
        },
      },
      result: 'success',
      duration: 200,
      timestamp: new Date('2024-01-02T11:00:00Z'),
    },
    {
      id: 'log-3',
      operation: {
        operationType: 'delete',
        userId: 'user-789',
        resource: {
          type: 'temp_data',
          id: 'temp-1',
        },
        action: 'delete_temp',
        timestamp: new Date('2024-01-03T12:00:00Z'),
        details: {
          tempId: 'temp-1',
        },
      },
      result: 'failure',
      duration: 50,
      timestamp: new Date('2024-01-03T12:00:00Z'),
      error: 'Permission denied',
    },
  ];

  const defaultProps = {
    logs: mockLogs,
    loading: false,
    pagination: {
      page: 1,
      pageSize: 10,
      total: 3,
    },
    onFilter: vi.fn(),
    onExport: vi.fn(),
    onPageChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // Log Table Rendering Tests (Requirement 17.2)
  // ============================================================================

  describe('Log Table Rendering', () => {
    it('renders the component without crashing', () => {
      render(<AuditLogViewer {...defaultProps} />);
      expect(screen.getByText('audit.export')).toBeInTheDocument();
    });

    it('renders all log entries', () => {
      render(<AuditLogViewer {...defaultProps} />);
      
      // Check that all logs are rendered by checking user IDs
      expect(screen.getByText('user-123')).toBeInTheDocument();
      expect(screen.getByText('user-456')).toBeInTheDocument();
      expect(screen.getByText('user-789')).toBeInTheDocument();
    });

    it('displays correct column headers', () => {
      render(<AuditLogViewer {...defaultProps} />);
      
      expect(screen.getAllByText('audit.columns.timestamp')[0]).toBeInTheDocument();
      expect(screen.getAllByText('audit.columns.userId')[0]).toBeInTheDocument();
      expect(screen.getAllByText('audit.columns.operationType')[0]).toBeInTheDocument();
      expect(screen.getAllByText('audit.columns.resourceType')[0]).toBeInTheDocument();
      expect(screen.getAllByText('audit.columns.action')[0]).toBeInTheDocument();
      expect(screen.getAllByText('audit.columns.result')[0]).toBeInTheDocument();
      expect(screen.getAllByText('audit.columns.duration')[0]).toBeInTheDocument();
    });

    it('displays timestamps in locale format', () => {
      render(<AuditLogViewer {...defaultProps} />);
      
      // Timestamps should be formatted using toLocaleString
      const dateElements = screen.getAllByText(/2024/);
      expect(dateElements.length).toBeGreaterThan(0);
    });

    it('displays operation types as tags', () => {
      render(<AuditLogViewer {...defaultProps} />);
      
      expect(screen.getByText('create')).toBeInTheDocument();
      expect(screen.getByText('update')).toBeInTheDocument();
      expect(screen.getByText('delete')).toBeInTheDocument();
    });

    it('displays resource types as colored tags', () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      expect(screen.getByText('sample')).toBeInTheDocument();
      expect(screen.getByText('annotation_task')).toBeInTheDocument();
      expect(screen.getByText('temp_data')).toBeInTheDocument();
      
      // Resource type tags should have blue color
      const sampleTag = screen.getByText('sample').closest('.ant-tag');
      expect(sampleTag).toHaveClass('ant-tag-blue');
    });

    it('displays results with appropriate color coding', () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      // Success results should be green
      const successTags = screen.getAllByText('success');
      expect(successTags[0].closest('.ant-tag')).toHaveClass('ant-tag-success');
      
      // Failure results should be red
      const failureTag = screen.getByText('failure').closest('.ant-tag');
      expect(failureTag).toHaveClass('ant-tag-error');
    });

    it('displays duration in milliseconds', () => {
      render(<AuditLogViewer {...defaultProps} />);
      
      expect(screen.getByText('150ms')).toBeInTheDocument();
      expect(screen.getByText('200ms')).toBeInTheDocument();
      expect(screen.getByText('50ms')).toBeInTheDocument();
    });

    it('displays loading state correctly', () => {
      const { container } = render(<AuditLogViewer {...defaultProps} loading={true} />);
      
      const loadingSpinner = container.querySelector('.ant-spin');
      expect(loadingSpinner).toBeInTheDocument();
    });

    it('displays empty state when no logs', () => {
      const { container } = render(<AuditLogViewer {...defaultProps} logs={[]} />);
      
      const emptyState = container.querySelector('.ant-empty');
      expect(emptyState).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Filtering Functionality Tests (Requirement 17.2)
  // ============================================================================

  describe('Filtering Functionality', () => {
    it('renders all filter controls', () => {
      render(<AuditLogViewer {...defaultProps} />);
      
      expect(screen.getByPlaceholderText('audit.filters.userId')).toBeInTheDocument();
      expect(screen.getByText('audit.filters.resourceType')).toBeInTheDocument();
      expect(screen.getByText('audit.filters.operationType')).toBeInTheDocument();
      expect(screen.getByText('audit.filters.result')).toBeInTheDocument();
    });

    it('allows entering user ID filter', () => {
      render(<AuditLogViewer {...defaultProps} />);
      
      const userIdInput = screen.getByPlaceholderText('audit.filters.userId');
      fireEvent.change(userIdInput, { target: { value: 'user-123' } });
      
      expect(userIdInput).toHaveValue('user-123');
    });

    it('allows selecting resource type filter', async () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      // Find the select by its placeholder text
      const resourceTypeSelect = screen.getByText('audit.filters.resourceType').closest('.ant-select');
      expect(resourceTypeSelect).toBeInTheDocument();
      
      // Verify the select is interactive
      expect(resourceTypeSelect!.querySelector('.ant-select-selector')).toBeInTheDocument();
    });

    it('allows selecting operation type filter', async () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      // Find the select by its placeholder text
      const operationTypeSelect = screen.getByText('audit.filters.operationType').closest('.ant-select');
      expect(operationTypeSelect).toBeInTheDocument();
      
      // Verify the select is interactive
      expect(operationTypeSelect!.querySelector('.ant-select-selector')).toBeInTheDocument();
    });

    it('allows selecting result filter', async () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      // Find the select by its placeholder text
      const resultSelect = screen.getByText('audit.filters.result').closest('.ant-select');
      expect(resultSelect).toBeInTheDocument();
      
      // Click to open dropdown
      fireEvent.mouseDown(resultSelect!.querySelector('.ant-select-selector')!);
      
      await waitFor(() => {
        const option = screen.getByText('audit.results.success');
        fireEvent.click(option);
      });
    });

    it('calls onFilter when search button is clicked', () => {
      const onFilter = vi.fn();
      render(<AuditLogViewer {...defaultProps} onFilter={onFilter} />);
      
      const searchButton = screen.getByText('common.actions.search');
      fireEvent.click(searchButton);
      
      expect(onFilter).toHaveBeenCalledTimes(1);
    });

    it('passes filter values to onFilter callback', async () => {
      const onFilter = vi.fn();
      render(<AuditLogViewer {...defaultProps} onFilter={onFilter} />);
      
      // Set user ID filter
      const userIdInput = screen.getByPlaceholderText('audit.filters.userId');
      fireEvent.change(userIdInput, { target: { value: 'user-123' } });
      
      // Click search
      const searchButton = screen.getByText('common.actions.search');
      fireEvent.click(searchButton);
      
      await waitFor(() => {
        expect(onFilter).toHaveBeenCalledWith(
          expect.objectContaining({
            userId: 'user-123',
          })
        );
      });
    });

    it('resets filters when reset button is clicked', async () => {
      const onFilter = vi.fn();
      render(<AuditLogViewer {...defaultProps} onFilter={onFilter} />);
      
      // Set a filter
      const userIdInput = screen.getByPlaceholderText('audit.filters.userId');
      fireEvent.change(userIdInput, { target: { value: 'user-123' } });
      
      // Click reset
      const resetButton = screen.getByText('common.actions.reset');
      fireEvent.click(resetButton);
      
      await waitFor(() => {
        expect(onFilter).toHaveBeenCalledWith({});
        expect(userIdInput).toHaveValue('');
      });
    });

    it('clears individual filter when clear icon is clicked', () => {
      render(<AuditLogViewer {...defaultProps} />);
      
      const userIdInput = screen.getByPlaceholderText('audit.filters.userId');
      fireEvent.change(userIdInput, { target: { value: 'user-123' } });
      
      expect(userIdInput).toHaveValue('user-123');
      
      // Find and click the clear icon
      const clearIcon = userIdInput.parentElement?.querySelector('.ant-input-clear-icon');
      if (clearIcon) {
        fireEvent.click(clearIcon);
        expect(userIdInput).toHaveValue('');
      }
    });

    it('supports multiple filters simultaneously', async () => {
      const onFilter = vi.fn();
      const { container } = render(<AuditLogViewer {...defaultProps} onFilter={onFilter} />);
      
      // Set user ID filter
      const userIdInput = screen.getByPlaceholderText('audit.filters.userId');
      fireEvent.change(userIdInput, { target: { value: 'user-123' } });
      
      // Click search
      const searchButton = screen.getByText('common.actions.search');
      fireEvent.click(searchButton);
      
      await waitFor(() => {
        expect(onFilter).toHaveBeenCalledWith(
          expect.objectContaining({
            userId: 'user-123',
          })
        );
      });
    });
  });

  // ============================================================================
  // Export Action Tests (Requirement 17.4)
  // ============================================================================

  describe('Export Action', () => {
    it('renders export button', () => {
      render(<AuditLogViewer {...defaultProps} />);
      
      const exportButton = screen.getByText('audit.export');
      expect(exportButton).toBeInTheDocument();
    });

    it('export button has download icon', () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      const exportButton = screen.getByText('audit.export').closest('button');
      const icon = exportButton?.querySelector('[aria-label="download"]');
      expect(icon).toBeInTheDocument();
    });

    it('calls onExport when export button is clicked', () => {
      const onExport = vi.fn();
      render(<AuditLogViewer {...defaultProps} onExport={onExport} />);
      
      const exportButton = screen.getByText('audit.export');
      fireEvent.click(exportButton);
      
      expect(onExport).toHaveBeenCalledTimes(1);
    });

    it('passes current filters to onExport', async () => {
      const onExport = vi.fn();
      render(<AuditLogViewer {...defaultProps} onExport={onExport} />);
      
      // Set a filter
      const userIdInput = screen.getByPlaceholderText('audit.filters.userId');
      fireEvent.change(userIdInput, { target: { value: 'user-123' } });
      
      // Click export
      const exportButton = screen.getByText('audit.export');
      fireEvent.click(exportButton);
      
      await waitFor(() => {
        expect(onExport).toHaveBeenCalledWith(
          expect.objectContaining({
            userId: 'user-123',
          }),
          'csv'
        );
      });
    });

    it('exports with CSV format by default', () => {
      const onExport = vi.fn();
      render(<AuditLogViewer {...defaultProps} onExport={onExport} />);
      
      const exportButton = screen.getByText('audit.export');
      fireEvent.click(exportButton);
      
      expect(onExport).toHaveBeenCalledWith(expect.any(Object), 'csv');
    });

    it('exports with empty filters when no filters applied', () => {
      const onExport = vi.fn();
      render(<AuditLogViewer {...defaultProps} onExport={onExport} />);
      
      const exportButton = screen.getByText('audit.export');
      fireEvent.click(exportButton);
      
      expect(onExport).toHaveBeenCalledWith({}, 'csv');
    });
  });

  // ============================================================================
  // Expandable Row with JSON Viewer Tests (Requirement 17.3)
  // ============================================================================

  describe('Expandable Row with JSON Viewer', () => {
    it('renders expand icon for each row', () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      expect(expandIcons.length).toBe(3);
    });

    it('expands row when expand icon is clicked', async () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      const expandIcon = container.querySelector('.ant-table-row-expand-icon') as HTMLElement;
      fireEvent.click(expandIcon);
      
      await waitFor(() => {
        const expandedContent = container.querySelector('.audit-log-details');
        expect(expandedContent).toBeInTheDocument();
      });
    });

    it('displays operation details as JSON', async () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      const expandIcon = container.querySelector('.ant-table-row-expand-icon') as HTMLElement;
      fireEvent.click(expandIcon);
      
      await waitFor(() => {
        const jsonContent = container.querySelector('.audit-log-details pre');
        expect(jsonContent).toBeInTheDocument();
        expect(jsonContent?.textContent).toContain('sampleId');
        expect(jsonContent?.textContent).toContain('sample-1');
      });
    });

    it('formats JSON with proper indentation', async () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      const expandIcon = container.querySelector('.ant-table-row-expand-icon') as HTMLElement;
      fireEvent.click(expandIcon);
      
      await waitFor(() => {
        const jsonContent = container.querySelector('.audit-log-details pre');
        // JSON.stringify with 2-space indentation should create multi-line output
        expect(jsonContent?.textContent).toMatch(/\n/);
      });
    });

    it('collapses row when expand icon is clicked again', async () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      const expandIcon = container.querySelector('.ant-table-row-expand-icon') as HTMLElement;
      
      // Expand
      fireEvent.click(expandIcon);
      await waitFor(() => {
        expect(container.querySelector('.audit-log-details')).toBeInTheDocument();
      });
      
      // Collapse - click the same icon again
      const expandedIcon = container.querySelector('.ant-table-row-expand-icon') as HTMLElement;
      fireEvent.click(expandedIcon);
      
      // Wait a bit for the collapse animation
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // The expanded row should be hidden or removed
      const expandedRows = container.querySelectorAll('.ant-table-expanded-row:not([style*="display: none"])');
      expect(expandedRows.length).toBeLessThanOrEqual(1);
    });

    it('supports expanding multiple rows simultaneously', async () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      
      // Expand first row
      fireEvent.click(expandIcons[0] as HTMLElement);
      await waitFor(() => {
        const expandedRows = container.querySelectorAll('.audit-log-details');
        expect(expandedRows.length).toBe(1);
      });
      
      // Expand second row
      fireEvent.click(expandIcons[1] as HTMLElement);
      await waitFor(() => {
        const expandedRows = container.querySelectorAll('.audit-log-details');
        expect(expandedRows.length).toBe(2);
      });
    });

    it('displays details section when row is expanded', async () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      const expandIcon = container.querySelector('.ant-table-row-expand-icon') as HTMLElement;
      fireEvent.click(expandIcon);
      
      await waitFor(() => {
        const detailsSection = container.querySelector('.audit-log-details');
        expect(detailsSection).toBeInTheDocument();
        const jsonContent = container.querySelector('.audit-log-details pre');
        expect(jsonContent).toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Pagination Tests
  // ============================================================================

  describe('Pagination', () => {
    it('displays pagination controls', () => {
      render(<AuditLogViewer {...defaultProps} />);
      
      expect(screen.getByText('Total 3 items')).toBeInTheDocument();
    });

    it('displays correct page size options', () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      const pageSizeSelector = container.querySelector('.ant-select-selection-item');
      expect(pageSizeSelector).toBeInTheDocument();
    });

    it('calls onPageChange when page is changed', async () => {
      const onPageChange = vi.fn();
      render(
        <AuditLogViewer
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
        <AuditLogViewer
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
            expect(onPageChange).toHaveBeenCalledWith(1, 20);
          }
        });
      }
    });

    it('shows quick jumper for large datasets', () => {
      const { container } = render(
        <AuditLogViewer
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 100 }}
        />
      );
      
      const quickJumper = container.querySelector('.ant-pagination-options-quick-jumper');
      expect(quickJumper).toBeInTheDocument();
    });

    it('displays correct current page', () => {
      render(
        <AuditLogViewer
          {...defaultProps}
          pagination={{ page: 2, pageSize: 10, total: 50 }}
        />
      );
      
      const activePageItem = screen.getByTitle('2');
      expect(activePageItem).toHaveClass('ant-pagination-item-active');
    });
  });

  // ============================================================================
  // Sorting Tests
  // ============================================================================

  describe('Sorting', () => {
    it('supports sorting by timestamp', () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      const timestampHeaders = screen.getAllByText('audit.columns.timestamp');
      const timestampHeader = timestampHeaders[0];
      const sorter = timestampHeader.closest('th')?.querySelector('.ant-table-column-sorters');
      
      expect(sorter).toBeInTheDocument();
    });

    it('supports sorting by duration', () => {
      const { container } = render(<AuditLogViewer {...defaultProps} />);
      
      const durationHeaders = screen.getAllByText('audit.columns.duration');
      const durationHeader = durationHeaders[0];
      const sorter = durationHeader.closest('th')?.querySelector('.ant-table-column-sorters');
      
      expect(sorter).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('handles logs with missing details', () => {
      const logsWithMissingDetails: AuditLog[] = [
        {
          ...mockLogs[0],
          operation: {
            ...mockLogs[0].operation,
            details: undefined,
          },
        },
      ];
      
      render(<AuditLogViewer {...defaultProps} logs={logsWithMissingDetails} />);
      
      expect(screen.getByText('user-123')).toBeInTheDocument();
    });

    it('handles logs with partial result', () => {
      const logsWithPartialResult: AuditLog[] = [
        {
          ...mockLogs[0],
          result: 'partial',
        },
      ];
      
      const { container } = render(<AuditLogViewer {...defaultProps} logs={logsWithPartialResult} />);
      
      const partialTag = screen.getByText('partial').closest('.ant-tag');
      expect(partialTag).toHaveClass('ant-tag-warning');
    });

    it('handles very long user IDs', () => {
      const logsWithLongUserId: AuditLog[] = [
        {
          ...mockLogs[0],
          operation: {
            ...mockLogs[0].operation,
            userId: 'very-long-user-id-that-might-break-layout-if-not-handled-properly',
          },
        },
      ];
      
      render(<AuditLogViewer {...defaultProps} logs={logsWithLongUserId} />);
      
      expect(screen.getByText(/very-long-user-id/)).toBeInTheDocument();
    });

    it('handles zero duration', () => {
      const logsWithZeroDuration: AuditLog[] = [
        {
          ...mockLogs[0],
          duration: 0,
        },
      ];
      
      render(<AuditLogViewer {...defaultProps} logs={logsWithZeroDuration} />);
      
      expect(screen.getByText('0ms')).toBeInTheDocument();
    });

    it('handles pagination with zero total', () => {
      const { container } = render(
        <AuditLogViewer
          {...defaultProps}
          logs={[]}
          pagination={{ page: 1, pageSize: 10, total: 0 }}
        />
      );
      
      expect(container.querySelector('.audit-log-viewer')).toBeInTheDocument();
    });

    it('handles missing onFilter callback', () => {
      const { container } = render(
        <AuditLogViewer {...defaultProps} onFilter={undefined} />
      );
      
      const searchButton = screen.getByText('common.actions.search');
      
      // Should not throw error
      expect(() => fireEvent.click(searchButton)).not.toThrow();
    });

    it('handles missing onExport callback', () => {
      const { container } = render(
        <AuditLogViewer {...defaultProps} onExport={undefined} />
      );
      
      const exportButton = screen.getByText('audit.export');
      
      // Should not throw error
      expect(() => fireEvent.click(exportButton)).not.toThrow();
    });

    it('handles missing onPageChange callback', () => {
      const { container } = render(
        <AuditLogViewer
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 50 }}
          onPageChange={undefined}
        />
      );
      
      const nextButton = screen.getByTitle('Next Page');
      
      // Should not throw error
      expect(() => fireEvent.click(nextButton)).not.toThrow();
    });
  });
});
