/**
 * Task Store Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useTaskStore, taskSelectors } from '../taskStore';
import type { Task, TaskStats } from '@/types';

describe('taskStore', () => {
  const mockTask: Task = {
    id: 'task-1',
    name: '测试任务',
    description: '测试描述',
    status: 'pending',
    priority: 'medium',
    annotation_type: 'text_classification',
    assignee_id: 'user-1',
    assignee_name: '测试用户',
    created_by: 'admin',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    progress: 0,
    total_items: 100,
    completed_items: 0,
    tenant_id: 'tenant-1',
    tags: ['test'],
  };

  const mockStats: TaskStats = {
    total: 100,
    pending: 30,
    in_progress: 40,
    completed: 25,
    cancelled: 5,
    overdue: 10,
  };

  beforeEach(() => {
    useTaskStore.getState().reset();
  });

  describe('initial state', () => {
    it('starts with empty tasks array', () => {
      const { tasks } = useTaskStore.getState();
      expect(tasks).toEqual([]);
    });

    it('starts with null current task', () => {
      const { currentTask } = useTaskStore.getState();
      expect(currentTask).toBeNull();
    });

    it('starts with default pagination', () => {
      const { pagination } = useTaskStore.getState();
      expect(pagination).toEqual({
        page: 1,
        pageSize: 20,
        total: 0,
      });
    });

    it('starts with empty selection', () => {
      const { selection } = useTaskStore.getState();
      expect(selection.selectedIds).toEqual([]);
      expect(selection.isAllSelected).toBe(false);
    });
  });

  describe('task actions', () => {
    it('setTasks updates tasks and resets selection', () => {
      const { setTasks } = useTaskStore.getState();
      
      // First select something
      useTaskStore.setState({
        selection: { selectedIds: ['old-id'], isAllSelected: false },
      });
      
      setTasks([mockTask]);
      
      const state = useTaskStore.getState();
      expect(state.tasks).toEqual([mockTask]);
      expect(state.selection.selectedIds).toEqual([]);
    });

    it('addTask adds task to beginning of list', () => {
      const { setTasks, addTask } = useTaskStore.getState();
      
      setTasks([mockTask]);
      
      const newTask = { ...mockTask, id: 'task-2', name: '新任务' };
      addTask(newTask);
      
      const { tasks, pagination } = useTaskStore.getState();
      expect(tasks[0]).toEqual(newTask);
      expect(tasks.length).toBe(2);
      expect(pagination.total).toBe(1); // Incremented from 0
    });

    it('updateTask updates task in list and current task', () => {
      const { setTasks, setCurrentTask, updateTask } = useTaskStore.getState();
      
      setTasks([mockTask]);
      setCurrentTask(mockTask);
      
      updateTask('task-1', { status: 'in_progress', progress: 50 });
      
      const state = useTaskStore.getState();
      expect(state.tasks[0].status).toBe('in_progress');
      expect(state.tasks[0].progress).toBe(50);
      expect(state.currentTask?.status).toBe('in_progress');
    });

    it('removeTask removes task and updates selection', () => {
      const { setTasks, selectTask, removeTask } = useTaskStore.getState();
      
      setTasks([mockTask, { ...mockTask, id: 'task-2' }]);
      selectTask('task-1');
      
      removeTask('task-1');
      
      const state = useTaskStore.getState();
      expect(state.tasks.length).toBe(1);
      expect(state.selection.selectedIds).not.toContain('task-1');
    });
  });

  describe('filter actions', () => {
    it('setFilters updates filters and resets page', () => {
      const { setPage, setFilters } = useTaskStore.getState();
      
      setPage(5);
      setFilters({ status: 'pending', priority: 'high' });
      
      const state = useTaskStore.getState();
      expect(state.filters.status).toBe('pending');
      expect(state.filters.priority).toBe('high');
      expect(state.pagination.page).toBe(1);
    });

    it('resetFilters clears all filters', () => {
      const { setFilters, resetFilters } = useTaskStore.getState();
      
      setFilters({ status: 'pending', search: 'test' });
      resetFilters();
      
      const { filters } = useTaskStore.getState();
      expect(filters.status).toBeUndefined();
      expect(filters.search).toBeUndefined();
    });
  });

  describe('selection actions', () => {
    it('selectTask adds task to selection', () => {
      const { setTasks, selectTask } = useTaskStore.getState();
      
      setTasks([mockTask, { ...mockTask, id: 'task-2' }]);
      selectTask('task-1');
      
      const { selection } = useTaskStore.getState();
      expect(selection.selectedIds).toContain('task-1');
    });

    it('selectAll selects all tasks', () => {
      const { setTasks, selectAll } = useTaskStore.getState();
      
      setTasks([mockTask, { ...mockTask, id: 'task-2' }]);
      selectAll();
      
      const { selection } = useTaskStore.getState();
      expect(selection.selectedIds).toEqual(['task-1', 'task-2']);
      expect(selection.isAllSelected).toBe(true);
    });

    it('deselectAll clears selection', () => {
      const { setTasks, selectAll, deselectAll } = useTaskStore.getState();
      
      setTasks([mockTask]);
      selectAll();
      deselectAll();
      
      const { selection } = useTaskStore.getState();
      expect(selection.selectedIds).toEqual([]);
      expect(selection.isAllSelected).toBe(false);
    });

    it('toggleSelection toggles task selection', () => {
      const { setTasks, toggleSelection } = useTaskStore.getState();
      
      setTasks([mockTask]);
      
      toggleSelection('task-1');
      expect(useTaskStore.getState().selection.selectedIds).toContain('task-1');
      
      toggleSelection('task-1');
      expect(useTaskStore.getState().selection.selectedIds).not.toContain('task-1');
    });
  });

  describe('selectors', () => {
    it('getCompletionPercentage calculates correctly', () => {
      const { setStats } = useTaskStore.getState();
      
      setStats(mockStats);
      
      const percentage = taskSelectors.getCompletionPercentage(useTaskStore.getState());
      expect(percentage).toBe(25); // 25/100 = 25%
    });

    it('hasActiveFilters returns true when filters are set', () => {
      const { setFilters } = useTaskStore.getState();
      
      expect(taskSelectors.hasActiveFilters(useTaskStore.getState())).toBe(false);
      
      setFilters({ status: 'pending' });
      
      expect(taskSelectors.hasActiveFilters(useTaskStore.getState())).toBe(true);
    });

    it('getTasksByStatus filters tasks correctly', () => {
      const { setTasks } = useTaskStore.getState();
      
      setTasks([
        mockTask,
        { ...mockTask, id: 'task-2', status: 'completed' },
        { ...mockTask, id: 'task-3', status: 'pending' },
      ]);
      
      const pendingTasks = taskSelectors.getTasksByStatus(useTaskStore.getState(), 'pending');
      expect(pendingTasks.length).toBe(2);
    });
  });
});
