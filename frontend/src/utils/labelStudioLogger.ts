/**
 * Label Studio 日志工具
 * 
 * 提供统一的日志格式，用于 Label Studio 相关操作的日志记录
 * 
 * 功能特性：
 * - 统一日志格式
 * - 自动添加时间戳
 * - 包含用户信息（当可用时）
 * - 支持请求 ID 追踪
 * - 支持不同日志级别
 * 
 * @example
 * import { labelStudioLogger } from '@/utils/labelStudioLogger';
 * 
 * // 基本使用
 * labelStudioLogger.info('Opening Label Studio', { projectId: 123 });
 * 
 * // 带请求 ID
 * const requestId = labelStudioLogger.generateRequestId();
 * labelStudioLogger.info('API call started', { endpoint: '/projects' }, requestId);
 * 
 * // 错误日志
 * labelStudioLogger.error('Failed to open project', { error: err.message });
 */

import { useAuthStore } from '@/stores/authStore';

/**
 * 日志级别
 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

/**
 * 日志条目接口
 */
export interface LogEntry {
  /** 时间戳 (ISO 8601 格式) */
  timestamp: string;
  /** 日志级别 */
  level: LogLevel;
  /** 日志模块 */
  module: string;
  /** 日志消息 */
  message: string;
  /** 用户 ID (如果可用) */
  userId?: string;
  /** 用户名 (如果可用) */
  username?: string;
  /** 租户 ID (如果可用) */
  tenantId?: string;
  /** 请求 ID (用于追踪) */
  requestId?: string;
  /** 额外数据 */
  data?: Record<string, unknown>;
}

/**
 * 日志配置
 */
interface LoggerConfig {
  /** 是否启用日志 */
  enabled: boolean;
  /** 最小日志级别 */
  minLevel: LogLevel;
  /** 是否在生产环境中启用 */
  enableInProduction: boolean;
  /** 模块名称 */
  moduleName: string;
}

/**
 * 日志级别优先级
 */
const LOG_LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

/**
 * 默认配置
 */
const DEFAULT_CONFIG: LoggerConfig = {
  enabled: true,
  minLevel: 'debug',
  enableInProduction: false,
  moduleName: 'LabelStudio',
};

/**
 * Label Studio 日志工具类
 */
class LabelStudioLogger {
  private config: LoggerConfig;
  private requestIdCounter = 0;

  constructor(config: Partial<LoggerConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * 检查是否应该记录日志
   */
  private shouldLog(level: LogLevel): boolean {
    // 检查是否启用
    if (!this.config.enabled) return false;

    // 检查生产环境
    const isProduction = import.meta.env.PROD;
    if (isProduction && !this.config.enableInProduction) return false;

    // 检查日志级别
    return LOG_LEVEL_PRIORITY[level] >= LOG_LEVEL_PRIORITY[this.config.minLevel];
  }

  /**
   * 获取当前用户信息
   */
  private getUserInfo(): { userId?: string; username?: string; tenantId?: string } {
    try {
      const state = useAuthStore.getState();
      const user = state.user;
      const tenant = state.currentTenant;

      return {
        userId: user?.id?.toString(),
        username: user?.username || user?.email,
        tenantId: tenant?.id?.toString(),
      };
    } catch {
      // 如果无法获取用户信息，返回空对象
      return {};
    }
  }

  /**
   * 格式化时间戳
   */
  private formatTimestamp(): string {
    return new Date().toISOString();
  }

  /**
   * 生成请求 ID
   * 格式: ls-{timestamp}-{counter}
   */
  generateRequestId(): string {
    this.requestIdCounter += 1;
    const timestamp = Date.now().toString(36);
    const counter = this.requestIdCounter.toString(36).padStart(4, '0');
    return `ls-${timestamp}-${counter}`;
  }

  /**
   * 创建日志条目
   */
  private createLogEntry(
    level: LogLevel,
    message: string,
    data?: Record<string, unknown>,
    requestId?: string
  ): LogEntry {
    const userInfo = this.getUserInfo();

    return {
      timestamp: this.formatTimestamp(),
      level,
      module: this.config.moduleName,
      message,
      ...userInfo,
      requestId,
      data,
    };
  }

  /**
   * 格式化日志输出
   */
  private formatLogOutput(entry: LogEntry): string {
    const parts: string[] = [
      `[${entry.timestamp}]`,
      `[${entry.module}]`,
      `[${entry.level.toUpperCase()}]`,
    ];

    // 添加请求 ID
    if (entry.requestId) {
      parts.push(`[${entry.requestId}]`);
    }

    // 添加用户信息
    if (entry.userId || entry.username) {
      const userPart = entry.username || entry.userId;
      parts.push(`[User: ${userPart}]`);
    }

    // 添加租户信息
    if (entry.tenantId) {
      parts.push(`[Tenant: ${entry.tenantId}]`);
    }

    // 添加消息
    parts.push(entry.message);

    return parts.join(' ');
  }

  /**
   * 输出日志
   */
  private log(
    level: LogLevel,
    message: string,
    data?: Record<string, unknown>,
    requestId?: string
  ): void {
    if (!this.shouldLog(level)) return;

    const entry = this.createLogEntry(level, message, data, requestId);
    const formattedMessage = this.formatLogOutput(entry);

    // 根据级别选择 console 方法
    switch (level) {
      case 'debug':
        console.debug(formattedMessage, data ? { data } : '');
        break;
      case 'info':
        console.log(formattedMessage, data ? { data } : '');
        break;
      case 'warn':
        console.warn(formattedMessage, data ? { data } : '');
        break;
      case 'error':
        console.error(formattedMessage, data ? { data } : '');
        break;
    }
  }

  /**
   * 调试日志
   */
  debug(message: string, data?: Record<string, unknown>, requestId?: string): void {
    this.log('debug', message, data, requestId);
  }

  /**
   * 信息日志
   */
  info(message: string, data?: Record<string, unknown>, requestId?: string): void {
    this.log('info', message, data, requestId);
  }

  /**
   * 警告日志
   */
  warn(message: string, data?: Record<string, unknown>, requestId?: string): void {
    this.log('warn', message, data, requestId);
  }

  /**
   * 错误日志
   */
  error(message: string, data?: Record<string, unknown>, requestId?: string): void {
    this.log('error', message, data, requestId);
  }

  /**
   * 记录操作开始
   */
  startOperation(operation: string, data?: Record<string, unknown>): string {
    const requestId = this.generateRequestId();
    this.info(`${operation} - START`, data, requestId);
    return requestId;
  }

  /**
   * 记录操作结束
   */
  endOperation(
    operation: string,
    requestId: string,
    success: boolean,
    data?: Record<string, unknown>
  ): void {
    const status = success ? 'SUCCESS' : 'FAILED';
    const level = success ? 'info' : 'error';
    this.log(level, `${operation} - END - ${status}`, data, requestId);
  }

  /**
   * 记录窗口打开操作
   */
  logWindowOpen(projectId: number, url: string, taskId?: number): string {
    const requestId = this.startOperation('Open Label Studio Window', {
      projectId,
      taskId,
      url,
    });
    return requestId;
  }

  /**
   * 记录项目创建操作
   */
  logProjectCreate(taskId: string, taskName: string): string {
    const requestId = this.startOperation('Create Label Studio Project', {
      taskId,
      taskName,
    });
    return requestId;
  }

  /**
   * 记录 API 调用
   */
  logApiCall(
    method: string,
    endpoint: string,
    requestId?: string,
    data?: Record<string, unknown>
  ): void {
    this.info(`API Call: ${method} ${endpoint}`, data, requestId);
  }

  /**
   * 记录 API 响应
   */
  logApiResponse(
    method: string,
    endpoint: string,
    status: number,
    requestId?: string,
    data?: Record<string, unknown>
  ): void {
    const level = status >= 400 ? 'error' : 'info';
    this.log(level, `API Response: ${method} ${endpoint} - ${status}`, data, requestId);
  }

  /**
   * 记录同步操作
   */
  logSync(
    operation: 'start' | 'progress' | 'complete' | 'error',
    data?: Record<string, unknown>,
    requestId?: string
  ): void {
    const messages: Record<string, string> = {
      start: 'Sync Started',
      progress: 'Sync Progress',
      complete: 'Sync Completed',
      error: 'Sync Error',
    };
    const level = operation === 'error' ? 'error' : 'info';
    this.log(level, messages[operation], data, requestId);
  }

  /**
   * 记录错误
   */
  logError(
    operation: string,
    error: unknown,
    requestId?: string,
    additionalData?: Record<string, unknown>
  ): void {
    const errorMessage = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : undefined;

    this.error(`${operation} - Error`, {
      error: errorMessage,
      stack: errorStack,
      ...additionalData,
    }, requestId);
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<LoggerConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * 获取当前配置
   */
  getConfig(): LoggerConfig {
    return { ...this.config };
  }
}

/**
 * 默认 Label Studio 日志实例
 */
export const labelStudioLogger = new LabelStudioLogger();

/**
 * 创建自定义日志实例
 */
export const createLabelStudioLogger = (config: Partial<LoggerConfig>): LabelStudioLogger => {
  return new LabelStudioLogger(config);
};

export default labelStudioLogger;
