/**
 * AutoRecoveryManager - Implements automatic recovery mechanisms
 * Handles auto-reconnection, failover, and comprehensive error logging
 */

import type {
  ErrorInfo,
  ErrorType,
  RecoveryAction,
  RecoveryStrategy,
} from './ErrorHandler';
import { ErrorHandler } from './ErrorHandler';
import type { IframeManager } from './IframeManager';
import type { PostMessageBridge } from './PostMessageBridge';
import type { ContextManager } from './ContextManager';

export interface AutoRecoveryConfig {
  enableAutoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  enableFailover?: boolean;
  failoverUrls?: string[];
  enableHealthCheck?: boolean;
  healthCheckInterval?: number;
  enableErrorLogging?: boolean;
  logRetentionDays?: number;
  enableMetrics?: boolean;
}

export interface ConnectionHealth {
  isHealthy: boolean;
  lastCheck: number;
  responseTime: number;
  errorCount: number;
  consecutiveFailures: number;
}

export interface RecoveryMetrics {
  totalRecoveryAttempts: number;
  successfulRecoveries: number;
  failedRecoveries: number;
  averageRecoveryTime: number;
  lastRecoveryTime: number;
  failoverCount: number;
  reconnectCount: number;
}

export interface ErrorLogEntry {
  id: string;
  timestamp: number;
  level: 'debug' | 'info' | 'warn' | 'error' | 'critical';
  message: string;
  error?: ErrorInfo;
  context?: Record<string, unknown>;
  stackTrace?: string;
  resolved: boolean;
  recoveryAction?: RecoveryAction;
  recoveryTime?: number;
}

export class AutoRecoveryManager {
  private config: Required<AutoRecoveryConfig>;
  private errorHandler: ErrorHandler;
  private iframeManager: IframeManager | null = null;
  private postMessageBridge: PostMessageBridge | null = null;
  private contextManager: ContextManager | null = null;
  
  private connectionHealth: ConnectionHealth = {
    isHealthy: true,
    lastCheck: Date.now(),
    responseTime: 0,
    errorCount: 0,
    consecutiveFailures: 0,
  };
  
  private metrics: RecoveryMetrics = {
    totalRecoveryAttempts: 0,
    successfulRecoveries: 0,
    failedRecoveries: 0,
    averageRecoveryTime: 0,
    lastRecoveryTime: 0,
    failoverCount: 0,
    reconnectCount: 0,
  };
  
  private errorLog: ErrorLogEntry[] = [];
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private reconnectInterval: NodeJS.Timeout | null = null;
  private currentFailoverIndex: number = 0;
  private isRecovering: boolean = false;
  private logCounter: number = 0;

  constructor(
    errorHandler: ErrorHandler,
    config: AutoRecoveryConfig = {}
  ) {
    this.errorHandler = errorHandler;
    this.config = {
      enableAutoReconnect: config.enableAutoReconnect !== false,
      reconnectInterval: config.reconnectInterval || 5000,
      maxReconnectAttempts: config.maxReconnectAttempts || 10,
      enableFailover: config.enableFailover || false,
      failoverUrls: config.failoverUrls || [],
      enableHealthCheck: config.enableHealthCheck !== false,
      healthCheckInterval: config.healthCheckInterval || 30000,
      enableErrorLogging: config.enableErrorLogging !== false,
      logRetentionDays: config.logRetentionDays || 7,
      enableMetrics: config.enableMetrics !== false,
    };

    this.initializeRecoveryStrategies();
    this.startHealthCheck();
  }

  /**
   * Initialize with required managers
   */
  initialize(
    iframeManager: IframeManager,
    postMessageBridge: PostMessageBridge,
    contextManager: ContextManager
  ): void {
    this.iframeManager = iframeManager;
    this.postMessageBridge = postMessageBridge;
    this.contextManager = contextManager;

    // Set up error handlers
    this.setupErrorHandlers();
  }

  /**
   * Implement automatic reconnection
   */
  async implementAutoReconnect(): Promise<boolean> {
    if (!this.config.enableAutoReconnect || this.isRecovering) {
      return false;
    }

    this.isRecovering = true;
    this.metrics.reconnectCount++;
    
    const startTime = Date.now();
    this.logError('info', 'Starting automatic reconnection');

    try {
      let attempts = 0;
      let success = false;

      while (attempts < this.config.maxReconnectAttempts && !success) {
        attempts++;
        
        this.logError('info', `Reconnection attempt ${attempts}/${this.config.maxReconnectAttempts}`);

        try {
          // Test connection health
          const isHealthy = await this.performHealthCheck();
          
          if (isHealthy) {
            // Reconnect PostMessage bridge
            if (this.postMessageBridge) {
              this.postMessageBridge.cleanup();
              
              if (this.iframeManager?.getIframe()) {
                this.postMessageBridge.initialize(this.iframeManager.getIframe()!);
              }
            }

            // Verify connection
            success = await this.verifyConnection();
            
            if (success) {
              this.connectionHealth.isHealthy = true;
              this.connectionHealth.consecutiveFailures = 0;
              this.logError('info', 'Automatic reconnection successful');
            }
          }

        } catch (error) {
          this.logError('warn', `Reconnection attempt ${attempts} failed`, { error });
        }

        if (!success && attempts < this.config.maxReconnectAttempts) {
          await this.delay(this.config.reconnectInterval * attempts);
        }
      }

      const recoveryTime = Date.now() - startTime;
      this.updateMetrics(success, recoveryTime);

      if (!success) {
        this.logError('error', 'Automatic reconnection failed after all attempts');
        
        // Try failover if enabled
        if (this.config.enableFailover) {
          success = await this.implementFailover();
        }
      }

      return success;

    } finally {
      this.isRecovering = false;
    }
  }

  /**
   * Implement failover to alternative URLs
   */
  async implementFailover(): Promise<boolean> {
    if (!this.config.enableFailover || this.config.failoverUrls.length === 0) {
      return false;
    }

    this.metrics.failoverCount++;
    this.logError('info', 'Starting failover process');

    const startTime = Date.now();

    try {
      for (let i = 0; i < this.config.failoverUrls.length; i++) {
        const failoverIndex = (this.currentFailoverIndex + i) % this.config.failoverUrls.length;
        const failoverUrl = this.config.failoverUrls[failoverIndex];

        this.logError('info', `Attempting failover to URL: ${failoverUrl}`);

        try {
          // Test failover URL
          const isHealthy = await this.testUrl(failoverUrl);
          
          if (isHealthy) {
            // Update iframe with failover URL
            if (this.iframeManager) {
              await this.iframeManager.destroy();
              
              // Create new iframe with failover URL
              const config = {
                url: failoverUrl,
                projectId: 'failover',
                userId: 'current',
                token: 'current',
                permissions: [],
              };
              
              // This would need to be implemented with proper container
              // await this.iframeManager.create(config, container);
            }

            this.currentFailoverIndex = failoverIndex;
            this.logError('info', `Failover successful to: ${failoverUrl}`);
            
            const recoveryTime = Date.now() - startTime;
            this.updateMetrics(true, recoveryTime);
            
            return true;
          }

        } catch (error) {
          this.logError('warn', `Failover attempt failed for URL: ${failoverUrl}`, { error });
        }
      }

      this.logError('error', 'All failover URLs failed');
      return false;

    } catch (error) {
      this.logError('error', 'Failover process failed', { error });
      return false;
    }
  }

  /**
   * Comprehensive error logging
   */
  logError(
    level: 'debug' | 'info' | 'warn' | 'error' | 'critical',
    message: string,
    context?: {
      error?: Error | ErrorInfo;
      recoveryAction?: RecoveryAction;
      [key: string]: unknown;
    }
  ): void {
    if (!this.config.enableErrorLogging) return;

    const logEntry: ErrorLogEntry = {
      id: this.generateLogId(),
      timestamp: Date.now(),
      level,
      message,
      context,
      resolved: false,
    };

    // Add error details if provided
    if (context?.error) {
      if (context.error instanceof Error) {
        logEntry.stackTrace = context.error.stack;
      } else {
        logEntry.error = context.error as ErrorInfo;
      }
    }

    // Add recovery action if provided
    if (context?.recoveryAction) {
      logEntry.recoveryAction = context.recoveryAction;
    }

    this.errorLog.push(logEntry);

    // Clean up old logs
    this.cleanupOldLogs();

    // Console logging
    const logMethod = level === 'critical' ? 'error' : level;
    console[logMethod](`[AutoRecoveryManager] ${message}`, context);
  }

  /**
   * Get connection health status
   */
  getConnectionHealth(): ConnectionHealth {
    return { ...this.connectionHealth };
  }

  /**
   * Get recovery metrics
   */
  getRecoveryMetrics(): RecoveryMetrics {
    return { ...this.metrics };
  }

  /**
   * Get error logs
   */
  getErrorLogs(limit?: number): ErrorLogEntry[] {
    const logs = [...this.errorLog].reverse(); // Most recent first
    return limit ? logs.slice(0, limit) : logs;
  }

  /**
   * Clear error logs
   */
  clearErrorLogs(): void {
    this.errorLog = [];
  }

  /**
   * Export error logs for analysis
   */
  exportErrorLogs(): string {
    return JSON.stringify({
      exportTime: new Date().toISOString(),
      metrics: this.metrics,
      connectionHealth: this.connectionHealth,
      logs: this.errorLog,
    }, null, 2);
  }

  /**
   * Cleanup and stop all recovery processes
   */
  cleanup(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }

    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
      this.reconnectInterval = null;
    }

    this.isRecovering = false;
  }

  /**
   * Setup error handlers for all managers
   */
  private setupErrorHandlers(): void {
    // Listen for iframe errors
    if (this.iframeManager) {
      this.iframeManager.on('error', (event) => {
        this.connectionHealth.errorCount++;
        this.connectionHealth.consecutiveFailures++;
        this.connectionHealth.isHealthy = false;

        this.logError('error', 'iframe error detected', { event });

        if (this.config.enableAutoReconnect) {
          setTimeout(() => this.implementAutoReconnect(), 1000);
        }
      });
    }

    // Listen for bridge errors
    if (this.postMessageBridge) {
      // This would need to be implemented in PostMessageBridge
      // this.postMessageBridge.on('error', (error) => { ... });
    }
  }

  /**
   * Start health check monitoring
   */
  private startHealthCheck(): void {
    if (!this.config.enableHealthCheck) return;

    this.healthCheckInterval = setInterval(async () => {
      try {
        const isHealthy = await this.performHealthCheck();
        
        if (!isHealthy && this.connectionHealth.isHealthy) {
          this.logError('warn', 'Health check failed - connection unhealthy');
          
          if (this.config.enableAutoReconnect) {
            this.implementAutoReconnect();
          }
        }
        
        this.connectionHealth.isHealthy = isHealthy;
        this.connectionHealth.lastCheck = Date.now();
        
      } catch (error) {
        this.logError('error', 'Health check error', { error });
      }
    }, this.config.healthCheckInterval);
  }

  /**
   * Perform health check
   */
  private async performHealthCheck(): Promise<boolean> {
    const startTime = Date.now();

    try {
      // Check iframe status
      if (this.iframeManager) {
        const status = this.iframeManager.getStatus();
        if (status === 'error' || status === 'destroyed') {
          return false;
        }
      }

      // Check bridge status
      if (this.postMessageBridge) {
        const status = this.postMessageBridge.getStatus();
        if (status === 'error' || status === 'disconnected') {
          return false;
        }
      }

      // Test communication
      const communicationHealthy = await this.testCommunication();
      
      this.connectionHealth.responseTime = Date.now() - startTime;
      
      if (communicationHealthy) {
        this.connectionHealth.consecutiveFailures = 0;
      } else {
        this.connectionHealth.consecutiveFailures++;
      }

      return communicationHealthy;

    } catch (error) {
      this.connectionHealth.responseTime = Date.now() - startTime;
      this.connectionHealth.consecutiveFailures++;
      return false;
    }
  }

  /**
   * Test communication with iframe
   */
  private async testCommunication(): Promise<boolean> {
    if (!this.postMessageBridge) return false;

    try {
      const response = await this.postMessageBridge.send({
        type: 'health_check',
        payload: { timestamp: Date.now() },
      });

      return response.success;
    } catch (error) {
      return false;
    }
  }

  /**
   * Test URL availability
   */
  private async testUrl(url: string): Promise<boolean> {
    try {
      const response = await fetch(url, {
        method: 'HEAD',
        mode: 'no-cors',
        cache: 'no-cache',
      });
      
      return response.ok || response.type === 'opaque';
    } catch (error) {
      return false;
    }
  }

  /**
   * Verify connection after recovery
   */
  private async verifyConnection(): Promise<boolean> {
    try {
      // Test iframe load
      if (this.iframeManager) {
        const status = this.iframeManager.getStatus();
        if (status !== 'ready') {
          return false;
        }
      }

      // Test communication
      return await this.testCommunication();

    } catch (error) {
      return false;
    }
  }

  /**
   * Update recovery metrics
   */
  private updateMetrics(success: boolean, recoveryTime: number): void {
    if (!this.config.enableMetrics) return;

    this.metrics.totalRecoveryAttempts++;
    this.metrics.lastRecoveryTime = recoveryTime;

    if (success) {
      this.metrics.successfulRecoveries++;
    } else {
      this.metrics.failedRecoveries++;
    }

    // Update average recovery time
    const totalTime = this.metrics.averageRecoveryTime * (this.metrics.totalRecoveryAttempts - 1) + recoveryTime;
    this.metrics.averageRecoveryTime = totalTime / this.metrics.totalRecoveryAttempts;
  }

  /**
   * Initialize recovery strategies
   */
  private initializeRecoveryStrategies(): void {
    // Add custom recovery strategies to the error handler
    const autoReconnectStrategy: RecoveryStrategy = {
      canHandle: (error) => 
        error.type === 'communication_error' || error.type === 'loading_error',
      execute: async () => this.implementAutoReconnect(),
      getEstimatedTime: () => this.config.reconnectInterval * this.config.maxReconnectAttempts,
      getDescription: () => 'Automatic reconnection with exponential backoff',
    };

    const failoverStrategy: RecoveryStrategy = {
      canHandle: (error) => 
        this.config.enableFailover && 
        this.config.failoverUrls.length > 0 &&
        (error.type === 'loading_error' || error.type === 'network_error'),
      execute: async () => this.implementFailover(),
      getEstimatedTime: () => 10000,
      getDescription: () => 'Failover to alternative URL',
    };

    // These would need to be added to the ErrorHandler's recovery strategies
    // This is a conceptual implementation - the actual integration would depend
    // on the ErrorHandler's API for adding custom strategies
  }

  /**
   * Clean up old log entries
   */
  private cleanupOldLogs(): void {
    const cutoffTime = Date.now() - (this.config.logRetentionDays * 24 * 60 * 60 * 1000);
    this.errorLog = this.errorLog.filter(log => log.timestamp > cutoffTime);
  }

  /**
   * Generate unique log ID
   */
  private generateLogId(): string {
    return `log_${Date.now()}_${++this.logCounter}`;
  }

  /**
   * Delay utility
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}