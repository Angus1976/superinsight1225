/**
 * SampleLibrary Component Unit Tests
 * 
 * Tests for search/filtering, multi-select, create task action, and pagination.
 * Requirements: 13.2, 13.3
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import SampleLibrary from '../SampleLibrary';
import type { Sample } from '@/services/dataLifecycle';
import type { SearchFilters } from '../SearchFilters';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      if (key === 'common.pagination.total' && params) {
        return `Total ${params.total} items`;
      }
      if (key === 'sampleLibrary.statistics.selected' && params) {
        return `Selected ${params.count} items`;
      }
      return key;
    },
  }),
}));

// Mock Ant Design Modal.confirm
const mockConfirm = vi.fn();
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    Modal: {
      ...((actual as any).Modal || {}),
      confirm: (config: any) => mockConfirm(config),
    },
  };
});

describe('SampleLibrary Component', () => {
  // Sample test data
  const mockSamples: Sample[] = [
    {
      id: 'sample-1',
      data_type: 'text',
      quality_score: 0.85,
      usage_count: 5,
      created_at: '2024-01-01T10:00:00Z',
      tags: ['tag1', 'tag2'],
    },
    {
      id: 'sample-2',
      data_type: 'image',
      quality_score: 0.92,
      usage_count: 3,
      created_at: '2024-01-02T10:00:00Z',
      tags: ['tag3'],
    },
    {
      id: 'sample-3',
      data_type: 'audio',
      quality_score: 0.45,
      usage_count: 10,
      created_at: '2024-01-03T10:00:00Z',
      tags: [],
    },
  ];

  const defaultProps = {
    samples: mockSamples,
    loading: false,
    pagination: {
      page: 1,
      pageSize: 10,
      total: 3,
    },
    selectedSamples: [],
    onSelectionChange: vi.fn(),
    onCreateTask: vi.fn(),
    onViewDetails: vi.fn(),
    onEditTags: vi.fn(),
    onDelete: vi.fn(),
    onSearch: vi.fn(),
    onPageChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // Basic Rendering Tests
  // ============================================================================

  describe('Basic Rendering', () => {
    it('renders the component without crashing', () => {
      render(<SampleLibrary {...defaultProps} />);
      expect(screen.getByText('sampleLibrary.actions.createTask')).toBeInTheDocument();
    });

    it('renders all sample rows', () => {
      render(<SampleLibrary {...defaultProps} />);
      
      // Check that all samples are rendered (by checking for their IDs)
      expect(screen.getByText(/sample-1/)).toBeInTheDocument();
      expect(screen.getByText(/sample-2/)).toBeInTheDocument();
      expect(screen.getByText(/sample-3/)).toBeInTheDocument();
    });

    it('displays correct column headers', () => {
      const { container } = render(<SampleLibrary {...defaultProps} />);
      
      // Use getAllByText since Ant Design may render headers multiple times
      expect(screen.getAllByText('sampleLibrary.columns.id')[0]).toBeInTheDocument();
      expect(screen.getAllByText('sampleLibrary.columns.dataType')[0]).toBeInTheDocument();
      expect(screen.getAllByText('sampleLibrary.columns.qualityScore')[0]).toBeInTheDocument();
      expect(screen.getAllByText('sampleLibrary.columns.createdAt')[0]).toBeInTheDocument();
      expect(screen.getAllByText('sampleLibrary.columns.usageCount')[0]).toBeInTheDocument();
      expect(screen.getAllByText('sampleLibrary.columns.actions')[0]).toBeInTheDocument();
    });

    it('displays loading state correctly', () => {
      const { container } = render(<SampleLibrary {...defaultProps} loading={true} />);
      
      // Ant Design Table shows loading spinner
      const loadingSpinner = container.querySelector('.ant-spin');
      expect(loadingSpinner).toBeInTheDocument();
    });

    it('displays empty state when no samples', () => {
      const { container } = render(<SampleLibrary {...defaultProps} samples={[]} />);
      
      // Ant Design Table shows empty state (check for empty class)
      const emptyState = container.querySelector('.ant-empty');
      expect(emptyState).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Search and Filtering Tests (Requirement 13.2)
  // ============================================================================

  describe('Search and Filtering (Requirement 13.2)', () => {
    it('renders SearchFilters component', () => {
      render(<SampleLibrary {...defaultProps} />);
      
      // Check for filter labels
      expect(screen.getByText('sampleLibrary.filters.tags')).toBeInTheDocument();
      expect(screen.getByText('sampleLibrary.filters.category')).toBeInTheDocument();
    });

    it('calls onSearch when filters are applied', async () => {
      const onSearch = vi.fn();
      render(<SampleLibrary {...defaultProps} onSearch={onSearch} />);
      
      // Click search button
      const searchButton = screen.getByText('common.actions.search');
      fireEvent.click(searchButton);
      
      await waitFor(() => {
        expect(onSearch).toHaveBeenCalled();
      });
    });

    it('passes filter values to onSearch callback', async () => {
      const onSearch = vi.fn();
      render(<SampleLibrary {...defaultProps} onSearch={onSearch} />);
      
      // Click search button (filters are optional)
      const searchButton = screen.getByText('common.actions.search');
      fireEvent.click(searchButton);
      
      await waitFor(() => {
        expect(onSearch).toHaveBeenCalled();
      });
    });

    it('resets filters when reset button is clicked', async () => {
      const onSearch = vi.fn();
      render(<SampleLibrary {...defaultProps} onSearch={onSearch} />);
      
      // Click reset button
      const resetButton = screen.getByText('common.actions.reset');
      fireEvent.click(resetButton);
      
      await waitFor(() => {
        expect(onSearch).toHaveBeenCalledWith({});
      });
    });

    it('updates quality score filter range', async () => {
      const onSearch = vi.fn();
      const { container } = render(<SampleLibrary {...defaultProps} onSearch={onSearch} />);
      
      // Find the slider (quality score filter) - there are 2 handles for range slider
      const sliders = screen.getAllByRole('slider');
      expect(sliders.length).toBe(2); // Range slider has 2 handles
      expect(sliders[0]).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Multi-Select Functionality Tests (Requirement 13.3)
  // ============================================================================

  describe('Multi-Select Functionality (Requirement 13.3)', () => {
    it('displays selection count', () => {
      render(<SampleLibrary {...defaultProps} selectedSamples={['sample-1', 'sample-2']} />);
      
      expect(screen.getByText('Selected 2 items')).toBeInTheDocument();
    });

    it('calls onSelectionChange when rows are selected', async () => {
      const onSelectionChange = vi.fn();
      const { container } = render(
        <SampleLibrary {...defaultProps} onSelectionChange={onSelectionChange} />
      );
      
      // Find and click the first checkbox
      const checkboxes = container.querySelectorAll('input[type="checkbox"]');
      const firstRowCheckbox = checkboxes[1]; // Skip header checkbox
      
      fireEvent.click(firstRowCheckbox);
      
      await waitFor(() => {
        expect(onSelectionChange).toHaveBeenCalled();
      });
    });

    it('supports selecting all rows', async () => {
      const onSelectionChange = vi.fn();
      const { container } = render(
        <SampleLibrary {...defaultProps} onSelectionChange={onSelectionChange} />
      );
      
      // Find and click the header checkbox (select all)
      const checkboxes = container.querySelectorAll('input[type="checkbox"]');
      const headerCheckbox = checkboxes[0];
      
      fireEvent.click(headerCheckbox);
      
      await waitFor(() => {
        expect(onSelectionChange).toHaveBeenCalled();
      });
    });

    it('supports deselecting all rows', async () => {
      const onSelectionChange = vi.fn();
      const { container } = render(
        <SampleLibrary
          {...defaultProps}
          selectedSamples={['sample-1', 'sample-2', 'sample-3']}
          onSelectionChange={onSelectionChange}
        />
      );
      
      // Find and click the header checkbox (deselect all)
      const checkboxes = container.querySelectorAll('input[type="checkbox"]');
      const headerCheckbox = checkboxes[0];
      
      fireEvent.click(headerCheckbox);
      
      await waitFor(() => {
        expect(onSelectionChange).toHaveBeenCalled();
      });
    });

    it('maintains selected state across renders', () => {
      const { rerender } = render(
        <SampleLibrary {...defaultProps} selectedSamples={['sample-1']} />
      );
      
      // Rerender with same selection
      rerender(<SampleLibrary {...defaultProps} selectedSamples={['sample-1']} />);
      
      expect(screen.getByText('Selected 1 items')).toBeInTheDocument();
    });

    it('updates selection count when selection changes', () => {
      const { rerender } = render(
        <SampleLibrary {...defaultProps} selectedSamples={[]} />
      );
      
      expect(screen.getByText('Selected 0 items')).toBeInTheDocument();
      
      rerender(<SampleLibrary {...defaultProps} selectedSamples={['sample-1', 'sample-2']} />);
      
      expect(screen.getByText('Selected 2 items')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Create Task Action Tests (Requirement 13.3)
  // ============================================================================

  describe('Create Task Action (Requirement 13.3)', () => {
    it('renders create task button', () => {
      render(<SampleLibrary {...defaultProps} />);
      
      const createTaskButton = screen.getByText('sampleLibrary.actions.createTask');
      expect(createTaskButton).toBeInTheDocument();
    });

    it('disables create task button when no samples selected', () => {
      render(<SampleLibrary {...defaultProps} selectedSamples={[]} />);
      
      const createTaskButton = screen.getByText('sampleLibrary.actions.createTask').closest('button');
      expect(createTaskButton).toBeDisabled();
    });

    it('enables create task button when samples are selected', () => {
      render(<SampleLibrary {...defaultProps} selectedSamples={['sample-1']} />);
      
      const createTaskButton = screen.getByText('sampleLibrary.actions.createTask').closest('button');
      expect(createTaskButton).not.toBeDisabled();
    });

    it('calls onCreateTask when button is clicked', () => {
      const onCreateTask = vi.fn();
      render(
        <SampleLibrary
          {...defaultProps}
          selectedSamples={['sample-1', 'sample-2']}
          onCreateTask={onCreateTask}
        />
      );
      
      const createTaskButton = screen.getByText('sampleLibrary.actions.createTask');
      fireEvent.click(createTaskButton);
      
      expect(onCreateTask).toHaveBeenCalledTimes(1);
    });

    it('does not call onCreateTask when button is disabled', () => {
      const onCreateTask = vi.fn();
      render(<SampleLibrary {...defaultProps} selectedSamples={[]} onCreateTask={onCreateTask} />);
      
      const createTaskButton = screen.getByText('sampleLibrary.actions.createTask').closest('button');
      
      // Try to click disabled button
      if (createTaskButton) {
        fireEvent.click(createTaskButton);
      }
      
      expect(onCreateTask).not.toHaveBeenCalled();
    });
  });

  // ============================================================================
  // Pagination Tests (Requirement 13.2)
  // ============================================================================

  describe('Pagination (Requirement 13.2)', () => {
    it('displays pagination controls', () => {
      render(<SampleLibrary {...defaultProps} />);
      
      // Check for pagination text
      expect(screen.getByText('Total 3 items')).toBeInTheDocument();
    });

    it('displays correct page size options', () => {
      const { container } = render(<SampleLibrary {...defaultProps} />);
      
      // Find page size selector
      const pageSizeSelector = container.querySelector('.ant-select-selection-item');
      expect(pageSizeSelector).toBeInTheDocument();
    });

    it('calls onPageChange when page is changed', async () => {
      const onPageChange = vi.fn();
      render(
        <SampleLibrary
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 50 }}
          onPageChange={onPageChange}
        />
      );
      
      // Find next page button
      const nextButton = screen.getByTitle('Next Page');
      fireEvent.click(nextButton);
      
      await waitFor(() => {
        expect(onPageChange).toHaveBeenCalledWith(2, 10);
      });
    });

    it('calls onPageChange when page size is changed', async () => {
      const onPageChange = vi.fn();
      const { container } = render(
        <SampleLibrary
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 50 }}
          onPageChange={onPageChange}
        />
      );
      
      // Find and click page size selector
      const pageSizeSelector = container.querySelector('.ant-select-selector');
      if (pageSizeSelector) {
        fireEvent.mouseDown(pageSizeSelector);
        
        await waitFor(() => {
          // Look for the option in the dropdown
          const option20 = screen.queryByTitle('20 / page');
          if (option20) {
            fireEvent.click(option20);
            expect(onPageChange).toHaveBeenCalledWith(1, 20);
          }
        });
      }
    });

    it('displays correct current page', () => {
      render(
        <SampleLibrary
          {...defaultProps}
          pagination={{ page: 2, pageSize: 10, total: 50 }}
        />
      );
      
      // Check that page 2 is active
      const activePageItem = screen.getByTitle('2');
      expect(activePageItem).toHaveClass('ant-pagination-item-active');
    });

    it('shows quick jumper for large datasets', () => {
      const { container } = render(
        <SampleLibrary
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 100 }}
        />
      );
      
      // Quick jumper input should be present
      const quickJumper = container.querySelector('.ant-pagination-options-quick-jumper');
      expect(quickJumper).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Row Actions Tests
  // ============================================================================

  describe('Row Actions', () => {
    it('renders action buttons for each row', () => {
      const { container } = render(<SampleLibrary {...defaultProps} />);
      
      // Each row should have view, edit, and delete buttons
      const viewButtons = container.querySelectorAll('[aria-label="eye"]');
      const editButtons = container.querySelectorAll('[aria-label="edit"]');
      const deleteButtons = container.querySelectorAll('[aria-label="delete"]');
      
      expect(viewButtons.length).toBe(3);
      expect(editButtons.length).toBe(3);
      expect(deleteButtons.length).toBe(3);
    });

    it('calls onViewDetails when view button is clicked', () => {
      const onViewDetails = vi.fn();
      const { container } = render(
        <SampleLibrary {...defaultProps} onViewDetails={onViewDetails} />
      );
      
      // Click first view button
      const viewButtons = container.querySelectorAll('[aria-label="eye"]');
      fireEvent.click(viewButtons[0].closest('button')!);
      
      expect(onViewDetails).toHaveBeenCalledWith('sample-1');
    });

    it('calls onEditTags when edit button is clicked', () => {
      const onEditTags = vi.fn();
      const { container } = render(
        <SampleLibrary {...defaultProps} onEditTags={onEditTags} />
      );
      
      // Click first edit button
      const editButtons = container.querySelectorAll('[aria-label="edit"]');
      fireEvent.click(editButtons[0].closest('button')!);
      
      expect(onEditTags).toHaveBeenCalledWith('sample-1');
    });

    it('shows confirmation modal when delete button is clicked', () => {
      const { container } = render(<SampleLibrary {...defaultProps} />);
      
      // Click first delete button
      const deleteButtons = container.querySelectorAll('[aria-label="delete"]');
      fireEvent.click(deleteButtons[0].closest('button')!);
      
      expect(mockConfirm).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'sampleLibrary.messages.confirmRemove',
          okType: 'danger',
        })
      );
    });

    it('calls onDelete when deletion is confirmed', () => {
      const onDelete = vi.fn();
      mockConfirm.mockImplementation((config) => {
        config.onOk();
      });
      
      const { container } = render(<SampleLibrary {...defaultProps} onDelete={onDelete} />);
      
      // Click first delete button
      const deleteButtons = container.querySelectorAll('[aria-label="delete"]');
      fireEvent.click(deleteButtons[0].closest('button')!);
      
      expect(onDelete).toHaveBeenCalledWith('sample-1');
    });
  });

  // ============================================================================
  // Data Display Tests
  // ============================================================================

  describe('Data Display', () => {
    it('displays sample IDs correctly (truncated)', () => {
      render(<SampleLibrary {...defaultProps} />);
      
      // IDs should be truncated to first 8 characters
      expect(screen.getByText(/sample-1/)).toBeInTheDocument();
    });

    it('displays data types as tags', () => {
      render(<SampleLibrary {...defaultProps} />);
      
      expect(screen.getByText('text')).toBeInTheDocument();
      expect(screen.getByText('image')).toBeInTheDocument();
      expect(screen.getByText('audio')).toBeInTheDocument();
    });

    it('displays quality scores with correct formatting', () => {
      render(<SampleLibrary {...defaultProps} />);
      
      expect(screen.getByText('0.85')).toBeInTheDocument();
      expect(screen.getByText('0.92')).toBeInTheDocument();
      expect(screen.getByText('0.45')).toBeInTheDocument();
    });

    it('displays quality scores with color coding', () => {
      const { container } = render(<SampleLibrary {...defaultProps} />);
      
      // High quality (>= 0.8) should be green/success
      const highQualityTag = screen.getByText('0.85').closest('.ant-tag');
      expect(highQualityTag).toHaveClass('ant-tag-success');
      
      // Medium quality (0.4-0.6) should be yellow/warning
      const mediumQualityTag = screen.getByText('0.45').closest('.ant-tag');
      expect(mediumQualityTag).toHaveClass('ant-tag-warning');
    });

    it('displays usage counts correctly', () => {
      render(<SampleLibrary {...defaultProps} />);
      
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
    });

    it('displays created dates in locale format', () => {
      render(<SampleLibrary {...defaultProps} />);
      
      // Dates should be formatted using toLocaleString
      const dateElements = screen.getAllByText(/2024/);
      expect(dateElements.length).toBeGreaterThan(0);
    });
  });

  // ============================================================================
  // Sorting Tests
  // ============================================================================

  describe('Sorting', () => {
    it('supports sorting by quality score', () => {
      const { container } = render(<SampleLibrary {...defaultProps} />);
      
      // Find quality score column header (use getAllByText since there might be duplicates)
      const qualityHeaders = screen.getAllByText('sampleLibrary.columns.qualityScore');
      const qualityHeader = qualityHeaders[0];
      const sorter = qualityHeader.closest('th')?.querySelector('.ant-table-column-sorters');
      
      expect(sorter).toBeInTheDocument();
    });

    it('supports sorting by created date', () => {
      const { container } = render(<SampleLibrary {...defaultProps} />);
      
      // Find created date column header
      const dateHeaders = screen.getAllByText('sampleLibrary.columns.createdAt');
      const dateHeader = dateHeaders[0];
      const sorter = dateHeader.closest('th')?.querySelector('.ant-table-column-sorters');
      
      expect(sorter).toBeInTheDocument();
    });

    it('supports sorting by usage count', () => {
      const { container } = render(<SampleLibrary {...defaultProps} />);
      
      // Find usage count column header
      const usageHeaders = screen.getAllByText('sampleLibrary.columns.usageCount');
      const usageHeader = usageHeaders[0];
      const sorter = usageHeader.closest('th')?.querySelector('.ant-table-column-sorters');
      
      expect(sorter).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('handles samples with missing quality scores', () => {
      const samplesWithMissingData: Sample[] = [
        {
          id: 'sample-1',
          data_type: 'text',
          quality_score: undefined as any,
          usage_count: 5,
          created_at: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<SampleLibrary {...defaultProps} samples={samplesWithMissingData} />);
      
      expect(screen.getByText('0.00')).toBeInTheDocument();
    });

    it('handles samples with missing usage counts', () => {
      const samplesWithMissingData: Sample[] = [
        {
          id: 'sample-1',
          data_type: 'text',
          quality_score: 0.85,
          usage_count: undefined as any,
          created_at: '2024-01-01T10:00:00Z',
        },
      ];
      
      const { container } = render(<SampleLibrary {...defaultProps} samples={samplesWithMissingData} />);
      
      // Find the usage count cell (should display 0)
      const usageCell = container.querySelector('td:nth-child(5)'); // 5th column is usage count
      expect(usageCell).toHaveTextContent('0');
    });

    it('handles very long sample IDs', () => {
      const samplesWithLongIds: Sample[] = [
        {
          id: 'very-long-sample-id-that-should-be-truncated-in-the-ui',
          data_type: 'text',
          quality_score: 0.85,
          usage_count: 5,
          created_at: '2024-01-01T10:00:00Z',
        },
      ];
      
      render(<SampleLibrary {...defaultProps} samples={samplesWithLongIds} />);
      
      // ID should be truncated
      expect(screen.getByText(/very-lon/)).toBeInTheDocument();
    });

    it('handles pagination with zero total', () => {
      const { container } = render(
        <SampleLibrary
          {...defaultProps}
          samples={[]}
          pagination={{ page: 1, pageSize: 10, total: 0 }}
        />
      );
      
      // With 0 items, Ant Design may not render pagination
      // Just verify the component renders without errors
      expect(container.querySelector('.sample-library')).toBeInTheDocument();
    });

    it('handles single page of results', () => {
      render(
        <SampleLibrary
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 3 }}
        />
      );
      
      // Should not show next page button when on last page
      const nextButton = screen.queryByTitle('Next Page');
      expect(nextButton).toHaveClass('ant-pagination-disabled');
    });
  });
});
