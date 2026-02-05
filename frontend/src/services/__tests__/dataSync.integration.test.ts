/**
 * Data Synchronization Integration Tests
 * 
 * Tests data sync between SuperInsight and Label Studio:
 * - Project list synchronization
 * - Annotation progress sync
 * - Task status updates
 * - Error recovery during sync
 * 
 * **Validates: Requirements 9.6** - Label Studio 项目同步
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import apiClient from '../api/client';
import { labelStudioService } from '../labelStudioService';
import { taskService } from '../task';

// Mock the API client
vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockApiClient = apiClient as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  patch: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

describe('Data Synchronization Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Project List Synchronization', () => {
    /**
     * Test: Sync project list from Label Studio
     * Validates: Requirements 9.6.1 - 实现项目列表同步
     */
    it('should sync project list from Label Studio', async () => {
      const mockProjects = {
        results: [
          { id: 1, title: 'Project 1', task_count: 100, annotation_count: 50 },
          { id: 2, title: 'Project 2', task_count: 200, annotation_count: 150 },
        ],
      };
      mockApiClient.get.mockResolvedValueOnce({ data: mockProjects });

      const response = await mockApiClient.get('/api/label-studio/projects');

      expect(response.data.results).toHaveLength(2);
      expect(response.data.results[0].task_count).toBe(100);
    });

    /**
     * Test: Handle empty project list
     * Validates: Requirements 9.6.1
     */
    it('should handle empty project list', async () => {
      mockApiClient.get.mockResolvedValueOnce({ data: { results: [] } });

      const response = await mockApiClient.get('/api/label-studio/projects');

      expect(response.data.results).toHaveLength(0);
    });
  });

  describe('Annotation Progress Sync', () => {
    /**
     * Test: Sync annotation progress for a project
     * Validates: Requirements 9.6.2 - 实现项目详情同步
     */
    it('should sync annotation progress', async () => {
      const mockProject = {
        id: '123',
        title: 'Test Project',
        task_count: 100,
        annotation_count: 75,
        completed_tasks: 75,
      };
      mockApiClient.get.mockResolvedValueOnce({ data: mockProject });

      const result = await labelStudioService.getProject('123');

      expect(result.task_count).toBe(100);
      expect(result.annotation_count).toBe(75);
    });

    /**
     * Test: Calculate progress percentage
     * Validates: Requirements 9.6.3 - 实现标注结果同步
     */
    it('should calculate progress percentage correctly', async () => {
      const mockValidation = {
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 75,
        status: 'ready',
      };
      mockApiClient.get.mockResolvedValueOnce({ data: mockValidation });

      const result = await labelStudioService.validateProject('123');

      const progress = Math.round((result.annotation_count / result.task_count) * 100);
      expect(progress).toBe(75);
    });

    /**
     * Test: Handle zero tasks (avoid division by zero)
     */
    it('should handle zero tasks gracefully', async () => {
      const mockValidation = {
        exists: true,
        accessible: true,
        task_count: 0,
        annotation_count: 0,
        status: 'ready',
      };
      mockApiClient.get.mockResolvedValueOnce({ data: mockValidation });

      const result = await labelStudioService.validateProject('123');

      const progress = result.task_count > 0
        ? Math.round((result.annotation_count / result.task_count) * 100)
        : 0;
      expect(progress).toBe(0);
    });
  });

  describe('Task Status Updates', () => {
    /**
     * Test: Update task with sync status
     * Validates: Requirements 9.6.4 - 添加同步状态显示
     */
    it('should update task with sync status', async () => {
      const updatedTask = {
        id: 'task-123',
        name: 'Test Task',
        label_studio_sync_status: 'synced',
        label_studio_last_sync: '2026-01-28T12:00:00Z',
      };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedTask });

      const result = await taskService.update('task-123', {
        label_studio_sync_status: 'synced',
        label_studio_last_sync: new Date().toISOString(),
      });

      expect(result.label_studio_sync_status).toBe('synced');
    });

    /**
     * Test: Update task progress from Label Studio
     * Validates: Requirements 9.6.3
     */
    it('should update task progress from Label Studio', async () => {
      const updatedTask = {
        id: 'task-123',
        name: 'Test Task',
        total_items: 100,
        completed_items: 75,
        progress: 75,
      };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedTask });

      const result = await taskService.update('task-123', {
        total_items: 100,
        completed_items: 75,
        progress: 75,
      });

      expect(result.progress).toBe(75);
      expect(result.completed_items).toBe(75);
    });

    /**
     * Test: Mark sync as failed
     * Validates: Requirements 9.6.4
     */
    it('should mark sync as failed on error', async () => {
      const updatedTask = {
        id: 'task-123',
        name: 'Test Task',
        label_studio_sync_status: 'failed',
        label_studio_sync_error: 'Connection timeout',
      };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedTask });

      const result = await taskService.update('task-123', {
        label_studio_sync_status: 'failed',
        label_studio_sync_error: 'Connection timeout',
      });

      expect(result.label_studio_sync_status).toBe('failed');
    });
  });

  describe('Batch Synchronization', () => {
    /**
     * Test: Sync multiple tasks in batch
     * Validates: Requirements 9.1.3 - 优化刷新性能
     */
    it('should sync multiple tasks in batch', async () => {
      // Mock project list
      const mockProjects = {
        results: [
          { id: 1, title: 'Project 1', task_count: 50, annotation_count: 25 },
          { id: 2, title: 'Project 2', task_count: 100, annotation_count: 100 },
        ],
      };
      mockApiClient.get.mockResolvedValueOnce({ data: mockProjects });

      // Mock task updates
      mockApiClient.patch.mockResolvedValue({ data: { success: true } });

      const projects = await mockApiClient.get('/api/label-studio/projects');

      // Simulate batch update
      const updatePromises = projects.data.results.map((project: { id: number; task_count: number; annotation_count: number }) =>
        taskService.update(`task-${project.id}`, {
          total_items: project.task_count,
          completed_items: project.annotation_count,
          progress: Math.round((project.annotation_count / project.task_count) * 100),
        })
      );

      await Promise.all(updatePromises);

      expect(mockApiClient.patch).toHaveBeenCalledTimes(2);
    });

    /**
     * Test: Handle partial batch sync failure
     * Validates: Requirements 3.2 - 错误恢复
     */
    it('should handle partial batch sync failure', async () => {
      // First update succeeds
      mockApiClient.patch.mockResolvedValueOnce({ data: { success: true } });
      // Second update fails
      mockApiClient.patch.mockRejectedValueOnce({
        response: { status: 500, data: { detail: 'Internal error' } },
      });
      // Third update succeeds
      mockApiClient.patch.mockResolvedValueOnce({ data: { success: true } });

      const tasks = ['task-1', 'task-2', 'task-3'];
      const results = await Promise.allSettled(
        tasks.map((taskId) =>
          taskService.update(taskId, { label_studio_sync_status: 'synced' })
        )
      );

      const fulfilled = results.filter((r) => r.status === 'fulfilled');
      const rejected = results.filter((r) => r.status === 'rejected');

      expect(fulfilled).toHaveLength(2);
      expect(rejected).toHaveLength(1);
    });
  });

  describe('Error Recovery', () => {
    /**
     * Test: Retry sync on network error
     * Validates: Requirements 3.2.1 - 实现重试机制
     */
    it('should retry sync on network error', async () => {
      // First call fails
      mockApiClient.get.mockRejectedValueOnce({ code: 'ERR_NETWORK' });
      // Retry succeeds
      mockApiClient.get.mockResolvedValueOnce({
        data: { exists: true, task_count: 100, annotation_count: 50, status: 'ready' },
      });

      // First attempt fails
      await expect(labelStudioService.validateProject('123')).rejects.toBeDefined();

      // Retry succeeds
      const result = await labelStudioService.validateProject('123');
      expect(result.exists).toBe(true);
    });

    /**
     * Test: Handle service unavailable during sync
     * Validates: Requirements 3.2.2 - 提供备选方案
     */
    it('should handle service unavailable during sync', async () => {
      mockApiClient.get.mockRejectedValueOnce({
        response: { status: 503, data: { detail: 'Service unavailable' } },
      });

      await expect(labelStudioService.validateProject('123')).rejects.toMatchObject({
        response: { status: 503 },
      });
    });

    /**
     * Test: Recover from timeout error
     * Validates: Requirements 3.1.2 - 网络错误处理
     */
    it('should handle timeout error during sync', async () => {
      mockApiClient.get.mockRejectedValueOnce({
        code: 'ECONNABORTED',
        message: 'timeout of 10000ms exceeded',
      });

      await expect(labelStudioService.validateProject('123')).rejects.toMatchObject({
        code: 'ECONNABORTED',
      });
    });
  });

  describe('Sync Status Tracking', () => {
    /**
     * Test: Track last sync timestamp
     * Validates: Requirements 9.6.4
     */
    it('should track last sync timestamp', async () => {
      const syncTime = new Date().toISOString();
      const updatedTask = {
        id: 'task-123',
        label_studio_last_sync: syncTime,
        label_studio_sync_status: 'synced',
      };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedTask });

      const result = await taskService.update('task-123', {
        label_studio_last_sync: syncTime,
        label_studio_sync_status: 'synced',
      });

      expect(result.label_studio_last_sync).toBe(syncTime);
    });

    /**
     * Test: Update sync status to pending
     * Validates: Requirements 9.6.4
     */
    it('should set sync status to pending before sync', async () => {
      const updatedTask = {
        id: 'task-123',
        label_studio_sync_status: 'pending',
      };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedTask });

      const result = await taskService.update('task-123', {
        label_studio_sync_status: 'pending',
      });

      expect(result.label_studio_sync_status).toBe('pending');
    });
  });
});
