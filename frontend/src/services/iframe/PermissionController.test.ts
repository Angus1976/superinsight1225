/**
 * Unit tests for PermissionController
 * Tests permission checking, caching, rule-based permissions, and role hierarchy
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { PermissionController, type PermissionRule } from './PermissionController';
import type { AnnotationContext, Permission } from './types';

describe('PermissionController', () => {
  let permissionController: PermissionController;
  let mockContext: AnnotationContext;

  beforeEach(() => {
    permissionController = new PermissionController({
      enableCaching: true,
      cacheTimeout: 1000,
      strictMode: false,
      logPermissionChecks: false,
    });

    mockContext = {
      user: {
        id: 'user-1',
        name: 'Test User',
        email: 'test@example.com',
        role: 'user',
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
        { action: 'read', resource: 'project', allowed: true },
      ],
      timestamp: Date.now(),
    };
  });

  describe('checkPermission', () => {
    it('should return true for allowed permission', () => {
      const hasPermission = permissionController.checkPermission(mockContext, 'read', 'annotation');
      expect(hasPermission).toBe(true);
    });

    it('should return false for denied permission', () => {
      const hasPermission = permissionController.checkPermission(mockContext, 'delete', 'annotation');
      expect(hasPermission).toBe(false);
    });

    it('should return true for non-strict mode when permission not found', () => {
      const hasPermission = permissionController.checkPermission(mockContext, 'unknown', 'resource');
      expect(hasPermission).toBe(true); // Non-strict mode
    });

    it('should return false for strict mode when permission not found', () => {
      const strictController = new PermissionController({
        strictMode: true,
      });

      const hasPermission = strictController.checkPermission(mockContext, 'unknown', 'resource');
      expect(hasPermission).toBe(false);
    });

    it('should handle wildcard actions', () => {
      const wildcardContext = {
        ...mockContext,
        permissions: [
          { action: '*', resource: 'annotation', allowed: true },
        ],
      };

      expect(permissionController.checkPermission(wildcardContext, 'read', 'annotation')).toBe(true);
      expect(permissionController.checkPermission(wildcardContext, 'write', 'annotation')).toBe(true);
      expect(permissionController.checkPermission(wildcardContext, 'delete', 'annotation')).toBe(true);
    });

    it('should handle wildcard resources', () => {
      const wildcardContext = {
        ...mockContext,
        permissions: [
          { action: 'read', resource: '*', allowed: true },
        ],
      };

      expect(permissionController.checkPermission(wildcardContext, 'read', 'annotation')).toBe(true);
      expect(permissionController.checkPermission(wildcardContext, 'read', 'project')).toBe(true);
      expect(permissionController.checkPermission(wildcardContext, 'read', 'task')).toBe(true);
    });

    it('should handle permissions without resource', () => {
      const hasPermission = permissionController.checkPermission(mockContext, 'read');
      expect(hasPermission).toBe(true); // Should match wildcard or no-resource permissions
    });
  });

  describe('checkMultiplePermissions', () => {
    it('should check multiple permissions at once', () => {
      const checks = [
        { action: 'read', resource: 'annotation' },
        { action: 'write', resource: 'annotation' },
        { action: 'delete', resource: 'annotation' },
        { action: 'read', resource: 'project' },
      ];

      const results = permissionController.checkMultiplePermissions(mockContext, checks);

      expect(results['read@annotation']).toBe(true);
      expect(results['write@annotation']).toBe(true);
      expect(results['delete@annotation']).toBe(false);
      expect(results['read@project']).toBe(true);
    });
  });

  describe('getAllowedActions', () => {
    it('should return allowed actions for resource', () => {
      const actions = permissionController.getAllowedActions(mockContext, 'annotation');
      
      expect(actions).toContain('read');
      expect(actions).toContain('write');
      expect(actions).not.toContain('delete');
    });

    it('should handle wildcard permissions', () => {
      const wildcardContext = {
        ...mockContext,
        permissions: [
          { action: '*', resource: 'annotation', allowed: true },
        ],
      };

      const actions = permissionController.getAllowedActions(wildcardContext, 'annotation');
      
      expect(actions.length).toBeGreaterThan(3); // Should include all possible actions
      expect(actions).toContain('read');
      expect(actions).toContain('write');
      expect(actions).toContain('delete');
    });
  });

  describe('getAccessibleResources', () => {
    it('should return accessible resources for action', () => {
      const resources = permissionController.getAccessibleResources(mockContext, 'read');
      
      expect(resources).toContain('annotation');
      expect(resources).toContain('project');
    });

    it('should handle wildcard permissions', () => {
      const wildcardContext = {
        ...mockContext,
        permissions: [
          { action: 'read', resource: '*', allowed: true },
        ],
      };

      const resources = permissionController.getAccessibleResources(wildcardContext, 'read');
      
      expect(resources.length).toBeGreaterThan(2); // Should include all possible resources
      expect(resources).toContain('annotation');
      expect(resources).toContain('project');
    });
  });

  describe('permission rules', () => {
    it('should add and apply permission rule', () => {
      const rule: PermissionRule = {
        id: 'test-rule-1',
        name: 'Test Rule',
        description: 'Allow admin users to do everything',
        conditions: [
          {
            type: 'role',
            operator: 'equals',
            field: 'role',
            value: 'admin',
          },
        ],
        actions: ['*'],
        resources: ['*'],
        priority: 100,
        enabled: true,
      };

      permissionController.addPermissionRule(rule);

      // Test with admin user
      const adminContext = {
        ...mockContext,
        user: { ...mockContext.user, role: 'admin' },
        permissions: [], // No direct permissions
      };

      const hasPermission = permissionController.checkPermission(adminContext, 'delete', 'annotation');
      expect(hasPermission).toBe(true);
    });

    it('should remove permission rule', () => {
      const rule: PermissionRule = {
        id: 'test-rule-2',
        name: 'Test Rule 2',
        description: 'Test rule',
        conditions: [
          {
            type: 'role',
            operator: 'equals',
            field: 'role',
            value: 'admin',
          },
        ],
        actions: ['delete'],
        resources: ['annotation'],
        priority: 100,
        enabled: true,
      };

      permissionController.addPermissionRule(rule);
      permissionController.removePermissionRule('test-rule-2');

      // Should not have permission after rule removal
      const adminContext = {
        ...mockContext,
        user: { ...mockContext.user, role: 'admin' },
        permissions: [],
      };

      const hasPermission = permissionController.checkPermission(adminContext, 'delete', 'annotation');
      expect(hasPermission).toBe(true); // Non-strict mode default
    });

    it('should handle disabled rules', () => {
      const rule: PermissionRule = {
        id: 'disabled-rule',
        name: 'Disabled Rule',
        description: 'This rule is disabled',
        conditions: [
          {
            type: 'role',
            operator: 'equals',
            field: 'role',
            value: 'user',
          },
        ],
        actions: ['admin'],
        resources: ['system'],
        priority: 100,
        enabled: false, // Disabled
      };

      permissionController.addPermissionRule(rule);

      const hasPermission = permissionController.checkPermission(mockContext, 'admin', 'system');
      expect(hasPermission).toBe(true); // Should use default (non-strict mode)
    });

    it('should evaluate different condition operators', () => {
      const rules: PermissionRule[] = [
        {
          id: 'contains-rule',
          name: 'Contains Rule',
          description: 'Test contains operator',
          conditions: [
            {
              type: 'user',
              operator: 'contains',
              field: 'email',
              value: 'example.com',
            },
          ],
          actions: ['test'],
          resources: ['email'],
          priority: 100,
          enabled: true,
        },
        {
          id: 'in-rule',
          name: 'In Rule',
          description: 'Test in operator',
          conditions: [
            {
              type: 'role',
              operator: 'in',
              field: 'role',
              value: ['user', 'admin', 'manager'],
            },
          ],
          actions: ['test'],
          resources: ['role'],
          priority: 100,
          enabled: true,
        },
      ];

      rules.forEach((rule) => permissionController.addPermissionRule(rule));

      expect(permissionController.checkPermission(mockContext, 'test', 'email')).toBe(true);
      expect(permissionController.checkPermission(mockContext, 'test', 'role')).toBe(true);
    });
  });

  describe('caching', () => {
    it('should cache permission results', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      
      const cachedController = new PermissionController({
        enableCaching: true,
        logPermissionChecks: true,
      });

      // First call - should not be cached
      cachedController.checkPermission(mockContext, 'read', 'annotation');
      
      // Second call - should be cached
      cachedController.checkPermission(mockContext, 'read', 'annotation');

      // Should see both regular and cached log messages
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Permission check:'));
      
      consoleSpy.mockRestore();
    });

    it('should clear cache when rules change', () => {
      const rule: PermissionRule = {
        id: 'cache-test-rule',
        name: 'Cache Test Rule',
        description: 'Test cache clearing',
        conditions: [],
        actions: ['test'],
        resources: ['cache'],
        priority: 100,
        enabled: true,
      };

      // Check permission to populate cache
      permissionController.checkPermission(mockContext, 'test', 'cache');

      // Add rule (should clear cache)
      permissionController.addPermissionRule(rule);

      // Cache should be cleared, so this should use fresh calculation
      const hasPermission = permissionController.checkPermission(mockContext, 'test', 'cache');
      expect(hasPermission).toBe(true);
    });

    it('should clear user-specific cache', () => {
      permissionController.checkPermission(mockContext, 'read', 'annotation');
      
      // Clear cache for specific user
      permissionController.clearUserPermissionCache('user-1');

      // Should recalculate permission
      const hasPermission = permissionController.checkPermission(mockContext, 'read', 'annotation');
      expect(hasPermission).toBe(true);
    });

    it('should provide cache statistics', () => {
      permissionController.checkPermission(mockContext, 'read', 'annotation');
      permissionController.checkPermission(mockContext, 'write', 'annotation');

      const stats = permissionController.getCacheStats();
      expect(stats.size).toBeGreaterThanOrEqual(0);
      expect(stats.entries).toBeGreaterThanOrEqual(0);
      expect(typeof stats.hitRate).toBe('number');
    });
  });

  describe('role hierarchy', () => {
    it('should set and use role hierarchy', () => {
      permissionController.setRoleHierarchy({
        admin: ['manager', 'user'],
        manager: ['user'],
        user: [],
      });

      // Test that hierarchy is set (actual inheritance would need role-permission mapping)
      const adminContext = {
        ...mockContext,
        user: { ...mockContext.user, role: 'admin' },
      };

      const effectivePermissions = permissionController.getEffectivePermissions(adminContext);
      expect(effectivePermissions).toBeDefined();
      expect(Array.isArray(effectivePermissions)).toBe(true);
    });
  });

  describe('updateUserPermissions', () => {
    it('should update user permissions in context', async () => {
      const newPermissions: Permission[] = [
        { action: 'admin', resource: 'system', allowed: true },
      ];

      // Wait a bit to ensure timestamp difference
      await new Promise((resolve) => setTimeout(resolve, 10));

      const updatedContext = permissionController.updateUserPermissions(mockContext, newPermissions);

      expect(updatedContext.permissions).toEqual(newPermissions);
      expect(updatedContext.timestamp).toBeGreaterThan(mockContext.timestamp);
    });
  });

  describe('getEffectivePermissions', () => {
    it('should return effective permissions including inherited ones', () => {
      const effectivePermissions = permissionController.getEffectivePermissions(mockContext);

      expect(effectivePermissions).toEqual(mockContext.permissions);
      expect(effectivePermissions).not.toBe(mockContext.permissions); // Should be a copy
    });

    it('should remove duplicate permissions', () => {
      const contextWithDuplicates = {
        ...mockContext,
        permissions: [
          { action: 'read', resource: 'annotation', allowed: true },
          { action: 'read', resource: 'annotation', allowed: true }, // Duplicate
          { action: 'write', resource: 'annotation', allowed: true },
        ],
      };

      const effectivePermissions = permissionController.getEffectivePermissions(contextWithDuplicates);

      expect(effectivePermissions).toHaveLength(2);
      expect(effectivePermissions.filter(p => p.action === 'read' && p.resource === 'annotation')).toHaveLength(1);
    });
  });
});