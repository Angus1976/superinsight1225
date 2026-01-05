/**
 * PermissionController - Advanced permission control and validation
 * Handles permission checking, caching, updates, and role-based access control
 */

import type { Permission, AnnotationContext, UserInfo } from './types';

export interface PermissionRule {
  id: string;
  name: string;
  description: string;
  conditions: PermissionCondition[];
  actions: string[];
  resources: string[];
  priority: number;
  enabled: boolean;
}

export interface PermissionCondition {
  type: 'role' | 'user' | 'project' | 'task' | 'time' | 'custom';
  operator: 'equals' | 'contains' | 'startsWith' | 'endsWith' | 'regex' | 'in' | 'not_in';
  field: string;
  value: unknown;
}

export interface PermissionCache {
  userId: string;
  permissions: Map<string, boolean>;
  timestamp: number;
  ttl: number;
}

export interface PermissionControllerConfig {
  enableCaching?: boolean;
  cacheTimeout?: number;
  strictMode?: boolean;
  logPermissionChecks?: boolean;
}

export class PermissionController {
  private config: Required<PermissionControllerConfig>;
  private permissionCache: Map<string, PermissionCache> = new Map();
  private permissionRules: PermissionRule[] = [];
  private roleHierarchy: Map<string, string[]> = new Map();

  constructor(config: PermissionControllerConfig = {}) {
    this.config = {
      enableCaching: config.enableCaching || true,
      cacheTimeout: config.cacheTimeout || 300000, // 5 minutes
      strictMode: config.strictMode || false,
      logPermissionChecks: config.logPermissionChecks || false,
    };

    this.initializeDefaultRoles();
  }

  /**
   * Check if user has permission for specific action and resource
   */
  checkPermission(
    context: AnnotationContext,
    action: string,
    resource?: string,
    additionalData?: Record<string, unknown>
  ): boolean {
    const cacheKey = this.generateCacheKey(context.user.id, action, resource);

    // Check cache first
    if (this.config.enableCaching) {
      const cached = this.getCachedPermission(cacheKey);
      if (cached !== null) {
        if (this.config.logPermissionChecks) {
          console.log(`Permission check (cached): ${action}@${resource} = ${cached}`);
        }
        return cached;
      }
    }

    // Perform permission check
    const hasPermission = this.performPermissionCheck(context, action, resource, additionalData);

    // Cache result
    if (this.config.enableCaching) {
      this.cachePermission(cacheKey, context.user.id, hasPermission);
    }

    if (this.config.logPermissionChecks) {
      console.log(`Permission check: ${action}@${resource} = ${hasPermission}`);
    }

    return hasPermission;
  }

  /**
   * Check multiple permissions at once
   */
  checkMultiplePermissions(
    context: AnnotationContext,
    checks: Array<{ action: string; resource?: string }>
  ): Record<string, boolean> {
    const results: Record<string, boolean> = {};

    for (const check of checks) {
      const key = `${check.action}@${check.resource || '*'}`;
      results[key] = this.checkPermission(context, check.action, check.resource);
    }

    return results;
  }

  /**
   * Get all allowed actions for a resource
   */
  getAllowedActions(context: AnnotationContext, resource: string): string[] {
    const allowedActions: string[] = [];

    // Check direct permissions
    for (const permission of context.permissions) {
      if (permission.allowed && (permission.resource === resource || permission.resource === '*')) {
        if (permission.action === '*') {
          // Return all possible actions for wildcard
          allowedActions.push(...this.getAllPossibleActions());
        } else {
          allowedActions.push(permission.action);
        }
      }
    }

    // Check rule-based permissions
    const ruleActions = this.getRuleBasedActions(context, resource);
    allowedActions.push(...ruleActions);

    // Remove duplicates and return
    return [...new Set(allowedActions)];
  }

  /**
   * Get all accessible resources for an action
   */
  getAccessibleResources(context: AnnotationContext, action: string): string[] {
    const accessibleResources: string[] = [];

    // Check direct permissions
    for (const permission of context.permissions) {
      if (permission.allowed && (permission.action === action || permission.action === '*')) {
        if (permission.resource === '*') {
          // Return all possible resources for wildcard
          accessibleResources.push(...this.getAllPossibleResources());
        } else {
          accessibleResources.push(permission.resource);
        }
      }
    }

    // Check rule-based permissions
    const ruleResources = this.getRuleBasedResources(context, action);
    accessibleResources.push(...ruleResources);

    // Remove duplicates and return
    return [...new Set(accessibleResources)];
  }

  /**
   * Add permission rule
   */
  addPermissionRule(rule: PermissionRule): void {
    // Validate rule
    if (!this.isValidPermissionRule(rule)) {
      throw new Error('Invalid permission rule');
    }

    // Remove existing rule with same ID
    this.permissionRules = this.permissionRules.filter((r) => r.id !== rule.id);

    // Add new rule
    this.permissionRules.push(rule);

    // Sort by priority (higher priority first)
    this.permissionRules.sort((a, b) => b.priority - a.priority);

    // Clear cache as rules have changed
    this.clearPermissionCache();

    console.log(`Permission rule added: ${rule.name}`);
  }

  /**
   * Remove permission rule
   */
  removePermissionRule(ruleId: string): void {
    const initialLength = this.permissionRules.length;
    this.permissionRules = this.permissionRules.filter((r) => r.id !== ruleId);

    if (this.permissionRules.length < initialLength) {
      this.clearPermissionCache();
      console.log(`Permission rule removed: ${ruleId}`);
    }
  }

  /**
   * Update user permissions in context
   */
  updateUserPermissions(context: AnnotationContext, newPermissions: Permission[]): AnnotationContext {
    const updatedContext: AnnotationContext = {
      ...context,
      permissions: newPermissions,
      timestamp: Date.now(),
    };

    // Clear cache for this user
    this.clearUserPermissionCache(context.user.id);

    return updatedContext;
  }

  /**
   * Set role hierarchy
   */
  setRoleHierarchy(hierarchy: Record<string, string[]>): void {
    this.roleHierarchy.clear();
    for (const [role, inherits] of Object.entries(hierarchy)) {
      this.roleHierarchy.set(role, inherits);
    }

    // Clear cache as hierarchy has changed
    this.clearPermissionCache();

    console.log('Role hierarchy updated');
  }

  /**
   * Get effective permissions including inherited from roles
   */
  getEffectivePermissions(context: AnnotationContext): Permission[] {
    const effectivePermissions = [...context.permissions];

    // Add permissions from role hierarchy
    const inheritedPermissions = this.getInheritedPermissions(context.user.role);
    effectivePermissions.push(...inheritedPermissions);

    // Remove duplicates (keep the first occurrence)
    const seen = new Set<string>();
    return effectivePermissions.filter((permission) => {
      const key = `${permission.action}:${permission.resource}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }

  /**
   * Clear permission cache
   */
  clearPermissionCache(): void {
    this.permissionCache.clear();
    console.log('Permission cache cleared');
  }

  /**
   * Clear permission cache for specific user
   */
  clearUserPermissionCache(userId: string): void {
    const keysToDelete: string[] = [];
    for (const [key, cache] of this.permissionCache.entries()) {
      if (cache.userId === userId) {
        keysToDelete.push(key);
      }
    }

    keysToDelete.forEach((key) => this.permissionCache.delete(key));
    console.log(`Permission cache cleared for user: ${userId}`);
  }

  /**
   * Get permission cache statistics
   */
  getCacheStats(): { size: number; hitRate: number; entries: number } {
    const now = Date.now();
    let validEntries = 0;

    for (const cache of this.permissionCache.values()) {
      if (now - cache.timestamp < cache.ttl) {
        validEntries++;
      }
    }

    return {
      size: this.permissionCache.size,
      hitRate: 0, // Would need to track hits/misses for accurate calculation
      entries: validEntries,
    };
  }

  /**
   * Perform actual permission check
   */
  private performPermissionCheck(
    context: AnnotationContext,
    action: string,
    resource?: string,
    additionalData?: Record<string, unknown>
  ): boolean {
    // Get effective permissions (including inherited)
    const effectivePermissions = this.getEffectivePermissions(context);

    // Check direct permissions first
    const directPermission = this.checkDirectPermissions(effectivePermissions, action, resource);
    if (directPermission !== null) {
      return directPermission;
    }

    // Check rule-based permissions
    const rulePermission = this.checkRuleBasedPermissions(context, action, resource, additionalData);
    if (rulePermission !== null) {
      return rulePermission;
    }

    // Default behavior based on strict mode
    return !this.config.strictMode;
  }

  /**
   * Check direct permissions
   */
  private checkDirectPermissions(permissions: Permission[], action: string, resource?: string): boolean | null {
    // Look for exact matches first
    for (const permission of permissions) {
      if (this.matchesPermission(permission, action, resource)) {
        return permission.allowed;
      }
    }

    return null;
  }

  /**
   * Check if permission matches action and resource
   */
  private matchesPermission(permission: Permission, action: string, resource?: string): boolean {
    // Check action match
    const actionMatch = permission.action === '*' || permission.action === action;
    if (!actionMatch) {
      return false;
    }

    // Check resource match
    const resourceMatch = 
      permission.resource === '*' || 
      !resource || 
      permission.resource === resource;

    return resourceMatch;
  }

  /**
   * Check rule-based permissions
   */
  private checkRuleBasedPermissions(
    context: AnnotationContext,
    action: string,
    resource?: string,
    additionalData?: Record<string, unknown>
  ): boolean | null {
    for (const rule of this.permissionRules) {
      if (!rule.enabled) {
        continue;
      }

      // Check if rule applies to this action/resource
      if (!this.ruleApplies(rule, action, resource)) {
        continue;
      }

      // Check if all conditions are met
      if (this.evaluateRuleConditions(rule, context, additionalData)) {
        return true; // Rule grants permission
      }
    }

    return null;
  }

  /**
   * Check if rule applies to action/resource
   */
  private ruleApplies(rule: PermissionRule, action: string, resource?: string): boolean {
    const actionMatch = rule.actions.includes('*') || rule.actions.includes(action);
    const resourceMatch = rule.resources.includes('*') || !resource || rule.resources.includes(resource);
    
    return actionMatch && resourceMatch;
  }

  /**
   * Evaluate rule conditions
   */
  private evaluateRuleConditions(
    rule: PermissionRule,
    context: AnnotationContext,
    additionalData?: Record<string, unknown>
  ): boolean {
    for (const condition of rule.conditions) {
      if (!this.evaluateCondition(condition, context, additionalData)) {
        return false; // All conditions must be true
      }
    }

    return true;
  }

  /**
   * Evaluate single condition
   */
  private evaluateCondition(
    condition: PermissionCondition,
    context: AnnotationContext,
    additionalData?: Record<string, unknown>
  ): boolean {
    let fieldValue: unknown;

    // Get field value based on condition type
    switch (condition.type) {
      case 'role':
        fieldValue = context.user.role;
        break;
      case 'user':
        fieldValue = (context.user as any)[condition.field];
        break;
      case 'project':
        fieldValue = (context.project as any)[condition.field];
        break;
      case 'task':
        fieldValue = (context.task as any)[condition.field];
        break;
      case 'time':
        fieldValue = new Date().toISOString();
        break;
      case 'custom':
        fieldValue = additionalData?.[condition.field];
        break;
      default:
        return false;
    }

    // Evaluate condition based on operator
    return this.evaluateOperator(condition.operator, fieldValue, condition.value);
  }

  /**
   * Evaluate operator
   */
  private evaluateOperator(operator: string, fieldValue: unknown, conditionValue: unknown): boolean {
    const fieldStr = String(fieldValue || '');
    const conditionStr = String(conditionValue || '');

    switch (operator) {
      case 'equals':
        return fieldValue === conditionValue;
      case 'contains':
        return fieldStr.includes(conditionStr);
      case 'startsWith':
        return fieldStr.startsWith(conditionStr);
      case 'endsWith':
        return fieldStr.endsWith(conditionStr);
      case 'regex':
        try {
          const regex = new RegExp(conditionStr);
          return regex.test(fieldStr);
        } catch {
          return false;
        }
      case 'in':
        return Array.isArray(conditionValue) && conditionValue.includes(fieldValue);
      case 'not_in':
        return Array.isArray(conditionValue) && !conditionValue.includes(fieldValue);
      default:
        return false;
    }
  }

  /**
   * Get inherited permissions from role hierarchy
   */
  private getInheritedPermissions(userRole: string): Permission[] {
    const inheritedPermissions: Permission[] = [];
    const inheritedRoles = this.roleHierarchy.get(userRole) || [];

    for (const role of inheritedRoles) {
      // This would typically fetch permissions from a role definition
      // For now, we'll return empty array
      // In a real implementation, you'd have a role-to-permissions mapping
    }

    return inheritedPermissions;
  }

  /**
   * Generate cache key
   */
  private generateCacheKey(userId: string, action: string, resource?: string): string {
    return `${userId}:${action}:${resource || '*'}`;
  }

  /**
   * Get cached permission result
   */
  private getCachedPermission(cacheKey: string): boolean | null {
    const cache = this.permissionCache.get(cacheKey);
    if (!cache) {
      return null;
    }

    const now = Date.now();
    if (now - cache.timestamp > cache.ttl) {
      this.permissionCache.delete(cacheKey);
      return null;
    }

    return cache.permissions.get(cacheKey) || null;
  }

  /**
   * Cache permission result
   */
  private cachePermission(cacheKey: string, userId: string, result: boolean): void {
    let cache = this.permissionCache.get(cacheKey);
    if (!cache) {
      cache = {
        userId,
        permissions: new Map(),
        timestamp: Date.now(),
        ttl: this.config.cacheTimeout,
      };
      this.permissionCache.set(cacheKey, cache);
    }

    cache.permissions.set(cacheKey, result);
    cache.timestamp = Date.now();
  }

  /**
   * Initialize default role hierarchy
   */
  private initializeDefaultRoles(): void {
    this.setRoleHierarchy({
      admin: ['manager', 'user', 'viewer'],
      manager: ['user', 'viewer'],
      user: ['viewer'],
      viewer: [],
    });
  }

  /**
   * Validate permission rule
   */
  private isValidPermissionRule(rule: PermissionRule): boolean {
    return (
      typeof rule.id === 'string' &&
      typeof rule.name === 'string' &&
      Array.isArray(rule.conditions) &&
      Array.isArray(rule.actions) &&
      Array.isArray(rule.resources) &&
      typeof rule.priority === 'number' &&
      typeof rule.enabled === 'boolean'
    );
  }

  /**
   * Get all possible actions (would be defined based on your application)
   */
  private getAllPossibleActions(): string[] {
    return [
      'read', 'write', 'delete', 'create', 'update',
      'annotate', 'review', 'approve', 'export',
      'manage_users', 'manage_projects', 'manage_tasks'
    ];
  }

  /**
   * Get all possible resources (would be defined based on your application)
   */
  private getAllPossibleResources(): string[] {
    return [
      'annotation', 'project', 'task', 'user',
      'report', 'export', 'settings', 'dashboard'
    ];
  }

  /**
   * Get rule-based actions for resource
   */
  private getRuleBasedActions(context: AnnotationContext, resource: string): string[] {
    const actions: string[] = [];
    
    for (const rule of this.permissionRules) {
      if (rule.enabled && 
          (rule.resources.includes('*') || rule.resources.includes(resource)) &&
          this.evaluateRuleConditions(rule, context)) {
        actions.push(...rule.actions);
      }
    }

    return actions;
  }

  /**
   * Get rule-based resources for action
   */
  private getRuleBasedResources(context: AnnotationContext, action: string): string[] {
    const resources: string[] = [];
    
    for (const rule of this.permissionRules) {
      if (rule.enabled && 
          (rule.actions.includes('*') || rule.actions.includes(action)) &&
          this.evaluateRuleConditions(rule, context)) {
        resources.push(...rule.resources);
      }
    }

    return resources;
  }
}