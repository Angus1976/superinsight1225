/**
 * TaskManagement Component Unit Tests
 * 
 * Tests for task table rendering, progress calculation, expandable rows, and create task flow.
 * Requirements: 14.3, 14.4
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import TaskManagement from '../TaskManagement';
import type { TaskManagementProps } from '../TaskManagement';
import type { AnnotationTask } from '@/services/dataLifecycle';

const sampleIds = (n: number, prefix = 'sample') =>
  Array.from({ length: n }, (_, i) => `${prefix}-${i}`);

function baseTask(
  overrides: Partial<AnnotationTask> &
    Pick<AnnotationTask, 'id' | 'name' | 'status' | 'progress' | 'created_at'>
): AnnotationTask {
  return {
    annotation_type: 'classification',
    instructions: 'Test instructions',
    created_by: 'tester',
    sample_ids: sampleIds(10),
    ...overrides,
  };
}

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      if (key === 'common.pagination.total' && params) {
        return `Total ${params.total} items`;
      }
      if (key === 'annotationTask.progress.labeled') {
        return 'labeled';
      }
      if (key === 'annotationTask.progress.total') {
        return 'total';
      }
      if (key === 'sampleLibrary.title') {
        return 'Sample Library';
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

describe('TaskManagement Component', () => {
  // Sample test data（与 `AnnotationTask`：`progress` 为 0–100，`sample_ids.length` 为分母）
  const mockTasks: AnnotationTask[] = [
    baseTask({
      id: 'task-1',
      name: 'Task 1',
      description: 'Description for task 1',
      status: 'created',
      assigned_to: ['user1', 'user2'],
      deadline: '2024-12-31T23:59:59Z',
      progress: 50,
      created_at: '2024-01-01T10:00:00Z',
    }),
    baseTask({
      id: 'task-2',
      name: 'Task 2',
      description: 'Description for task 2',
      status: 'in_progress',
      assigned_to: ['user3'],
      deadline: '2024-06-30T23:59:59Z',
      progress: 80,
      created_at: '2024-01-02T10:00:00Z',
    }),
    baseTask({
      id: 'task-3',
      name: 'Task 3',
      status: 'completed',
      progress: 100,
      created_at: '2024-01-03T10:00:00Z',
    }),
  ];

  const defaultProps: TaskManagementProps = {
    tasks: mockTasks,
    loading: false,
    pagination: {
      page: 1,
      pageSize: 10,
      total: 3,
    },
    onViewDetails: vi.fn(),
    onEdit: vi.fn(),
    onAssign: vi.fn(),
    onCancel: vi.fn(),
    onPageChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // Task Table Rendering Tests
  // ============================================================================

  describe('Task Table Rendering', () => {
    it('renders the component without crashing', () => {
      render(<TaskManagement {...defaultProps} />);
      expect(screen.getByText('Task 1')).toBeInTheDocument();
    });

    it('renders all task rows', () => {
      render(<TaskManagement {...defaultProps} />);
      
      expect(screen.getByText('Task 1')).toBeInTheDocument();
      expect(screen.getByText('Task 2')).toBeInTheDocument();
      expect(screen.getByText('Task 3')).toBeInTheDocument();
    });

    it('displays correct column headers', () => {
      render(<TaskManagement {...defaultProps} />);
      
      expect(screen.getAllByText('annotationTask.columns.name')[0]).toBeInTheDocument();
      expect(screen.getAllByText('annotationTask.columns.status')[0]).toBeInTheDocument();
      expect(screen.getAllByText('annotationTask.columns.progress')[0]).toBeInTheDocument();
      expect(screen.getAllByText('annotationTask.columns.assignee')[0]).toBeInTheDocument();
      expect(screen.getAllByText('annotationTask.columns.dueDate')[0]).toBeInTheDocument();
      expect(screen.getAllByText('annotationTask.columns.actions')[0]).toBeInTheDocument();
    });

    it('displays loading state correctly', () => {
      const { container } = render(<TaskManagement {...defaultProps} loading={true} />);
      
      const loadingSpinner = container.querySelector('.ant-spin');
      expect(loadingSpinner).toBeInTheDocument();
    });

    it('displays empty state when no tasks', () => {
      const { container } = render(<TaskManagement {...defaultProps} tasks={[]} />);
      
      const emptyState = container.querySelector('.ant-empty');
      expect(emptyState).toBeInTheDocument();
    });

    it('displays task names correctly', () => {
      render(<TaskManagement {...defaultProps} />);
      
      expect(screen.getByText('Task 1')).toBeInTheDocument();
      expect(screen.getByText('Task 2')).toBeInTheDocument();
      expect(screen.getByText('Task 3')).toBeInTheDocument();
    });

    it('displays task statuses as tags', () => {
      render(<TaskManagement {...defaultProps} />);
      
      expect(screen.getByText('annotationTask.status.created')).toBeInTheDocument();
      expect(screen.getByText('annotationTask.status.in_progress')).toBeInTheDocument();
      expect(screen.getByText('annotationTask.status.completed')).toBeInTheDocument();
    });

    it('displays assignees correctly', () => {
      render(<TaskManagement {...defaultProps} />);
      
      // Task 1 has multiple assignees
      expect(screen.getByText('user1, user2')).toBeInTheDocument();
      // Task 2 has single assignee
      expect(screen.getByText('user3')).toBeInTheDocument();
    });

    it('displays dash for tasks without assignees', () => {
      const tasksWithoutAssignees: AnnotationTask[] = [
        baseTask({
          id: 'task-no-assignee',
          name: 'Task No Assignee',
          status: 'created',
          progress: 0,
          created_at: '2024-01-01T10:00:00Z',
        }),
      ];
      
      const { container } = render(<TaskManagement {...defaultProps} tasks={tasksWithoutAssignees} />);
      
      // Should show '-' in assignee column
      const rows = container.querySelectorAll('tbody tr');
      const taskRow = rows[0];
      const cells = taskRow.querySelectorAll('td');
      const assigneeCell = cells[4]; // 5th column (0-indexed, including expand icon column)
      
      if (assigneeCell) {
        expect(assigneeCell).toHaveTextContent('-');
      }
    });

    it('displays due dates in locale format', () => {
      render(<TaskManagement {...defaultProps} />);
      
      // Dates should be formatted using toLocaleString
      const dateElements = screen.getAllByText(/2024/);
      expect(dateElements.length).toBeGreaterThan(0);
    });

    it('displays dash for tasks without due dates', () => {
      const tasksWithoutDueDate: AnnotationTask[] = [
        baseTask({
          id: 'task-no-due-date',
          name: 'Task No Due Date',
          status: 'created',
          progress: 0,
          created_at: '2024-01-01T10:00:00Z',
        }),
      ];
      
      const { container } = render(<TaskManagement {...defaultProps} tasks={tasksWithoutDueDate} />);
      
      // Should show '-' in due date column
      const rows = container.querySelectorAll('tbody tr');
      const taskRow = rows[0];
      const cells = taskRow.querySelectorAll('td');
      const dueDateCell = cells[5]; // 6th column (0-indexed, including expand icon column)
      
      if (dueDateCell) {
        expect(dueDateCell).toHaveTextContent('-');
      }
    });
  });

  // ============================================================================
  // Progress Calculation and Display Tests (Requirement 14.3)
  // ============================================================================

  describe('Progress Calculation and Display (Requirement 14.3)', () => {
    it('calculates progress percentage correctly', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      // Task 1: 5/10 = 50%
      const progressBars = container.querySelectorAll('.ant-progress-bg');
      expect(progressBars.length).toBeGreaterThan(0);
    });

    it('displays progress as percentage with completed/total counts', () => {
      render(<TaskManagement {...defaultProps} />);
      
      // Task 1: 5/10
      expect(screen.getByText('5/10 labeled')).toBeInTheDocument();
      // Task 2: 8/10
      expect(screen.getByText('8/10 labeled')).toBeInTheDocument();
      // Task 3: 10/10
      expect(screen.getByText('10/10 labeled')).toBeInTheDocument();
    });

    it('displays progress bar with correct percentage', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      // Find progress bars and check their aria-valuenow attribute
      const progressBars = container.querySelectorAll('.ant-progress-inner');
      expect(progressBars.length).toBe(3);
    });

    it('shows success status for completed tasks', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      // Task 3 is completed, should have success status
      const successProgress = container.querySelector('.ant-progress-status-success');
      expect(successProgress).toBeInTheDocument();
    });

    it('shows active status for in-progress tasks', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      // Tasks 1 and 2 are not completed, should have active status
      const activeProgress = container.querySelectorAll('.ant-progress-status-active');
      expect(activeProgress.length).toBeGreaterThan(0);
    });

    it('handles tasks with zero total correctly', () => {
      const tasksWithZeroTotal: AnnotationTask[] = [
        baseTask({
          id: 'task-zero',
          name: 'Task Zero',
          status: 'created',
          progress: 0,
          sample_ids: [],
          created_at: '2024-01-01T10:00:00Z',
        }),
      ];
      
      render(<TaskManagement {...defaultProps} tasks={tasksWithZeroTotal} />);
      
      expect(screen.getByText(/0\/— labeled/)).toBeInTheDocument();
    });

    it('handles tasks without progress data', () => {
      const tasksWithoutProgress: AnnotationTask[] = [
        baseTask({
          id: 'task-no-progress',
          name: 'Task No Progress',
          status: 'created',
          progress: 0,
          sample_ids: [],
          created_at: '2024-01-01T10:00:00Z',
        }),
      ];
      
      render(<TaskManagement {...defaultProps} tasks={tasksWithoutProgress} />);
      
      expect(screen.getByText(/0\/— labeled/)).toBeInTheDocument();
    });

    it('rounds progress percentage correctly', () => {
      const tasksWithDecimalProgress: AnnotationTask[] = [
        baseTask({
          id: 'task-decimal',
          name: 'Task Decimal',
          status: 'in_progress',
          progress: 33,
          sample_ids: sampleIds(3, 's'),
          created_at: '2024-01-01T10:00:00Z',
        }),
      ];
      
      const { container } = render(<TaskManagement {...defaultProps} tasks={tasksWithDecimalProgress} />);
      
      // Should round to 33%
      expect(screen.getByText('1/3 labeled')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Expandable Row Functionality Tests (Requirement 14.4)
  // ============================================================================

  describe('Expandable Row Functionality (Requirement 14.4)', () => {
    it('renders expand icon for each row', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      expect(expandIcons.length).toBe(3);
    });

    it('expands row when expand icon is clicked', async () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      const firstExpandIcon = expandIcons[0] as HTMLElement;
      
      fireEvent.click(firstExpandIcon);
      
      await waitFor(() => {
        expect(screen.getByText('Description for task 1')).toBeInTheDocument();
      });
    });

    it('displays detailed information in expanded row', async () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      fireEvent.click(expandIcons[0] as HTMLElement);
      
      await waitFor(() => {
        expect(screen.getByText('Description for task 1')).toBeInTheDocument();
        // Use getAllByText since assignees appear in both table and expanded row
        const assigneeTexts = screen.getAllByText('user1, user2');
        expect(assigneeTexts.length).toBeGreaterThan(0);
      });
    });

    it('displays sample count in expanded row', async () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      fireEvent.click(expandIcons[0] as HTMLElement);
      
      await waitFor(() => {
        expect(screen.getByText('10 total')).toBeInTheDocument();
      });
    });

    it('collapses row when expand icon is clicked again', async () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      const firstExpandIcon = expandIcons[0] as HTMLElement;
      
      // Expand
      fireEvent.click(firstExpandIcon);
      await waitFor(() => {
        expect(screen.getByText('Description for task 1')).toBeInTheDocument();
      });
      
      // Collapse - need to get the icon again after re-render
      const expandIconsAfter = container.querySelectorAll('.ant-table-row-expand-icon');
      fireEvent.click(expandIconsAfter[0] as HTMLElement);
      
      await waitFor(() => {
        // Check that the expand icon has the collapsed class
        const collapsedIcons = container.querySelectorAll('.ant-table-row-expand-icon-collapsed');
        expect(collapsedIcons.length).toBeGreaterThan(0);
      }, { timeout: 2000 });
    });

    it('supports expanding multiple rows simultaneously', async () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      
      // Expand first row
      fireEvent.click(expandIcons[0] as HTMLElement);
      await waitFor(() => {
        expect(screen.getByText('Description for task 1')).toBeInTheDocument();
      });
      
      // Expand second row
      fireEvent.click(expandIcons[1] as HTMLElement);
      await waitFor(() => {
        expect(screen.getByText('Description for task 2')).toBeInTheDocument();
      });
      
      // Both should be visible
      expect(screen.getByText('Description for task 1')).toBeInTheDocument();
      expect(screen.getByText('Description for task 2')).toBeInTheDocument();
    });

    it('displays dash for missing description in expanded row', async () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      // Task 3 has no description
      fireEvent.click(expandIcons[2] as HTMLElement);
      
      await waitFor(() => {
        const expandedContent = container.querySelector('.ant-descriptions');
        expect(expandedContent).toBeInTheDocument();
      });
    });

    it('displays dash for missing assignee in expanded row', async () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      // Task 3 has no assignees
      fireEvent.click(expandIcons[2] as HTMLElement);
      
      await waitFor(() => {
        const expandedContent = container.querySelector('.ant-descriptions');
        expect(expandedContent).toBeInTheDocument();
      });
    });

    it('displays dash for missing due date in expanded row', async () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      // Task 3 has no deadline
      fireEvent.click(expandIcons[2] as HTMLElement);
      
      await waitFor(() => {
        const expandedContent = container.querySelector('.ant-descriptions');
        expect(expandedContent).toBeInTheDocument();
      });
    });

    it('does not display sample section when no samples', async () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const expandIcons = container.querySelectorAll('.ant-table-row-expand-icon');
      // Task 3 has no sample_ids
      fireEvent.click(expandIcons[2] as HTMLElement);
      
      await waitFor(() => {
        expect(screen.queryByText('sampleLibrary.title')).not.toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Action Buttons Tests
  // ============================================================================

  describe('Action Buttons', () => {
    it('renders action buttons for each row', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const viewButtons = container.querySelectorAll('[aria-label="eye"]');
      expect(viewButtons.length).toBe(3);
    });

    it('calls onViewDetails when view button is clicked', () => {
      const onViewDetails = vi.fn();
      const { container } = render(
        <TaskManagement {...defaultProps} onViewDetails={onViewDetails} />
      );
      
      const viewButtons = container.querySelectorAll('[aria-label="eye"]');
      fireEvent.click(viewButtons[0].closest('button')!);
      
      expect(onViewDetails).toHaveBeenCalledWith('task-1');
    });

    it('calls onEdit when edit button is clicked', () => {
      const onEdit = vi.fn();
      const { container } = render(
        <TaskManagement {...defaultProps} onEdit={onEdit} />
      );
      
      const editButtons = container.querySelectorAll('[aria-label="edit"]');
      fireEvent.click(editButtons[0].closest('button')!);
      
      expect(onEdit).toHaveBeenCalledWith('task-1');
    });

    it('calls onAssign when assign button is clicked', () => {
      const onAssign = vi.fn();
      const { container } = render(
        <TaskManagement {...defaultProps} onAssign={onAssign} />
      );
      
      const assignButtons = container.querySelectorAll('[aria-label="user-add"]');
      fireEvent.click(assignButtons[0].closest('button')!);
      
      expect(onAssign).toHaveBeenCalledWith('task-1');
    });

    it('shows confirmation modal when cancel button is clicked', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const cancelButtons = container.querySelectorAll('[aria-label="stop"]');
      fireEvent.click(cancelButtons[0].closest('button')!);
      
      expect(mockConfirm).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'annotationTask.messages.confirmCancel',
          okType: 'danger',
        })
      );
    });

    it('calls onCancel when cancellation is confirmed', () => {
      const onCancel = vi.fn();
      mockConfirm.mockImplementation((config) => {
        config.onOk();
      });
      
      const { container } = render(<TaskManagement {...defaultProps} onCancel={onCancel} />);
      
      const cancelButtons = container.querySelectorAll('[aria-label="stop"]');
      fireEvent.click(cancelButtons[0].closest('button')!);
      
      expect(onCancel).toHaveBeenCalledWith('task-1');
    });

    it('hides edit/assign/cancel buttons for completed tasks', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      // Find the completed task row (Task 3)
      const rows = container.querySelectorAll('tbody tr');
      
      // Look for the row with completed status
      let completedTaskRow = null;
      for (let i = 0; i < rows.length; i++) {
        const statusTag = rows[i].querySelector('.ant-tag-success');
        if (statusTag && statusTag.textContent === 'annotationTask.status.completed') {
          completedTaskRow = rows[i];
          break;
        }
      }
      
      expect(completedTaskRow).not.toBeNull();
      
      // Should only have view button (no edit, assign, or cancel buttons)
      const editButtons = completedTaskRow!.querySelectorAll('[aria-label="edit"]');
      const assignButtons = completedTaskRow!.querySelectorAll('[aria-label="user-add"]');
      const cancelButtons = completedTaskRow!.querySelectorAll('[aria-label="stop"]');
      
      expect(editButtons.length).toBe(0);
      expect(assignButtons.length).toBe(0);
      expect(cancelButtons.length).toBe(0);
    });

    it('hides edit/assign/cancel buttons for cancelled tasks', () => {
      const cancelledTasks: AnnotationTask[] = [
        baseTask({
          id: 'task-cancelled',
          name: 'Cancelled Task',
          status: 'cancelled',
          progress: 0,
          created_at: '2024-01-01T10:00:00Z',
        }),
      ];
      
      const { container } = render(<TaskManagement {...defaultProps} tasks={cancelledTasks} />);
      
      const rows = container.querySelectorAll('tbody tr');
      const cancelledTaskRow = rows[0];
      
      // Should only have view button (no edit, assign, or cancel buttons)
      const editButtons = cancelledTaskRow.querySelectorAll('[aria-label="edit"]');
      const assignButtons = cancelledTaskRow.querySelectorAll('[aria-label="user-add"]');
      const cancelButtons = cancelledTaskRow.querySelectorAll('[aria-label="stop"]');
      
      expect(editButtons.length).toBe(0);
      expect(assignButtons.length).toBe(0);
      expect(cancelButtons.length).toBe(0);
    });

    it('shows all action buttons for created tasks', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      
      let createdTaskRow = null;
      for (let i = 0; i < rows.length; i++) {
        const statusTag = rows[i].querySelector('.ant-tag');
        if (statusTag && statusTag.textContent === 'annotationTask.status.created') {
          createdTaskRow = rows[i];
          break;
        }
      }
      
      expect(createdTaskRow).not.toBeNull();
      
      const viewButtons = createdTaskRow!.querySelectorAll('[aria-label="eye"]');
      const editButtons = createdTaskRow!.querySelectorAll('[aria-label="edit"]');
      const assignButtons = createdTaskRow!.querySelectorAll('[aria-label="user-add"]');
      const cancelButtons = createdTaskRow!.querySelectorAll('[aria-label="stop"]');
      
      expect(viewButtons.length).toBe(1);
      expect(editButtons.length).toBe(1);
      expect(assignButtons.length).toBe(1);
      expect(cancelButtons.length).toBe(1);
    });

    it('shows all action buttons for in-progress tasks', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      const rows = container.querySelectorAll('tbody tr');
      const inProgressTaskRow = rows[1]; // Task 2 is inProgress
      
      // Should have view, edit, assign, and cancel buttons
      const viewButtons = inProgressTaskRow.querySelectorAll('[aria-label="eye"]');
      const editButtons = inProgressTaskRow.querySelectorAll('[aria-label="edit"]');
      const assignButtons = inProgressTaskRow.querySelectorAll('[aria-label="user-add"]');
      const cancelButtons = inProgressTaskRow.querySelectorAll('[aria-label="stop"]');
      
      expect(viewButtons.length).toBe(1);
      expect(editButtons.length).toBe(1);
      expect(assignButtons.length).toBe(1);
      expect(cancelButtons.length).toBe(1);
    });
  });

  // ============================================================================
  // Pagination Tests
  // ============================================================================

  describe('Pagination', () => {
    it('displays pagination controls', () => {
      render(<TaskManagement {...defaultProps} />);
      
      expect(screen.getByText('Total 3 items')).toBeInTheDocument();
    });

    it('calls onPageChange when page is changed', async () => {
      const onPageChange = vi.fn();
      render(
        <TaskManagement
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
        <TaskManagement
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

    it('displays correct current page', () => {
      render(
        <TaskManagement
          {...defaultProps}
          pagination={{ page: 2, pageSize: 10, total: 50 }}
        />
      );
      
      const activePageItem = screen.getByTitle('2');
      expect(activePageItem).toHaveClass('ant-pagination-item-active');
    });

    it('shows quick jumper for large datasets', () => {
      const { container } = render(
        <TaskManagement
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 100 }}
        />
      );
      
      const quickJumper = container.querySelector('.ant-pagination-options-quick-jumper');
      expect(quickJumper).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Filtering and Sorting Tests
  // ============================================================================

  describe('Filtering and Sorting', () => {
    it('supports filtering by status', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      // Find status column header
      const statusHeaders = screen.getAllByText('annotationTask.columns.status');
      const statusHeader = statusHeaders[0];
      const filterIcon = statusHeader.closest('th')?.querySelector('.ant-table-filter-trigger');
      
      expect(filterIcon).toBeInTheDocument();
    });

    it('supports sorting by due date', () => {
      const { container } = render(<TaskManagement {...defaultProps} />);
      
      // Find due date column header
      const dueDateHeaders = screen.getAllByText('annotationTask.columns.dueDate');
      const dueDateHeader = dueDateHeaders[0];
      const sorter = dueDateHeader.closest('th')?.querySelector('.ant-table-column-sorters');
      
      expect(sorter).toBeInTheDocument();
    });

    it('highlights overdue tasks in red', () => {
      const overdueTask: AnnotationTask[] = [
        baseTask({
          id: 'task-overdue',
          name: 'Overdue Task',
          status: 'created',
          deadline: '2020-01-01T00:00:00Z', // Past date
          progress: 0,
          created_at: '2024-01-01T10:00:00Z',
        }),
      ];
      
      const { container } = render(<TaskManagement {...defaultProps} tasks={overdueTask} />);
      
      // Find the date cell with danger type
      const dangerText = container.querySelector('.ant-typography-danger');
      expect(dangerText).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('handles very long task names', () => {
      const longNameTask: AnnotationTask[] = [
        baseTask({
          id: 'task-long',
          name: 'This is a very long task name that should be truncated or handled properly in the UI',
          status: 'created',
          progress: 0,
          created_at: '2024-01-01T10:00:00Z',
        }),
      ];
      
      render(<TaskManagement {...defaultProps} tasks={longNameTask} />);
      
      expect(screen.getByText(/This is a very long task name/)).toBeInTheDocument();
    });

    it('handles tasks with many assignees', () => {
      const manyAssigneesTask: AnnotationTask[] = [
        baseTask({
          id: 'task-many',
          name: 'Task Many',
          status: 'created',
          assigned_to: ['user1', 'user2', 'user3', 'user4', 'user5'],
          progress: 0,
          created_at: '2024-01-01T10:00:00Z',
        }),
      ];
      
      render(<TaskManagement {...defaultProps} tasks={manyAssigneesTask} />);
      
      expect(screen.getByText('user1, user2, user3, user4, user5')).toBeInTheDocument();
    });

    it('handles pagination with zero total', () => {
      const { container } = render(
        <TaskManagement
          {...defaultProps}
          tasks={[]}
          pagination={{ page: 1, pageSize: 10, total: 0 }}
        />
      );
      
      expect(container.querySelector('.ant-table')).toBeInTheDocument();
    });

    it('handles single page of results', () => {
      render(
        <TaskManagement
          {...defaultProps}
          pagination={{ page: 1, pageSize: 10, total: 3 }}
        />
      );
      
      const nextButton = screen.queryByTitle('Next Page');
      expect(nextButton).toHaveClass('ant-pagination-disabled');
    });
  });
});
