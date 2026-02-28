/**
 * TaskDeleteModal Component Tests
 *
 * Tests for task deletion confirmation, progress, and error handling.
 * Validates: Requirements 1.2
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TaskDeleteModal } from '../TaskDeleteModal';
import type { Task } from '@/types';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        'delete.title': 'Delete Task',
        'delete.batchTitle': 'Batch Delete Tasks',
        'delete.warning': 'This action cannot be undone.',
        'delete.batchConfirmMessage': `Are you sure you want to delete ${params?.count || 0} tasks?`,
        'delete.buttons.cancel': 'Cancel',
        'delete.buttons.confirm': 'Delete',
        'delete.impact.title': 'Impact',
        'delete.impact.taskInfo': 'Task information',
        'delete.impact.annotationData': 'Annotation data',
        'delete.impact.labelStudioProject': 'Label Studio project',
        'delete.options.deleteLabelStudioProject': 'Also delete Label Studio project',
        'delete.options.deleteLabelStudioProjectTip': 'This will permanently delete the project.',
        'delete.progress.deleting': 'Deleting...',
        'delete.progress.deletingTask': `Deleting task ${params?.current || 0} of ${params?.total || 0}`,
        'delete.progress.completed': 'Completed',
        'delete.progress.failed': 'Failed',
        'delete.result.success': `Successfully deleted ${params?.count || 0} tasks`,
        'delete.result.partialSuccess': `Deleted ${params?.success || 0}, failed ${params?.failed || 0}`,
        'delete.result.failed': 'Delete failed',
        'delete.result.failedTasks': 'Failed tasks:',
        taskName: 'Task Name',
        close: 'Close',
        'export.tasks': 'tasks',
      };
      return translations[key] || key;
    },
  }),
}));

// Mock API client
vi.mock('@/services', () => ({
  apiClient: {
    delete: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('@/constants', () => ({
  API_ENDPOINTS: {
    TASKS: { BY_ID: (id: string) => `/api/tasks/${id}` },
    LABEL_STUDIO: { PROJECT_BY_ID: (id: string) => `/api/label-studio/projects/${id}` },
  },
}));

const createTask = (overrides: Partial<Task> = {}): Task => ({
  id: 'task-1',
  name: 'Test Task',
  description: 'Test description',
  status: 'pending',
  priority: 'medium',
  annotation_type: 'text_classification',
  created_by: 'admin',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  progress: 50,
  total_items: 100,
  completed_items: 50,
  tenant_id: 'tenant-1',
  ...overrides,
});

describe('TaskDeleteModal', () => {
  const mockOnCancel = vi.fn();
  const mockOnSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders modal when open with single task', () => {
    render(
      <TaskDeleteModal
        open={true}
        tasks={[createTask()]}
        onCancel={mockOnCancel}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText('Delete Task')).toBeInTheDocument();
    expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <TaskDeleteModal
        open={false}
        tasks={[createTask()]}
        onCancel={mockOnCancel}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.queryByText('Delete Task')).not.toBeInTheDocument();
  });

  it('shows batch delete title for multiple tasks', () => {
    render(
      <TaskDeleteModal
        open={true}
        tasks={[createTask({ id: '1' }), createTask({ id: '2' })]}
        onCancel={mockOnCancel}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText('Batch Delete Tasks')).toBeInTheDocument();
  });

  it('displays task name for single task delete', () => {
    render(
      <TaskDeleteModal
        open={true}
        tasks={[createTask({ name: 'My Important Task' })]}
        onCancel={mockOnCancel}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText('My Important Task')).toBeInTheDocument();
  });

  it('shows cancel and delete buttons', () => {
    render(
      <TaskDeleteModal
        open={true}
        tasks={[createTask()]}
        onCancel={mockOnCancel}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <TaskDeleteModal
        open={true}
        tasks={[createTask()]}
        onCancel={mockOnCancel}
        onSuccess={mockOnSuccess}
      />
    );

    await user.click(screen.getByText('Cancel'));
    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('shows Label Studio checkbox when task has project', () => {
    render(
      <TaskDeleteModal
        open={true}
        tasks={[createTask({ label_studio_project_id: 'ls-123' })]}
        onCancel={mockOnCancel}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText('Also delete Label Studio project')).toBeInTheDocument();
  });

  it('does not show Label Studio checkbox when no project linked', () => {
    render(
      <TaskDeleteModal
        open={true}
        tasks={[createTask()]}
        onCancel={mockOnCancel}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.queryByText('Also delete Label Studio project')).not.toBeInTheDocument();
  });

  it('shows impact information', () => {
    render(
      <TaskDeleteModal
        open={true}
        tasks={[createTask({ total_items: 200, completed_items: 150 })]}
        onCancel={mockOnCancel}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText('Impact')).toBeInTheDocument();
    expect(screen.getByText('Task information')).toBeInTheDocument();
    expect(screen.getByText('Annotation data')).toBeInTheDocument();
  });

  it('calls delete API and onSuccess when confirmed', async () => {
    const user = userEvent.setup();
    const { apiClient } = await import('@/services');

    render(
      <TaskDeleteModal
        open={true}
        tasks={[createTask({ id: 'task-to-delete' })]}
        onCancel={mockOnCancel}
        onSuccess={mockOnSuccess}
      />
    );

    await user.click(screen.getByText('Delete'));

    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith('/api/tasks/task-to-delete');
    });

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalledWith(['task-to-delete']);
    }, { timeout: 3000 });
  });
});
