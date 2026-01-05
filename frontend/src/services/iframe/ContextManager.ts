/**
 * ContextManager - Manages annotation context and permission information
 * Handles context setting, retrieval, permission validation, and encryption
 */

import type {
  AnnotationContext,
  UserInfo,
  ProjectInfo,
  TaskInfo,
  Permission,
  ContextManagerConfig,
} from './types';
import { MessageSecurity } from './MessageSecurity';

export class ContextManager {
  private context: AnnotationContext | null = null;
  private config: Required<ContextManagerConfig>;
  private security: MessageSecurity;
  private sessionTimer: NodeJS.Timeout | null = null;
  private contextListeners: Set<(context: AnnotationContext | null) => void> = new Set();

  constructor(config: ContextManagerConfig = {}) {
    this.config = {
      enableEncryption: config.enableEncryption || false,
      encryptionKey: config.encryptionKey || 'default-context-key',
      sessionTimeout: config.sessionTimeout || 3600000, // 1 hour
      autoRefresh: config.autoRefresh || true,
    };

    this.security = new MessageSecurity({
      enableEncryption: this.config.enableEncryption,
      enableSignature: false, // Context doesn't need signatures
      secretKey: this.config.encryptionKey,
    });
  }

  /**
   * Set annotation context
   */
  setContext(context: AnnotationContext): void {
    // Validate context structure
    if (!this.isValidContext(context)) {
      throw new Error('Invalid context structure');
    }

    // Update timestamp
    const updatedContext: AnnotationContext = {
      ...context,
      timestamp: Date.now(),
      sessionId: context.sessionId || this.generateSessionId(),
    };

    this.context = updatedContext;

    // Setup session timeout
    this.setupSessionTimeout();

    // Notify listeners
    this.notifyContextChange(updatedContext);

    console.log('Context set successfully:', {
      user: updatedContext.user.name,
      project: updatedContext.project.name,
      task: updatedContext.task.name,
      permissions: updatedContext.permissions.length,
    });
  }

  /**
   * Get current annotation context
   */
  getContext(): AnnotationContext | null {
    if (!this.context) {
      return null;
    }

    // Check if context is expired
    if (this.isContextExpired()) {
      this.clearContext();
      return null;
    }

    return { ...this.context };
  }

  /**
   * Check if user has specific permission
   */
  checkPermission(action: string, resource?: string): boolean {
    if (!this.context) {
      console.warn('No context available for permission check');
      return false;
    }

    const permissions = this.context.permissions;
    
    // Check for exact match
    const exactMatch = permissions.find(
      (p) => p.action === action && (!resource || p.resource === resource) && p.allowed
    );

    if (exactMatch) {
      return true;
    }

    // Check for wildcard permissions
    const wildcardMatch = permissions.find(
      (p) => 
        (p.action === '*' || p.action === action) &&
        (p.resource === '*' || !resource || p.resource === resource) &&
        p.allowed
    );

    return !!wildcardMatch;
  }

  /**
   * Update permissions
   */
  updatePermissions(permissions: Permission[]): void {
    if (!this.context) {
      throw new Error('No context available to update permissions');
    }

    this.context = {
      ...this.context,
      permissions,
      timestamp: Date.now(),
    };

    // Notify listeners
    this.notifyContextChange(this.context);

    console.log('Permissions updated:', permissions.length);
  }

  /**
   * Get encrypted context for transmission
   */
  getEncryptedContext(): string {
    if (!this.context) {
      throw new Error('No context available to encrypt');
    }

    const contextData = {
      ...this.context,
      // Remove sensitive data that shouldn't be transmitted
      metadata: this.sanitizeMetadata(this.context.metadata),
    };

    if (this.config.enableEncryption) {
      return this.security.encryptPayload(contextData);
    }

    return JSON.stringify(contextData);
  }

  /**
   * Set context from encrypted data
   */
  setEncryptedContext(encryptedData: string): void {
    try {
      let contextData: AnnotationContext;

      if (this.config.enableEncryption) {
        contextData = this.security.decryptPayload(encryptedData) as AnnotationContext;
      } else {
        contextData = JSON.parse(encryptedData);
      }

      this.setContext(contextData);
    } catch (error) {
      console.error('Failed to decrypt context:', error);
      throw new Error('Invalid encrypted context data');
    }
  }

  /**
   * Clear current context
   */
  clearContext(): void {
    if (this.sessionTimer) {
      clearTimeout(this.sessionTimer);
      this.sessionTimer = null;
    }

    this.context = null;
    this.notifyContextChange(null);

    console.log('Context cleared');
  }

  /**
   * Refresh context (extend session)
   */
  refreshContext(): void {
    if (!this.context) {
      return;
    }

    this.context = {
      ...this.context,
      timestamp: Date.now(),
    };

    this.setupSessionTimeout();
    this.notifyContextChange(this.context);

    console.log('Context refreshed');
  }

  /**
   * Get user information
   */
  getUser(): UserInfo | null {
    return this.context?.user || null;
  }

  /**
   * Get project information
   */
  getProject(): ProjectInfo | null {
    return this.context?.project || null;
  }

  /**
   * Get task information
   */
  getTask(): TaskInfo | null {
    return this.context?.task || null;
  }

  /**
   * Get all permissions
   */
  getPermissions(): Permission[] {
    return this.context?.permissions || [];
  }

  /**
   * Check if context is expired
   */
  isContextExpired(): boolean {
    if (!this.context) {
      return true;
    }

    const now = Date.now();
    const contextAge = now - this.context.timestamp;
    return contextAge > this.config.sessionTimeout;
  }

  /**
   * Add context change listener
   */
  onContextChange(listener: (context: AnnotationContext | null) => void): void {
    this.contextListeners.add(listener);
  }

  /**
   * Remove context change listener
   */
  offContextChange(listener: (context: AnnotationContext | null) => void): void {
    this.contextListeners.delete(listener);
  }

  /**
   * Get context summary for logging
   */
  getContextSummary(): Record<string, unknown> | null {
    if (!this.context) {
      return null;
    }

    return {
      userId: this.context.user.id,
      userName: this.context.user.name,
      userRole: this.context.user.role,
      projectId: this.context.project.id,
      projectName: this.context.project.name,
      taskId: this.context.task.id,
      taskName: this.context.task.name,
      permissionCount: this.context.permissions.length,
      sessionId: this.context.sessionId,
      timestamp: this.context.timestamp,
      isExpired: this.isContextExpired(),
    };
  }

  /**
   * Validate context structure
   */
  private isValidContext(context: unknown): context is AnnotationContext {
    if (typeof context !== 'object' || context === null) {
      return false;
    }

    const ctx = context as Record<string, unknown>;

    // Check required fields
    return (
      this.isValidUserInfo(ctx.user) &&
      this.isValidProjectInfo(ctx.project) &&
      this.isValidTaskInfo(ctx.task) &&
      Array.isArray(ctx.permissions) &&
      ctx.permissions.every((p: unknown) => this.isValidPermission(p))
    );
  }

  /**
   * Validate user info structure
   */
  private isValidUserInfo(user: unknown): user is UserInfo {
    if (typeof user !== 'object' || user === null) {
      return false;
    }

    const u = user as Record<string, unknown>;
    return (
      typeof u.id === 'string' &&
      typeof u.name === 'string' &&
      typeof u.email === 'string' &&
      typeof u.role === 'string'
    );
  }

  /**
   * Validate project info structure
   */
  private isValidProjectInfo(project: unknown): project is ProjectInfo {
    if (typeof project !== 'object' || project === null) {
      return false;
    }

    const p = project as Record<string, unknown>;
    return (
      typeof p.id === 'string' &&
      typeof p.name === 'string' &&
      typeof p.description === 'string' &&
      typeof p.status === 'string'
    );
  }

  /**
   * Validate task info structure
   */
  private isValidTaskInfo(task: unknown): task is TaskInfo {
    if (typeof task !== 'object' || task === null) {
      return false;
    }

    const t = task as Record<string, unknown>;
    return (
      typeof t.id === 'string' &&
      typeof t.name === 'string' &&
      typeof t.status === 'string' &&
      typeof t.progress === 'number'
    );
  }

  /**
   * Validate permission structure
   */
  private isValidPermission(permission: unknown): permission is Permission {
    if (typeof permission !== 'object' || permission === null) {
      return false;
    }

    const p = permission as Record<string, unknown>;
    return (
      typeof p.action === 'string' &&
      typeof p.resource === 'string' &&
      typeof p.allowed === 'boolean'
    );
  }

  /**
   * Setup session timeout
   */
  private setupSessionTimeout(): void {
    if (this.sessionTimer) {
      clearTimeout(this.sessionTimer);
    }

    if (this.config.autoRefresh) {
      this.sessionTimer = setTimeout(() => {
        if (this.context && !this.isContextExpired()) {
          this.refreshContext();
        } else {
          this.clearContext();
        }
      }, this.config.sessionTimeout);
    }
  }

  /**
   * Generate unique session ID
   */
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
  }

  /**
   * Notify context change listeners
   */
  private notifyContextChange(context: AnnotationContext | null): void {
    this.contextListeners.forEach((listener) => {
      try {
        listener(context);
      } catch (error) {
        console.error('Error in context change listener:', error);
      }
    });
  }

  /**
   * Sanitize metadata for transmission
   */
  private sanitizeMetadata(metadata?: Record<string, unknown>): Record<string, unknown> | undefined {
    if (!metadata) {
      return undefined;
    }

    // Remove sensitive keys
    const sensitiveKeys = ['password', 'token', 'secret', 'key', 'auth'];
    const sanitized: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(metadata)) {
      const lowerKey = key.toLowerCase();
      const isSensitive = sensitiveKeys.some((sensitive) => lowerKey.includes(sensitive));

      if (!isSensitive) {
        sanitized[key] = value;
      }
    }

    return sanitized;
  }
}