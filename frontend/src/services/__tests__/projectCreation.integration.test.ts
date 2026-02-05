/**
 * Project Creation Flow Integration Tests
 * 
 * Tests the complete project creation workflow:
 * - Ensure project exists or create new
 * - Import tasks to project
 * - Update task with project ID
 * 
 * **Validates: Requirements 1.3** - 项目管理
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import apiClient from '../api/client';
import { labelStudioService } from '../labelStudioService';
import { taskService } from '../task';
import type { EnsureProjectResponse, ImportTasksResponse } from '../labelStudioService';

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

describe('Project Creation Flow Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Complete Project Creation Flow', () => {
    /**
     * Test: Full project creation workflow
     * 
     * Flow:
     * 1. Check if project exists (ensureProject)
     * 2. Create project if not exists
     * 3. Import tasks to project
     * 4. Update task with project ID
     * 
     * Validates: Requirements 1.3.1, 1.3.2
     */
    it('should complete full project creation workflow', async () => {
      // Step 1: Ensure project (creates new)
      const ensureResponse: EnsureProjectResponse = {
        project_id: 'new-project-123',
        created: true,
        status: 'ready',
        task_count: 0,
        message: 'Project created successfully',
      };
      mockApiClient.post.mockResolvedValueOnce({ data: ensureResponse });

      // Step 2: Import tasks
      const importResponse: ImportTasksResponse = {
        imported_count: 50,
        failed_count: 0,
        status: 'success',
      };
      mockApiClient.post.mockResolvedValueOnce({ data: importResponse });

      // Step 3: Update task with project ID
      const updatedTask = {
        id: 'task-456',
        name: 'Test Task',
        label_studio_project_id: 'new-project-123',
      };
      mockApiClient.patch.mockResolvedValueOnce({ data: updatedTask });

      // Execute workflow
      const projectResult = await labelStudioService.ensureProject({
        task_id: 'task-456',
        task_name: 'Test Task',
        annotation_type: 'sentiment',
      });

      expect(projectResult.created).toBe(true);
      expect(projectResult.project_id).toBe('new-project-123');

      const importResult = await labelStudioService.importTasks(
        projectResult.project_id,
        'task-456'
      );

      expect(importResult.status).toBe('success');
      expect(importResult.imported_count).toBe(50);

      const taskResult = await taskService.update('task-456', {
        label_studio_project_id: projectResult.project_id,
      });

      expect(taskResult.label_studio_project_id).toBe('new-project-123');
    });

    /**
     * Test: Project already exists workflow
     * 
     * Flow:
     * 1. Check if project exists (ensureProject returns existing)
     * 2. Skip creation, proceed with existing project
     * 3. Import additional tasks if needed
     * 
     * Validates: Requirements 1.3.1
     */
    it('should handle existing project workflow', async () => {
      const ensureResponse: EnsureProjectResponse = {
        project_id: 'existing-project-789',
        created: false,
        status: 'ready',
        task_count: 100,
        message: 'Project already exists',
      };
      mockApiClient.post.mockResolvedValueOnce({ data: ensureResponse });

      const result = await labelStudioService.ensureProject({
        task_id: 'task-456',
        task_name: 'Test Task',
        annotation_type: 'sentiment',
      });

      expect(result.created).toBe(false);
      expect(result.project_id).toBe('existing-project-789');
      expect(result.task_count).toBe(100);
    });

    /**
     * Test: Project creation with immediate task import
     * 
     * Validates: Requirements 1.3.1, 1.3.2
     */
    it('should create project and import tasks in sequence', async () => {
      const ensureResponse: EnsureProjectResponse = {
        project_id: 'new-project-abc',
        created: true,
        status: 'ready',
        task_count: 0,
      };
      mockApiClient.post.mockResolvedValueOnce({ data: ensureResponse });

      const importResponse: ImportTasksResponse = {
        imported_count: 25,
        failed_count: 0,
        status: 'success',
      };
      mockApiClient.post.mockResolvedValueOnce({ data: importResponse });

      // Create project
      const project = await labelStudioService.ensureProject({
        task_id: 'task-new',
        task_name: 'New Task',
        annotation_type: 'ner',
      });

      // Import tasks
      const importResult = await labelStudioService.importTasks(
        project.project_id,
        'task-new'
      );

      expect(project.created).toBe(true);
      expect(importResult.imported_count).toBe(25);
      expect(mockApiClient.post).toHaveBeenCalledTimes(2);
    });
  });

  describe('Error Handling in Project Creation', () => {
    /**
     * Test: Handle project creation failure
     * 
     * Validates: Requirements 3.1 - 错误类型处理
     */
    it('should handle project creation failure', async () => {
      const error = {
        response: {
          status: 500,
          data: { detail: 'Failed to create project in Label Studio' },
        },
      };
      mockApiClient.post.mockRejectedValueOnce(error);

      await expect(
        labelStudioService.ensureProject({
          task_id: 'task-456',
          task_name: 'Test Task',
          annotation_type: 'sentiment',
        })
      ).rejects.toEqual(error);
    });

    /**
     * Test: Handle task import failure after project creation
     * 
     * Validates: Requirements 1.3.2 - 处理导入失败情况
     */
    it('should handle task import failure after project creation', async () => {
      // Project creation succeeds
      const ensureResponse: EnsureProjectResponse = {
        project_id: 'new-project-123',
        created: true,
        status: 'ready',
        task_count: 0,
      };
      mockApiClient.post.mockResolvedValueOnce({ data: ensureResponse });

      // Task import fails
      const importError = {
        response: {
          status: 400,
          data: { detail: 'Invalid task data format' },
        },
      };
      mockApiClient.post.mockRejectedValueOnce(importError);

      // Project creation should succeed
      const project = await labelStudioService.ensureProject({
        task_id: 'task-456',
        task_name: 'Test Task',
        annotation_type: 'sentiment',
      });
      expect(project.project_id).toBe('new-project-123');

      // Task import should fail
      await expect(
        labelStudioService.importTasks(project.project_id, 'task-456')
      ).rejects.toEqual(importError);
    });

    /**
     * Test: Handle partial import failure
     * 
     * Validates: Requirements 1.3.2 - 处理导入失败情况
     */
    it('should handle partial import failure', async () => {
      const ensureResponse: EnsureProjectResponse = {
        project_id: 'new-project-123',
        created: true,
        status: 'ready',
        task_count: 0,
      };
      mockApiClient.post.mockResolvedValueOnce({ data: ensureResponse });

      const importResponse: ImportTasksResponse = {
        imported_count: 80,
        failed_count: 20,
        status: 'partial',
        errors: ['20 items had invalid format'],
      };
      mockApiClient.post.mockResolvedValueOnce({ data: importResponse });

      const project = await labelStudioService.ensureProject({
        task_id: 'task-456',
        task_name: 'Test Task',
        annotation_type: 'sentiment',
      });

      const importResult = await labelStudioService.importTasks(
        project.project_id,
        'task-456'
      );

      expect(importResult.status).toBe('partial');
      expect(importResult.failed_count).toBe(20);
      expect(importResult.errors).toHaveLength(1);
    });

    /**
     * Test: Handle authentication error during project creation
     * 
     * Validates: Requirements 3.1.3 - 认证错误处理
     */
    it('should handle authentication error during project creation', async () => {
      const authError = {
        response: {
          status: 401,
          data: { detail: 'Invalid or expired token' },
        },
      };
      mockApiClient.post.mockRejectedValueOnce(authError);

      await expect(
        labelStudioService.ensureProject({
          task_id: 'task-456',
          task_name: 'Test Task',
          annotation_type: 'sentiment',
        })
      ).rejects.toEqual(authError);
    });

    /**
     * Test: Handle Label Studio service unavailable
     * 
     * Validates: Requirements 3.1.2 - 网络错误处理
     */
    it('should handle Label Studio service unavailable', async () => {
      const serviceError = {
        response: {
          status: 503,
          data: { detail: 'Label Studio service is unavailable' },
        },
      };
      mockApiClient.post.mockRejectedValueOnce(serviceError);

      await expect(
        labelStudioService.ensureProject({
          task_id: 'task-456',
          task_name: 'Test Task',
          annotation_type: 'sentiment',
        })
      ).rejects.toEqual(serviceError);
    });
  });

  describe('Project Creation with Different Annotation Types', () => {
    /**
     * Test: Create project for sentiment analysis
     */
    it('should create project for sentiment analysis', async () => {
      const ensureResponse: EnsureProjectResponse = {
        project_id: 'sentiment-project',
        created: true,
        status: 'ready',
        task_count: 0,
      };
      mockApiClient.post.mockResolvedValueOnce({ data: ensureResponse });

      const result = await labelStudioService.ensureProject({
        task_id: 'task-1',
        task_name: 'Sentiment Task',
        annotation_type: 'sentiment',
      });

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/label-studio/projects/ensure',
        expect.objectContaining({ annotation_type: 'sentiment' })
      );
      expect(result.project_id).toBe('sentiment-project');
    });

    /**
     * Test: Create project for NER (Named Entity Recognition)
     */
    it('should create project for NER', async () => {
      const ensureResponse: EnsureProjectResponse = {
        project_id: 'ner-project',
        created: true,
        status: 'ready',
        task_count: 0,
      };
      mockApiClient.post.mockResolvedValueOnce({ data: ensureResponse });

      const result = await labelStudioService.ensureProject({
        task_id: 'task-2',
        task_name: 'NER Task',
        annotation_type: 'ner',
      });

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/label-studio/projects/ensure',
        expect.objectContaining({ annotation_type: 'ner' })
      );
      expect(result.project_id).toBe('ner-project');
    });

    /**
     * Test: Create project for text classification
     */
    it('should create project for text classification', async () => {
      const ensureResponse: EnsureProjectResponse = {
        project_id: 'classification-project',
        created: true,
        status: 'ready',
        task_count: 0,
      };
      mockApiClient.post.mockResolvedValueOnce({ data: ensureResponse });

      const result = await labelStudioService.ensureProject({
        task_id: 'task-3',
        task_name: 'Classification Task',
        annotation_type: 'text_classification',
      });

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/label-studio/projects/ensure',
        expect.objectContaining({ annotation_type: 'text_classification' })
      );
      expect(result.project_id).toBe('classification-project');
    });
  });

  describe('Concurrent Project Operations', () => {
    /**
     * Test: Handle concurrent project creation requests
     * 
     * Validates: Requirements 6.2.2 - 添加请求去重
     */
    it('should handle concurrent project creation requests', async () => {
      const ensureResponse: EnsureProjectResponse = {
        project_id: 'concurrent-project',
        created: true,
        status: 'ready',
        task_count: 0,
      };
      mockApiClient.post.mockResolvedValue({ data: ensureResponse });

      // Simulate concurrent requests
      const requests = [
        labelStudioService.ensureProject({
          task_id: 'task-1',
          task_name: 'Task 1',
          annotation_type: 'sentiment',
        }),
        labelStudioService.ensureProject({
          task_id: 'task-1',
          task_name: 'Task 1',
          annotation_type: 'sentiment',
        }),
      ];

      const results = await Promise.all(requests);

      // Both should succeed (deduplication handled by API)
      expect(results[0].project_id).toBe('concurrent-project');
      expect(results[1].project_id).toBe('concurrent-project');
    });
  });
});
