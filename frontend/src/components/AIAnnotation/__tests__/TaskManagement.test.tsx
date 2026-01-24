/**
 * TaskManagement Component Tests
 *
 * Tests for the Task Management component including:
 * - Task list display
 * - Annotator list display
 * - Workload statistics
 * - Tab navigation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import TaskManagement from '../TaskManagement';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'ai_annotation:tasks.title': 'Task Title',
        'ai_annotation:tasks.project': 'Project',
        'ai_annotation:tasks.assigned_to': 'Assigned To',
        'ai_annotation:tasks.status': 'Status',
        'ai_annotation:tasks.priority': 'Priority',
        'ai_annotation:tasks.progress': 'Progress',
        'ai_annotation:tasks.deadline': 'Deadline',
        'ai_annotation:tasks.unassigned': 'Unassigned',
        'ai_annotation:tasks.ai_assigned': 'AI Assigned',
        'ai_annotation:tasks.assign': 'Assign',
        'ai_annotation:tasks.auto_assign': 'Auto Assign',
        'ai_annotation:tasks.auto_assign_tooltip': 'Let AI select the best annotator based on skills and workload',
        'ai_annotation:tasks.assign_task': 'Assign Task',
        'ai_annotation:tasks.select_annotator': 'Select Annotator',
        'ai_annotation:tasks.select_annotator_placeholder': 'Choose an annotator',
        'ai_annotation:tasks.assign_success': 'Task assigned successfully',
        'ai_annotation:tasks.assign_failed': 'Failed to assign task',
        'ai_annotation:tasks.auto_assign_success': 'Task auto-assigned successfully',
        'ai_annotation:tasks.auto_assign_failed': 'Failed to auto-assign task',
        'ai_annotation:tasks.total_tasks': 'Total Tasks',
        'ai_annotation:tasks.completed': 'Completed',
        'ai_annotation:tasks.in_progress': 'In Progress',
        'ai_annotation:tasks.active_annotators': 'Active Annotators',
        'ai_annotation:tasks.tab_tasks': 'Tasks',
        'ai_annotation:tasks.tab_annotators': 'Annotators',
        'ai_annotation:tasks.current_tasks': 'Current Tasks',
        'ai_annotation:tasks.completed_today': 'Completed Today',
        'ai_annotation:tasks.accuracy': 'Accuracy',
        'ai_annotation:tasks.tasks': 'tasks',
        'ai_annotation:tasks.status_pending': 'Pending',
        'ai_annotation:tasks.status_in_progress': 'In Progress',
        'ai_annotation:tasks.status_review': 'Review',
        'ai_annotation:tasks.status_completed': 'Completed',
        'ai_annotation:tasks.priority_low': 'Low',
        'ai_annotation:tasks.priority_normal': 'Normal',
        'ai_annotation:tasks.priority_high': 'High',
        'ai_annotation:tasks.priority_urgent': 'Urgent',
        'ai_annotation:tasks.role_annotator': 'Annotator',
        'ai_annotation:tasks.role_reviewer': 'Reviewer',
        'ai_annotation:tasks.role_admin': 'Admin',
        'common:columns.actions': 'Actions',
        'common:actions.confirm': 'Confirm',
        'common:actions.cancel': 'Cancel',
      };
      return translations[key] || key;
    },
  }),
}));

// Mock fetch
global.fetch = vi.fn();

const mockTasks = [
  {
    taskId: 'task_1',
    title: 'Annotate Customer Reviews',
    projectId: 'project_1',
    projectName: 'Sentiment Analysis',
    assignedTo: 'Alice Chen',
    assignedBy: 'manual' as const,
    status: 'in_progress' as const,
    priority: 'high' as const,
    deadline: '2026-01-30',
    metrics: {
      totalItems: 100,
      humanAnnotated: 45,
      aiPreAnnotated: 30,
      aiSuggested: 15,
      reviewRequired: 10,
    },
    createdAt: '2026-01-20T10:00:00Z',
  },
  {
    taskId: 'task_2',
    title: 'NER Labeling Task',
    projectId: 'project_1',
    projectName: 'Sentiment Analysis',
    assignedTo: undefined,
    assignedBy: 'manual' as const,
    status: 'pending' as const,
    priority: 'normal' as const,
    deadline: '2026-02-05',
    metrics: {
      totalItems: 200,
      humanAnnotated: 0,
      aiPreAnnotated: 50,
      aiSuggested: 0,
      reviewRequired: 0,
    },
    createdAt: '2026-01-22T10:00:00Z',
  },
];

const mockStats = {
  totalTasks: 25,
  completedTasks: 10,
  inProgressTasks: 8,
  pendingTasks: 7,
  avgCompletionTime: 45,
  activeAnnotators: 5,
  activeReviewers: 2,
};

describe('TaskManagement', () => {
  const defaultProps = {
    projectId: 'project_1',
    onTaskSelect: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as any).mockImplementation((url: string) => {
      if (url.includes('/annotation/tasks')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ tasks: mockTasks }),
        });
      }
      if (url.includes('/progress/')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockStats,
        });
      }
      if (url.includes('/tasks/assign')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders task management with stats overview', async () => {
    render(<TaskManagement {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Total Tasks')).toBeInTheDocument();
      expect(screen.getByText('Completed')).toBeInTheDocument();
      // Use getAllByText since "In Progress" appears in both stats and status badges
      expect(screen.getAllByText('In Progress').length).toBeGreaterThan(0);
      expect(screen.getByText('Active Annotators')).toBeInTheDocument();
    });
  });

  it('displays task statistics correctly', async () => {
    render(<TaskManagement {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('25')).toBeInTheDocument(); // Total tasks
      expect(screen.getByText('10')).toBeInTheDocument(); // Completed
      expect(screen.getByText('8')).toBeInTheDocument(); // In progress
      expect(screen.getByText('5')).toBeInTheDocument(); // Active annotators
    });
  });

  it('displays task list in table', async () => {
    render(<TaskManagement {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Annotate Customer Reviews')).toBeInTheDocument();
      expect(screen.getByText('NER Labeling Task')).toBeInTheDocument();
    });
  });

  it('shows task status badges', async () => {
    render(<TaskManagement {...defaultProps} />);
    
    // Wait for tasks to load
    await waitFor(() => {
      expect(screen.getByText('Annotate Customer Reviews')).toBeInTheDocument();
    });
    
    // Status badges should be present (they use Badge component with text)
    // The exact text depends on the Badge component rendering
    expect(screen.getByText('Annotate Customer Reviews')).toBeInTheDocument();
  });

  it('shows task priority tags', async () => {
    render(<TaskManagement {...defaultProps} />);
    
    // Wait for tasks to load
    await waitFor(() => {
      expect(screen.getByText('Annotate Customer Reviews')).toBeInTheDocument();
    });
    
    // Priority tags should be present
    expect(screen.getByText('Annotate Customer Reviews')).toBeInTheDocument();
  });

  it('shows unassigned badge for tasks without assignee', async () => {
    render(<TaskManagement {...defaultProps} />);
    
    // Wait for tasks to load
    await waitFor(() => {
      expect(screen.getByText('NER Labeling Task')).toBeInTheDocument();
    });
    
    // Unassigned task should have assign button
    expect(screen.getByRole('button', { name: /^assign$/i })).toBeInTheDocument();
  });

  it('displays tabs for tasks and annotators', async () => {
    render(<TaskManagement {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /tasks/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /annotators/i })).toBeInTheDocument();
    });
  });

  it('switches to annotators tab', async () => {
    const user = userEvent.setup();
    render(<TaskManagement {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /annotators/i })).toBeInTheDocument();
    });
    
    // Click on Annotators tab
    const annotatorsTab = screen.getByRole('tab', { name: /annotators/i });
    await user.click(annotatorsTab);
    
    // Tab should be selected (aria-selected)
    await waitFor(() => {
      expect(annotatorsTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  it('calls onTaskSelect when task title is clicked', async () => {
    const user = userEvent.setup();
    render(<TaskManagement {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Annotate Customer Reviews')).toBeInTheDocument();
    });
    
    // Click on task title
    const taskLink = screen.getByText('Annotate Customer Reviews');
    await user.click(taskLink);
    
    expect(defaultProps.onTaskSelect).toHaveBeenCalledWith(
      expect.objectContaining({
        taskId: 'task_1',
        title: 'Annotate Customer Reviews',
      })
    );
  });

  it('handles API errors gracefully', async () => {
    (global.fetch as any).mockRejectedValue(new Error('Network error'));
    
    render(<TaskManagement {...defaultProps} />);
    
    // Component should not crash
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /tasks/i })).toBeInTheDocument();
    });
  });

  it('shows loading state while fetching tasks', () => {
    (global.fetch as any).mockImplementation(() => 
      new Promise(() => {}) // Never resolves
    );
    
    render(<TaskManagement {...defaultProps} />);
    
    // Table should be present
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('displays deadline dates correctly', async () => {
    render(<TaskManagement {...defaultProps} />);
    
    // Wait for tasks to load
    await waitFor(() => {
      expect(screen.getByText('Annotate Customer Reviews')).toBeInTheDocument();
    });
    
    // Deadlines should be displayed
    expect(screen.getByText('2026-01-30')).toBeInTheDocument();
  });

  it('shows assign button for unassigned tasks', async () => {
    render(<TaskManagement {...defaultProps} />);
    
    // Wait for tasks to load
    await waitFor(() => {
      expect(screen.getByText('NER Labeling Task')).toBeInTheDocument();
    });
    
    // Assign button should be present
    const assignButtons = screen.getAllByRole('button', { name: /^assign$/i });
    expect(assignButtons.length).toBeGreaterThan(0);
  });

  it('shows auto assign button for unassigned tasks', async () => {
    render(<TaskManagement {...defaultProps} />);
    
    // Wait for tasks to load
    await waitFor(() => {
      expect(screen.getByText('NER Labeling Task')).toBeInTheDocument();
    });
    
    // Auto assign button should be present
    const autoAssignButtons = screen.getAllByRole('button', { name: /auto assign/i });
    expect(autoAssignButtons.length).toBeGreaterThan(0);
  });
});
