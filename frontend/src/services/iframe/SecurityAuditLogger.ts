/**
 * Security Audit Logger for iframe integration
 * Handles comprehensive audit logging for security events
 */

export interface SecurityAuditEvent {
  id: string;
  type: 'authentication' | 'authorization' | 'data_access' | 'encryption' | 'policy_violation' | 'configuration_change';
  action: string;
  resource?: string;
  userId?: string;
  sessionId?: string;
  ipAddress?: string;
  userAgent?: string;
  timestamp: number;
  success: boolean;
  details?: Record<string, unknown>;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  error?: string;
}

export interface AuditLogConfig {
  maxLogSize: number;
  retentionDays: number;
  enableRemoteLogging: boolean;
  remoteEndpoint?: string;
  enableLocalStorage: boolean;
  enableConsoleLogging: boolean;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  enableEncryption: boolean;
  encryptionKey?: string;
}

export interface AuditQuery {
  type?: SecurityAuditEvent['type'];
  action?: string;
  userId?: string;
  sessionId?: string;
  riskLevel?: SecurityAuditEvent['riskLevel'];
  startTime?: number;
  endTime?: number;
  success?: boolean;
  limit?: number;
  offset?: number;
}

export interface AuditSummary {
  totalEvents: number;
  successfulEvents: number;
  failedEvents: number;
  riskDistribution: Record<SecurityAuditEvent['riskLevel'], number>;
  typeDistribution: Record<SecurityAuditEvent['type'], number>;
  timeRange: {
    start: number;
    end: number;
  };
}

export type AuditEventHandler = (event: SecurityAuditEvent) => void;

export class SecurityAuditLogger {
  private config: AuditLogConfig;
  private events: SecurityAuditEvent[] = [];
  private handlers: AuditEventHandler[] = [];
  private isInitialized = false;

  constructor(config: AuditLogConfig) {
    this.config = config;
  }

  /**
   * Initialize audit logger
   */
  public async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    try {
      // Load existing logs from local storage if enabled
      if (this.config.enableLocalStorage) {
        await this.loadFromLocalStorage();
      }

      // Clean up old logs
      this.cleanupOldLogs();

      this.isInitialized = true;
      
      // Log initialization
      await this.logEvent({
        type: 'configuration_change',
        action: 'audit_logger_initialized',
        success: true,
        riskLevel: 'low',
        details: {
          config: {
            maxLogSize: this.config.maxLogSize,
            retentionDays: this.config.retentionDays,
            enableRemoteLogging: this.config.enableRemoteLogging,
            enableLocalStorage: this.config.enableLocalStorage,
          },
        },
      });
    } catch (error) {
      throw new Error(`Failed to initialize audit logger: ${error}`);
    }
  }

  /**
   * Log security event
   */
  public async logEvent(eventData: Omit<SecurityAuditEvent, 'id' | 'timestamp'>): Promise<void> {
    const event: SecurityAuditEvent = {
      id: this.generateId(),
      timestamp: Date.now(),
      ipAddress: await this.getClientIP(),
      userAgent: navigator.userAgent,
      ...eventData,
    };

    // Add to memory
    this.events.push(event);

    // Enforce max log size
    if (this.events.length > this.config.maxLogSize) {
      this.events = this.events.slice(-Math.floor(this.config.maxLogSize * 0.8));
    }

    // Console logging
    if (this.config.enableConsoleLogging) {
      this.logToConsole(event);
    }

    // Local storage
    if (this.config.enableLocalStorage) {
      await this.saveToLocalStorage();
    }

    // Remote logging
    if (this.config.enableRemoteLogging && this.config.remoteEndpoint) {
      await this.sendToRemote(event);
    }

    // Notify handlers
    this.handlers.forEach(handler => {
      try {
        handler(event);
      } catch (error) {
        console.error('Error in audit event handler:', error);
      }
    });
  }

  /**
   * Log authentication event
   */
  public async logAuthentication(action: string, success: boolean, details?: Record<string, unknown>): Promise<void> {
    await this.logEvent({
      type: 'authentication',
      action,
      success,
      riskLevel: success ? 'low' : 'high',
      details,
    });
  }

  /**
   * Log authorization event
   */
  public async logAuthorization(action: string, resource: string, success: boolean, userId?: string): Promise<void> {
    await this.logEvent({
      type: 'authorization',
      action,
      resource,
      userId,
      success,
      riskLevel: success ? 'low' : 'medium',
    });
  }

  /**
   * Log data access event
   */
  public async logDataAccess(action: string, resource: string, userId?: string, details?: Record<string, unknown>): Promise<void> {
    await this.logEvent({
      type: 'data_access',
      action,
      resource,
      userId,
      success: true,
      riskLevel: 'medium',
      details,
    });
  }

  /**
   * Log encryption event
   */
  public async logEncryption(action: string, success: boolean, details?: Record<string, unknown>): Promise<void> {
    await this.logEvent({
      type: 'encryption',
      action,
      success,
      riskLevel: success ? 'low' : 'high',
      details,
    });
  }

  /**
   * Log policy violation
   */
  public async logPolicyViolation(action: string, details: Record<string, unknown>): Promise<void> {
    await this.logEvent({
      type: 'policy_violation',
      action,
      success: false,
      riskLevel: 'critical',
      details,
    });
  }

  /**
   * Log configuration change
   */
  public async logConfigurationChange(action: string, details: Record<string, unknown>): Promise<void> {
    await this.logEvent({
      type: 'configuration_change',
      action,
      success: true,
      riskLevel: 'medium',
      details,
    });
  }

  /**
   * Query audit events
   */
  public queryEvents(query: AuditQuery = {}): SecurityAuditEvent[] {
    let filteredEvents = [...this.events];

    // Apply filters
    if (query.type) {
      filteredEvents = filteredEvents.filter(event => event.type === query.type);
    }

    if (query.action) {
      filteredEvents = filteredEvents.filter(event => event.action.includes(query.action!));
    }

    if (query.userId) {
      filteredEvents = filteredEvents.filter(event => event.userId === query.userId);
    }

    if (query.sessionId) {
      filteredEvents = filteredEvents.filter(event => event.sessionId === query.sessionId);
    }

    if (query.riskLevel) {
      filteredEvents = filteredEvents.filter(event => event.riskLevel === query.riskLevel);
    }

    if (query.startTime) {
      filteredEvents = filteredEvents.filter(event => event.timestamp >= query.startTime!);
    }

    if (query.endTime) {
      filteredEvents = filteredEvents.filter(event => event.timestamp <= query.endTime!);
    }

    if (query.success !== undefined) {
      filteredEvents = filteredEvents.filter(event => event.success === query.success);
    }

    // Sort by timestamp (newest first)
    filteredEvents.sort((a, b) => b.timestamp - a.timestamp);

    // Apply pagination
    const offset = query.offset || 0;
    const limit = query.limit || filteredEvents.length;
    
    return filteredEvents.slice(offset, offset + limit);
  }

  /**
   * Get audit summary
   */
  public getSummary(query: AuditQuery = {}): AuditSummary {
    const events = this.queryEvents(query);

    const summary: AuditSummary = {
      totalEvents: events.length,
      successfulEvents: events.filter(e => e.success).length,
      failedEvents: events.filter(e => !e.success).length,
      riskDistribution: {
        low: 0,
        medium: 0,
        high: 0,
        critical: 0,
      },
      typeDistribution: {
        authentication: 0,
        authorization: 0,
        data_access: 0,
        encryption: 0,
        policy_violation: 0,
        configuration_change: 0,
      },
      timeRange: {
        start: events.length > 0 ? Math.min(...events.map(e => e.timestamp)) : 0,
        end: events.length > 0 ? Math.max(...events.map(e => e.timestamp)) : 0,
      },
    };

    // Calculate distributions
    events.forEach(event => {
      summary.riskDistribution[event.riskLevel]++;
      summary.typeDistribution[event.type]++;
    });

    return summary;
  }

  /**
   * Export audit log
   */
  public exportLog(format: 'json' | 'csv' = 'json', query: AuditQuery = {}): string {
    const events = this.queryEvents(query);

    if (format === 'csv') {
      return this.exportToCSV(events);
    }

    return JSON.stringify(events, null, 2);
  }

  /**
   * Export to CSV format
   */
  private exportToCSV(events: SecurityAuditEvent[]): string {
    if (events.length === 0) {
      return '';
    }

    const headers = [
      'id', 'type', 'action', 'resource', 'userId', 'sessionId', 
      'ipAddress', 'timestamp', 'success', 'riskLevel', 'error'
    ];

    const csvRows = [headers.join(',')];

    events.forEach(event => {
      const row = headers.map(header => {
        const value = event[header as keyof SecurityAuditEvent];
        if (value === undefined || value === null) {
          return '';
        }
        // Escape commas and quotes
        const stringValue = String(value);
        if (stringValue.includes(',') || stringValue.includes('"')) {
          return `"${stringValue.replace(/"/g, '""')}"`;
        }
        return stringValue;
      });
      csvRows.push(row.join(','));
    });

    return csvRows.join('\n');
  }

  /**
   * Clear audit log
   */
  public async clearLog(): Promise<void> {
    const clearedCount = this.events.length;
    
    this.events = [];

    if (this.config.enableLocalStorage) {
      localStorage.removeItem('iframe_security_audit_log');
    }

    // Log the clear event after clearing
    await this.logEvent({
      type: 'configuration_change',
      action: 'audit_log_cleared',
      success: true,
      riskLevel: 'medium',
      details: {
        clearedEvents: clearedCount,
      },
    });
  }

  /**
   * Load from local storage
   */
  private async loadFromLocalStorage(): Promise<void> {
    try {
      const stored = localStorage.getItem('iframe_security_audit_log');
      if (stored) {
        const events = JSON.parse(stored) as SecurityAuditEvent[];
        this.events = events.filter(event => this.isEventValid(event));
      }
    } catch (error) {
      console.warn('Failed to load audit log from local storage:', error);
    }
  }

  /**
   * Save to local storage
   */
  private async saveToLocalStorage(): Promise<void> {
    try {
      const data = JSON.stringify(this.events);
      localStorage.setItem('iframe_security_audit_log', data);
    } catch (error) {
      console.warn('Failed to save audit log to local storage:', error);
    }
  }

  /**
   * Send event to remote endpoint
   */
  private async sendToRemote(event: SecurityAuditEvent): Promise<void> {
    if (!this.config.remoteEndpoint) {
      return;
    }

    try {
      await fetch(this.config.remoteEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(event),
      });
    } catch (error) {
      console.warn('Failed to send audit event to remote endpoint:', error);
    }
  }

  /**
   * Log to console
   */
  private logToConsole(event: SecurityAuditEvent): void {
    const logLevel = this.getConsoleLogLevel(event.riskLevel);
    const message = `[AUDIT] ${event.type}:${event.action} - ${event.success ? 'SUCCESS' : 'FAILED'}`;
    
    switch (logLevel) {
      case 'error':
        console.error(message, event);
        break;
      case 'warn':
        console.warn(message, event);
        break;
      case 'info':
        console.info(message, event);
        break;
      default:
        console.log(message, event);
    }
  }

  /**
   * Get console log level based on risk level
   */
  private getConsoleLogLevel(riskLevel: SecurityAuditEvent['riskLevel']): string {
    switch (riskLevel) {
      case 'critical':
      case 'high':
        return 'error';
      case 'medium':
        return 'warn';
      case 'low':
        return 'info';
      default:
        return 'log';
    }
  }

  /**
   * Clean up old logs
   */
  private cleanupOldLogs(): void {
    const cutoffTime = Date.now() - (this.config.retentionDays * 24 * 60 * 60 * 1000);
    this.events = this.events.filter(event => event.timestamp > cutoffTime);
  }

  /**
   * Validate event structure
   */
  private isEventValid(event: unknown): event is SecurityAuditEvent {
    if (!event || typeof event !== 'object') {
      return false;
    }

    const e = event as Record<string, unknown>;
    
    return (
      typeof e.id === 'string' &&
      typeof e.type === 'string' &&
      typeof e.action === 'string' &&
      typeof e.timestamp === 'number' &&
      typeof e.success === 'boolean' &&
      typeof e.riskLevel === 'string'
    );
  }

  /**
   * Get client IP address (best effort)
   */
  private async getClientIP(): Promise<string> {
    try {
      // This is a simplified approach - in production, you might use a service
      return 'client-ip-not-available';
    } catch {
      return 'unknown';
    }
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return `audit-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Add event handler
   */
  public onEvent(handler: AuditEventHandler): () => void {
    this.handlers.push(handler);
    
    return () => {
      const index = this.handlers.indexOf(handler);
      if (index > -1) {
        this.handlers.splice(index, 1);
      }
    };
  }

  /**
   * Update configuration
   */
  public updateConfig(config: Partial<AuditLogConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get current configuration
   */
  public getConfig(): AuditLogConfig {
    return { ...this.config };
  }

  /**
   * Check if logger is ready
   */
  public isReady(): boolean {
    return this.isInitialized;
  }

  /**
   * Cleanup resources
   */
  public cleanup(): void {
    this.handlers = [];
    this.isInitialized = false;
  }
}

/**
 * Create default audit logger configuration
 */
export function createDefaultAuditConfig(): AuditLogConfig {
  return {
    maxLogSize: 10000,
    retentionDays: 90,
    enableRemoteLogging: false,
    enableLocalStorage: true,
    enableConsoleLogging: process.env.NODE_ENV === 'development',
    logLevel: 'info',
    enableEncryption: false,
  };
}

/**
 * Global security audit logger instance
 */
let globalSecurityAuditLogger: SecurityAuditLogger | null = null;

/**
 * Get global security audit logger
 */
export function getGlobalSecurityAuditLogger(): SecurityAuditLogger {
  if (!globalSecurityAuditLogger) {
    globalSecurityAuditLogger = new SecurityAuditLogger(createDefaultAuditConfig());
  }
  return globalSecurityAuditLogger;
}

/**
 * Initialize global security audit logger
 */
export async function initializeGlobalSecurityAuditLogger(config?: Partial<AuditLogConfig>): Promise<SecurityAuditLogger> {
  const finalConfig = { ...createDefaultAuditConfig(), ...config };
  globalSecurityAuditLogger = new SecurityAuditLogger(finalConfig);
  await globalSecurityAuditLogger.initialize();
  return globalSecurityAuditLogger;
}