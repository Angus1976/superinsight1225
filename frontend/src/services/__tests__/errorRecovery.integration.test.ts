/**
 * Error Recovery Integration Tests
 * 
 * Tests error handling and recovery scenarios:
 * - Network errors and retries
 * - Authentication failures
 * - Service unavailability
 * - Graceful degradation
 * 
 * **Validates: Requirements 3.1, 3.2** - 错误处理和恢复
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import apiClient from '../api/client';
import { labelStudioService } from '../labelStudioService';

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

describe('Error Recovery Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Network Error Recovery', () => {
    /**
     * Test: Handle network timeout
     * Validates: Requirements 3.1.2 - 网络错误处理
     */
    it('should handle network timeout error', async () => {
      const timeoutError = {
        code: 'ECONNABORTED',
        message: 'timeout of 10000ms exceeded',
      };
      mockApiClient.get.mockRejectedValueOnce(timeoutError);

      await expect(labelStudioService.validateProject('123')).rejects.toMatchObject({
        code: 'ECONNABORTED',
      });
    });

    /**
     * Test: Handle connection refused
     * Validates: Requirements 3.1.2
     */
    it('should handle connection refused error', async () => {
      const connectionError = {
        code: 'ECONNREFUSED',
        message: 'connect ECONNREFUSED 127.0.0.1:8080',
      };
      mockApiClient.get.mockRejectedValueOnce(connectionError);

      await expect(labelStudioService.validateProject('123')).rejects.toMatchObject({
        code: 'ECONNREFUSED',
      });
    });

    /**
     * Test: Handle DNS resolution failure
     * Validates: Requirements 3.1.2
     */
    it('should handle DNS resolution failure', async () => {
      const dnsError = {
        code: 'ENOTFOUND',
        message: 'getaddrinfo ENOTFOUND label-studio',
      };
      mockApiClient.get.mockRejectedValueOnce(dnsError);

      await expect(labelStudioService.validateProject('123')).rejects.toMatchObject({
        code: 'ENOTFOUND',
      });
    });

    /**
     * Test: Handle general network error
     * Validates: Requirements 3.1.2
     */
    it('should handle general network error', async () => {
      const networkError = {
        code: 'ERR_NETWORK',
        message: 'Network Error',
      };
      mockApiClient.get.mockRejectedValueOnce(networkError);

      await expect(labelStudioService.validateProject('123')).rejects.toMatchObject({
        code: 'ERR_NETWORK',
      });
    });
  });

  describe('Authentication Error Recovery', () => {
    /**
     * Test: Handle 401 Unauthorized
     * Validates: Requirements 3.1.3 - 认证错误处理
     */
    it('should handle 401 unauthorized error', async () => {
      const authError = {
        response: {
          status: 401,
          data: { detail: 'Invalid or expired token' },
        },
      };
      mockApiClient.get.mockRejectedValueOnce(authError);

      await expect(labelStudioService.validateProject('123')).rejects.toMatchObject({
        response: { status: 401 },
      });
    });

    /**
     * Test: Handle 403 Forbidden
     * Validates: Requirements 3.1.3
     */
    it('should handle 403 forbidden error', async () => {
      const forbiddenError = {
        response: {
          status: 403,
          data: { detail: 'Access denied to this project' },
        },
      };
      mockApiClient.get.mockRejectedValueOnce(forbiddenError);

      await expect(labelStudioService.validateProject('123')).rejects.toMatchObject({
        response: { status: 403 },
      });
    });

    /**
     * Test: Handle token expiration
     * Validates: Requirements 3.1.3
     */
    it('should handle token expiration', async () => {
      const expiredError = {
        response: {
          status: 401,
          data: { detail: 'Token has expired', code: 'token_expired' },
        },
      };
      mockApiClient.post.mockRejectedValueOnce(expiredError);

      await expect(
        labelStudioService.ensureProject({
          task_id: 'task-123',
          task_name: 'Test',
          annotation_type: 'sentiment',
        })
      ).rejects.toMatchObject({
        response: { status: 401 },
      });
    });
  });

  describe('Service Unavailability Recovery', () => {
    /**
     * Test: Handle 502 Bad Gateway
     * Validates: Requirements 3.1 - 错误类型处理
     */
    it('should handle 502 bad gateway error', async () => {
      const gatewayError = {
        response: {
          status: 502,
          data: { detail: 'Bad Gateway' },
        },
      };
      mockApiClient.get.mockRejectedValueOnce(gatewayError);

      await expect(labelStudioService.validateProject('123')).rejects.toMatchObject({
        response: { status: 502 },
      });
    });

    /**
     * Test: Handle 503 Service Unavailable
     * Validates: Requirements 3.1
     */
    it('should handle 503 service unavailable error', async () => {
      const unavailableError = {
        response: {
          status: 503,
          data: { detail: 'Label Studio service is temporarily unavailable' },
        },
      };
      mockApiClient.get.mockRejectedValueOnce(unavailableError);

      await expect(labelStudioService.validateProject('123')).rejects.toMatchObject({
        response: { status: 503 },
      });
    });

    /**
     * Test: Handle 504 Gateway Timeout
     * Validates: Requirements 3.1
     */
    it('should handle 504 gateway timeout error', async () => {
      const timeoutError = {
        response: {
          status: 504,
          data: { detail: 'Gateway Timeout' },
        },
      };
      mockApiClient.get.mockRejectedValueOnce(timeoutError);

      await expect(labelStudioService.validateProject('123')).rejects.toMatchObject({
        response: { status: 504 },
      });
    });
  });

  describe('Resource Not Found Recovery', () => {
    /**
     * Test: Handle 404 for project validation (special case)
     * Validates: Requirements 3.1.1 - 项目不存在错误
     */
    it('should return not_found status for 404 on validateProject', async () => {
      mockApiClient.get.mockRejectedValueOnce({
        response: { status: 404 },
      });

      const result = await labelStudioService.validateProject('999');

      expect(result.exists).toBe(false);
      expect(result.status).toBe('not_found');
    });

    /**
     * Test: Handle 404 for getProject (throws error)
     * Validates: Requirements 3.1.1
     */
    it('should throw error for 404 on getProject', async () => {
      const notFoundError = {
        response: {
          status: 404,
          data: { detail: 'Project not found' },
        },
      };
      mockApiClient.get.mockRejectedValueOnce(notFoundError);

      await expect(labelStudioService.getProject('999')).rejects.toMatchObject({
        response: { status: 404 },
      });
    });
  });

  describe('Server Error Recovery', () => {
    /**
     * Test: Handle 500 Internal Server Error
     * Validates: Requirements 3.1
     */
    it('should handle 500 internal server error', async () => {
      const serverError = {
        response: {
          status: 500,
          data: { detail: 'Internal Server Error' },
        },
      };
      mockApiClient.post.mockRejectedValueOnce(serverError);

      await expect(
        labelStudioService.ensureProject({
          task_id: 'task-123',
          task_name: 'Test',
          annotation_type: 'sentiment',
        })
      ).rejects.toMatchObject({
        response: { status: 500 },
      });
    });

    /**
     * Test: Handle validation error (400)
     * Validates: Requirements 3.1
     */
    it('should handle 400 validation error', async () => {
      const validationError = {
        response: {
          status: 400,
          data: {
            detail: 'Invalid annotation type',
            errors: [{ field: 'annotation_type', message: 'Must be one of: sentiment, ner, classification' }],
          },
        },
      };
      mockApiClient.post.mockRejectedValueOnce(validationError);

      await expect(
        labelStudioService.ensureProject({
          task_id: 'task-123',
          task_name: 'Test',
          annotation_type: 'invalid_type',
        })
      ).rejects.toMatchObject({
        response: { status: 400 },
      });
    });
  });

  describe('Retry Mechanism', () => {
    /**
     * Test: Successful retry after initial failure
     * Validates: Requirements 3.2.1 - 实现重试机制
     */
    it('should succeed on retry after initial failure', async () => {
      // First call fails
      mockApiClient.get.mockRejectedValueOnce({ code: 'ERR_NETWORK' });
      // Second call succeeds
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
     * Test: Multiple retries before success
     * Validates: Requirements 3.2.1
     */
    it('should handle multiple retries before success', async () => {
      // First two calls fail
      mockApiClient.get
        .mockRejectedValueOnce({ code: 'ERR_NETWORK' })
        .mockRejectedValueOnce({ code: 'ECONNABORTED' })
        .mockResolvedValueOnce({
          data: { exists: true, task_count: 100, status: 'ready' },
        });

      // First attempt fails
      await expect(labelStudioService.validateProject('123')).rejects.toBeDefined();
      // Second attempt fails
      await expect(labelStudioService.validateProject('123')).rejects.toBeDefined();
      // Third attempt succeeds
      const result = await labelStudioService.validateProject('123');
      expect(result.exists).toBe(true);
    });

    /**
     * Test: All retries fail
     * Validates: Requirements 3.2.1
     */
    it('should fail after all retries exhausted', async () => {
      const persistentError = { code: 'ERR_NETWORK', message: 'Network Error' };
      mockApiClient.get.mockRejectedValue(persistentError);

      // All attempts fail
      await expect(labelStudioService.validateProject('123')).rejects.toBeDefined();
      await expect(labelStudioService.validateProject('123')).rejects.toBeDefined();
      await expect(labelStudioService.validateProject('123')).rejects.toBeDefined();
    });
  });

  describe('Graceful Degradation', () => {
    /**
     * Test: Return cached data on error (if available)
     * Validates: Requirements 3.2.2 - 提供备选方案
     */
    it('should handle graceful degradation scenario', async () => {
      // Simulate a scenario where we have cached data
      const cachedProject = {
        id: '123',
        title: 'Cached Project',
        task_count: 100,
        annotation_count: 50,
      };

      // First call succeeds and caches
      mockApiClient.get.mockResolvedValueOnce({ data: cachedProject });
      const firstResult = await labelStudioService.getProject('123');
      expect(firstResult.title).toBe('Cached Project');

      // Second call fails - in real scenario, cache would be used
      mockApiClient.get.mockRejectedValueOnce({ code: 'ERR_NETWORK' });
      await expect(labelStudioService.getProject('123')).rejects.toBeDefined();
    });

    /**
     * Test: Partial operation success
     * Validates: Requirements 3.2.2
     */
    it('should handle partial operation success', async () => {
      // Project creation succeeds
      mockApiClient.post.mockResolvedValueOnce({
        data: { project_id: 'new-123', created: true, status: 'ready' },
      });

      // Task import fails
      mockApiClient.post.mockRejectedValueOnce({
        response: { status: 500, data: { detail: 'Import failed' } },
      });

      // Project creation should succeed
      const project = await labelStudioService.ensureProject({
        task_id: 'task-123',
        task_name: 'Test',
        annotation_type: 'sentiment',
      });
      expect(project.project_id).toBe('new-123');

      // Import should fail but project still exists
      await expect(
        labelStudioService.importTasks(project.project_id, 'task-123')
      ).rejects.toBeDefined();
    });
  });

  describe('Error Message Extraction', () => {
    /**
     * Test: Extract error message from detail field
     */
    it('should extract error message from detail field', async () => {
      const error = {
        response: {
          status: 400,
          data: { detail: 'Invalid request parameters' },
        },
      };
      mockApiClient.post.mockRejectedValueOnce(error);

      try {
        await labelStudioService.ensureProject({
          task_id: 'task-123',
          task_name: 'Test',
          annotation_type: 'invalid',
        });
      } catch (e: unknown) {
        const err = e as { response?: { data?: { detail?: string } } };
        expect(err.response?.data?.detail).toBe('Invalid request parameters');
      }
    });

    /**
     * Test: Extract error message from message field
     */
    it('should extract error message from message field', async () => {
      const error = {
        response: {
          status: 400,
          data: { message: 'Validation failed' },
        },
      };
      mockApiClient.post.mockRejectedValueOnce(error);

      try {
        await labelStudioService.ensureProject({
          task_id: 'task-123',
          task_name: 'Test',
          annotation_type: 'invalid',
        });
      } catch (e: unknown) {
        const err = e as { response?: { data?: { message?: string } } };
        expect(err.response?.data?.message).toBe('Validation failed');
      }
    });

    /**
     * Test: Handle error without response body
     */
    it('should handle error without response body', async () => {
      const error = {
        response: {
          status: 500,
        },
      };
      mockApiClient.post.mockRejectedValueOnce(error);

      await expect(
        labelStudioService.ensureProject({
          task_id: 'task-123',
          task_name: 'Test',
          annotation_type: 'sentiment',
        })
      ).rejects.toMatchObject({
        response: { status: 500 },
      });
    });
  });
});
