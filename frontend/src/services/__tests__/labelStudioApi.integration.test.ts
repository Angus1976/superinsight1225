/**
 * Label Studio API Integration Tests
 * 
 * Tests the Label Studio service API calls including:
 * - Project validation
 * - Project creation (ensureProject)
 * - Task import
 * - Authenticated URL generation
 * 
 * **Validates: Requirements 3.1, 3.2** - API 调用和错误处理
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import apiClient from '../api/client';
import { labelStudioService } from '../labelStudioService';
import type { ProjectValidationResult, EnsureProjectResponse, ImportTasksResponse } from '../labelStudioService';

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

describe('Label Studio API Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('validateProject', () => {
    /**
     * Test: Successful project validation
     * Validates: Requirements 3.1 - 项目验证
     */
    it('should return validation result for existing project', async () => {
      const mockResponse: ProjectValidationResult = {
        exists: true,
        accessible: true,
        task_count: 100,
        annotation_count: 50,
        status: 'ready',
      };

      mockApiClient.get.mockResolvedValue({ data: mockResponse });

      const result = await labelStudioService.validateProject('123');

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/label-studio/projects/123/validate');
      expect(result).toEqual(mockResponse);
      expect(result.exists).toBe(true);
      expect(result.status).toBe('ready');
    });

    /**
     * Test: Project not found (404)
     * Validates: Requirements 3.1.1 - 项目不存在错误
     */
    it('should return not_found status for 404 error', async () => {
      mockApiClient.get.mockRejectedValue({
        response: { status: 404 },
      });

      const result = await labelStudioService.validateProject('999');

      expect(result.exists).toBe(false);
      expect(result.accessible).toBe(false);
      expect(result.status).toBe('not_found');
      expect(result.error_message).toBe('Project not found');
    });

    /**
     * Test: API error propagation
     * Validates: Requirements 3.1.2 - 网络错误处理
     */
    it('should propagate non-404 errors', async () => {
      const error = {
        response: { status: 500, data: { detail: 'Internal Server Error' } },
      };
      mockApiClient.get.mockRejectedValue(error);

      await expect(labelStudioService.validateProject('123')).rejects.toEqual(error);
    });

    /**
     * Test: Network error handling
     * Validates: Requirements 3.1.2 - 网络错误处理
     */
    it('should propagate network errors', async () => {
      const error = { code: 'ERR_NETWORK', message: 'Network Error' };
      mockApiClient.get.mockRejectedValue(error);

      await expect(labelStudioService.validateProject('123')).rejects.toEqual(error);
    });
  });

  describe('ensureProject', () => {
    /**
     * Test: Create new project
     * Validates: Requirements 1.3 - 项目管理
     */
    it('should create new project when not exists', async () => {
      const mockResponse: EnsureProjectResponse = {
        project_id: 'new-project-456',
        created: true,
        status: 'ready',
        task_count: 0,
        message: 'Project created successfully',
      };

      mockApiClient.post.mockResolvedValue({ data: mockResponse });

      const result = await labelStudioService.ensureProject({
        task_id: 'task-123',
        task_name: 'Test Task',
        annotation_type: 'sentiment',
      });

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/label-studio/projects/ensure',
        {
          task_id: 'task-123',
          task_name: 'Test Task',
          annotation_type: 'sentiment',
        }
      );
      expect(result.created).toBe(true);
      expect(result.status).toBe('ready');
    });

    /**
     * Test: Return existing project
     * Validates: Requirements 1.3 - 项目管理
     */
    it('should return existing project when already exists', async () => {
      const mockResponse: EnsureProjectResponse = {
        project_id: 'existing-project-789',
        created: false,
        status: 'ready',
        task_count: 50,
        message: 'Project already exists',
      };

      mockApiClient.post.mockResolvedValue({ data: mockResponse });

      const result = await labelStudioService.ensureProject({
        task_id: 'task-456',
        task_name: 'Existing Task',
        annotation_type: 'ner',
      });

      expect(result.created).toBe(false);
      expect(result.task_count).toBe(50);
    });

    /**
     * Test: Handle creation error
     * Validates: Requirements 3.1 - 错误类型处理
     */
    it('should handle project creation errors', async () => {
      const error = {
        response: { status: 400, data: { detail: 'Invalid annotation type' } },
      };
      mockApiClient.post.mockRejectedValue(error);

      await expect(
        labelStudioService.ensureProject({
          task_id: 'task-123',
          task_name: 'Test Task',
          annotation_type: 'invalid_type',
        })
      ).rejects.toEqual(error);
    });
  });

  describe('importTasks', () => {
    /**
     * Test: Successful task import
     * Validates: Requirements 1.3.2 - 实现任务导入
     */
    it('should import tasks successfully', async () => {
      const mockResponse: ImportTasksResponse = {
        imported_count: 100,
        failed_count: 0,
        status: 'success',
      };

      mockApiClient.post.mockResolvedValue({ data: mockResponse });

      const result = await labelStudioService.importTasks('project-123', 'task-456');

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/label-studio/projects/project-123/import-tasks',
        { task_id: 'task-456' }
      );
      expect(result.imported_count).toBe(100);
      expect(result.status).toBe('success');
    });

    /**
     * Test: Partial import success
     * Validates: Requirements 1.3.2 - 处理导入失败情况
     */
    it('should handle partial import success', async () => {
      const mockResponse: ImportTasksResponse = {
        imported_count: 80,
        failed_count: 20,
        status: 'partial',
        errors: ['Invalid data format for 20 items'],
      };

      mockApiClient.post.mockResolvedValue({ data: mockResponse });

      const result = await labelStudioService.importTasks('project-123', 'task-456');

      expect(result.status).toBe('partial');
      expect(result.failed_count).toBe(20);
      expect(result.errors).toContain('Invalid data format for 20 items');
    });

    /**
     * Test: Import failure
     * Validates: Requirements 1.3.2 - 处理导入失败情况
     */
    it('should handle import failure', async () => {
      const mockResponse: ImportTasksResponse = {
        imported_count: 0,
        failed_count: 100,
        status: 'failed',
        errors: ['Project not found', 'Invalid task data'],
      };

      mockApiClient.post.mockResolvedValue({ data: mockResponse });

      const result = await labelStudioService.importTasks('project-123', 'task-456');

      expect(result.status).toBe('failed');
      expect(result.imported_count).toBe(0);
    });
  });

  describe('getAuthUrl', () => {
    /**
     * Test: Get authenticated URL with default language
     * Validates: Requirements 3.4 - 认证处理
     */
    it('should get authenticated URL with default language', async () => {
      const mockResponse = {
        url: 'http://localhost:8080/projects/123/data?token=xyz&lang=zh-cn',
        expires_at: '2026-01-28T12:00:00Z',
        project_id: '123',
      };

      mockApiClient.get.mockResolvedValue({ data: mockResponse });

      const result = await labelStudioService.getAuthUrl('123');

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/api/label-studio/projects/123/auth-url',
        { params: { language: 'zh' } }
      );
      expect(result.url).toContain('/projects/123/data');
    });

    /**
     * Test: Get authenticated URL with English language
     * Validates: Requirements 10.3 - Label Studio 语言同步
     */
    it('should get authenticated URL with specified language', async () => {
      const mockResponse = {
        url: 'http://localhost:8080/projects/123/data?token=xyz&lang=en',
        expires_at: '2026-01-28T12:00:00Z',
        project_id: '123',
      };

      mockApiClient.get.mockResolvedValue({ data: mockResponse });

      const result = await labelStudioService.getAuthUrl('123', 'en');

      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/api/label-studio/projects/123/auth-url',
        { params: { language: 'en' } }
      );
      expect(result.url).toContain('lang=en');
    });

    /**
     * Test: Handle authentication error
     * Validates: Requirements 3.1.3 - 认证错误处理
     */
    it('should handle authentication errors', async () => {
      const error = {
        response: { status: 401, data: { detail: 'Invalid token' } },
      };
      mockApiClient.get.mockRejectedValue(error);

      await expect(labelStudioService.getAuthUrl('123')).rejects.toEqual(error);
    });
  });

  describe('getProject', () => {
    /**
     * Test: Get project by ID
     * Validates: Requirements 1.3 - 项目管理
     */
    it('should get project by ID', async () => {
      const mockProject = {
        id: '123',
        title: 'Test Project',
        description: 'Test description',
        task_count: 100,
        annotation_count: 50,
        created_at: '2026-01-01T00:00:00Z',
      };

      mockApiClient.get.mockResolvedValue({ data: mockProject });

      const result = await labelStudioService.getProject('123');

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/label-studio/projects/123');
      expect(result.id).toBe('123');
      expect(result.title).toBe('Test Project');
    });

    /**
     * Test: Handle project not found
     * Validates: Requirements 3.1.1 - 项目不存在错误
     */
    it('should handle project not found', async () => {
      const error = {
        response: { status: 404, data: { detail: 'Project not found' } },
      };
      mockApiClient.get.mockRejectedValue(error);

      await expect(labelStudioService.getProject('999')).rejects.toEqual(error);
    });
  });

  describe('createProject (alias for ensureProject)', () => {
    /**
     * Test: Create project using alias method
     * Validates: Requirements 1.3 - 项目管理
     */
    it('should create project using createProject alias', async () => {
      const mockResponse: EnsureProjectResponse = {
        project_id: 'new-project-123',
        created: true,
        status: 'ready',
        task_count: 0,
      };

      mockApiClient.post.mockResolvedValue({ data: mockResponse });

      const result = await labelStudioService.createProject(
        'task-123',
        'Test Task',
        'sentiment'
      );

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/label-studio/projects/ensure',
        {
          task_id: 'task-123',
          task_name: 'Test Task',
          annotation_type: 'sentiment',
        }
      );
      expect(result.created).toBe(true);
    });
  });

  describe('generateLabelConfig (data transformation)', () => {
    /**
     * Test: Generate default template for annotation type
     * Validates: Requirements 6.3.1 - 测试数据转换
     */
    it('should return default template when no config provided', () => {
      const config = labelStudioService.generateLabelConfig('text_classification');
      
      expect(config).toContain('<View>');
      expect(config).toContain('<Choices');
      expect(config).toContain('toName="text"');
    });

    /**
     * Test: Generate custom classification template
     * Validates: Requirements 6.3.1 - 测试数据转换
     */
    it('should generate custom classification template with categories', () => {
      const config = labelStudioService.generateLabelConfig('text_classification', {
        categories: ['Spam', 'Not Spam', 'Uncertain'],
      });
      
      expect(config).toContain('Spam');
      expect(config).toContain('Not Spam');
      expect(config).toContain('Uncertain');
    });

    /**
     * Test: Generate multi-label classification template
     * Validates: Requirements 6.3.1 - 测试数据转换
     */
    it('should generate multi-label template when multiLabel is true', () => {
      const config = labelStudioService.generateLabelConfig('text_classification', {
        categories: ['Tag1', 'Tag2'],
        multiLabel: true,
      });
      
      expect(config).toContain('choice="multiple"');
    });

    /**
     * Test: Generate custom NER template
     * Validates: Requirements 6.3.1 - 测试数据转换
     */
    it('should generate custom NER template with entity types', () => {
      const config = labelStudioService.generateLabelConfig('ner', {
        entityTypes: ['Product', 'Brand', 'Price'],
      });
      
      expect(config).toContain('Product');
      expect(config).toContain('Brand');
      expect(config).toContain('Price');
      expect(config).toContain('<Labels');
    });

    /**
     * Test: Generate custom sentiment template
     * Validates: Requirements 6.3.1 - 测试数据转换
     */
    it('should generate binary sentiment template', () => {
      const config = labelStudioService.generateLabelConfig('sentiment', {
        sentimentScale: 'binary',
      });
      
      expect(config).toContain('Positive');
      expect(config).toContain('Negative');
      expect(config).not.toContain('Neutral');
    });

    /**
     * Test: Generate ternary sentiment template
     * Validates: Requirements 6.3.1 - 测试数据转换
     */
    it('should generate ternary sentiment template', () => {
      const config = labelStudioService.generateLabelConfig('sentiment', {
        sentimentScale: 'ternary',
      });
      
      expect(config).toContain('Positive');
      expect(config).toContain('Neutral');
      expect(config).toContain('Negative');
    });

    /**
     * Test: Return default template for empty config
     * Validates: Requirements 6.3.1 - 测试数据转换
     */
    it('should return default template when config has empty arrays', () => {
      const config = labelStudioService.generateLabelConfig('text_classification', {
        categories: [],
      });
      
      // Should fall back to default template
      expect(config).toContain('<Choices');
    });

    /**
     * Test: Handle unknown annotation type
     * Validates: Requirements 6.3.1 - 测试数据转换
     */
    it('should return default template for unknown annotation type', () => {
      // @ts-expect-error Testing unknown type
      const config = labelStudioService.generateLabelConfig('unknown_type');
      
      expect(config).toContain('<View>');
    });
  });
});
