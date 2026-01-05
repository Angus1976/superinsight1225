/**
 * Unit tests for ContextManager
 * Tests context management, permission validation, encryption, and session handling
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ContextManager } from './ContextManager';
import type { AnnotationContext, UserInfo, ProjectInfo, TaskInfo, Permission } from './types';

describe('ContextManager', () => {
  let contextManager: ContextManager;
  let mockContext: AnnotationContext;

  beforeEach(() => {
    contextManager = new ContextManager({
      enableEncryption: false,
      sessionTimeout: 1000, // 1 second for testing
      autoRefresh: false,
    });

    mockContext = {
      user: {
        id: 'user-1',
        name: 'Test User',
        email: 'test@example.com',
        role: 'annotator',
      },
      project: {
        id: 'project-1',
        name: 'Test Project',
        description: 'Test project description',
        status: 'active',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      },
      task: {
        id: 'task-1',
        name: 'Test Task',
        status: 'pending',
        progress: 0,
      },
      permissions: [
        { action: 'read', resource: 'annotation', allowed: true },
        { action: 'write', resource: 'annotation', allowed: true },
        { action: 'delete', resource: 'annotation', allowed: false },
      ],
      timestamp: Date.now(),
    };
  });

  afterEach(() => {
    contextManager.clearContext();
  });

  describe('setContext', () => {
    it('should set valid context', () => {
      contextManager.setContext(mockContext);

      const retrievedContext = contextManager.getContext();
      expect(retrievedContext).toBeDefined();
      expect(retrievedContext?.user.id).toBe('user-1');
      expect(retrievedContext?.project.id).toBe('project-1');
      expect(retrievedContext?.task.id).toBe('task-1');
    });

    it('should generate session ID if not provided', () => {
      contextManager.setContext(mockContext);

      const retrievedContext = contextManager.getContext();
      expect(retrievedContext?.sessionId).toBeDefined();
      expect(retrievedContext?.sessionId).toMatch(/^session_/);
    });

    it('should update timestamp when setting context', () => {
      const originalTimestamp = mockContext.timestamp;
      
      // Wait a bit to ensure timestamp difference
      setTimeout(() => {
        contextManager.setContext(mockContext);
        
        const retrievedContext = contextManager.getContext();
        expect(retrievedContext?.timestamp).toBeGreaterThan(originalTimestamp);
      }, 10);
    });

    it('should throw error for invalid context', () => {
      const invalidContext = {
        user: { id: 'user-1' }, // Missing required fields
        project: mockContext.project,
        task: mockContext.task,
        permissions: mockContext.permissions,
        timestamp: Date.now(),
      };

      expect(() => {
        contextManager.setContext(invalidContext as AnnotationContext);
      }).toThrow('Invalid context structure');
    });

    it('should notify context change listeners', () => {
      const listener = vi.fn();
      contextManager.onContextChange(listener);

      contextManager.setContext(mockContext);

      expect(listener).toHaveBeenCalledWith(expect.objectContaining({
        user: mockContext.user,
        project: mockContext.project,
        task: mockContext.task,
      }));
    });
  });

  describe('getContext', () => {
    it('should return null when no context is set', () => {
      const context = contextManager.getContext();
      expect(context).toBeNull();
    });

    it('should return copy of context', () => {
      contextManager.setContext(mockContext);

      const context1 = contextManager.getContext();
      const context2 = contextManager.getContext();

      expect(context1).toEqual(context2);
      expect(context1).not.toBe(context2); // Different objects
    });

    it('should return null for expired context', async () => {
      const shortTimeoutManager = new ContextManager({
        sessionTimeout: 50, // 50ms
        autoRefresh: false,
      });

      shortTimeoutManager.setContext(mockContext);

      // Wait for context to expire
      await new Promise((resolve) => setTimeout(resolve, 100));

      const context = shortTimeoutManager.getContext();
      expect(context).toBeNull();
    });
  });

  describe('checkPermission', () => {
    beforeEach(() => {
      contextManager.setContext(mockContext);
    });

    it('should return true for allowed permission', () => {
      const hasPermission = contextManager.checkPermission('read', 'annotation');
      expect(hasPermission).toBe(true);
    });

    it('should return false for denied permission', () => {
      const hasPermission = contextManager.checkPermission('delete', 'annotation');
      expect(hasPermission).toBe(false);
    });

    it('should return false for non-existent permission', () => {
      const hasPermission = contextManager.checkPermission('admin', 'system');
      expect(hasPermission).toBe(false);
    });

    it('should handle wildcard permissions', () => {
      const wildcardContext = {
        ...mockContext,
        permissions: [
          { action: '*', resource: 'annotation', allowed: true },
        ],
      };

      contextManager.setContext(wildcardContext);

      expect(contextManager.checkPermission('read', 'annotation')).toBe(true);
      expect(contextManager.checkPermission('write', 'annotation')).toBe(true);
      expect(contextManager.checkPermission('delete', 'annotation')).toBe(true);
    });

    it('should handle resource wildcard permissions', () => {
      const wildcardContext = {
        ...mockContext,
        permissions: [
          { action: 'read', resource: '*', allowed: true },
        ],
      };

      contextManager.setContext(wildcardContext);

      expect(contextManager.checkPermission('read', 'annotation')).toBe(true);
      expect(contextManager.checkPermission('read', 'project')).toBe(true);
      expect(contextManager.checkPermission('read', 'task')).toBe(true);
    });

    it('should return false when no context is available', () => {
      contextManager.clearContext();

      const hasPermission = contextManager.checkPermission('read', 'annotation');
      expect(hasPermission).toBe(false);
    });
  });

  describe('updatePermissions', () => {
    beforeEach(() => {
      contextManager.setContext(mockContext);
    });

    it('should update permissions successfully', () => {
      const newPermissions: Permission[] = [
        { action: 'read', resource: 'annotation', allowed: true },
        { action: 'admin', resource: 'system', allowed: true },
      ];

      contextManager.updatePermissions(newPermissions);

      expect(contextManager.checkPermission('admin', 'system')).toBe(true);
      expect(contextManager.checkPermission('write', 'annotation')).toBe(false);
    });

    it('should notify listeners when permissions are updated', () => {
      const listener = vi.fn();
      contextManager.onContextChange(listener);

      const newPermissions: Permission[] = [
        { action: 'read', resource: 'annotation', allowed: true },
      ];

      contextManager.updatePermissions(newPermissions);

      expect(listener).toHaveBeenCalledWith(expect.objectContaining({
        permissions: newPermissions,
      }));
    });

    it('should throw error when no context is available', () => {
      contextManager.clearContext();

      expect(() => {
        contextManager.updatePermissions([]);
      }).toThrow('No context available to update permissions');
    });
  });

  describe('encryption', () => {
    it('should encrypt and decrypt context', () => {
      const encryptedManager = new ContextManager({
        enableEncryption: true,
        encryptionKey: 'test-key',
      });

      encryptedManager.setContext(mockContext);

      const encrypted = encryptedManager.getEncryptedContext();
      expect(encrypted).toBeDefined();
      expect(encrypted).not.toContain('Test User');

      // Create new manager and set encrypted context
      const newManager = new ContextManager({
        enableEncryption: true,
        encryptionKey: 'test-key',
      });

      newManager.setEncryptedContext(encrypted);

      const decryptedContext = newManager.getContext();
      expect(decryptedContext?.user.name).toBe('Test User');
      expect(decryptedContext?.project.name).toBe('Test Project');
    });

    it('should handle unencrypted context when encryption is disabled', () => {
      contextManager.setContext(mockContext);

      const contextData = contextManager.getEncryptedContext();
      const parsed = JSON.parse(contextData);

      expect(parsed.user.name).toBe('Test User');
    });

    it('should throw error for invalid encrypted data', () => {
      const encryptedManager = new ContextManager({
        enableEncryption: true,
      });

      expect(() => {
        encryptedManager.setEncryptedContext('invalid-data');
      }).toThrow('Invalid encrypted context data');
    });
  });

  describe('session management', () => {
    it('should refresh context', () => {
      contextManager.setContext(mockContext);
      const originalTimestamp = contextManager.getContext()?.timestamp;

      // Wait a bit and refresh
      setTimeout(() => {
        contextManager.refreshContext();
        
        const refreshedContext = contextManager.getContext();
        expect(refreshedContext?.timestamp).toBeGreaterThan(originalTimestamp!);
      }, 10);
    });

    it('should clear context', () => {
      contextManager.setContext(mockContext);
      expect(contextManager.getContext()).toBeDefined();

      contextManager.clearContext();
      expect(contextManager.getContext()).toBeNull();
    });

    it('should notify listeners when context is cleared', () => {
      const listener = vi.fn();
      contextManager.onContextChange(listener);

      contextManager.setContext(mockContext);
      contextManager.clearContext();

      expect(listener).toHaveBeenCalledWith(null);
    });

    it('should check if context is expired', () => {
      const shortTimeoutManager = new ContextManager({
        sessionTimeout: 50, // 50ms
      });

      shortTimeoutManager.setContext(mockContext);
      expect(shortTimeoutManager.isContextExpired()).toBe(false);

      // Wait for expiration
      setTimeout(() => {
        expect(shortTimeoutManager.isContextExpired()).toBe(true);
      }, 100);
    });
  });

  describe('context accessors', () => {
    beforeEach(() => {
      contextManager.setContext(mockContext);
    });

    it('should get user information', () => {
      const user = contextManager.getUser();
      expect(user).toEqual(mockContext.user);
    });

    it('should get project information', () => {
      const project = contextManager.getProject();
      expect(project).toEqual(mockContext.project);
    });

    it('should get task information', () => {
      const task = contextManager.getTask();
      expect(task).toEqual(mockContext.task);
    });

    it('should get permissions', () => {
      const permissions = contextManager.getPermissions();
      expect(permissions).toEqual(mockContext.permissions);
    });

    it('should return null when no context is set', () => {
      contextManager.clearContext();

      expect(contextManager.getUser()).toBeNull();
      expect(contextManager.getProject()).toBeNull();
      expect(contextManager.getTask()).toBeNull();
      expect(contextManager.getPermissions()).toEqual([]);
    });
  });

  describe('context summary', () => {
    it('should generate context summary', () => {
      contextManager.setContext(mockContext);

      const summary = contextManager.getContextSummary();
      expect(summary).toBeDefined();
      expect(summary?.userId).toBe('user-1');
      expect(summary?.userName).toBe('Test User');
      expect(summary?.userRole).toBe('annotator');
      expect(summary?.projectId).toBe('project-1');
      expect(summary?.taskId).toBe('task-1');
      expect(summary?.permissionCount).toBe(3);
    });

    it('should return null summary when no context', () => {
      const summary = contextManager.getContextSummary();
      expect(summary).toBeNull();
    });
  });

  describe('event listeners', () => {
    it('should add and remove context change listeners', () => {
      const listener1 = vi.fn();
      const listener2 = vi.fn();

      contextManager.onContextChange(listener1);
      contextManager.onContextChange(listener2);

      contextManager.setContext(mockContext);

      expect(listener1).toHaveBeenCalled();
      expect(listener2).toHaveBeenCalled();

      // Remove one listener
      contextManager.offContextChange(listener1);
      listener1.mockClear();
      listener2.mockClear();

      contextManager.refreshContext();

      expect(listener1).not.toHaveBeenCalled();
      expect(listener2).toHaveBeenCalled();
    });

    it('should handle listener errors gracefully', () => {
      const errorListener = vi.fn(() => {
        throw new Error('Listener error');
      });
      const normalListener = vi.fn();

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      contextManager.onContextChange(errorListener);
      contextManager.onContextChange(normalListener);

      contextManager.setContext(mockContext);

      expect(errorListener).toHaveBeenCalled();
      expect(normalListener).toHaveBeenCalled();
      expect(consoleSpy).toHaveBeenCalledWith('Error in context change listener:', expect.any(Error));

      consoleSpy.mockRestore();
    });
  });
});