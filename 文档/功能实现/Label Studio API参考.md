# Label Studio iframe 集成 API 参考文档

## 概述

本文档详细描述了 Label Studio iframe 集成系统的所有 API 接口、类型定义和使用方法。

## 核心模块

### IframeManager

iframe 容器管理器，负责 Label Studio iframe 的生命周期管理。

#### 接口定义

```typescript
interface IframeManager {
  create(config: IframeConfig): Promise<HTMLIFrameElement>;
  destroy(): Promise<void>;
  refresh(): Promise<void>;
  getStatus(): IframeStatus;
  on(event: string, callback: Function): void;
  off(event: string, callback: Function): void;
}
```

#### 类型定义

```typescript
interface IframeConfig {
  url: string;                    // Label Studio URL
  projectId: string;              // 项目ID
  taskId: string;                 // 任务ID
  userId: string;                 // 用户ID
  token: string;                  // JWT token
  permissions: Permission[];      // 权限列表
  theme?: 'light' | 'dark';      // 主题
  fullscreen?: boolean;          // 全屏模式
}

enum IframeStatus {
  LOADING = 'loading',
  READY = 'ready',
  ERROR = 'error',
  DESTROYED = 'destroyed'
}
```

#### 使用示例

```typescript
import { IframeManager } from '@/services/iframe/IframeManager';

const manager = new IframeManager();

// 创建 iframe
const iframe = await manager.create({
  url: 'http://localhost:8080',
  projectId: 'project-123',
  taskId: 'task-456',
  userId: 'user-789',
  token: 'jwt-token',
  permissions: [
    { action: 'annotate', resource: 'task', allowed: true }
  ]
});

// 监听状态变化
manager.on('statusChanged', (status) => {
  console.log('iframe status:', status);
});

// 销毁 iframe
await manager.destroy();
```

### PostMessageBridge

PostMessage 通信桥梁，管理 iframe 与主窗口的通信。

#### 接口定义

```typescript
interface PostMessageBridge {
  send(message: Message): Promise<Response>;
  on(type: string, handler: MessageHandler): void;
  off(type: string, handler: MessageHandler): void;
  getStatus(): BridgeStatus;
  cleanup(): void;
}
```

#### 类型定义

```typescript
interface Message {
  id: string;                    // 消息ID
  type: string;                  // 消息类型
  payload: any;                  // 消息内容
  timestamp: number;             // 时间戳
  signature?: string;            // 签名
}

interface Response {
  id: string;                    // 响应ID
  success: boolean;              // 是否成功
  data?: any;                    // 响应数据
  error?: string;                // 错误信息
}

enum BridgeStatus {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  ERROR = 'error'
}
```

#### 使用示例

```typescript
import { PostMessageBridge } from '@/services/iframe/PostMessageBridge';

const bridge = new PostMessageBridge(iframe);

// 发送消息
const response = await bridge.send({
  id: 'msg-001',
  type: 'LOAD_TASK',
  payload: { taskId: 'task-123' },
  timestamp: Date.now()
});

// 监听消息
bridge.on('ANNOTATION_SAVED', (message) => {
  console.log('Annotation saved:', message.payload);
});
```

### ContextManager

权限和上下文管理器，管理标注上下文和权限信息。

#### 接口定义

```typescript
interface ContextManager {
  setContext(context: AnnotationContext): void;
  getContext(): AnnotationContext;
  checkPermission(action: string): boolean;
  updatePermissions(permissions: Permission[]): void;
  getEncryptedContext(): string;
}
```

#### 类型定义

```typescript
interface AnnotationContext {
  user: UserInfo;                // 用户信息
  project: ProjectInfo;          // 项目信息
  task: TaskInfo;                // 任务信息
  permissions: Permission[];     // 权限列表
  timestamp: number;             // 时间戳
}

interface Permission {
  action: string;                // 操作类型
  resource: string;              // 资源类型
  allowed: boolean;              // 是否允许
}
```

#### 使用示例

```typescript
import { ContextManager } from '@/services/iframe/ContextManager';

const contextManager = new ContextManager();

// 设置上下文
contextManager.setContext({
  user: { id: 'user-123', name: 'John Doe', role: 'annotator' },
  project: { id: 'project-456', name: 'Image Classification' },
  task: { id: 'task-789', name: 'Batch 1', status: 'pending' },
  permissions: [
    { action: 'annotate', resource: 'task', allowed: true },
    { action: 'delete', resource: 'annotation', allowed: false }
  ],
  timestamp: Date.now()
});

// 检查权限
if (contextManager.checkPermission('annotate')) {
  // 允许标注
}
```

### SyncManager

数据同步管理器，管理标注数据的同步。

#### 接口定义

```typescript
interface SyncManager {
  start(): void;
  stop(): void;
  sync(): Promise<SyncResult>;
  getStatus(): SyncStatus;
  on(event: string, callback: Function): void;
}
```

#### 类型定义

```typescript
interface SyncResult {
  success: boolean;              // 是否成功
  itemsSynced: number;           // 同步条目数
  itemsFailed: number;           // 失败条目数
  duration: number;              // 同步耗时
  errors?: Error[];              // 错误列表
}

enum SyncStatus {
  IDLE = 'idle',
  SYNCING = 'syncing',
  ERROR = 'error',
  PAUSED = 'paused'
}
```

#### 使用示例

```typescript
import { SyncManager } from '@/services/iframe/SyncManager';

const syncManager = new SyncManager();

// 启动自动同步
syncManager.start();

// 监听同步事件
syncManager.on('syncCompleted', (result) => {
  console.log(`Synced ${result.itemsSynced} items in ${result.duration}ms`);
});

// 手动同步
const result = await syncManager.sync();
```

### EventEmitter

事件处理器，处理标注相关的事件。

#### 接口定义

```typescript
interface EventEmitter {
  on(event: string, handler: EventHandler): void;
  once(event: string, handler: EventHandler): void;
  off(event: string, handler: EventHandler): void;
  emit(event: string, data: any): void;
  getHistory(event?: string): EventRecord[];
}
```

#### 类型定义

```typescript
interface EventRecord {
  event: string;                 // 事件名称
  data: any;                     // 事件数据
  timestamp: number;             // 时间戳
  source: 'iframe' | 'main';     // 事件源
}

enum AnnotationEvent {
  STARTED = 'annotation:started',
  UPDATED = 'annotation:updated',
  COMPLETED = 'annotation:completed',
  SAVED = 'annotation:saved',
  ERROR = 'annotation:error'
}
```

#### 使用示例

```typescript
import { EventEmitter, AnnotationEvent } from '@/services/iframe/EventEmitter';

const eventEmitter = new EventEmitter();

// 监听标注事件
eventEmitter.on(AnnotationEvent.COMPLETED, (data) => {
  console.log('Annotation completed:', data);
});

// 发射事件
eventEmitter.emit(AnnotationEvent.STARTED, {
  taskId: 'task-123',
  userId: 'user-456'
});
```

### UICoordinator

UI 协调器，协调 iframe 与主窗口的 UI 交互。

#### 接口定义

```typescript
interface UICoordinator {
  setFullscreen(enabled: boolean): void;
  resize(width: number, height: number): void;
  setLoading(loading: boolean): void;
  showError(message: string): void;
  hideNavigation(): void;
  showNavigation(): void;
}
```

#### 使用示例

```typescript
import { UICoordinator } from '@/services/iframe/UICoordinator';

const uiCoordinator = new UICoordinator();

// 设置全屏模式
uiCoordinator.setFullscreen(true);

// 调整大小
uiCoordinator.resize(1920, 1080);

// 显示加载状态
uiCoordinator.setLoading(true);
```

## 错误处理

### ErrorHandler

错误处理器，处理各种错误情况。

#### 接口定义

```typescript
interface ErrorHandler {
  handleError(error: Error, context?: any): void;
  getErrorHistory(): ErrorRecord[];
  clearErrorHistory(): void;
}
```

#### 错误类型

```typescript
enum ErrorType {
  IFRAME_LOAD_ERROR = 'iframe_load_error',
  COMMUNICATION_ERROR = 'communication_error',
  PERMISSION_ERROR = 'permission_error',
  SYNC_ERROR = 'sync_error',
  VALIDATION_ERROR = 'validation_error'
}
```

## 性能监控

### PerformanceMonitor

性能监控器，监控系统性能指标。

#### 接口定义

```typescript
interface PerformanceMonitor {
  startMonitoring(): void;
  stopMonitoring(): void;
  getMetrics(): PerformanceMetrics;
  on(event: string, callback: Function): void;
}
```

#### 性能指标

```typescript
interface PerformanceMetrics {
  loadTime: number;              // 加载时间
  memoryUsage: number;           // 内存使用量
  cpuUsage: number;              // CPU 使用率
  messageLatency: number;        // 消息延迟
  syncSpeed: number;             // 同步速度
}
```

## 安全性

### SecurityPolicyManager

安全策略管理器，管理安全策略和配置。

#### 接口定义

```typescript
interface SecurityPolicyManager {
  setPolicy(policy: SecurityPolicy): void;
  validateMessage(message: Message): boolean;
  encryptData(data: any): string;
  decryptData(encryptedData: string): any;
}
```

#### 安全策略

```typescript
interface SecurityPolicy {
  allowedOrigins: string[];      // 允许的来源
  requireSignature: boolean;     // 是否需要签名
  encryptionEnabled: boolean;    // 是否启用加密
  auditEnabled: boolean;         // 是否启用审计
}
```

## 配置选项

### 全局配置

```typescript
interface LabelStudioConfig {
  baseUrl: string;               // Label Studio 基础URL
  apiKey: string;                // API密钥
  timeout: number;               // 超时时间
  retryAttempts: number;         // 重试次数
  enableCache: boolean;          // 是否启用缓存
  enableMonitoring: boolean;     // 是否启用监控
  securityPolicy: SecurityPolicy; // 安全策略
}
```

### 环境变量

```bash
# Label Studio 配置
LABEL_STUDIO_URL=http://localhost:8080
LABEL_STUDIO_API_KEY=your-api-key

# 安全配置
IFRAME_ALLOWED_ORIGINS=http://localhost:3000,https://your-domain.com
IFRAME_REQUIRE_SIGNATURE=true
IFRAME_ENCRYPTION_ENABLED=true

# 性能配置
IFRAME_TIMEOUT=30000
IFRAME_RETRY_ATTEMPTS=3
IFRAME_ENABLE_CACHE=true
```

## 版本兼容性

| 版本 | Label Studio | React | TypeScript |
|------|-------------|-------|------------|
| 1.0.x | 1.8.x+ | 18.x+ | 4.9.x+ |

## 更新日志

### v1.0.0 (2026-01-05)
- 初始版本发布
- 支持基础 iframe 集成
- 支持 PostMessage 通信
- 支持权限控制和数据同步

---

**版本**: v1.0  
**更新日期**: 2026年1月5日