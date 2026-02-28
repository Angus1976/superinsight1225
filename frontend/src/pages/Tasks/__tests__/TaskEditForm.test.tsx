/**
 * TaskEditForm Component Tests
 *
 * Tests for task edit form rendering, validation, and submission.
 * Validates: Requirements 1.2
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TaskEditForm } from '../TaskEditForm';
import type { Task } from '@/types';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        taskName: 'Task Name',
        taskNameRequired: 'Please enter task name',
        enterTaskName: 'Enter task name',
        annotationType: 'Annotation Type',
        annotationTypeRequired: 'Please select annotation type',
        selectAnnotationType: 'Select annotation type',
        description: 'Description',
        enterDescription: 'Enter description',
        'columns.status': 'Status',
        'columns.priority': 'Priority',
        dueDate: 'Due Date',
        statusPending: 'Pending',
        statusInProgress: 'In Progress',
        statusCompleted: 'Completed',
        statusCancelled: 'Cancelled',
        priorityLow: 'Low',
        priorityMedium: 'Medium',
        priorityHigh: 'High',
        priorityUrgent: 'Urgent',
        typeTextClassification: 'Text Classification',
        typeNER: 'NER',
        typeSentiment: 'Sentiment',
        typeQA: 'QA',
        typeCustom: 'Custom',
        save: 'Save',
        cancel: 'Cancel',
      };
      return translations[key] || key;
    },
  }),
}));

const defaultTask: Partial<Task> = {
  id: 'task-1',
  name: 'Test Task',
  description: 'Test description',
  status: 'pending',
  priority: 'medium',
  annotation_type: 'text_classification',
};

describe('TaskEditForm', () => {
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all form fields', () => {
    render(
      <TaskEditForm
        initialValues={defaultTask}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Task Name')).toBeInTheDocument();
    expect(screen.getByText('Annotation Type')).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Priority')).toBeInTheDocument();
    expect(screen.getByText('Due Date')).toBeInTheDocument();
  });

  it('renders save and cancel buttons', () => {
    render(
      <TaskEditForm
        initialValues={defaultTask}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByRole('button', { name: /Save|save/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Cancel|cancel/ })).toBeInTheDocument();
  });

  it('populates form with initial values', () => {
    render(
      <TaskEditForm
        initialValues={defaultTask}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    const nameInput = screen.getByRole('textbox', { name: /Task Name/i });
    expect(nameInput).toHaveValue('Test Task');
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <TaskEditForm
        initialValues={defaultTask}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    await user.click(screen.getByRole('button', { name: /Cancel|cancel/ }));
    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('shows validation error when name is empty', async () => {
    const user = userEvent.setup();
    render(
      <TaskEditForm
        initialValues={{ ...defaultTask, name: '' }}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Clear the name field and submit
    const nameInput = screen.getByRole('textbox', { name: /Task Name/i });
    await user.clear(nameInput);
    await user.click(screen.getByRole('button', { name: /Save|save/ }));

    await waitFor(() => {
      expect(screen.getByText('Please enter task name')).toBeInTheDocument();
    });
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows loading state on save button', () => {
    render(
      <TaskEditForm
        initialValues={defaultTask}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        loading={true}
      />
    );

    const saveButton = screen.getByRole('button', { name: /Save|save/ });
    expect(saveButton).toHaveClass('ant-btn-loading');
  });

  it('submits form with correct values', async () => {
    const user = userEvent.setup();
    render(
      <TaskEditForm
        initialValues={defaultTask}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    // Modify the name
    const nameInput = screen.getByRole('textbox', { name: /Task Name/i });
    await user.clear(nameInput);
    await user.type(nameInput, 'Updated Task Name');

    await user.click(screen.getByRole('button', { name: /Save|save/ }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Updated Task Name',
          status: 'pending',
          priority: 'medium',
          annotation_type: 'text_classification',
        })
      );
    });
  });

  it('renders with empty initial values', () => {
    render(
      <TaskEditForm
        initialValues={{}}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Task Name')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save|save/ })).toBeInTheDocument();
  });
});
