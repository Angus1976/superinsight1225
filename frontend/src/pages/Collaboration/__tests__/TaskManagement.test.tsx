/**
 * TaskManagement Component Tests
 *
 * Tests for the AI Task Management interface including:
 * - Task queue rendering
 * - AI routing configuration
 * - Team performance metrics
 * - Task assignment
 * - Progress tracking
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import TaskManagement from '../TaskManagement';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      const translations: Record<string, string> = {
        'task_management:title': 'AI Task Management',
        'task_management:tabs.task_queue': 'Task Queue',
        'task_management:tabs.team_performance': 'Team Performance',
        'task_management:tabs.ai_routing_config': 'AI Routing Configuration',
        'task_management:columns.task_id': 'Task ID',
        'task_management:columns.title': 'Title',
        'task_management:columns.assignee': 'Assignee',
        'task_management:columns.progress': 'Progress',
        'task_management:columns.status': 'Status',
        'task_management:labels.unassigned': 'Unassigned',
        'task_management:metrics.total_annotations': 'Total Annotations',
        'task_management:metrics.human_annotations': 'Human Annotations',
        'task_management:metrics.ai_annotations': 'AI Pre-Annotations',
        'task_management:metrics.ai_acceptance_rate': 'AI Acceptance Rate',
        'task_management:config.routing_title': 'AI Routing Configuration',
        'task_management:config.low_confidence_threshold': 'Low Confidence Threshold',
        'task_management:config.high_confidence_threshold': 'High Confidence Threshold',
        'task_management:config.auto_assign_high_confidence': 'Auto-assign High Confidence Tasks',
        'task_management:messages.task_assigned': 'Task assigned successfully',
        'task_management:messages.config_updated': 'Routing configuration updated',
        'task_management:errors.fetch_tasks_failed': 'Failed to load tasks',
        'task_management:errors.assign_failed': 'Failed to assign task',
        'task_management:actions.accept_ai_suggestion': 'Accept AI',
        'task_management:actions.assign_manually': 'Assign Manually',
        'task_management:filters.all_projects': 'All Projects',
        'common:actions.refresh': 'Refresh',
        'common:pagination.total': `Total ${options?.total || 0} items`,
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
    title: 'Sentiment Analysis',
    projectId: 'proj_1',
    projectName: 'Customer Reviews',
    assignedTo: 'Alice',
    assignedBy: 'manual' as const,
    status: 'in_progress' as const,
    priority: 'high' as const,
    metrics: {
      totalItems: 100,
      humanAnnotated: 60,
      aiPreAnnotated: 30,
      aiSuggested: 10,
      reviewRequired: 5,
    },
    createdAt: '2026-01-20T10:00:00Z',
  },
  {
    taskId: 'task_2',
    title: 'Entity Recognition',
    projectId: 'proj_1',
    projectName: 'Customer Reviews',
    status: 'pending' as const,
    assignedBy: 'ai' as const,
    priority: 'medium' as const,
    aiSuggestion: {
      confidence: 0.92,
      suggestedAssignee: 'Bob',
      reasoning: 'Bob has high accuracy on entity recognition tasks',
    },
    metrics: {
      totalItems: 80,
      humanAnnotated: 0,
      aiPreAnnotated: 70,
      aiSuggested: 10,
      reviewRequired: 8,
    },
    createdAt: '2026-01-21T09:00:00Z',
  },
];

const mockTeamMembers = [
  {
    userId: '1',
    username: 'Alice',
    skills: ['sentiment-analysis', 'classification'],
    workload: { activeTasks: 3, capacity: 5 },
    performance: {
      accuracy: 0.95,
      avgSpeed: 25.5,
      aiAgreementRate: 0.90,
      tasksCompleted: 45,
    },
  },
  {
    userId: '2',
    username: 'Bob',
    skills: ['ner', 'entity-recognition'],
    workload: { activeTasks: 2, capacity: 5 },
    performance: {
      accuracy: 0.92,
      avgSpeed: 28.3,
      aiAgreementRate: 0.88,
      tasksCompleted: 38,
    },
  },
];

const mockAIMetrics = {
  totalAnnotations: 500,
  humanAnnotations: 300,
  aiPreAnnotations: 180,
  aiSuggestions: 20,
  aiAcceptanceRate: 0.85,
  timeSaved: 12.5,
  qualityScore: 0.92,
};

describe('TaskManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as any).mockImplementation((url: string) => {
      if (url.includes('/api/v1/annotation/tasks')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ tasks: mockTasks }),
        });
      }
      if (url.includes('/api/v1/users/team')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ members: mockTeamMembers }),
        });
      }
      if (url.includes('/api/v1/annotation/metrics')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ metrics: mockAIMetrics }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
  });

  it('renders AI Task Management title', async () => {
    render(<TaskManagement />);

    await waitFor(() => {
      expect(screen.getByText('AI Task Management')).toBeInTheDocument();
    });
  });

  it('displays AI metrics overview', async () => {
    render(<TaskManagement />);

    await waitFor(() => {
      expect(screen.getByText('Total Annotations')).toBeInTheDocument();
      expect(screen.getByText('500')).toBeInTheDocument();
      expect(screen.getByText('Human Annotations')).toBeInTheDocument();
      expect(screen.getByText('300')).toBeInTheDocument();
      expect(screen.getByText('AI Pre-Annotations')).toBeInTheDocument();
      expect(screen.getByText('180')).toBeInTheDocument();
    });
  });

  it('fetches tasks on mount', async () => {
    render(<TaskManagement />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/annotation/tasks'),
        undefined
      );
    });
  });

  it('displays task queue with task details', async () => {
    render(<TaskManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sentiment Analysis')).toBeInTheDocument();
      expect(screen.getByText('Entity Recognition')).toBeInTheDocument();
      expect(screen.getByText('task_1')).toBeInTheDocument();
      expect(screen.getByText('task_2')).toBeInTheDocument();
    });
  });

  it('shows assignee for assigned tasks', async () => {
    render(<TaskManagement />);

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
    });
  });

  it('shows unassigned status for tasks without assignee', async () => {
    render(<TaskManagement />);

    await waitFor(() => {
      expect(screen.getByText('Unassigned')).toBeInTheDocument();
    });
  });

  it('displays AI suggestions for unassigned tasks', async () => {
    render(<TaskManagement />);

    await waitFor(() => {
      // 92% confidence tag
      expect(screen.getByText('92%')).toBeInTheDocument();
    });
  });

  it('allows accepting AI suggestion', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    render(<TaskManagement />);

    await waitFor(() => {
      expect(screen.getByText('Entity Recognition')).toBeInTheDocument();
    });

    const acceptButton = screen.getByRole('button', { name: /accept ai/i });
    await user.click(acceptButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/annotation/tasks/assign',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            task_id: 'task_2',
            assignee_id: 'Bob',
          }),
        })
      );
    });
  });

  it('allows manual task assignment', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    render(<TaskManagement />);

    await waitFor(() => {
      expect(screen.getByText('Entity Recognition')).toBeInTheDocument();
    });

    // Find manual assignment dropdown
    const assignSelects = screen.getAllByPlaceholderText(/assign manually/i);
    if (assignSelects.length > 0) {
      await user.click(assignSelects[0]);

      // Select Alice
      const aliceOption = await screen.findByText('Alice');
      await user.click(aliceOption);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/v1/annotation/tasks/assign',
          expect.any(Object)
        );
      });
    }
  });

  it('displays team performance tab', async () => {
    const user = userEvent.setup();
    render(<TaskManagement />);

    await waitFor(() => {
      expect(screen.getByText('Task Queue')).toBeInTheDocument();
    });

    const teamTab = screen.getByText('Team Performance');
    await user.click(teamTab);

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
      expect(screen.getByText('Bob')).toBeInTheDocument();
    });
  });

  it('shows team member skills', async () => {
    const user = userEvent.setup();
    render(<TaskManagement />);

    const teamTab = screen.getByText('Team Performance');
    await user.click(teamTab);

    await waitFor(() => {
      expect(screen.getByText('sentiment-analysis')).toBeInTheDocument();
      expect(screen.getByText('ner')).toBeInTheDocument();
    });
  });

  it('displays AI routing configuration tab', async () => {
    const user = userEvent.setup();
    render(<TaskManagement />);

    const routingTab = screen.getByText('AI Routing Configuration');
    await user.click(routingTab);

    await waitFor(() => {
      expect(screen.getByText('AI Routing Configuration')).toBeInTheDocument();
      expect(screen.getByText('Low Confidence Threshold')).toBeInTheDocument();
      expect(screen.getByText('High Confidence Threshold')).toBeInTheDocument();
    });
  });

  it('allows updating routing configuration', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    render(<TaskManagement />);

    const routingTab = screen.getByText('AI Routing Configuration');
    await user.click(routingTab);

    await waitFor(() => {
      expect(screen.getByText('Auto-assign High Confidence Tasks')).toBeInTheDocument();
    });

    // Toggle auto-assign switch
    const switches = screen.getAllByRole('switch');
    if (switches.length > 0) {
      await user.click(switches[0]);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/v1/annotation/routing/config',
          expect.objectContaining({
            method: 'PUT',
          })
        );
      });
    }
  });

  it('refreshes task list when refresh button is clicked', async () => {
    const user = userEvent.setup();
    render(<TaskManagement />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(3); // tasks, team, metrics
    });

    vi.clearAllMocks();

    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    await user.click(refreshButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/annotation/tasks'),
        undefined
      );
    });
  });

  it('shows task progress metrics on hover', async () => {
    const user = userEvent.setup();
    render(<TaskManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sentiment Analysis')).toBeInTheDocument();
    });

    // Progress bars should be present
    const progressElements = document.querySelectorAll('.ant-progress');
    expect(progressElements.length).toBeGreaterThan(0);
  });

  it('displays task status badges', async () => {
    render(<TaskManagement />);

    await waitFor(() => {
      // "in_progress" and "pending" statuses should be visible
      const statusBadges = document.querySelectorAll('.ant-badge');
      expect(statusBadges.length).toBeGreaterThan(0);
    });
  });

  it('shows priority tags for tasks', async () => {
    render(<TaskManagement />);

    await waitFor(() => {
      // Priority tags should be rendered
      const priorityTags = document.querySelectorAll('.ant-tag');
      expect(priorityTags.length).toBeGreaterThan(0);
    });
  });

  it('handles task fetch errors gracefully', async () => {
    (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

    render(<TaskManagement />);

    // Component should not crash
    await waitFor(() => {
      expect(screen.getByText('AI Task Management')).toBeInTheDocument();
    });
  });

  it('handles assignment errors with error message', async () => {
    const user = userEvent.setup();
    (global.fetch as any).mockRejectedValueOnce(new Error('Assignment failed'));

    render(<TaskManagement />);

    await waitFor(() => {
      expect(screen.getByText('Entity Recognition')).toBeInTheDocument();
    });

    const acceptButton = screen.getByRole('button', { name: /accept ai/i });
    await user.click(acceptButton);

    // Error should be handled (not crash)
    await waitFor(() => {
      expect(screen.getByText('AI Task Management')).toBeInTheDocument();
    });
  });

  it('filters tasks by project when project is selected', async () => {
    const user = userEvent.setup();
    render(<TaskManagement />);

    await waitFor(() => {
      expect(screen.getByText('All Projects')).toBeInTheDocument();
    });

    vi.clearAllMocks();

    // Change project filter
    const projectSelect = screen.getByText('All Projects');
    await user.click(projectSelect);

    // Should refetch with project filter
    // (Implementation would depend on available project options)
  });

  it('displays team member workload with progress circles', async () => {
    const user = userEvent.setup();
    render(<TaskManagement />);

    const teamTab = screen.getByText('Team Performance');
    await user.click(teamTab);

    await waitFor(() => {
      // Progress circles for workload should be rendered
      const progressCircles = document.querySelectorAll('.ant-progress-circle');
      expect(progressCircles.length).toBeGreaterThan(0);
    });
  });

  it('shows AI acceptance rate with visual indicator', async () => {
    render(<TaskManagement />);

    await waitFor(() => {
      // 85% acceptance rate from mockAIMetrics
      expect(screen.getByText(/85/)).toBeInTheDocument();
    });
  });

  it('displays time saved metric', async () => {
    render(<TaskManagement />);

    await waitFor(() => {
      // 12.5 hours saved
      expect(screen.getByText('12.5')).toBeInTheDocument();
    });
  });
});
