/**
 * Task Management Components Unit Tests
 *
 * Tests for task list rendering, form validation, filtering/sorting, and status updates.
 * Validates: Requirements 1.2
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TaskStatsCards } from '../TaskStatsCards';
import { useTaskStore, taskSelectors } from '@/stores/taskStore';
import type { Task, TaskStats } from '@/types';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        totalTasks: 'Total Tasks',
        inProgress: 'In Progress',
        completed: 'Completed',
        overdue: 'Overdue',
      };
      return translations[key] || key;
    },
  }),
}));

// ============================================================================
// Test Data
// ============================================================================

const mockStats: TaskStats = {
  total: 120,
  pending: 30,
  in_progress: 45,
  completed: 40,
  cancelled: 5,
  overdue: 8,
};

const createMockTask = (overrides: Partial<Task> = {}): Task => ({
  id: `task-${Math.random().toString(36).slice(2, 8)}`,
  name: 'Test Task',
  description: 'Test description',
  status: 'pending',
  priority: 'medium',
  annotation_type: 'text_classification',
  assignee_id: 'user-1',
  assignee_name: 'Test User',
  created_by: 'admin',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  progress: 0,
  total_items: 100,
  completed_items: 0,
  tenant_id: 'tenant-1',
  tags: [],
  ...overrides,
});

// ============================================================================
// TaskStatsCards Tests
// ============================================================================

describe('TaskStatsCards', () => {
  it('renders all four statistic cards', () => {
    render(<TaskStatsCards stats={mockStats} />);

    expect(screen.getByText('Total Tasks')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Overdue')).toBeInTheDocument();
  });

  it('displays correct stat values', () => {
    render(<TaskStatsCards stats={mockStats} />);

    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();
    expect(screen.getByText('40')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('renders with zero stats', () => {
    const zeroStats: TaskStats = {
      total: 0, pending: 0, in_progress: 0,
      completed: 0, cancelled: 0, overdue: 0,
    };
    render(<TaskStatsCards stats={zeroStats} />);

    const zeros = screen.getAllByText('0');
    expect(zeros.length).toBe(4);
  });
});

// ============================================================================
// Task Store - Filtering Tests
// ============================================================================

describe('taskStore - filtering', () => {
  beforeEach(() => {
    useTaskStore.getState().reset();
  });

  it('filters tasks by status using selector', () => {
    const tasks = [
      createMockTask({ id: '1', status: 'pending' }),
      createMockTask({ id: '2', status: 'in_progress' }),
      createMockTask({ id: '3', status: 'completed' }),
      createMockTask({ id: '4', status: 'pending' }),
    ];
    useTaskStore.getState().setTasks(tasks);

    const pending = taskSelectors.getTasksByStatus(useTaskStore.getState(), 'pending');
    const inProgress = taskSelectors.getTasksByStatus(useTaskStore.getState(), 'in_progress');
    const completed = taskSelectors.getTasksByStatus(useTaskStore.getState(), 'completed');

    expect(pending).toHaveLength(2);
    expect(inProgress).toHaveLength(1);
    expect(completed).toHaveLength(1);
  });

  it('setFilters with status resets page to 1', () => {
    const store = useTaskStore.getState();
    store.setPage(5);
    store.setFilters({ status: 'in_progress' });

    const state = useTaskStore.getState();
    expect(state.filters.status).toBe('in_progress');
    expect(state.pagination.page).toBe(1);
  });

  it('setFilters with priority preserves other filters', () => {
    const store = useTaskStore.getState();
    store.setFilters({ status: 'pending' });
    store.setFilters({ priority: 'high' });

    const { filters } = useTaskStore.getState();
    expect(filters.status).toBe('pending');
    expect(filters.priority).toBe('high');
  });

  it('setFilters with search term works', () => {
    const store = useTaskStore.getState();
    store.setFilters({ search: 'annotation' });

    expect(useTaskStore.getState().filters.search).toBe('annotation');
  });

  it('setFilters with tags works', () => {
    const store = useTaskStore.getState();
    store.setFilters({ tags: ['urgent', 'review'] });

    expect(useTaskStore.getState().filters.tags).toEqual(['urgent', 'review']);
  });

  it('setFilters with dateRange works', () => {
    const store = useTaskStore.getState();
    store.setFilters({ dateRange: ['2025-01-01', '2025-01-31'] });

    expect(useTaskStore.getState().filters.dateRange).toEqual(['2025-01-01', '2025-01-31']);
  });

  it('resetFilters clears all filters and resets page', () => {
    const store = useTaskStore.getState();
    store.setPage(3);
    store.setFilters({ status: 'pending', priority: 'high', search: 'test' });
    store.resetFilters();

    const { filters, pagination } = useTaskStore.getState();
    expect(filters.status).toBeUndefined();
    expect(filters.priority).toBeUndefined();
    expect(filters.search).toBeUndefined();
    expect(pagination.page).toBe(1);
  });

  it('hasActiveFilters returns false when no filters set', () => {
    expect(taskSelectors.hasActiveFilters(useTaskStore.getState())).toBe(false);
  });

  it('hasActiveFilters returns true for each filter type', () => {
    const store = useTaskStore.getState();

    store.setFilters({ status: 'pending' });
    expect(taskSelectors.hasActiveFilters(useTaskStore.getState())).toBe(true);

    store.resetFilters();
    store.setFilters({ search: 'test' });
    expect(taskSelectors.hasActiveFilters(useTaskStore.getState())).toBe(true);

    store.resetFilters();
    store.setFilters({ tags: ['tag1'] });
    expect(taskSelectors.hasActiveFilters(useTaskStore.getState())).toBe(true);

    store.resetFilters();
    store.setFilters({ dateRange: ['2025-01-01', '2025-01-31'] });
    expect(taskSelectors.hasActiveFilters(useTaskStore.getState())).toBe(true);
  });
});

// ============================================================================
// Task Store - Sorting Tests
// ============================================================================

describe('taskStore - sorting', () => {
  beforeEach(() => {
    useTaskStore.getState().reset();
  });

  it('starts with default sort (created_at desc)', () => {
    const { sort } = useTaskStore.getState();
    expect(sort.field).toBe('created_at');
    expect(sort.order).toBe('desc');
  });

  it('setSort updates sort config', () => {
    useTaskStore.getState().setSort({ field: 'name', order: 'asc' });

    const { sort } = useTaskStore.getState();
    expect(sort.field).toBe('name');
    expect(sort.order).toBe('asc');
  });

  it('setSort can change to different fields', () => {
    const store = useTaskStore.getState();

    store.setSort({ field: 'priority', order: 'desc' });
    expect(useTaskStore.getState().sort.field).toBe('priority');

    store.setSort({ field: 'due_date', order: 'asc' });
    expect(useTaskStore.getState().sort.field).toBe('due_date');

    store.setSort({ field: 'progress', order: 'desc' });
    expect(useTaskStore.getState().sort.field).toBe('progress');
  });
});

// ============================================================================
// Task Store - Status Update Tests
// ============================================================================

describe('taskStore - status updates', () => {
  beforeEach(() => {
    useTaskStore.getState().reset();
  });

  it('updateTask changes task status', () => {
    const task = createMockTask({ id: 'task-1', status: 'pending' });
    useTaskStore.getState().setTasks([task]);

    useTaskStore.getState().updateTask('task-1', { status: 'in_progress' });

    expect(useTaskStore.getState().tasks[0].status).toBe('in_progress');
  });

  it('updateTask changes status and progress together', () => {
    const task = createMockTask({ id: 'task-1', status: 'in_progress', progress: 50 });
    useTaskStore.getState().setTasks([task]);

    useTaskStore.getState().updateTask('task-1', {
      status: 'completed',
      progress: 100,
      completed_items: 100,
    });

    const updated = useTaskStore.getState().tasks[0];
    expect(updated.status).toBe('completed');
    expect(updated.progress).toBe(100);
    expect(updated.completed_items).toBe(100);
  });

  it('updateTask also updates currentTask if it matches', () => {
    const task = createMockTask({ id: 'task-1', status: 'pending' });
    useTaskStore.getState().setTasks([task]);
    useTaskStore.getState().setCurrentTask(task);

    useTaskStore.getState().updateTask('task-1', { status: 'in_progress' });

    expect(useTaskStore.getState().currentTask?.status).toBe('in_progress');
  });

  it('updateTask does not affect other tasks', () => {
    const tasks = [
      createMockTask({ id: 'task-1', status: 'pending' }),
      createMockTask({ id: 'task-2', status: 'pending' }),
    ];
    useTaskStore.getState().setTasks(tasks);

    useTaskStore.getState().updateTask('task-1', { status: 'completed' });

    expect(useTaskStore.getState().tasks[0].status).toBe('completed');
    expect(useTaskStore.getState().tasks[1].status).toBe('pending');
  });

  it('removeTask removes task and cleans up selection', () => {
    const tasks = [
      createMockTask({ id: 'task-1' }),
      createMockTask({ id: 'task-2' }),
    ];
    useTaskStore.getState().setTasks(tasks);
    useTaskStore.getState().selectTask('task-1');
    useTaskStore.getState().selectTask('task-2');

    useTaskStore.getState().removeTask('task-1');

    const state = useTaskStore.getState();
    expect(state.tasks).toHaveLength(1);
    expect(state.tasks[0].id).toBe('task-2');
    expect(state.selection.selectedIds).not.toContain('task-1');
    expect(state.selection.selectedIds).toContain('task-2');
  });

  it('removeTask clears currentTask if it matches', () => {
    const task = createMockTask({ id: 'task-1' });
    useTaskStore.getState().setTasks([task]);
    useTaskStore.getState().setCurrentTask(task);

    useTaskStore.getState().removeTask('task-1');

    expect(useTaskStore.getState().currentTask).toBeNull();
  });

  it('addTask prepends to list and increments total', () => {
    const existing = createMockTask({ id: 'task-1', name: 'Existing' });
    useTaskStore.getState().setTasks([existing]);

    const newTask = createMockTask({ id: 'task-2', name: 'New Task' });
    useTaskStore.getState().addTask(newTask);

    const state = useTaskStore.getState();
    expect(state.tasks).toHaveLength(2);
    expect(state.tasks[0].id).toBe('task-2');
    expect(state.pagination.total).toBe(1);
  });
});

// ============================================================================
// Task Store - Selectors Tests
// ============================================================================

describe('taskStore - selectors', () => {
  beforeEach(() => {
    useTaskStore.getState().reset();
  });

  it('getSelectedTasks returns only selected tasks', () => {
    const tasks = [
      createMockTask({ id: 'task-1' }),
      createMockTask({ id: 'task-2' }),
      createMockTask({ id: 'task-3' }),
    ];
    useTaskStore.getState().setTasks(tasks);
    useTaskStore.getState().selectTask('task-1');
    useTaskStore.getState().selectTask('task-3');

    const selected = taskSelectors.getSelectedTasks(useTaskStore.getState());
    expect(selected).toHaveLength(2);
    expect(selected.map(t => t.id)).toEqual(['task-1', 'task-3']);
  });

  it('isTaskSelected returns correct boolean', () => {
    const tasks = [createMockTask({ id: 'task-1' })];
    useTaskStore.getState().setTasks(tasks);
    useTaskStore.getState().selectTask('task-1');

    expect(taskSelectors.isTaskSelected(useTaskStore.getState(), 'task-1')).toBe(true);
    expect(taskSelectors.isTaskSelected(useTaskStore.getState(), 'task-2')).toBe(false);
  });

  it('getCompletionPercentage returns 0 when no stats', () => {
    expect(taskSelectors.getCompletionPercentage(useTaskStore.getState())).toBe(0);
  });

  it('getCompletionPercentage returns 0 when total is 0', () => {
    useTaskStore.getState().setStats({
      total: 0, pending: 0, in_progress: 0,
      completed: 0, cancelled: 0, overdue: 0,
    });
    expect(taskSelectors.getCompletionPercentage(useTaskStore.getState())).toBe(0);
  });

  it('getCompletionPercentage calculates correctly', () => {
    useTaskStore.getState().setStats(mockStats);
    // 40 completed / 120 total = 33.33... → rounds to 33
    expect(taskSelectors.getCompletionPercentage(useTaskStore.getState())).toBe(33);
  });

  it('getFilteredCount returns tasks array length', () => {
    useTaskStore.getState().setTasks([
      createMockTask({ id: '1' }),
      createMockTask({ id: '2' }),
    ]);
    expect(taskSelectors.getFilteredCount(useTaskStore.getState())).toBe(2);
  });
});

// ============================================================================
// Task Store - Pagination Tests
// ============================================================================

describe('taskStore - pagination', () => {
  beforeEach(() => {
    useTaskStore.getState().reset();
  });

  it('setPage updates current page', () => {
    useTaskStore.getState().setPage(3);
    expect(useTaskStore.getState().pagination.page).toBe(3);
  });

  it('setPageSize updates page size and resets to page 1', () => {
    useTaskStore.getState().setPage(5);
    useTaskStore.getState().setPageSize(50);

    const { pagination } = useTaskStore.getState();
    expect(pagination.pageSize).toBe(50);
    expect(pagination.page).toBe(1);
  });

  it('setPagination merges partial updates', () => {
    useTaskStore.getState().setPagination({ total: 200 });

    const { pagination } = useTaskStore.getState();
    expect(pagination.total).toBe(200);
    expect(pagination.page).toBe(1);
    expect(pagination.pageSize).toBe(20);
  });
});

// ============================================================================
// Task Store - Loading & Error States
// ============================================================================

describe('taskStore - loading and error states', () => {
  beforeEach(() => {
    useTaskStore.getState().reset();
  });

  it('setLoading toggles loading state', () => {
    useTaskStore.getState().setLoading(true);
    expect(useTaskStore.getState().isLoading).toBe(true);

    useTaskStore.getState().setLoading(false);
    expect(useTaskStore.getState().isLoading).toBe(false);
  });

  it('setError sets and clearError clears error', () => {
    useTaskStore.getState().setError('Something went wrong');
    expect(useTaskStore.getState().error).toBe('Something went wrong');

    useTaskStore.getState().clearError();
    expect(useTaskStore.getState().error).toBeNull();
  });

  it('reset restores all state to initial values', () => {
    const store = useTaskStore.getState();
    store.setTasks([createMockTask()]);
    store.setFilters({ status: 'pending' });
    store.setPage(5);
    store.setLoading(true);
    store.setError('error');

    store.reset();

    const state = useTaskStore.getState();
    expect(state.tasks).toEqual([]);
    expect(state.filters.status).toBeUndefined();
    expect(state.pagination.page).toBe(1);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
  });
});
